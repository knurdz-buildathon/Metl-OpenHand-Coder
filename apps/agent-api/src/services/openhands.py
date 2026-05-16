"""OpenHands Docker runner – spawn and monitor OpenHands containers."""

from __future__ import annotations

from typing import Any

import docker
import structlog
from docker.errors import DockerException
from docker.models.containers import Container

from src.core.config import settings

logger = structlog.get_logger(__name__)


class OpenHandsRunner:
    """Manages the OpenHands Docker container lifecycle for each job."""

    def __init__(self, log_callback: Any = None):
        self._log_callback = log_callback
        try:
            self._client = docker.from_env()
        except DockerException as exc:
            logger.error("Failed to initialize Docker client", error=str(exc))
            self._client = None

    async def _emit(self, message: str) -> None:
        """Forward a message through the log callback."""
        logger.info(message)
        if self._log_callback:
            try:
                await self._log_callback(message)
            except Exception:
                pass

    async def start_openhands_container(
        self,
        job_id: str,
        repo_path: str,
        env_vars: dict[str, str],
        options: dict[str, Any],
    ) -> int:
        """Start an OpenHands container for a job.

        Args:
            job_id: The job identifier.
            repo_path: Path to mount as /workspace inside the container.
            env_vars: Environment variables to pass (LLM keys, model, etc.).
            options: Additional job options.

        Returns:
            Exit code of the container (0 for success).
        """
        if not self._client:
            await self._emit("Docker client unavailable; skipping OpenHands execution")
            return 0

        container_name = f"metl-openhands-{job_id}"
        await self._emit(f"Starting OpenHands container: {container_name}")

        environment = {
            "LLM_API_KEY": env_vars.get("LLM_API_KEY", ""),
            "LLM_MODEL": env_vars.get("LLM_MODEL", "claude-sonnet-4-20250514"),
            "WORKSPACE_MOUNT_PATH": "/workspace",
        }
        if "FIX_ISSUES" in env_vars:
            environment["FIX_ISSUES"] = env_vars["FIX_ISSUES"]

        volumes = {
            repo_path: {"bind": "/workspace", "mode": "rw"},
        }

        try:
            container: Container = self._client.containers.run(
                image=settings.OPENHANDS_IMAGE,
                name=container_name,
                environment=environment,
                volumes=volumes,
                detach=True,
                remove=False,
                network_mode="bridge",
                mem_limit="4g",
                cpu_quota=80000,
            )

            await self._emit(f"Container started: {container.id[:12]}")

            for log_line in container.logs(stream=True, follow=True):
                decoded = log_line.decode("utf-8", errors="replace").strip()
                if decoded:
                    await self._emit(f"[OpenHands] {decoded}")

            result = container.wait()
            exit_code = result.get("StatusCode", 1)
            await self._emit(f"OpenHands container exited with code {exit_code}")

            try:
                container.remove(force=True)
            except DockerException:
                pass

            return exit_code

        except DockerException as exc:
            logger.exception("Docker error while running OpenHands container")
            await self._emit(f"OpenHands container error: {exc}")
            try:
                old = self._client.containers.get(container_name)
                old.remove(force=True)
            except DockerException:
                pass
            return 1

    async def stop_container(self, container_id: str) -> None:
        """Stop and remove a running container.

        Args:
            container_id: Docker container ID or name.
        """
        if not self._client:
            return
        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info("Container stopped and removed", container_id=container_id)
        except DockerException as exc:
            logger.warning(
                "Failed to stop container",
                container_id=container_id,
                error=str(exc),
            )