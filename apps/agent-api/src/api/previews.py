"""Preview management API endpoints."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.config import settings
from src.models import PreviewBuildModel, PreviewStatus
from src.models.database import Job, PreviewBuild

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/jobs", tags=["previews"])

_preview_log_subscribers: dict[str, list[WebSocket]] = {}


async def _broadcast_preview_log(preview_id: str, message: str) -> None:
    """Push a build log line to all WebSocket subscribers for a preview."""
    payload = json.dumps({"message": message})
    if preview_id in _preview_log_subscribers:
        disconnected = []
        for ws in _preview_log_subscribers[preview_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            _preview_log_subscribers[preview_id].remove(ws)


@router.get("/{job_id}/preview", response_model=PreviewBuildModel)
async def get_preview_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PreviewBuild:
    """Get the preview build status for a job."""
    # Load the latest preview for this job
    result = await db.execute(
        select(PreviewBuild)
        .where(PreviewBuild.job_id == job_id)
        .order_by(PreviewBuild.created_at.desc())
        .limit(1)
    )
    preview = result.scalar_one_or_none()
    if not preview:
        raise HTTPException(status_code=404, detail="No preview found for this job")
    return preview


@router.websocket("/{job_id}/preview/stream")
async def stream_preview_logs(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint to stream real-time preview build logs."""
    await websocket.accept()

    # Use job_id as a proxy for the preview log channel
    channel_key = f"preview-{job_id}"
    if channel_key not in _preview_log_subscribers:
        _preview_log_subscribers[channel_key] = []
    _preview_log_subscribers[channel_key].append(websocket)

    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        if channel_key in _preview_log_subscribers and websocket in _preview_log_subscribers[channel_key]:
            _preview_log_subscribers[channel_key].remove(websocket)