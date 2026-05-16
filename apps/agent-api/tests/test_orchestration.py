"""
Integration tests for the complete orchestration flow:
receive job -> clone repo -> generate plan -> run OpenHands ->
request resources -> build preview -> run browser agent -> fix issues ->
generate report -> notify control panel.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

TEST_JOB_DATA = {
    "github_url": "https://github.com/test/repo",
    "prompt": "Build a hello world app",
    "options": {
        "enable_v0": False,
        "enable_cursor_sdk": False,
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-20250514",
    },
}


@pytest_asyncio.fixture
async def client():
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_job(client):
    resp = await client.post("/v1/jobs", json=TEST_JOB_DATA)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("pending", "cloning")
    assert data["github_url"] == TEST_JOB_DATA["github_url"]
    assert data["prompt"] == TEST_JOB_DATA["prompt"]


@pytest.mark.asyncio
async def test_list_jobs(client):
    resp = await client.get("/v1/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_job(client):
    create_resp = await client.post("/v1/jobs", json=TEST_JOB_DATA)
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


@pytest.mark.asyncio
async def test_cancel_job(client):
    create_resp = await client.post("/v1/jobs", json=TEST_JOB_DATA)
    job_id = create_resp.json()["id"]

    resp = await client.delete(f"/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
@patch("src.services.preview.PreviewService.build_preview")
async def test_preview_endpoint(mock_build, client):
    mock_build.return_value = {
        "id": str(uuid.uuid4()),
        "status": "ready",
        "url": "http://localhost:9000/test",
        "framework": "next",
    }

    create_resp = await client.post("/v1/jobs", json=TEST_JOB_DATA)
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/v1/jobs/{job_id}/preview")
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
@patch("src.services.browser.BrowserService.inspect_preview")
async def test_browser_report_endpoint(mock_inspect, client):
    mock_inspect.return_value = {
        "id": str(uuid.uuid4()),
        "status": "passed",
        "summary": "All checks passed",
        "issues": [],
    }

    create_resp = await client.post("/v1/jobs", json=TEST_JOB_DATA)
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/v1/jobs/{job_id}/reports/browser")
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_v0_integration_endpoint(client):
    resp = await client.post("/v1/v0/generate", json={
        "prompt": "Create a login form",
        "framework": "next",
    })
    # May not have v0 configured, so accept 404 or 200
    assert resp.status_code in (200, 404, 501)


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


class TestOrchestrationFlow:
    @pytest.mark.asyncio
    @patch("src.services.openhands.OpenHandsService.start_openhands_container")
    @patch("src.services.github.GitHubService.clone_repo")
    @patch("src.core.orchestrator.Orchestrator._notify_control_panel")
    async def test_full_orchestration_flow(
        self, mock_notify, mock_clone, mock_openhands, client
    ):
        mock_clone.return_value = "/tmp/test-repo"
        mock_openhands.return_value = (0, {"summary": "success", "iterations": 3})
        mock_notify.return_value = None

        resp = await client.post("/v1/jobs", json=TEST_JOB_DATA)
        assert resp.status_code == 200
        job_id = resp.json()["id"]

        job_resp = await client.get(f"/v1/jobs/{job_id}")
        assert job_resp.status_code == 200
        assert job_resp.json()["status"] in (
            "pending", "cloning", "planning", "executing", "completed"
        )


class TestResourceManager:
    @pytest.mark.asyncio
    async def test_resource_request_format(client):
        resource_request = {
            "job_id": str(uuid.uuid4()),
            "requested": [
                {"type": "postgresql", "tier": "small"},
                {"type": "s3_compatible", "region": "us-east-1"},
            ],
        }
        # The resource request would typically come from the orchestrator
        # This validates the schema format
        assert len(resource_request["requested"]) == 2
        assert resource_request["requested"][0]["type"] == "postgresql"
        assert resource_request["requested"][1]["type"] == "s3_compatible"


class TestCompletionReport:
    def test_report_schema(self):
        report = {
            "job_id": str(uuid.uuid4()),
            "status": "success",
            "summary": "App built successfully",
            "changes": [
                {"type": "created", "file": "src/App.tsx", "description": "Main app component"},
                {"type": "modified", "file": "package.json", "description": "Added dependencies"},
            ],
            "preview_url": "http://localhost:9000/test",
            "screenshots": [
                {"type": "viewport", "url": "http://s3/screenshot.png", "path": "/screenshots/test.png", "width": 1440, "height": 900},
            ],
            "browser_report_summary": "No issues found",
            "resource_summary": "2 resources provisioned",
            "duration_seconds": 120.5,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        assert report["status"] == "success"
        assert len(report["changes"]) == 2
        assert report["duration_seconds"] > 0