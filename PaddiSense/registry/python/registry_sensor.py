#!/usr/bin/env python3
"""
Farm Registry Sensor - PaddiSense Shared Core
PaddiSense Farm Management System

This script provides read-only JSON output for the Home Assistant sensor.
It reads the registry config and server.yaml, outputting the farm hierarchy
for consumption by all PaddiSense modules (PWM, HFM, IPM, ASM, etc.).

Output includes:
  - grower: Grower/server info from server.yaml
  - farms: Farm definitions from server.yaml
  - paddocks: Paddock configurations from registry
  - bays: Bay configurations from registry
  - seasons: Season definitions with active season
  - status: System status information
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Paths
DATA_DIR = Path("/config/local_data/registry")
CONFIG_FILE = DATA_DIR / "config.json"
CROPS_FILE = DATA_DIR / "crops.json"
BACKUP_DIR = DATA_DIR / "backups"
SERVER_YAML = Path("/config/server.yaml")
VERSION_FILE = Path("/config/PaddiSense/registry/VERSION")


def get_version() -> str:
    """Read module version from VERSION file."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip()
    except IOError:
        pass
    return "unknown"


def load_config() -> dict[str, Any]:
    """Load registry config from JSON file."""
    if not CONFIG_FILE.exists():
        return {
            "initialized": False,
            "paddocks": {},
            "bays": {},
            "seasons": {},
            "version": "1.0.0",
        }
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {
            "initialized": False,
            "paddocks": {},
            "bays": {},
            "seasons": {},
            "version": "1.0.0",
        }


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


def extract_farms(server_config: dict[str, Any], registry_farms: dict[str, Any]) -> dict[str, Any]:
    """
    Merge farm definitions from server.yaml (read-only legacy) and config.json (editable).

    Priority: config.json farms override server.yaml farms if same ID.
    This allows editing farms via UI while preserving backward compatibility.
    """
    # Start with farms from server.yaml (pwm.farms or registry.farms)
    pwm_config = server_config.get("pwm", {})
    server_farms = dict(pwm_config.get("farms", {}))

    # Check for dedicated registry.farms section in server.yaml
    registry_config = server_config.get("registry", {})
    if "farms" in registry_config:
        server_farms.update(registry_config.get("farms", {}))

    # Merge in farms from config.json (these take precedence)
    # This allows farms to be edited via the UI
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


def load_crops() -> dict[str, Any]:
    """Load crops config from JSON file."""
    if not CROPS_FILE.exists():
        return {
            "version": "1.0.0",
            "crops": {},
        }
    try:
        return json.loads(CROPS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {
            "version": "1.0.0",
            "crops": {},
        }


def is_in_month_range(current_month: int, start_month: int, end_month: int) -> bool:
    """Check if current month is within a start-end range (handles year wrapping)."""
    if start_month <= end_month:
        # Normal range (e.g., May-Sep: 5-9)
        return start_month <= current_month <= end_month
    else:
        # Wraps around year (e.g., Oct-May: 10-5)
        return current_month >= start_month or current_month <= end_month


def get_current_crop_for_paddock(paddock: dict, current_month: int) -> dict | None:
    """Determine the current crop for a paddock based on today's month."""
    crop_1 = paddock.get("crop_1", {})
    crop_2 = paddock.get("crop_2", {})

    # Check if today falls in crop_1 range
    if crop_1 and crop_1.get("crop_id"):
        start = crop_1.get("start_month", 1)
        end = crop_1.get("end_month", 12)
        if is_in_month_range(current_month, start, end):
            return crop_1

    # Check if today falls in crop_2 range
    if crop_2 and crop_2.get("crop_id"):
        start = crop_2.get("start_month", 1)
        end = crop_2.get("end_month", 12)
        if is_in_month_range(current_month, start, end):
            return crop_2

    return None


def build_current_crops(
    paddocks: dict[str, Any],
    crops: dict[str, Any],
    current_month: int
) -> dict[str, Any]:
    """Build a mapping of paddock_id to current crop info."""
    current_crops = {}

    for pid, paddock in paddocks.items():
        current = get_current_crop_for_paddock(paddock, current_month)
        if current:
            crop_id = current.get("crop_id")
            crop_data = crops.get(crop_id, {})
            current_crops[pid] = {
                "crop_id": crop_id,
                "crop_name": crop_data.get("name", crop_id),
                "crop_color": crop_data.get("color", "#4caf50"),
                "stages": crop_data.get("stages", []),
            }
        else:
            current_crops[pid] = None

    return current_crops


def build_hierarchy_summary(
    farms: dict[str, Any],
    paddocks: dict[str, Any],
    bays: dict[str, Any]
) -> dict[str, Any]:
    """Build a hierarchical summary for the UI."""
    hierarchy = {}

    for farm_id, farm in farms.items():
        farm_paddocks = {
            pid: p for pid, p in paddocks.items()
            if p.get("farm_id") == farm_id
        }

        paddock_data = {}
        for pid, paddock in farm_paddocks.items():
            paddock_bays = [
                {"id": bid, "name": b.get("name"), "order": b.get("order", 0)}
                for bid, b in bays.items()
                if b.get("paddock_id") == pid
            ]
            paddock_bays.sort(key=lambda x: x["order"])

            paddock_data[pid] = {
                "name": paddock.get("name", pid),
                "bay_count": len(paddock_bays),
                "bays": paddock_bays,
            }

        hierarchy[farm_id] = {
            "name": farm.get("name", farm_id),
            "paddock_count": len(farm_paddocks),
            "paddocks": paddock_data,
        }

    return hierarchy


def main() -> int:
    config = load_config()
    server = load_server_yaml()
    crops_data = load_crops()

    # Extract data
    grower = extract_grower(server)
    registry_farms = config.get("farms", {})  # Farms stored in config.json (editable)
    farms = extract_farms(server, registry_farms)  # Merge with server.yaml farms
    paddocks = config.get("paddocks", {})
    bays = config.get("bays", {})
    seasons = config.get("seasons", {})
    crops = crops_data.get("crops", {})

    # System status
    initialized = config.get("initialized", False)
    config_ok = CONFIG_FILE.exists()

    # Active season
    active_season = get_active_season(seasons)

    # Build lists for dropdowns
    farm_names = sorted([f.get("name", fid) for fid, f in farms.items()])
    paddock_names = sorted([p.get("name", pid) for pid, p in paddocks.items()])
    season_names = sorted([s.get("name", sid) for sid, s in seasons.items()])
    crop_names = sorted([c.get("name", cid) for cid, c in crops.items()])

    # Build hierarchy
    hierarchy = build_hierarchy_summary(farms, paddocks, bays)

    # Build current crops mapping (paddock_id -> current crop info)
    from datetime import datetime
    current_month = datetime.now().month
    current_crops = build_current_crops(paddocks, crops, current_month)

    # Count backups
    backup_count = 0
    if BACKUP_DIR.exists():
        backup_count = len(list(BACKUP_DIR.glob("*.json")))

    # Get version
    version = get_version()

    # Check which modules are enabled
    modules = server.get("modules", {})

    output = {
        # System status
        "status": "ready" if initialized else "not_initialized",
        "initialized": initialized,
        "config_ok": config_ok,
        "version": version,

        # Grower info
        "grower": grower,

        # Counts
        "total_farms": len(farms),
        "total_paddocks": len(paddocks),
        "total_bays": len(bays),
        "total_seasons": len(seasons),
        "backup_count": backup_count,

        # Active season
        "active_season": active_season,
        "active_season_name": seasons.get(active_season, {}).get("name") if active_season else None,

        # Raw data for other modules to consume
        "farms": farms,
        "paddocks": paddocks,
        "bays": bays,
        "seasons": seasons,
        "crops": crops,

        # Current crops per paddock (based on today's month)
        "current_crops": current_crops,
        "current_month": current_month,

        # Hierarchy summary for UI
        "hierarchy": hierarchy,

        # Lists for dropdowns
        "farm_names": farm_names,
        "paddock_names": paddock_names,
        "season_names": season_names,
        "crop_names": crop_names,

        # Enabled modules (for conditional UI)
        "modules": modules,
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
