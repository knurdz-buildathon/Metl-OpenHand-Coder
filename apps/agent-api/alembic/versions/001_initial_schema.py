"""Create initial database schema (SQLite compatible)

Revision ID: 001
Revises:
Create Date: 2026-05-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("github_url", sa.Text, nullable=False),
        sa.Column("plan_md_url", sa.Text, nullable=True),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("options", sa.JSON, server_default=sa.text("'{}'")),
        sa.Column("branch_name", sa.String(128), nullable=True),
        sa.Column("repo_clone_path", sa.Text, nullable=True),
        sa.Column("preview_url", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "resource_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("requested", sa.JSON, server_default=sa.text("'[]'")),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("config", sa.JSON, server_default=sa.text("'{}'")),
        sa.Column("env_vars", sa.JSON, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_resource_requests_job_id", "resource_requests", ["job_id"])

    op.create_table(
        "preview_builds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="building"),
        sa.Column("framework", sa.String(32), server_default="unknown"),
        sa.Column("build_log", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("container_id", sa.String(128), nullable=True),
        sa.Column("port", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_preview_builds_job_id", "preview_builds", ["job_id"])

    op.create_table(
        "browser_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("preview_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="passed"),
        sa.Column("summary", sa.Text, server_default=""),
        sa.Column("issues", sa.JSON, server_default=sa.text("'[]'")),
        sa.Column("console_errors", sa.JSON, server_default=sa.text("'[]'")),
        sa.Column("screenshots", sa.JSON, server_default=sa.text("'[]'")),
        sa.Column("performance_metrics", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_browser_reports_job_id", "browser_reports", ["job_id"])


def downgrade() -> None:
    op.drop_table("browser_reports")
    op.drop_table("preview_builds")
    op.drop_table("resource_requests")
    op.drop_table("jobs")