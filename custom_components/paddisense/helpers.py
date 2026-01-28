"""Helper utilities for PaddiSense integration."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .const import (
    REGISTRY_BACKUP_DIR,
    REGISTRY_CONFIG_FILE,
    REGISTRY_DATA_DIR,
    SERVER_YAML,
    VERSION_FILE,
)


def generate_id(name: str) -> str:
    """Generate a clean ID from a name."""
    clean = re.sub(r"[^a-z0-9]+", "_", name.lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean[:30] if clean else "unknown"


def get_version() -> str:
    """Read module version from VERSION file."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip()
    except IOError:
        pass
    return "unknown"


def load_registry_config() -> dict[str, Any]:
    """Load registry config from JSON file."""
    if not REGISTRY_CONFIG_FILE.exists():
        return {
            "initialized": False,
            "paddocks": {},
            "bays": {},
            "seasons": {},
            "farms": {},
            "version": "1.0.0",
        }
    try:
        return json.loads(REGISTRY_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {
            "initialized": False,
            "paddocks": {},
            "bays": {},
            "seasons": {},
            "farms": {},
            "version": "1.0.0",
        }


def save_registry_config(config: dict[str, Any]) -> None:
    """Save registry config to JSON file."""
    config["modified"] = datetime.now().isoformat(timespec="seconds")
    REGISTRY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def create_backup(tag: str = "") -> Path:
    """Create a timestamped backup of the config file."""
    REGISTRY_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    suffix = f"_{tag}" if tag else ""
    backup_name = f"backup_{ts}{suffix}.json"
    backup_path = REGISTRY_BACKUP_DIR / backup_name
    if REGISTRY_CONFIG_FILE.exists():
        backup_path.write_text(
            REGISTRY_CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return backup_path


def load_server_yaml() -> dict[str, Any]:
    """Load server.yaml for grower and farm definitions."""
    if not SERVER_YAML.exists():
        return {}
    try:
        content = SERVER_YAML.read_text(encoding="utf-8")
        return yaml.safe_load(content) or {}
    except (yaml.YAMLError, IOError):
        return {}


def extract_grower(server_config: dict[str, Any]) -> dict[str, Any]:
    """Extract grower/server info from server.yaml."""
    server = server_config.get("server", {})
    return {
        "name": server.get("name", "PaddiSense Farm"),
        "location": server.get("location", ""),
    }


def extract_farms(
    server_config: dict[str, Any], registry_farms: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge farm definitions from server.yaml and config.json.

    Priority: config.json farms override server.yaml farms if same ID.
    """
    pwm_config = server_config.get("pwm", {})
    server_farms = dict(pwm_config.get("farms", {}))

    registry_config = server_config.get("registry", {})
    if "farms" in registry_config:
        server_farms.update(registry_config.get("farms", {}))

    merged = dict(server_farms)
    for farm_id, farm_data in registry_farms.items():
        merged[farm_id] = farm_data

    return merged


def get_active_season(seasons: dict[str, Any]) -> str | None:
    """Get the ID of the active season, if any."""
    for season_id, season in seasons.items():
        if season.get("active", False):
            return season_id
    return None


def existing_data_detected() -> bool:
    """Check if existing registry data exists."""
    return REGISTRY_CONFIG_FILE.exists()


def get_existing_data_summary() -> dict[str, Any]:
    """Get summary of existing data for import."""
    config = load_registry_config()
    return {
        "paddock_count": len(config.get("paddocks", {})),
        "bay_count": len(config.get("bays", {})),
        "season_count": len(config.get("seasons", {})),
        "farm_count": len(config.get("farms", {})),
        "initialized": config.get("initialized", False),
    }
