#!/usr/bin/env python3
"""
PWM Sensor - Precision Water Management
PaddiSense Farm Management System

This script provides read-only JSON output for the Home Assistant sensor.
It merges:
  - Farm Registry (structure): paddocks, bays
  - PWM Config (settings): enabled, device assignments, water levels
  - server.yaml: farm definitions

Output includes:
  - paddocks: Merged paddock data (structure + settings)
  - bays: Merged bay data (structure + settings)
  - farms: Farm definitions from server.yaml
  - paddock_names: List of paddock names for dropdowns
  - enabled_paddocks: List of enabled paddock IDs
  - device_list: All unique devices in use
  - status: System status information
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Paths
REGISTRY_FILE = Path("/config/local_data/registry/config.json")
PWM_DATA_DIR = Path("/config/local_data/pwm")
PWM_CONFIG_FILE = PWM_DATA_DIR / "config.json"
BACKUP_DIR = PWM_DATA_DIR / "backups"
SERVER_YAML = Path("/config/server.yaml")
VERSION_FILE = Path("/config/PaddiSense/pwm/VERSION")


def get_version() -> str:
    """Read module version from VERSION file."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip()
    except IOError:
        pass
    return "unknown"


def load_registry() -> dict[str, Any]:
    """Load Farm Registry (paddock/bay structure)."""
    if not REGISTRY_FILE.exists():
        return {"initialized": False, "paddocks": {}, "bays": {}}
    try:
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {"initialized": False, "paddocks": {}, "bays": {}}


def load_pwm_config() -> dict[str, Any]:
    """Load PWM-specific settings (enabled, devices, water levels)."""
    if not PWM_CONFIG_FILE.exists():
        return {"paddock_settings": {}, "bay_settings": {}}
    try:
        return json.loads(PWM_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {"paddock_settings": {}, "bay_settings": {}}


def load_merged_config() -> dict[str, Any]:
    """
    Merge Registry structure with PWM settings.

    Registry provides: paddock/bay structure (id, name, order, farm_id)
    PWM provides: enabled, automation_state_individual, device assignments, water levels
    """
    registry = load_registry()
    pwm = load_pwm_config()

    # Support both old and new PWM config format
    # Old format: paddocks/bays directly in config
    # New format: paddock_settings/bay_settings
    pwm_paddock_settings = pwm.get("paddock_settings", {})
    pwm_bay_settings = pwm.get("bay_settings", {})

    # Fall back to old format if new format is empty
    if not pwm_paddock_settings and "paddocks" in pwm:
        pwm_paddock_settings = {
            pid: {
                "enabled": p.get("enabled", True),
                "automation_state_individual": p.get("automation_state_individual", False),
                "image_url": p.get("image_url"),
            }
            for pid, p in pwm.get("paddocks", {}).items()
        }

    if not pwm_bay_settings and "bays" in pwm:
        pwm_bay_settings = {
            bid: {
                "supply_1": b.get("supply_1"),
                "supply_2": b.get("supply_2"),
                "drain_1": b.get("drain_1"),
                "drain_2": b.get("drain_2"),
                "level_sensor": b.get("level_sensor"),
                "settings": b.get("settings", {}),
                "badge_position": b.get("badge_position", {"top": 50, "left": 40}),
            }
            for bid, b in pwm.get("bays", {}).items()
        }

    # Merge paddocks: structure from registry + settings from PWM
    merged_paddocks = {}
    for pid, p in registry.get("paddocks", {}).items():
        pwm_settings = pwm_paddock_settings.get(pid, {})
        merged_paddocks[pid] = {
            **p,
            "enabled": pwm_settings.get("enabled", True),
            "automation_state_individual": pwm_settings.get("automation_state_individual", False),
            "image_url": pwm_settings.get("image_url"),
        }

    # Merge bays: structure from registry + settings from PWM
    merged_bays = {}
    for bid, b in registry.get("bays", {}).items():
        pwm_settings = pwm_bay_settings.get(bid, {})
        merged_bays[bid] = {
            **b,
            "supply_1": pwm_settings.get("supply_1"),
            "supply_2": pwm_settings.get("supply_2"),
            "drain_1": pwm_settings.get("drain_1"),
            "drain_2": pwm_settings.get("drain_2"),
            "level_sensor": pwm_settings.get("level_sensor"),
            "settings": pwm_settings.get("settings", {
                "water_level_min": 5,
                "water_level_max": 15,
                "water_level_offset": 0,
                "flush_time_on_water": 3600
            }),
            "badge_position": pwm_settings.get("badge_position", {"top": 50, "left": 40}),
        }

    return {
        "paddocks": merged_paddocks,
        "bays": merged_bays,
        "initialized": registry.get("initialized", False)
    }


def load_server_yaml() -> dict[str, Any]:
    """Load server.yaml for farm definitions."""
    if not SERVER_YAML.exists():
        return {}
    try:
        content = SERVER_YAML.read_text(encoding="utf-8")
        return yaml.safe_load(content) or {}
    except (yaml.YAMLError, IOError):
        return {}


def extract_farms(server_config: dict[str, Any]) -> dict[str, Any]:
    """Extract farm definitions from server.yaml."""
    pwm_config = server_config.get("pwm", {})
    farms = pwm_config.get("farms", {})
    return farms


def collect_devices(bays: dict[str, Any]) -> list[str]:
    """Collect all unique device names from bay configurations."""
    devices = set()
    for bay_id, bay in bays.items():
        # Check all device slots
        for slot in ["supply_1", "supply_2", "drain_1", "drain_2"]:
            slot_data = bay.get(slot, {})
            if isinstance(slot_data, dict):
                device = slot_data.get("device")
                if device and device not in (None, "null", "unset", ""):
                    devices.add(device)
        # Level sensor
        level_sensor = bay.get("level_sensor")
        if level_sensor and level_sensor not in (None, "null", "unset", ""):
            devices.add(level_sensor)
    return sorted(devices)


def build_paddock_summary(
    paddocks: dict[str, Any], bays: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build summary list of paddocks with bay counts and status."""
    summary = []
    for pid, paddock in paddocks.items():
        # Count bays for this paddock
        bay_count = sum(1 for b in bays.values() if b.get("paddock_id") == pid)
        # Count enabled bays (bays with at least one device assigned)
        configured_bays = sum(
            1
            for b in bays.values()
            if b.get("paddock_id") == pid
            and (
                b.get("level_sensor")
                or (b.get("supply_1", {}) or {}).get("device")
            )
        )
        summary.append(
            {
                "id": pid,
                "name": paddock.get("name", pid),
                "farm_id": paddock.get("farm_id", ""),
                "enabled": paddock.get("enabled", False),
                "individual_mode": paddock.get("automation_state_individual", False),
                "bay_count": bay_count,
                "configured_bays": configured_bays,
                "image_url": paddock.get("image_url"),
            }
        )
    return sorted(summary, key=lambda x: x["name"])


def build_bay_summary(bays: dict[str, Any], paddocks: dict[str, Any]) -> list[dict[str, Any]]:
    """Build summary list of bays with device info."""
    summary = []
    for bid, bay in bays.items():
        paddock_id = bay.get("paddock_id", "")
        paddock = paddocks.get(paddock_id, {})

        # Get device names
        supply_1 = (bay.get("supply_1", {}) or {}).get("device")
        supply_2 = (bay.get("supply_2", {}) or {}).get("device")
        drain_1 = (bay.get("drain_1", {}) or {}).get("device")
        drain_2 = (bay.get("drain_2", {}) or {}).get("device")
        level = bay.get("level_sensor")

        # Get badge position with defaults
        badge_pos = bay.get("badge_position", {"top": 50, "left": 40})

        summary.append(
            {
                "id": bid,
                "name": bay.get("name", bid),
                "paddock_id": paddock_id,
                "paddock_name": paddock.get("name", paddock_id),
                "order": bay.get("order", 0),
                "is_last_bay": bay.get("is_last_bay", False),
                "supply_1": supply_1,
                "supply_2": supply_2,
                "drain_1": drain_1,
                "drain_2": drain_2,
                "level_sensor": level,
                "has_device": bool(level or supply_1),
                "settings": bay.get("settings", {}),
                "badge_position": badge_pos,
            }
        )
    return sorted(summary, key=lambda x: (x["paddock_name"], x["order"]))


def main() -> int:
    # Load merged config (Registry structure + PWM settings)
    config = load_merged_config()
    server = load_server_yaml()

    # Check if PWM is enabled in server.yaml
    modules = server.get("modules", {})
    pwm_enabled = modules.get("pwm", False)

    # Extract data
    paddocks = config.get("paddocks", {})
    bays = config.get("bays", {})
    farms = extract_farms(server)

    # System status
    initialized = config.get("initialized", False)
    config_ok = REGISTRY_FILE.exists()

    # Build lists for dropdowns
    paddock_names = sorted([p.get("name", pid) for pid, p in paddocks.items()])
    enabled_paddock_ids = [pid for pid, p in paddocks.items() if p.get("enabled", False)]
    farm_names = sorted([f.get("name", fid) for fid, f in farms.items()])

    # Collect devices in use
    device_list = collect_devices(bays)

    # Build summaries
    paddock_summary = build_paddock_summary(paddocks, bays)
    bay_summary = build_bay_summary(bays, paddocks)

    # Count backups
    backup_count = 0
    if BACKUP_DIR.exists():
        backup_count = len(list(BACKUP_DIR.glob("*.json")))

    # Get version
    version = get_version()

    output = {
        # System status
        "status": "ready" if initialized else "not_initialized",
        "initialized": initialized,
        "config_ok": config_ok,
        "pwm_enabled": pwm_enabled,
        "version": version,
        # Counts
        "total_paddocks": len(paddocks),
        "total_bays": len(bays),
        "total_farms": len(farms),
        "enabled_paddock_count": len(enabled_paddock_ids),
        "device_count": len(device_list),
        "backup_count": backup_count,
        # Raw data
        "paddocks": paddocks,
        "bays": bays,
        "farms": farms,
        # Summaries for UI
        "paddock_summary": paddock_summary,
        "bay_summary": bay_summary,
        # Lists for dropdowns
        "paddock_names": paddock_names,
        "enabled_paddock_ids": enabled_paddock_ids,
        "farm_names": farm_names,
        "device_list": device_list,
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
