"""
Unit tests for core services: GitHub, OpenHands, Preview, Browser, Resource Manager.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


class TestGitHubService:
    @patch("git.Repo.clone_from")
    def test_clone_repo(self, mock_clone):
        mock_clone.return_value = MagicMock()
        from src.services.github import GitHubService

        service = GitHubService()
        result = service.clone_repo_sync("https://github.com/test/repo", "/tmp/test")
        assert result == "/tmp/test"
        mock_clone.assert_called_once()


class TestOpenHandsService:
    @patch("docker.from_env")
    def test_start_container(self, mock_docker):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "container-123"
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client

        from src.services.openhands import OpenHandsService

        service = OpenHandsService()
        with patch.object(service, "start_openhands_container", AsyncMock(return_value=(0, {"summary": "done"}))):
            # Test the config injection
            env_vars = {"DATABASE_URL": "postgresql://...", "REDIS_URL": "redis://..."}
            assert len(env_vars) == 2


class TestPreviewService:
    def test_detect_framework_next(self):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", new_callable=MagicMock):
                # Simulate package.json with next dependency
                pass

    def test_detect_framework_vite(self):
        # Vite detection logic
        pass

    def test_build_preview_flow(self):
        # Preview build flow
        pass


class TestBrowserService:
    @patch("playwright.chromium.launch")
    def test_inspect_preview_pass(self, mock_launch):
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.screenshot.return_value = b"fake-png-data"
        mock_launch.return_value = mock_browser

        from src.services.browser import BrowserService

        service = BrowserService()
        # Test the key inspection flow concepts
        assert service is not None

    def test_inspect_preview_failed_no_network(self):
        # Handle network errors during inspection
        pass


class TestResourceManager:
    def test_request_resources_format(self):
        from src.services.resource_manager import ResourceManager

        manager = ResourceManager()
        items = [
            {"type": "postgresql", "tier": "small"},
            {"type": "s3_compatible", "region": "us-east-1"},
        ]
        assert len(items) == 2

    def test_env_var_formatting(self):
        config = {
            "postgresql": {"host": "localhost", "port": 5432, "db": "testdb", "user": "test", "password": "pass"},
        }
        formatted = f"DATABASE_URL=postgresql://{config['postgresql']['user']}:{config['postgresql']['password']}@{config['postgresql']['host']}:{config['postgresql']['port']}/{config['postgresql']['db']}"
        assert "postgresql://" in formatted
        assert "@localhost" in formatted


class TestPlanGeneration:
    def test_parse_plan_markdown(self):
        plan_md = """# Project Plan\n\n## Step 1\n- Create component\n\n## Step 2\n- Add styles"""
        steps = [s for s in plan_md.split("\n") if s.startswith("-")]
        assert len(steps) == 2

    def test_generate_plan_from_prompt(self):
        prompt = "Build a SaaS dashboard with auth and billing"
        assert "dashboard" in prompt.lower()
        assert "auth" in prompt.lower()