#!/usr/bin/env python3
"""
Metl OpenHands Agent Wrapper

Wraps OpenHands execution for the Metl platform. Reads job configuration,
starts an OpenHands agent session, streams progress to Redis, handles
resource requests, and writes completion status.

Environment variables expected:
    METL_REDIS_URL        - Redis connection string
    METL_JOB_ID           - Unique job identifier
    METL_API_URL          - Metl API base URL
    METL_API_KEY          - Metl API authentication key
    LLM_MODEL             - LLM model name for OpenHands
    LLM_API_KEY           - LLM API key for OpenHands
    MAX_ITERATIONS        - Max iterations for OpenHands (default: 10)
    TASK_TIMEOUT          - Task timeout in seconds (default: 3600)
"""

import json
import os
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread

import redis
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_DIR = Path("/workspace")
METL_DIR = WORKSPACE_DIR / ".metl"
TASK_CONFIG_PATH = METL_DIR / "task.json"
ENV_CONFIG_PATH = METL_DIR / "env.json"
STATUS_FILE_PATH = METL_DIR / "status.json"
PROMPT_FILE_PATH = METL_DIR / "prompt.txt"
RESOURCE_REQUESTS_DIR = METL_DIR / "resource-requests"

LOG_KEY = "metl:openhands:log:{job_id}"
STATUS_KEY = "metl:openhands:status:{job_id}"

DEFAULT_TIMEOUT = 3600
DEFAULT_MAX_ITERATIONS = 10

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path, default=None):
    """Load a JSON file, returning *default* if the file does not exist."""
    if not path.exists():
        return default
    with open(path, "r") as fh:
        return json.load(fh)


def save_json(path: Path, data: dict):
    """Atomically write a JSON file."""
    tmp = path.with_suffix(".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2)
    tmp.rename(path)


# ---------------------------------------------------------------------------
# Redis publisher
# ---------------------------------------------------------------------------


class RedisPublisher:
    """Publishes structured log/status entries to Redis streams or pubsub."""

    def __init__(self, redis_url: str, job_id: str):
        self.job_id = job_id
        self.redis_url = redis_url
        self.client: redis.Redis | None = None

    # ------------------------------------------------------------------
    def connect(self):
        """Establish Redis connection."""
        try:
            self.client = redis.Redis.from_url(
                self.redis_url, decode_responses=True, socket_timeout=5
            )
            self.client.ping()
        except Exception as exc:
            print(f"[metl-wrapper] Redis connection failed: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    def publish_log(self, level: str, message: str, **extra):
        """Push a log entry onto a Redis list."""
        if self.client is None:
            return
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "job_id": self.job_id,
            **extra,
        }
        try:
            key = LOG_KEY.format(job_id=self.job_id)
            self.client.rpush(key, json.dumps(entry))
            # Keep only the last 10K entries
            self.client.ltrim(key, -10000, -1)
        except Exception as exc:
            print(f"[metl-wrapper] Redis publish error: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    def publish_status(self, status: str, **extra):
        """Update the Redis status hash for this job."""
        if self.client is None:
            return
        entry = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        try:
            key = STATUS_KEY.format(job_id=self.job_id)
            self.client.hset(key, mapping=entry)
            # Expire in 7 days
            self.client.expire(key, 604800)
        except Exception as exc:
            print(f"[metl-wrapper] Redis status error: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    def disconnect(self):
        """Cleanly close the Redis connection."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Resource request handler
# ---------------------------------------------------------------------------


class ResourceRequestHandler:
    """Monitors resource-requests directory and signals the Metl API."""

    def __init__(self, api_url: str, api_key: str, job_id: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.job_id = job_id
        self._seen: set[str] = set()
        self._stop_event = Event()

    # ------------------------------------------------------------------
    def start(self):
        """Start a background watcher thread."""
        self._stop_event.clear()
        thread = Thread(target=self._watch_loop, daemon=True)
        thread.start()
        return thread

    # ------------------------------------------------------------------
    def stop(self):
        """Signal the watcher thread to exit."""
        self._stop_event.set()

    # ------------------------------------------------------------------
    def _watch_loop(self):
        RESOURCE_REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
        while not self._stop_event.is_set():
            self._scan()
            self._stop_event.wait(timeout=5)

    # ------------------------------------------------------------------
    def _scan(self):
        for path in sorted(RESOURCE_REQUESTS_DIR.glob("*.json")):
            name = path.name
            if name in self._seen:
                continue
            self._seen.add(name)
            try:
                request = load_json(path)
                self._signal_api(request)
            except Exception as exc:
                print(f"[metl-wrapper] Resource-request error: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    def _signal_api(self, request: dict):
        """POST the resource request to the Metl API."""
        url = f"{self.api_url}/v1/jobs/{self.job_id}/resource-requests"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(url, json=request, headers=headers, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[metl-wrapper] API signal failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# OpenHands runner
# ---------------------------------------------------------------------------


class OpenHandsRunner:
    """Manages OpenHands execution (SDK or subprocess fallback)."""

    def __init__(
        self,
        prompt: str,
        workspace: str,
        model: str,
        api_key: str,
        max_iterations: int,
        redis_pub: RedisPublisher,
    ):
        self.prompt = prompt
        self.workspace = workspace
        self.model = model
        self.api_key = api_key
        self.max_iterations = max_iterations
        self.redis_pub = redis_pub
        self.process: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    def run(self) -> int:
        """Execute OpenHands. Returns exit code."""
        if self._try_sdk_run():
            return 0
        return self._subprocess_run()

    # ------------------------------------------------------------------
    def _try_sdk_run(self) -> bool:
        """Attempt to use the openhands SDK. Returns True on success."""
        try:
            import openhands  # noqa: F401
        except ImportError:
            return False

        try:
            self.redis_pub.publish_log("info", "Running OpenHands via SDK")

            # This is a best-effort SDK integration. The exact API surface
            # depends on the installed openhands package version.
            from openhands.core.config import AppConfig
            from openhands.core.main import run_controller

            config = AppConfig(
                workspace=self.workspace,
                llm_model=self.model,
                llm_api_key=self.api_key,
                max_iterations=self.max_iterations,
            )

            self.redis_pub.publish_log("info", "OpenHands controller starting")

            # run_controller is assumed to be a blocking call that streams
            # events; we wrap it with a progress reporter.
            run_controller(
                config=config,
                task=self.prompt,
                on_event=lambda event: self._on_sdk_event(event),
            )

            self.redis_pub.publish_log("info", "OpenHands SDK run completed")
            return True
        except Exception as exc:
            self.redis_pub.publish_log("warn", f"SDK run failed, falling back: {exc}")
            return False

    # ------------------------------------------------------------------
    def _on_sdk_event(self, event):
        """Handle streaming events from the OpenHands SDK."""
        event_type = getattr(event, "event_type", getattr(event, "type", "unknown"))
        message = getattr(event, "message", str(event))
        self.redis_pub.publish_log("info", message, event_type=event_type)

    # ------------------------------------------------------------------
    def _subprocess_run(self) -> int:
        """Run OpenHands as a subprocess."""
        cmd = [
            sys.executable,
            "-m",
            "openhands.core.main",
            "-t",
            self.prompt,
            "-f",
            self.workspace,
            "--model",
            self.model,
            "--api-key",
            self.api_key,
            "--max-iterations",
            str(self.max_iterations),
        ]

        self.redis_pub.publish_log("info", f"Running: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ},
        )

        # Stream output line-by-line to Redis
        for line in self.process.stdout:
            line = line.strip()
            if line:
                self.redis_pub.publish_log("info", line, source="openhands")

        return self.process.wait()

    # ------------------------------------------------------------------
    def terminate(self):
        """Attempt graceful termination of the subprocess."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


# ---------------------------------------------------------------------------
# Signal handlers
# ---------------------------------------------------------------------------


class SignalHandler:
    """Handles SIGTERM/SIGINT to gracefully shut down the runner."""

    def __init__(self, runner: OpenHandsRunner, redis_pub: RedisPublisher):
        self.runner = runner
        self.redis_pub = redis_pub
        self._original_handlers: dict = {}

    # ------------------------------------------------------------------
    def register(self):
        self._original_handlers[signal.SIGTERM] = signal.signal(
            signal.SIGTERM, self._handle
        )
        self._original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT, self._handle
        )

    # ------------------------------------------------------------------
    def _handle(self, signum, frame):
        self.redis_pub.publish_log("warn", f"Received signal {signum}, shutting down")
        self.runner.terminate()
        # Restore original handlers so a second signal kills immediately
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)


# ---------------------------------------------------------------------------
# Status writer
# ---------------------------------------------------------------------------


def write_completion_status(
    exit_code: int,
    start_time: float,
    redis_pub: RedisPublisher,
):
    """Write the final status JSON to disk and Redis."""
    elapsed = time.time() - start_time
    status = {
        "job_id": os.environ.get("METL_JOB_ID", "unknown"),
        "status": "completed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "duration_seconds": round(elapsed, 2),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    save_json(STATUS_FILE_PATH, status)
    redis_pub.publish_status(status["status"], duration=elapsed, exit_code=exit_code)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    start_time = time.time()
    exit_code = 1

    # --- load configuration -----------------------------------------------
    job_id = os.environ.get("METL_JOB_ID", "unknown")
    redis_url = os.environ.get("METL_REDIS_URL", "redis://localhost:6379")
    api_url = os.environ.get("METL_API_URL", "http://localhost:8080")
    api_key = os.environ.get("METL_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-4o")
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    max_iterations = int(os.environ.get("MAX_ITERATIONS", DEFAULT_MAX_ITERATIONS))
    timeout = int(os.environ.get("TASK_TIMEOUT", DEFAULT_TIMEOUT))

    # --- Redis ------------------------------------------------------------
    redis_pub = RedisPublisher(redis_url, job_id)
    redis_pub.connect()
    redis_pub.publish_status("starting")
    redis_pub.publish_log("info", f"Metl OpenHands wrapper started (job={job_id})")

    try:
        # --- load env overrides -------------------------------------------
        if ENV_CONFIG_PATH.exists():
            env_overrides = load_json(ENV_CONFIG_PATH, {})
            if isinstance(env_overrides, dict):
                for key, val in env_overrides.items():
                    os.environ[str(key)] = str(val)
            redis_pub.publish_log("info", "Loaded env.json overrides")

        # --- load task config ---------------------------------------------
        task_config = load_json(TASK_CONFIG_PATH, {})

        prompt = ""
        if PROMPT_FILE_PATH.exists():
            prompt = PROMPT_FILE_PATH.read_text().strip()
        if not prompt:
            prompt = task_config.get("prompt", "") or os.environ.get("METL_PROMPT", "")

        if not prompt:
            redis_pub.publish_log("error", "No prompt found — aborting")
            write_completion_status(1, start_time, redis_pub)
            return 1

        # --- resource request watcher -------------------------------------
        resource_handler = ResourceRequestHandler(api_url, api_key, job_id)
        watcher_thread = resource_handler.start()

        # --- OpenHands runner ---------------------------------------------
        runner = OpenHandsRunner(
            prompt=prompt,
            workspace=str(WORKSPACE_DIR),
            model=model,
            api_key=llm_api_key,
            max_iterations=max_iterations,
            redis_pub=redis_pub,
        )

        signal_handler = SignalHandler(runner, redis_pub)
        signal_handler.register()

        redis_pub.publish_status("running")
        redis_pub.publish_log("info", "Starting OpenHands execution")

        # Run with a timeout (Python-level fallback)
        run_completed = Event()
        run_result = {"exit_code": -1}

        def _run():
            try:
                run_result["exit_code"] = runner.run()
            except Exception as exc:
                redis_pub.publish_log(
                    "error", f"Runner crashed: {exc}", traceback=traceback.format_exc()
                )
                run_result["exit_code"] = 1
            finally:
                run_completed.set()

        run_thread = Thread(target=_run, daemon=True)
        run_thread.start()

        finished = run_completed.wait(timeout=timeout)
        if not finished:
            redis_pub.publish_log("error", f"Task timed out after {timeout}s")
            runner.terminate()
            run_completed.wait(timeout=30)

        exit_code = run_result["exit_code"]

        # --- cleanup ------------------------------------------------------
        resource_handler.stop()
        watcher_thread.join(timeout=5)

    except Exception as exc:
        redis_pub.publish_log(
            "error", f"Fatal error: {exc}", traceback=traceback.format_exc()
        )
        exit_code = 1
    finally:
        write_completion_status(exit_code, start_time, redis_pub)
        redis_pub.publish_log("info", f"Wrapper exiting (exit_code={exit_code})")
        redis_pub.disconnect()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())