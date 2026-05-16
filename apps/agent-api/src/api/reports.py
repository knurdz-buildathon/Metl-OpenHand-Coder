"""Report and screenshot retrieval API endpoints."""

from __future__ import annotations

import os
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.models import CompletionReportModel
from src.models.database import BrowserReport, Job

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/jobs", tags=["reports"])


def _screenshot_path(job_id: str, screenshot_id: str) -> str:
    return os.path.join(settings.ARTIFACTS_DIR, "jobs", job_id, "screenshots", screenshot_id)


@router.get("/{job_id}/reports/browser")
async def get_browser_reports(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> list:
    result = await db.execute(
        select(BrowserReport)
        .where(BrowserReport.job_id == job_id)
        .order_by(BrowserReport.created_at.desc())
    )
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "preview_id": r.preview_id,
            "status": r.status,
            "summary": r.summary,
            "issues": r.issues,
            "console_errors": r.console_errors,
            "screenshots": r.screenshots,
            "performance_metrics": r.performance_metrics,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@router.get("/{job_id}/reports/completion")
async def get_completion_report(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    br_result = await db.execute(
        select(BrowserReport)
        .where(BrowserReport.job_id == job_id)
        .order_by(BrowserReport.created_at.desc())
    )
    browser_reports = br_result.scalars().all()

    duration_seconds = 0.0
    if job.completed_at and job.created_at:
        duration_seconds = (job.completed_at - job.created_at).total_seconds()

    browser_summary = "No issues found"
    screenshots = []
    if browser_reports:
        last_report = browser_reports[0]
        browser_summary = last_report.summary or "No issues found"
        screenshots = last_report.screenshots if isinstance(last_report.screenshots, list) else []

    return {
        "job_id": job.id,
        "status": job.status or "unknown",
        "summary": f"Job completed with status: {job.status}",
        "changes": [],
        "preview_url": job.preview_url,
        "screenshots": screenshots,
        "browser_report_summary": browser_summary,
        "resource_summary": None,
        "artifacts_local_path": f"{settings.ARTIFACTS_DIR}/jobs/{job_id}",
        "duration_seconds": duration_seconds,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/{job_id}/screenshots/{screenshot_id}")
async def get_screenshot(
    job_id: str,
    screenshot_id: str,
):
    path = _screenshot_path(job_id, screenshot_id)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path, media_type="image/png")