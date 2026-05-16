"""v0 API integration – optional, skips gracefully when not configured."""

from __future__ import annotations

from typing import Any, Optional

import httpx
import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/v0", tags=["v0"])


class V0GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    project_context: Optional[dict[str, Any]] = None
    framework: str = "react"
    style_library: str = "tailwind"


class V0GenerateResponse(BaseModel):
    code: str = ""
    files: list[dict[str, str]] = Field(default_factory=list)
    explanation: Optional[str] = None
    message: str = ""


@router.post("/generate", response_model=V0GenerateResponse)
async def generate_code(request: V0GenerateRequest) -> V0GenerateResponse:
    """Generate frontend code using the v0 API, if configured."""
    if not settings.V0_API_URL or not settings.V0_API_KEY:
        return V0GenerateResponse(
            message="v0 integration is not configured. Set V0_API_URL and V0_API_KEY in .env to enable.",
        )

    payload = {
        "prompt": request.prompt,
        "project_context": request.project_context,
        "framework": request.framework,
        "style_library": request.style_library,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.V0_API_URL.rstrip('/')}/generate",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.V0_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            logger.info("v0 generation successful")
            return V0GenerateResponse(**data)
    except Exception as exc:
        logger.exception("v0 generation failed")
        return V0GenerateResponse(message=f"v0 generation failed: {str(exc)}")