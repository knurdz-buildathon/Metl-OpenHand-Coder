"""Main orchestration pipeline that runs jobs end-to-end."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.database import async_session_factory
from src.models import JobStatus
from src.models.database import Job
from src.services.browser import BrowserInspector
from src.services.github import GitHubService
from src.services.openhands import OpenHandsRunner
from src.services.preview import PreviewBuilder

logger = structlog.get_logger(__name__)

LogCallback = Callable[[str], Coroutine[Any, Any, None]]


class RetryableError(Exception):
    """A transient error that should be retried."""


class FatalJobError(Exception):
    """An unrecoverable error that should abort the job."""


class Orchestrator:
    """Coordinates the full autonomous coding pipeline for a single job."""

    def __init__(self, log_callback: LogCallback | None = None):
        self.github = GitHubService()
        self.log_callback = log_callback
        self._job_id = ""

    async def _log(self, message: str) -> None:
        logger.info(message, job_id=self._job_id)
        if self.log_callback:
            await self.log_callback(message)

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    async def execute_job(self, job_id: str) -> None:
        """Run the full pipeline:

        1. Clone repository
        2. Generate / parse plan
        3. Run OpenHands to write code
        4. Build preview
        5. Browser inspection
        6. Fix issues loop (back to OpenHands)
        7. Push changes
        8. Completion report
        """
        self._job_id = job_id
        await self._log(f"Starting pipeline for job {job_id}")

        async with async_session_factory() as db:
            job = await self._get_job(db, job_id)
            if not job:
                raise FatalJobError(f"Job {job_id} not found")

            try:
                # Step 1 – Clone
                await self._set_status(db, job, JobStatus.CLONING)
                clone_path = f"/tmp/metl-jobs/{job_id}"
                branch_name = f"metl-agent-{str(job.id)[:8]}"
                await self._log("Cloning repository...")
                await self.github.clone_repo(job.github_url, clone_path)
                await self.github.create_branch(clone_path, branch_name)

                job.repo_clone_path = clone_path
                job.branch_name = branch_name
                await db.commit()

                # Step 2 – Planning
                await self._set_status(db, job, JobStatus.PLANNING)
                await self._log("Analysing plan...")

                # Step 3 – OpenHands execution
                await self._set_status(db, job, JobStatus.EXECUTING)
                await self._log("Starting OpenHands execution...")
                openhands = OpenHandsRunner(self._log)
                options = job.options or {}
                provider = options.get("llm_provider", "azure")
                model = options.get("llm_model", "gpt-4o")
                api_key = self._get_llm_key(provider)
                exit_code = await openhands.start_openhands_container(
                    str(job.id),
                    clone_path,
                    env_vars={
                        "LLM_API_KEY": api_key or "",
                        "LLM_MODEL": model,
                        "LLM_PROVIDER": provider,
                    },
                    options=options,
                )
                if exit_code != 0:
                    await self._log(f"OpenHands exited with non-zero code: {exit_code}")

                # Step 4 – Preview build
                await self._set_status(db, job, JobStatus.PREVIEW_BUILDING)
                await self._log("Building preview...")
                preview_builder = PreviewBuilder()
                preview = await preview_builder.build_preview(str(job.id), clone_path)
                if preview and preview.url:
                    job.preview_url = preview.url
                    await db.commit()

                # Step 5 – Browser inspection
                await self._set_status(db, job, JobStatus.BROWSER_TESTING)
                await self._log("Running browser inspection...")
                browser = BrowserInspector()
                report = await browser.inspect_preview(
                    preview_url=preview.url if preview else "",
                    job_id=str(job.id),
                    preview_id=str(preview.id) if preview else str(uuid.uuid4()),
                )

                # Step 6 – Fix issues loop
                iteration = 0
                max_iterations = settings.MAX_ITERATIONS
                while report and report.issues and iteration < max_iterations:
                    iteration += 1
                    await self._set_status(db, job, JobStatus.FIXING_ISSUES)
                    await self._log(f"Fixing issues – iteration {iteration}/{max_iterations}")
                    issues_text = "\n".join(
                        f"- [{i.get('severity', 'info')}] {i.get('category', 'general')}: {i.get('message', '')}"
                        for i in report.issues
                    )
                    await openhands.start_openhands_container(
                        str(job.id),
                        clone_path,
                        env_vars={
                            "LLM_API_KEY": api_key or "",
                            "LLM_MODEL": model,
                            "LLM_PROVIDER": provider,
                            "FIX_ISSUES": issues_text,
                        },
                        options=options,
                    )
                    await self._set_status(db, job, JobStatus.PREVIEW_BUILDING)
                    preview = await preview_builder.build_preview(str(job.id), clone_path)
                    if preview and preview.url:
                        job.preview_url = preview.url
                        await db.commit()
                    await self._set_status(db, job, JobStatus.BROWSER_TESTING)
                    report = await browser.inspect_preview(
                        preview_url=preview.url if preview else "",
                        job_id=str(job.id),
                        preview_id=str(preview.id) if preview else str(uuid.uuid4()),
                    )

                # Step 7 – Push changes
                await self._log("Pushing changes to remote...")
                await self.github.commit_and_push(clone_path, "Metl Agent: automated changes")

                # Step 8 – Completion
                final_status = JobStatus.COMPLETED if not report or not report.issues else JobStatus.PARTIAL_SUCCESS
                await self._set_status(db, job, final_status)
                await self._log(f"Job {job_id} completed with status: {final_status.value}")
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

            except FatalJobError:
                await self._set_status(db, job, JobStatus.FAILED)
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                raise
            except Exception as exc:
                logger.exception("Unhandled error during job execution", job_id=job_id)
                await self._set_status(db, job, JobStatus.FAILED)
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

    def _get_llm_key(self, provider: str) -> str | None:
        keys = {
            "openai": settings.LLM_OPENAI_API_KEY,
            "anthropic": settings.LLM_ANTHROPIC_API_KEY,
            "google": settings.LLM_GOOGLE_API_KEY,
            "mistral": settings.LLM_MISTRAL_API_KEY,
            "azure": settings.AZURE_AI_API_KEY,
        }
        return keys.get(provider)

    async def _get_job(self, db: AsyncSession, job_id: str) -> Job | None:
        result = await db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def _set_status(self, db: AsyncSession, job: Job, status: JobStatus) -> None:
        job.status = status.value
        job.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await self._log(f"Status updated -> {status.value}")