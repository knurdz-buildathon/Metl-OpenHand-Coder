"""Resource Catalog & Manager – handles resource requests to the control panel."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from src.core.config import settings
from src.models import (
    ResourceItem,
    ResourceRequestModel,
    ResourceStatus,
    ResourceTier,
    ResourceType,
)

logger = structlog.get_logger(__name__)


class ResourceCatalog:
    """Catalog of available resource types and their metadata."""

    RESOURCES = {
        ResourceType.POSTGRESQL: {
            "name": "PostgreSQL Database",
            "env_prefix": "DATABASE_URL",
            "env_format": "postgresql://{user}:{password}@{host}:{port}/{name}",
            "tiers": {
                ResourceTier.SMALL: {"connections": 20, "storage_gb": 10},
                ResourceTier.MEDIUM: {"connections": 100, "storage_gb": 50},
                ResourceTier.LARGE: {"connections": 500, "storage_gb": 200},
            },
        },
        ResourceType.REDIS: {
            "name": "Redis Cache",
            "env_prefix": "REDIS_URL",
            "env_format": "redis://{host}:{port}/{db}",
            "tiers": {
                ResourceTier.SMALL: {"memory_mb": 256},
                ResourceTier.MEDIUM: {"memory_mb": 1024},
                ResourceTier.LARGE: {"memory_mb": 4096},
            },
        },
        ResourceType.S3_COMPATIBLE: {
            "name": "S3-Compatible Storage",
            "env_prefix": "S3",
            "env_format": "s3://{endpoint}/{bucket}",
            "env_vars": ["S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET", "S3_REGION"],
            "tiers": {
                ResourceTier.SMALL: {"storage_gb": 5},
                ResourceTier.MEDIUM: {"storage_gb": 50},
                ResourceTier.LARGE: {"storage_gb": 500},
            },
        },
        ResourceType.SMTP: {
            "name": "SMTP Email Service",
            "env_prefix": "SMTP",
            "env_vars": ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"],
            "tiers": {
                ResourceTier.SMALL: {"daily_limit": 100},
                ResourceTier.MEDIUM: {"daily_limit": 1000},
                ResourceTier.LARGE: {"daily_limit": 10000},
            },
        },
    }

    def get_resource_info(self, resource_type: ResourceType) -> dict | None:
        """Get metadata for a resource type."""
        return self.RESOURCES.get(resource_type)

    def list_available_types(self) -> list[dict]:
        """List all available resource types."""
        return [
            {
                "type": rt.value,
                "name": info["name"],
                "tiers": [t.value for t in info["tiers"]],
            }
            for rt, info in self.RESOURCES.items()
        ]


class ResourceManager:
    """Manages resource requests between the agent and control panel."""

    def __init__(self):
        self.catalog = ResourceCatalog()

    async def request_resources(
        self,
        job_id: str,
        requested_items: list[ResourceItem],
    ) -> ResourceRequestModel:
        """Send a resource request to the control panel.

        Args:
            job_id: The job requesting resources.
            requested_items: List of resources needed.

        Returns:
            ResourceRequestModel with status.
        """
        request_model = ResourceRequestModel(
            job_id=job_id,
            requested=requested_items,
            status=ResourceStatus.PENDING,
        )

        if not settings.CONTROL_PANEL_WEBHOOK_URL:
            logger.warning("No control panel webhook URL configured, skipping resource request")
            request_model.status = ResourceStatus.FAILED
            return request_model

        payload = {
            "job_id": job_id,
            "requested": [
                {
                    "type": item.type.value,
                    "tier": item.tier.value,
                    "region": item.region,
                    "name": item.name,
                }
                for item in requested_items
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.CONTROL_PANEL_WEBHOOK_URL}/resource-request",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code in (200, 201, 202):
                    data = resp.json()
                    request_model.status = ResourceStatus.APPROVED
                    request_model.config = data.get("config", {})
                    request_model.env_vars = self._format_env_vars(requested_items, data)
                    request_model.resolved_at = datetime.now(timezone.utc)
                    logger.info("Resources approved", job_id=job_id)
                else:
                    request_model.status = ResourceStatus.FAILED
                    logger.warning("Resource request denied", job_id=job_id, status_code=resp.status_code)

        except Exception as exc:
            logger.exception("Failed to request resources", job_id=job_id)
            request_model.status = ResourceStatus.FAILED

        return request_model

    def _format_env_vars(
        self,
        items: list[ResourceItem],
        response_data: dict[str, Any],
    ) -> dict[str, str]:
        """Format environment variables from the control panel response.

        Args:
            items: The requested resource items.
            response_data: The response from the control panel.

        Returns:
            Dictionary of environment variable names to values.
        """
        env_vars: dict[str, str] = {}

        resources_config = response_data.get("resources", {})

        for item in items:
            resource_info = self.catalog.get_resource_info(item.type)
            if not resource_info:
                continue

            resource_data = resources_config.get(item.type.value, {})
            if not resource_data:
                continue

            if "env_vars" in resource_info:
                for env_key in resource_info["env_vars"]:
                    value = resource_data.get(env_key.lower(), "")
                    if value:
                        env_vars[env_key] = str(value)
            elif "env_format" in resource_info:
                try:
                    url = resource_info["env_format"].format(**resource_data)
                    env_vars[resource_info["env_prefix"]] = url
                except KeyError:
                    env_vars[resource_info["env_prefix"]] = json.dumps(resource_data)

        return env_vars