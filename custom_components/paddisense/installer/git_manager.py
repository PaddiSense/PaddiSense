"""Git operations for PaddiSense installer."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from ..const import (
    PADDISENSE_DIR,
    PADDISENSE_REPO_URL,
    PADDISENSE_REPO_BRANCH,
    PADDISENSE_VERSION_FILE,
)

_LOGGER = logging.getLogger(__name__)


class GitManager:
    """Manage git operations for PaddiSense repository."""

    def __init__(self, token: str | None = None) -> None:
        """Initialize the git manager."""
        self.repo_dir = PADDISENSE_DIR
        self._base_url = PADDISENSE_REPO_URL
        self.branch = PADDISENSE_REPO_BRANCH
        self._token = token

    @property
    def repo_url(self) -> str:
        """Get repo URL with token if available."""
        if self._token:
            # https://TOKEN@github.com/user/repo.git
            return self._base_url.replace("https://", f"https://{self._token}@")
        return self._base_url

    def set_token(self, token: str | None) -> None:
        """Update token for authenticated operations."""
        self._token = token

    def is_git_available(self) -> bool:
        """Check if git is available on the system."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def is_repo_cloned(self) -> bool:
        """Check if the PaddiSense repo is already cloned."""
        git_dir = self.repo_dir / ".git"
        return git_dir.is_dir()

    def clone(self) -> dict[str, Any]:
        """Clone the PaddiSense repository."""
        if self.is_repo_cloned():
            return {
                "success": False,
                "error": "Repository already exists",
            }

        try:
            # Ensure parent directory exists
            self.repo_dir.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--branch",
                    self.branch,
                    "--single-branch",
                    "--depth",
                    "1",
                    self.repo_url,
                    str(self.repo_dir),
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if result.returncode != 0:
                _LOGGER.error("Git clone failed: %s", result.stderr)
                return {
                    "success": False,
                    "error": f"Clone failed: {result.stderr}",
                }

            _LOGGER.info("Successfully cloned PaddiSense repository")
            return {
                "success": True,
                "message": "Repository cloned successfully",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Clone timed out. Check your network connection.",
            }
        except subprocess.SubprocessError as e:
            return {
                "success": False,
                "error": f"Clone failed: {e}",
            }

    def pull(self) -> dict[str, Any]:
        """Pull latest changes from the repository."""
        if not self.is_repo_cloned():
            return {
                "success": False,
                "error": "Repository not found. Run clone first.",
            }

        try:
            # Fetch first
            fetch_result = subprocess.run(
                ["git", "fetch", "origin", self.branch],
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if fetch_result.returncode != 0:
                _LOGGER.error("Git fetch failed: %s", fetch_result.stderr)
                return {
                    "success": False,
                    "error": f"Fetch failed: {fetch_result.stderr}",
                }

            # Reset to origin/branch (force update, preserving nothing)
            reset_result = subprocess.run(
                ["git", "reset", "--hard", f"origin/{self.branch}"],
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if reset_result.returncode != 0:
                _LOGGER.error("Git reset failed: %s", reset_result.stderr)
                return {
                    "success": False,
                    "error": f"Reset failed: {reset_result.stderr}",
                }

            _LOGGER.info("Successfully pulled latest changes")
            return {
                "success": True,
                "message": "Repository updated successfully",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Pull timed out. Check your network connection.",
            }
        except subprocess.SubprocessError as e:
            return {
                "success": False,
                "error": f"Pull failed: {e}",
            }

    def get_local_version(self) -> str | None:
        """Get the local version from VERSION file."""
        if not PADDISENSE_VERSION_FILE.exists():
            return None
        try:
            return PADDISENSE_VERSION_FILE.read_text(encoding="utf-8").strip()
        except IOError:
            return None

    def get_remote_version(self) -> str | None:
        """Get the latest version from remote repository."""
        if not self.is_repo_cloned():
            return None

        try:
            # Fetch latest without merging
            subprocess.run(
                ["git", "fetch", "origin", self.branch],
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Read VERSION from remote
            result = subprocess.run(
                ["git", "show", f"origin/{self.branch}:VERSION"],
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            return None

        except subprocess.SubprocessError:
            return None

    def check_for_updates(self) -> dict[str, Any]:
        """Check if updates are available."""
        local_version = self.get_local_version()
        remote_version = self.get_remote_version()

        if local_version is None:
            return {
                "success": False,
                "error": "Local version not found",
                "update_available": False,
            }

        if remote_version is None:
            return {
                "success": False,
                "error": "Could not fetch remote version",
                "update_available": False,
                "local_version": local_version,
            }

        update_available = remote_version != local_version

        return {
            "success": True,
            "local_version": local_version,
            "remote_version": remote_version,
            "update_available": update_available,
        }

    def get_commit_info(self) -> dict[str, Any]:
        """Get current commit information."""
        if not self.is_repo_cloned():
            return {"error": "Repository not found"}

        try:
            # Get commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Get commit date
            date_result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"],
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )

            return {
                "commit": hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown",
                "date": date_result.stdout.strip() if date_result.returncode == 0 else "unknown",
            }

        except subprocess.SubprocessError:
            return {"error": "Failed to get commit info"}

    def verify_repo_integrity(self) -> dict[str, Any]:
        """Verify the repository is in good state."""
        if not self.is_repo_cloned():
            return {
                "success": False,
                "error": "Repository not found",
            }

        checks = {
            "git_dir_exists": (self.repo_dir / ".git").is_dir(),
            "version_file_exists": PADDISENSE_VERSION_FILE.exists(),
            "modules_json_exists": (self.repo_dir / "modules.json").exists(),
        }

        all_passed = all(checks.values())

        return {
            "success": all_passed,
            "checks": checks,
            "error": None if all_passed else "Repository integrity check failed",
        }
