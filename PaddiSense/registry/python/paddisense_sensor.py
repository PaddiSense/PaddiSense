#!/usr/bin/env python3
"""
PaddiSense Version Sensor
=========================
Provides system-wide version, module availability, and licensing information.

Output attributes:
  - version: PaddiSense system version
  - available_modules: List of all modules from modules.json
  - installed_modules: List of currently installed modules (with versions)
  - licensed_modules: List of licensed module IDs (dev mode = all licensed)
  - dev_mode: True if on dev/development branch (bypasses licensing)
  - git_branch: Current git branch name
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Paths
PADDISENSE_DIR = Path("/config/PaddiSense")
MODULES_JSON = PADDISENSE_DIR / "modules.json"
VERSION_FILE = PADDISENSE_DIR / "VERSION"
SERVER_YAML = Path("/config/server.yaml")
LICENSE_FILE = Path("/config/local_data/registry/license.json")

# Branches that bypass licensing (dev mode)
DEV_BRANCHES = {"dev", "develop", "development", "feature", "fix", "test", "local"}


def get_git_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "-C", str(PADDISENSE_DIR), "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return "unknown"


def is_dev_mode(branch: str) -> bool:
    """Check if current branch is a development branch (bypasses licensing)."""
    if not branch or branch == "unknown":
        return False
    # Check exact match or prefix match for feature/fix branches
    branch_lower = branch.lower()
    for dev_branch in DEV_BRANCHES:
        if branch_lower == dev_branch or branch_lower.startswith(f"{dev_branch}/"):
            return True
    return False


def get_version() -> str:
    """Read PaddiSense system version."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip()
    except IOError:
        pass
    return "unknown"


def load_modules_json() -> dict[str, Any]:
    """Load modules.json for available modules."""
    try:
        if MODULES_JSON.exists():
            return json.loads(MODULES_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        pass
    return {"modules": {}}


def load_license_file() -> list[str]:
    """Load licensed modules from license.json (production mode)."""
    try:
        if LICENSE_FILE.exists():
            data = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
            return data.get("licensed_modules", [])
    except (json.JSONDecodeError, IOError):
        pass
    return []


def get_installed_modules() -> list[dict[str, Any]]:
    """Scan for installed modules by checking for package.yaml files."""
    installed = []
    modules_data = load_modules_json()
    all_modules = modules_data.get("modules", {})

    for module_id, module_info in all_modules.items():
        module_dir = PADDISENSE_DIR / module_id
        package_file = module_dir / "package.yaml"
        version_file = module_dir / "VERSION"

        # Check if module is installed (has package.yaml)
        if package_file.exists():
            version = "unknown"
            try:
                if version_file.exists():
                    version = version_file.read_text(encoding="utf-8").strip()
            except IOError:
                pass

            installed.append({
                "id": module_id,
                "name": module_info.get("name", module_id),
                "version": version,
                "icon": module_info.get("icon", "mdi:puzzle"),
            })

    return installed


def get_available_modules() -> list[dict[str, Any]]:
    """Get all available modules from modules.json."""
    modules_data = load_modules_json()
    all_modules = modules_data.get("modules", {})

    available = []
    for module_id, module_info in all_modules.items():
        available.append({
            "id": module_id,
            "name": module_info.get("name", module_id),
            "description": module_info.get("description", ""),
            "icon": module_info.get("icon", "mdi:puzzle"),
            "status": module_info.get("status", "unknown"),
            "dependencies": module_info.get("dependencies", []),
        })

    return available


def get_licensed_modules(dev_mode: bool) -> list[str]:
    """
    Get list of licensed module IDs.

    In dev mode: All modules are licensed (bypass).
    In production: Read from license.json file.
    """
    if dev_mode:
        # Dev mode bypass - all modules licensed
        modules_data = load_modules_json()
        return list(modules_data.get("modules", {}).keys())

    # Production mode - read from license file
    return load_license_file()


def main() -> int:
    # Get git branch and dev mode status
    git_branch = get_git_branch()
    dev_mode = is_dev_mode(git_branch)

    # Get version
    version = get_version()

    # Get module lists
    available_modules = get_available_modules()
    installed_modules = get_installed_modules()
    licensed_modules = get_licensed_modules(dev_mode)

    # Build output
    output = {
        # System info
        "version": version,
        "git_branch": git_branch,
        "dev_mode": dev_mode,

        # Module info
        "available_modules": available_modules,
        "installed_modules": installed_modules,
        "licensed_modules": licensed_modules,

        # Counts for display
        "total_available": len(available_modules),
        "total_installed": len(installed_modules),
        "total_licensed": len(licensed_modules),
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
