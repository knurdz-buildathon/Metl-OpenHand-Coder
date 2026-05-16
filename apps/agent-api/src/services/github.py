"""GitHub service – clone, branch, commit, and push operations."""

from __future__ import annotations

from pathlib import Path

import structlog
from git import Repo
from git.exc import GitCommandError

from src.core.config import settings

logger = structlog.get_logger(__name__)


class GitHubService:
    """Handles Git operations (clone, branch, commit, push) for job repositories."""

    async def clone_repo(self, github_url: str, clone_path: str) -> None:
        """Clone a GitHub repository to the given local path.

        Args:
            github_url: The HTTPS URL of the GitHub repository.
            clone_path: Local filesystem path where the repo will be cloned.
        """
        logger.info("Cloning repository", url=github_url, path=clone_path)

        clone_url = github_url
        if settings.GITHUB_TOKEN and "github.com" in github_url:
            clone_url = github_url.replace(
                "https://",
                f"https://{settings.GITHUB_TOKEN}@",
            )

        Path(clone_path).mkdir(parents=True, exist_ok=True)
        try:
            Repo.clone_from(clone_url, clone_path, depth=1)
            logger.info("Repository cloned successfully", path=clone_path)
        except GitCommandError as exc:
            logger.exception("Failed to clone repository", url=github_url)
            raise RuntimeError(f"Failed to clone {github_url}") from exc

    async def create_branch(self, repo_path: str, branch_name: str) -> None:
        """Create and switch to a new branch in the cloned repository.

        Args:
            repo_path: Local path to the cloned repository.
            branch_name: Name of the new branch.
        """
        logger.info("Creating branch", branch=branch_name, path=repo_path)
        try:
            repo = Repo(repo_path)
            current = repo.create_head(branch_name)
            current.checkout()
            logger.info("Branch created and checked out", branch=branch_name)
        except GitCommandError as exc:
            logger.exception("Failed to create branch", branch=branch_name)
            raise RuntimeError(f"Failed to create branch {branch_name}") from exc

    async def commit_and_push(self, repo_path: str, message: str) -> None:
        """Stage all changes, commit, and push to the remote branch.

        Args:
            repo_path: Local path to the cloned repository.
            message: Commit message.
        """
        logger.info("Committing and pushing changes", path=repo_path)
        try:
            repo = Repo(repo_path)

            if not repo.is_dirty(untracked_files=True):
                logger.info("No changes to commit", path=repo_path)
                return

            repo.git.add(A=True)
            repo.index.commit(message)

            origin = repo.remote(name="origin")
            origin.push(refspec=f"{repo.active_branch.name}:{repo.active_branch.name}")
            logger.info("Changes pushed successfully", branch=repo.active_branch.name)
        except GitCommandError as exc:
            logger.exception("Failed to commit and push")
            raise RuntimeError(f"Failed to commit and push: {message}") from exc