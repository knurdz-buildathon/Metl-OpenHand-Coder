"""Database models for the Metl Agent API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    github_url: Mapped[str] = mapped_column(Text, nullable=False)
    plan_md_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    branch_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    repo_clone_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preview_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(), nullable=True
    )

    resource_requests: Mapped[list["ResourceRequest"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    previews: Mapped[list["PreviewBuild"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    browser_reports: Mapped[list["BrowserReport"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class ResourceRequest(Base):
    __tablename__ = "resource_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=False, index=True
    )
    requested: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    env_vars: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=utcnow, server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(), nullable=True
    )

    job: Mapped[Job] = relationship(back_populates="resource_requests")


class PreviewBuild(Base):
    __tablename__ = "preview_builds"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="building")
    framework: Mapped[str] = mapped_column(String(32), default="unknown")
    build_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    container_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=utcnow, server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(), nullable=True
    )

    job: Mapped[Job] = relationship(back_populates="previews")


class BrowserReport(Base):
    __tablename__ = "browser_reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=False, index=True
    )
    preview_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="passed")
    summary: Mapped[str] = mapped_column(Text, default="")
    issues: Mapped[list] = mapped_column(JSON, default=list)
    console_errors: Mapped[list] = mapped_column(JSON, default=list)
    screenshots: Mapped[list] = mapped_column(JSON, default=list)
    performance_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=utcnow, server_default=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="browser_reports")