"""Browser inspection service – screenshot capture, console monitoring, and accessibility checks."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import structlog
from playwright.async_api import async_playwright

from src.core.config import settings

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class ConsoleEntry:
    def __init__(self, level: str, message: str, source: str = "", line: int = 0):
        self.level = level
        self.message = message
        self.source = source
        self.line = line


class Issue:
    def __init__(self, severity: str = "info", category: str = "general", message: str = "", element_selector: str = ""):
        self.severity = severity
        self.category = category
        self.message = message
        self.element_selector = element_selector


class PerformanceMetrics:
    def __init__(self, load_time_ms: int = 0, dom_content_loaded_ms: int = 0, first_paint_ms: int = 0, first_contentful_paint_ms: int = 0):
        self.load_time_ms = load_time_ms
        self.dom_content_loaded_ms = dom_content_loaded_ms
        self.first_paint_ms = first_paint_ms
        self.first_contentful_paint_ms = first_contentful_paint_ms


class ScreenshotInfo:
    def __init__(self, type: str = "", url: str = "", path: str = "", width: int = 0, height: int = 0):
        self.type = type
        self.url = url
        self.path = path
        self.width = width
        self.height = height


class BrowserReportModel:
    def __init__(self, job_id: str = "", preview_id: str = "", status: str = "passed", summary: str = ""):
        self.job_id = job_id
        self.preview_id = preview_id
        self.status = status
        self.summary = summary
        self.issues: list = []
        self.console_errors: list = []
        self.screenshots: list = []
        self.performance_metrics = PerformanceMetrics()


class BrowserInspector:
    """Inspects frontend previews using headless Chromium via Playwright."""

    async def inspect_preview(
        self, preview_url: str, job_id: str, preview_id: str
    ) -> Optional[BrowserReportModel]:
        if not preview_url:
            logger.warning("No preview URL for browser inspection", job_id=job_id)
            return None

        report = BrowserReportModel(job_id=job_id, preview_id=preview_id, status="passed", summary="")
        console_messages: list[ConsoleEntry] = []
        issues: list[Issue] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(viewport={"width": 1280, "height": 720})
                page = await context.new_page()

                page.on("console", lambda msg: console_messages.append(ConsoleEntry(level=msg.type, message=msg.text)))
                page.on("pageerror", lambda err: issues.append(Issue(severity="error", category="javascript", message=str(err))))

                start_time = datetime.now(timezone.utc)
                await page.goto(preview_url, wait_until="networkidle", timeout=30000)
                load_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                metrics = PerformanceMetrics(load_time_ms=int(load_time))

                # Capture and save screenshots to local disk
                screenshot_dir = os.path.join(settings.ARTIFACTS_DIR, "jobs", job_id, "screenshots")
                os.makedirs(screenshot_dir, exist_ok=True)

                full_page_bytes = await page.screenshot(full_page=True)
                viewport_bytes = await page.screenshot(full_page=False)

                full_page_id = f"{uuid.uuid4()}.png"
                viewport_id = f"{uuid.uuid4()}.png"

                with open(os.path.join(screenshot_dir, full_page_id), "wb") as f:
                    f.write(full_page_bytes)
                with open(os.path.join(screenshot_dir, viewport_id), "wb") as f:
                    f.write(viewport_bytes)

                screenshots = [
                    ScreenshotInfo(
                        type="fullpage",
                        url=f"/v1/jobs/{job_id}/screenshots/{full_page_id}",
                        path=f"jobs/{job_id}/screenshots/{full_page_id}",
                        width=1280,
                        height=720,
                    ),
                    ScreenshotInfo(
                        type="viewport",
                        url=f"/v1/jobs/{job_id}/screenshots/{viewport_id}",
                        path=f"jobs/{job_id}/screenshots/{viewport_id}",
                        width=1280,
                        height=720,
                    ),
                ]

                # Accessibility checks
                a11y_issues = await self._check_accessibility(page)
                issues.extend(a11y_issues)

                for msg in console_messages:
                    if msg.level in ("error", "warning"):
                        issues.append(Issue(severity=msg.level, category="console", message=msg.message))

                has_errors = any(i.severity == "error" for i in issues)
                has_warnings = any(i.severity == "warning" for i in issues)
                if has_errors:
                    report.status = "failed"
                elif has_warnings:
                    report.status = "warning"

                error_count = sum(1 for i in issues if i.severity == "error")
                warning_count = sum(1 for i in issues if i.severity == "warning")
                parts = []
                if error_count:
                    parts.append(f"{error_count} error(s)")
                if warning_count:
                    parts.append(f"{warning_count} warning(s)")
                report.summary = f"Browser inspection: {', '.join(parts)}" if parts else "All checks passed"

                report.issues = [{"severity": i.severity, "category": i.category, "message": i.message, "element_selector": i.element_selector} for i in issues]
                report.console_errors = [{"level": c.level, "message": c.message} for c in console_messages if c.level in ("error", "warning")]
                report.screenshots = [{"type": s.type, "url": s.url, "path": s.path, "width": s.width, "height": s.height} for s in screenshots]
                report.performance_metrics = metrics

                await browser.close()
        except Exception as exc:
            logger.exception("Browser inspection failed", job_id=job_id)
            report.status = "failed"
            report.summary = f"Inspection failed: {exc}"

        return report

    async def _check_accessibility(self, page) -> list[Issue]:
        issues: list[Issue] = []
        try:
            img_count = await page.evaluate("""() => document.querySelectorAll('img:not([alt])').length""")
            if img_count > 0:
                issues.append(Issue(severity="warning", category="accessibility", message=f"{img_count} image(s) missing alt text"))
            has_lang = await page.evaluate("""() => !!document.documentElement.getAttribute('lang')""")
            if not has_lang:
                issues.append(Issue(severity="info", category="accessibility", message="HTML element missing 'lang' attribute"))
        except Exception:
            pass
        return issues