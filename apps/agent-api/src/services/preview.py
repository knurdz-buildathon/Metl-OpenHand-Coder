"""Preview Builder service – builds and serves frontend previews in ephemeral containers."""

from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import docker
import structlog

from src.core.config import settings
from src.models import PreviewBuildModel, PreviewStatus

logger = structlog.get_logger(__name__)

FRAMEWORK_DETECTORS = {
    "next": ["next.config.js", "next.config.ts", "next.config.mjs"],
    "vite": ["vite.config.js", "vite.config.ts"],
    "react-scripts": ["react-scripts"],
    "vue-cli": ["vue.config.js"],
}


class PreviewBuilder:
    """Builds and serves frontend previews in ephemeral Docker containers."""

    def __init__(self):
        self.docker_client = docker.from_env()
        self._used_ports: set[int] = set()

    async def detect_framework(self, repo_path: str) -> str:
        """Detect the frontend framework from package.json."""
        package_json_path = os.path.join(repo_path, "package.json")
        if not os.path.exists(package_json_path):
            if os.path.isfile(os.path.join(repo_path, "index.html")):
                return "static"
            return "unknown"

        try:
            with open(package_json_path) as f:
                pkg = json.load(f)

            dependencies = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "next" in dependencies:
                return "next"
            if "vite" in dependencies:
                return "vite"
            if "react-scripts" in dependencies:
                return "react-scripts"
            if "@vue/cli-service" in dependencies:
                return "vue-cli"

            return "static"
        except (json.JSONDecodeError, KeyError):
            return "unknown"

    async def build_preview(self, job_id: str, repo_path: str) -> PreviewBuildModel | None:
        """Build a preview of the frontend in an ephemeral Docker container.

        Args:
            job_id: The job identifier.
            repo_path: Local path to the repository.

        Returns:
            PreviewBuildModel with preview details, or None if build failed.
        """
        framework = await self.detect_framework(repo_path)
        logger.info("Detected framework", job_id=job_id, framework=framework, path=repo_path)

        preview = PreviewBuildModel(
            id=uuid.uuid4(),
            job_id=uuid.UUID(job_id),
            status=PreviewStatus.BUILDING,
            framework=framework,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.PREVIEW_PORT_RANGE_START or 120),
        )

        port = await self._assign_port()

        try:
            container = self.docker_client.containers.run(
                image=settings.PREVIEW_NGINX_IMAGE,
                command="nginx -g 'daemon off;'",
                volumes={
                    os.path.abspath(repo_path): {"bind": "/workspace", "mode": "ro"},
                },
                ports={80: port},
                environment={
                    "METL_JOB_ID": job_id,
                    "PORT": "80",
                },
                detach=True,
                remove=True,
                labels={"metl-job-id": job_id, "metl-type": "preview"},
            )

            preview.container_id = container.id
            preview.port = port
            preview.url = f"http://{settings.PREVIEW_BASE_DOMAIN}:{port}"
            preview.status = PreviewStatus.READY

            logger.info(
                "Preview built successfully",
                job_id=job_id,
                url=preview.url,
                container_id=container.id,
            )

        except Exception as exc:
            logger.exception("Failed to build preview", job_id=job_id)
            preview.status = PreviewStatus.FAILED
            preview.build_log = str(exc)
            return preview

        return preview

    async def _assign_port(self) -> int:
        """Assign an available port from the preview port range."""
        start = settings.PREVIEW_PORT_RANGE_START
        end = settings.PREVIEW_PORT_RANGE_END

        available = list(set(range(start, end + 1)) - self._used_ports)
        if not available:
            # Cleanup old entries and retry
            self._used_ports.clear()
            available = list(range(start, end + 1))

        port = random.choice(available)
        self._used_ports.add(port)
        return port

    async def cleanup_preview(self, container_id: str) -> None:
        """Stop and remove a preview container."""
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
            logger.info("Preview container cleaned up", container_id=container_id)
        except docker.errors.NotFound:
            logger.warning("Preview container not found for cleanup", container_id=container_id)
        except Exception as exc:
            logger.exception("Failed to cleanup preview", container_id=container_id)