"""Job management API endpoints – CRUD + real-time log streaming."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.orchestrator import Orchestrator
from src.models import CreateJobRequest, JobResponse, JobStatus
from src.models.database import Job

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])

# In-memory log channels keyed by job_id
_log_channels: dict[str, asyncio.Queue[str]] = {}

# In-memory active WebSocket connections per job
_active_subscribers: dict[str, list[WebSocket]] = {}


async def _broadcast_log(job_id: str, message: str) -> None:
    """Push a log line to all WebSocket subscribers for a job."""
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = json.dumps({"timestamp": timestamp, "message": message})
    if job_id in _active_subscribers:
        disconnected = []
        for ws in _active_subscribers[job_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            _active_subscribers[job_id].remove(ws)


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Job:
    """Create a new coding job and enqueue it for execution."""
    job = Job(
        id=uuid.uuid4(),
        status=JobStatus.PENDING.value,
        github_url=request.github_url,
        plan_md_url=request.plan_md_url,
        prompt=request.prompt,
        options=request.options.model_dump(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info("Job created", job_id=str(job.id))

    # Enqueue background execution
    orchestrator = Orchestrator(log_callback=lambda msg: _broadcast_log(str(job.id), msg))
    background_tasks.add_task(orchestrator.execute_job, str(job.id))

    return job


@router.get("", response_model=dict)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List jobs with pagination and optional status filter."""
    query = select(Job)
    count_query = select(func.count(Job.id))

    if status:
        query = query.where(Job.status == status.value)
        count_query = count_query.where(Job.status == status.value)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "items": [JobResponse.model_validate(j) for j in jobs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Job:
    """Retrieve details for a single job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", response_model=dict)
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a running or pending job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value):
        raise HTTPException(status_code=409, detail="Job is already in a terminal state")

    job.status = JobStatus.CANCELLED.value
    job.completed_at = datetime.now(timezone.utc)
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("Job cancelled", job_id=str(job.id))
    return {"status": "cancelled", "job_id": str(job.id)}


@router.websocket("/{job_id}/logs")
async def stream_job_logs(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint to stream real-time logs for a running job."""
    await websocket.accept()

    if job_id not in _active_subscribers:
        _active_subscribers[job_id] = []
    _active_subscribers[job_id].append(websocket)

    try:
        while True:
            # Keep the connection alive; messages are pushed via _broadcast_log
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        if job_id in _active_subscribers and websocket in _active_subscribers[job_id]:
            _active_subscribers[job_id].remove(websocket)