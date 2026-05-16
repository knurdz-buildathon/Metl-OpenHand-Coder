"""Pydantic models for the Metl Agent API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PLANNING = "planning"
    EXECUTING = "executing"
    RESOURCE_REQUESTED = "resource_requested"
    PREVIEW_BUILDING = "preview_building"
    BROWSER_TESTING = "browser_testing"
    FIXING_ISSUES = "fixing_issues"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    AZURE = "azure"


# --- Job request/response ---

class JobOptions(BaseModel):
    enable_v0: bool = False
    enable_cursor_sdk: bool = False
    llm_provider: LLMProvider = LLMProvider.AZURE
    llm_model: Optional[str] = None
    max_iterations: int = 10
    preview_ttl_minutes: int = 120


class CreateJobRequest(BaseModel):
    github_url: str
    plan_md_url: Optional[str] = None
    prompt: str = Field(..., min_length=1)
    options: JobOptions = Field(default_factory=JobOptions)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    github_url: str
    plan_md_url: Optional[str] = None
    prompt: str
    options: dict = Field(default_factory=dict)
    branch_name: Optional[str] = None
    repo_clone_path: Optional[str] = None
    preview_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# --- Preview ---

class PreviewBuildModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    status: str = "building"
    framework: str = "unknown"
    build_log: Optional[str] = None
    url: Optional[str] = None
    container_id: Optional[str] = None
    port: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


# --- Browser report ---

class Issue(BaseModel):
    severity: str = "info"
    category: str = "general"
    message: str = ""


class ConsoleEntry(BaseModel):
    level: str = "info"
    message: str = ""


class PerformanceMetrics(BaseModel):
    load_time_ms: Optional[int] = None
    dom_content_loaded_ms: Optional[int] = None
    first_paint_ms: Optional[int] = None
    first_contentful_paint_ms: Optional[int] = None


class ScreenshotInfo(BaseModel):
    type: str = ""
    url: str = ""
    path: str = ""
    width: int = 0
    height: int = 0


class BrowserReportModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    preview_id: str
    status: str = "passed"
    summary: str = ""
    issues: list[Issue] = Field(default_factory=list)
    console_errors: list[ConsoleEntry] = Field(default_factory=list)
    screenshots: list[ScreenshotInfo] = Field(default_factory=list)
    performance_metrics: Optional[PerformanceMetrics] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Completion report ---

class ChangeEntry(BaseModel):
    type: str
    file: str
    description: Optional[str] = None


class CompletionReportModel(BaseModel):
    job_id: str
    status: str
    summary: str
    changes: list[ChangeEntry] = Field(default_factory=list)
    preview_url: Optional[str] = None
    screenshots: list[ScreenshotInfo] = Field(default_factory=list)
    browser_report_summary: Optional[str] = None
    resource_summary: Optional[str] = None
    artifacts_local_path: Optional[str] = None
    duration_seconds: float = 0.0
    completed_at: Optional[str] = None


# Export database models too
from . import database  # noqa: E402, F401

__all__ = [
    "JobStatus", "LLMProvider", "JobOptions", "CreateJobRequest", "JobResponse",
    "PreviewBuildModel", "BrowserReportModel", "CompletionReportModel",
    "Issue", "ConsoleEntry", "PerformanceMetrics", "ScreenshotInfo", "ChangeEntry",
    "database",
]