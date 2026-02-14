#!/usr/bin/env python3
"""
Farm Registry Backend - PaddiSense Shared Core
PaddiSense Farm Management System

This script handles all write operations for the farm registry:
  - Paddock management: add_paddock, edit_paddock, delete_paddock
  - Bay management: add_bay, edit_bay, delete_bay
  - Season management: add_season, edit_season, delete_season, set_active_season
  - System: init, status, export, import_backup, reset, backup_list, migrate

Data is stored in: /config/local_data/registry/config.json
Backups are stored in: /config/local_data/registry/backups/

Usage:
  python3 registry_backend.py init
  python3 registry_backend.py status
  python3 registry_backend.py add_paddock --farm farm_1 --name "SW6" --bay_count 5
  python3 registry_backend.py add_season --name "CY26" --start 2025-04-01 --end 2026-03-31
  python3 registry_backend.py set_active_season --id cy26
  python3 registry_backend.py migrate_from_pwm
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# File locations
DATA_DIR = Path("/config/local_data/registry")
CONFIG_FILE = DATA_DIR / "config.json"
CROPS_FILE = DATA_DIR / "crops.json"
BACKUP_DIR = DATA_DIR / "backups"

# PWM data for migration
PWM_CONFIG_FILE = Path("/config/local_data/pwm/config.json")


def generate_id(name: str) -> str:
    """Generate a clean ID from the name."""
    clean = re.sub(r"[^a-z0-9]+", "_", name.lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean[:30] if clean else "unknown"


def load_config() -> dict[str, Any]:
    """Load config from JSON file, or return empty structure."""
    if not CONFIG_FILE.exists():
        return {
            "initialized": False,
            "businesses": {},
            "farms": {},
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
            "businesses": {},
            "farms": {},
            "paddocks": {},
            "bays": {},
            "seasons": {},
            "version": "1.0.0",
        }


def save_config(config: dict[str, Any]) -> None:
    """Save config to JSON file."""
    config["modified"] = datetime.now().isoformat(timespec="seconds")
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def create_backup(tag: str = "") -> Path:
    """Create a timestamped backup of the config file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    suffix = f"_{tag}" if tag else ""
    backup_name = f"backup_{ts}{suffix}.json"
    backup_path = BACKUP_DIR / backup_name
    if CONFIG_FILE.exists():
        backup_path.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def log_transaction(
    config: dict,
    action: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    details: str = "",
) -> None:
    """Append a transaction record for audit trail."""
    config.setdefault("transactions", []).append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "details": details,
        }
    )


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


def save_crops(crops_data: dict[str, Any]) -> None:
    """Save crops config to JSON file."""
    crops_data["modified"] = datetime.now().isoformat(timespec="seconds")
    CROPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CROPS_FILE.write_text(
        json.dumps(crops_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# =============================================================================
# PADDOCK COMMANDS
# =============================================================================


def cmd_add_paddock(args: argparse.Namespace) -> int:
    """Add a new paddock with specified number of bays."""
    config = load_config()
    paddocks = config.setdefault("paddocks", {})
    bays = config.setdefault("bays", {})

    paddock_id = generate_id(args.name)

    # Check if paddock already exists
    if paddock_id in paddocks:
        print(json.dumps({"error": f"Paddock '{paddock_id}' already exists"}))
        return 1

    # Create paddock
    now = datetime.now().isoformat(timespec="seconds")
    bay_prefix = args.bay_prefix or "B-"

    paddock_data = {
        "farm_id": args.farm or "farm_1",
        "name": args.name,
        "bay_prefix": bay_prefix,
        "bay_count": args.bay_count,
        "current_season": args.current_season if args.current_season is not None else True,
        "created": now,
        "modified": now,
    }

    # Add brown area (total paddock area) if provided
    if args.brown_area is not None:
        paddock_data["brown_area_ha"] = args.brown_area

    # Add green area (cropped/irrigated area) if provided
    if args.green_area is not None:
        paddock_data["green_area_ha"] = args.green_area

    paddocks[paddock_id] = paddock_data

    # Create bays
    for i in range(1, args.bay_count + 1):
        bay_name = f"{bay_prefix}{i:02d}"
        bay_id = f"{paddock_id}_{generate_id(bay_name)}"
        is_last = i == args.bay_count

        bays[bay_id] = {
            "paddock_id": paddock_id,
            "name": bay_name,
            "order": i,
            "is_last_bay": is_last,
            "created": now,
            "modified": now,
        }

    log_transaction(
        config, "add", "paddock", paddock_id, args.name,
        f"Created with {args.bay_count} bays"
    )
    save_config(config)

    print(json.dumps({
        "success": True,
        "paddock_id": paddock_id,
        "bay_count": args.bay_count,
        "message": f"Created paddock '{args.name}' with {args.bay_count} bays"
    }))
    return 0


def cmd_edit_paddock(args: argparse.Namespace) -> int:
    """Edit an existing paddock."""
    config = load_config()
    paddocks = config.get("paddocks", {})

    if args.id not in paddocks:
        print(json.dumps({"error": f"Paddock '{args.id}' not found"}))
        return 1

    paddock = paddocks[args.id]
    changes = []

    if args.name is not None:
        paddock["name"] = args.name
        changes.append(f"name={args.name}")

    if args.farm is not None:
        paddock["farm_id"] = args.farm
        changes.append(f"farm={args.farm}")

    if args.current_season is not None:
        paddock["current_season"] = args.current_season
        changes.append(f"current_season={args.current_season}")

    if args.brown_area is not None:
        paddock["brown_area_ha"] = args.brown_area
        changes.append(f"brown_area_ha={args.brown_area}")

    if args.green_area is not None:
        paddock["green_area_ha"] = args.green_area
        changes.append(f"green_area_ha={args.green_area}")

    # Crop 1 assignment (early season crop)
    if args.crop_1_id is not None:
        if args.crop_1_id == "" or args.crop_1_id.lower() == "none":
            # Clear crop 1
            if "crop_1" in paddock:
                del paddock["crop_1"]
                changes.append("crop_1=cleared")
        else:
            crop_1 = paddock.setdefault("crop_1", {})
            crop_1["crop_id"] = args.crop_1_id
            if args.crop_1_start is not None:
                crop_1["start_month"] = args.crop_1_start
            if args.crop_1_end is not None:
                crop_1["end_month"] = args.crop_1_end
            changes.append(f"crop_1={args.crop_1_id}")

    # Crop 2 assignment (late season crop)
    if args.crop_2_id is not None:
        if args.crop_2_id == "" or args.crop_2_id.lower() == "none":
            # Clear crop 2
            if "crop_2" in paddock:
                del paddock["crop_2"]
                changes.append("crop_2=cleared")
        else:
            crop_2 = paddock.setdefault("crop_2", {})
            crop_2["crop_id"] = args.crop_2_id
            if args.crop_2_start is not None:
                crop_2["start_month"] = args.crop_2_start
            if args.crop_2_end is not None:
                crop_2["end_month"] = args.crop_2_end
            changes.append(f"crop_2={args.crop_2_id}")

    paddock["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(
        config, "edit", "paddock", args.id, paddock["name"],
        ", ".join(changes)
    )
    save_config(config)

    print(json.dumps({
        "success": True,
        "paddock_id": args.id,
        "message": f"Updated paddock '{paddock['name']}'"
    }))
    return 0


def cmd_set_current_season(args: argparse.Namespace) -> int:
    """Set paddock current_season flag."""
    config = load_config()
    paddocks = config.get("paddocks", {})

    if args.id not in paddocks:
        print(json.dumps({"error": f"Paddock '{args.id}' not found"}))
        return 1

    paddock = paddocks[args.id]

    # Toggle if no value specified, otherwise set to specified value
    if args.value is not None:
        new_value = args.value
    else:
        new_value = not paddock.get("current_season", True)

    paddock["current_season"] = new_value
    paddock["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(
        config, "set_current_season", "paddock", args.id, paddock["name"],
        f"current_season={new_value}"
    )
    save_config(config)

    print(json.dumps({
        "success": True,
        "paddock_id": args.id,
        "current_season": new_value,
        "message": f"Set {paddock['name']} current_season to {new_value}"
    }))
    return 0


def cmd_delete_paddock(args: argparse.Namespace) -> int:
    """Delete a paddock and all its bays."""
    config = load_config()
    paddocks = config.get("paddocks", {})
    bays = config.get("bays", {})

    if args.id not in paddocks:
        print(json.dumps({"error": f"Paddock '{args.id}' not found"}))
        return 1

    # Create backup before delete
    create_backup("pre_delete")

    paddock_name = paddocks[args.id].get("name", args.id)

    # Delete associated bays
    bays_to_delete = [bid for bid, b in bays.items() if b.get("paddock_id") == args.id]
    for bid in bays_to_delete:
        del bays[bid]

    # Delete paddock
    del paddocks[args.id]

    log_transaction(
        config, "delete", "paddock", args.id, paddock_name,
        f"Deleted with {len(bays_to_delete)} bays"
    )
    save_config(config)

    print(json.dumps({
        "success": True,
        "paddock_id": args.id,
        "bays_deleted": len(bays_to_delete),
        "message": f"Deleted paddock '{paddock_name}' and {len(bays_to_delete)} bays"
    }))
    return 0


# =============================================================================
# BAY COMMANDS
# =============================================================================


def cmd_add_bay(args: argparse.Namespace) -> int:
    """Add a bay to an existing paddock."""
    config = load_config()
    paddocks = config.get("paddocks", {})
    bays = config.setdefault("bays", {})

    if args.paddock not in paddocks:
        print(json.dumps({"error": f"Paddock '{args.paddock}' not found"}))
        return 1

    paddock = paddocks[args.paddock]
    bay_id = f"{args.paddock}_{generate_id(args.name)}"

    if bay_id in bays:
        print(json.dumps({"error": f"Bay '{bay_id}' already exists"}))
        return 1

    # Determine order
    existing_bays = [b for b in bays.values() if b.get("paddock_id") == args.paddock]
    max_order = max([b.get("order", 0) for b in existing_bays], default=0)

    now = datetime.now().isoformat(timespec="seconds")
    bays[bay_id] = {
        "paddock_id": args.paddock,
        "name": args.name,
        "order": args.order if args.order else max_order + 1,
        "is_last_bay": args.is_last or False,
        "created": now,
        "modified": now,
    }

    # Update paddock bay count
    paddock["bay_count"] = len([b for b in bays.values() if b.get("paddock_id") == args.paddock])
    paddock["modified"] = now

    log_transaction(config, "add", "bay", bay_id, args.name, f"Added to {args.paddock}")
    save_config(config)

    print(json.dumps({
        "success": True,
        "bay_id": bay_id,
        "message": f"Added bay '{args.name}' to paddock"
    }))
    return 0


def cmd_edit_bay(args: argparse.Namespace) -> int:
    """Edit bay basic info."""
    config = load_config()
    bays = config.get("bays", {})

    if args.id not in bays:
        print(json.dumps({"error": f"Bay '{args.id}' not found"}))
        return 1

    bay = bays[args.id]
    changes = []

    if args.name is not None:
        bay["name"] = args.name
        changes.append(f"name={args.name}")

    if args.order is not None:
        bay["order"] = args.order
        changes.append(f"order={args.order}")

    if args.is_last is not None:
        bay["is_last_bay"] = args.is_last
        changes.append(f"is_last={args.is_last}")

    bay["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(config, "edit", "bay", args.id, bay["name"], ", ".join(changes))
    save_config(config)

    print(json.dumps({
        "success": True,
        "bay_id": args.id,
        "message": f"Updated bay '{bay['name']}'"
    }))
    return 0


def cmd_delete_bay(args: argparse.Namespace) -> int:
    """Delete a bay."""
    config = load_config()
    bays = config.get("bays", {})
    paddocks = config.get("paddocks", {})

    if args.id not in bays:
        print(json.dumps({"error": f"Bay '{args.id}' not found"}))
        return 1

    bay = bays[args.id]
    bay_name = bay.get("name", args.id)
    paddock_id = bay.get("paddock_id")

    del bays[args.id]

    # Update paddock bay count
    if paddock_id and paddock_id in paddocks:
        paddocks[paddock_id]["bay_count"] = len(
            [b for b in bays.values() if b.get("paddock_id") == paddock_id]
        )
        paddocks[paddock_id]["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(config, "delete", "bay", args.id, bay_name, "")
    save_config(config)

    print(json.dumps({
        "success": True,
        "bay_id": args.id,
        "message": f"Deleted bay '{bay_name}'"
    }))
    return 0


# =============================================================================
# SEASON COMMANDS
# =============================================================================


def cmd_add_season(args: argparse.Namespace) -> int:
    """Add a new season."""
    config = load_config()
    seasons = config.setdefault("seasons", {})

    season_id = generate_id(args.name)

    if season_id in seasons:
        print(json.dumps({"error": f"Season '{season_id}' already exists"}))
        return 1

    now = datetime.now().isoformat(timespec="seconds")
    seasons[season_id] = {
        "name": args.name,
        "start_date": args.start,
        "end_date": args.end,
        "active": args.active or False,
        "created": now,
        "modified": now,
    }

    # If this is set as active, deactivate others
    if args.active:
        for sid, season in seasons.items():
            if sid != season_id:
                season["active"] = False

    log_transaction(config, "add", "season", season_id, args.name, f"{args.start} to {args.end}")
    save_config(config)

    print(json.dumps({
        "success": True,
        "season_id": season_id,
        "message": f"Created season '{args.name}'"
    }))
    return 0


def cmd_edit_season(args: argparse.Namespace) -> int:
    """Edit a season."""
    config = load_config()
    seasons = config.get("seasons", {})

    if args.id not in seasons:
        print(json.dumps({"error": f"Season '{args.id}' not found"}))
        return 1

    season = seasons[args.id]
    changes = []

    if args.name is not None:
        season["name"] = args.name
        changes.append(f"name={args.name}")

    if args.start is not None:
        season["start_date"] = args.start
        changes.append(f"start={args.start}")

    if args.end is not None:
        season["end_date"] = args.end
        changes.append(f"end={args.end}")

    season["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(config, "edit", "season", args.id, season["name"], ", ".join(changes))
    save_config(config)

    print(json.dumps({
        "success": True,
        "season_id": args.id,
        "message": f"Updated season '{season['name']}'"
    }))
    return 0


def cmd_delete_season(args: argparse.Namespace) -> int:
    """Delete a season."""
    config = load_config()
    seasons = config.get("seasons", {})

    if args.id not in seasons:
        print(json.dumps({"error": f"Season '{args.id}' not found"}))
        return 1

    season_name = seasons[args.id].get("name", args.id)
    del seasons[args.id]

    log_transaction(config, "delete", "season", args.id, season_name, "")
    save_config(config)

    print(json.dumps({
        "success": True,
        "season_id": args.id,
        "message": f"Deleted season '{season_name}'"
    }))
    return 0


def cmd_set_active_season(args: argparse.Namespace) -> int:
    """Set the active season."""
    config = load_config()
    seasons = config.get("seasons", {})

    if args.id not in seasons:
        print(json.dumps({"error": f"Season '{args.id}' not found"}))
        return 1

    # Deactivate all, then activate the specified one
    for sid, season in seasons.items():
        season["active"] = sid == args.id
        season["modified"] = datetime.now().isoformat(timespec="seconds")

    season_name = seasons[args.id].get("name", args.id)
    log_transaction(config, "set_active", "season", args.id, season_name, "")
    save_config(config)

    print(json.dumps({
        "success": True,
        "season_id": args.id,
        "message": f"Set active season to '{season_name}'"
    }))
    return 0


# =============================================================================
# FARM COMMANDS
# =============================================================================


def cmd_add_farm(args: argparse.Namespace) -> int:
    """Add a new farm."""
    config = load_config()
    farms = config.setdefault("farms", {})

    farm_id = generate_id(args.name)

    if farm_id in farms:
        print(json.dumps({"error": f"Farm '{farm_id}' already exists"}))
        return 1

    now = datetime.now().isoformat(timespec="seconds")
    farm_data = {
        "name": args.name,
        "created": now,
        "modified": now,
    }

    # Add business assignment if provided
    if args.business:
        businesses = config.get("businesses", {})
        if args.business in businesses:
            farm_data["business_id"] = args.business

    farms[farm_id] = farm_data

    log_transaction(config, "add", "farm", farm_id, args.name, "")
    save_config(config)

    print(json.dumps({
        "success": True,
        "farm_id": farm_id,
        "message": f"Created farm '{args.name}'"
    }))
    return 0


def cmd_edit_farm(args: argparse.Namespace) -> int:
    """Edit an existing farm."""
    config = load_config()
    farms = config.get("farms", {})

    if args.id not in farms:
        print(json.dumps({"error": f"Farm '{args.id}' not found"}))
        return 1

    farm = farms[args.id]
    changes = []

    if args.name is not None:
        farm["name"] = args.name
        changes.append(f"name={args.name}")

    # Business assignment
    if args.business is not None:
        if args.business == "" or args.business.lower() == "none":
            # Clear business assignment
            if "business_id" in farm:
                del farm["business_id"]
                changes.append("business=cleared")
        else:
            businesses = config.get("businesses", {})
            if args.business in businesses:
                farm["business_id"] = args.business
                changes.append(f"business={args.business}")

    farm["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(config, "edit", "farm", args.id, farm["name"], ", ".join(changes))
    save_config(config)

    print(json.dumps({
        "success": True,
        "farm_id": args.id,
        "message": f"Updated farm '{farm['name']}'"
    }))
    return 0


def cmd_delete_farm(args: argparse.Namespace) -> int:
    """Delete a farm (only if no paddocks assigned)."""
    config = load_config()
    farms = config.get("farms", {})
    paddocks = config.get("paddocks", {})

    if args.id not in farms:
        print(json.dumps({"error": f"Farm '{args.id}' not found"}))
        return 1

    # Check for assigned paddocks
    assigned_paddocks = [p for p in paddocks.values() if p.get("farm_id") == args.id]
    if assigned_paddocks:
        print(json.dumps({
            "error": f"Cannot delete farm with {len(assigned_paddocks)} assigned paddocks",
            "paddock_count": len(assigned_paddocks)
        }))
        return 1

    farm_name = farms[args.id].get("name", args.id)
    del farms[args.id]

    log_transaction(config, "delete", "farm", args.id, farm_name, "")
    save_config(config)

    print(json.dumps({
        "success": True,
        "farm_id": args.id,
        "message": f"Deleted farm '{farm_name}'"
    }))
    return 0


# =============================================================================
# BUSINESS COMMANDS
# =============================================================================


def cmd_add_business(args: argparse.Namespace) -> int:
    """Add a new business."""
    config = load_config()
    businesses = config.setdefault("businesses", {})

    business_id = generate_id(args.name)

    if business_id in businesses:
        print(json.dumps({"error": f"Business '{business_id}' already exists"}))
        return 1

    now = datetime.now().isoformat(timespec="seconds")
    businesses[business_id] = {
        "name": args.name,
        "created": now,
        "modified": now,
    }

    log_transaction(config, "add", "business", business_id, args.name, "")
    save_config(config)

    print(json.dumps({
        "success": True,
        "business_id": business_id,
        "message": f"Created business '{args.name}'"
    }))
    return 0


def cmd_edit_business(args: argparse.Namespace) -> int:
    """Edit an existing business."""
    config = load_config()
    businesses = config.get("businesses", {})

    if args.id not in businesses:
        print(json.dumps({"error": f"Business '{args.id}' not found"}))
        return 1

    business = businesses[args.id]
    changes = []

    if args.name is not None:
        business["name"] = args.name
        changes.append(f"name={args.name}")

    business["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(config, "edit", "business", args.id, business["name"], ", ".join(changes))
    save_config(config)

    print(json.dumps({
        "success": True,
        "business_id": args.id,
        "message": f"Updated business '{business['name']}'"
    }))
    return 0


def cmd_delete_business(args: argparse.Namespace) -> int:
    """Delete a business (only if no farms assigned)."""
    config = load_config()
    businesses = config.get("businesses", {})
    farms = config.get("farms", {})

    if args.id not in businesses:
        print(json.dumps({"error": f"Business '{args.id}' not found"}))
        return 1

    # Check for assigned farms
    assigned_farms = [f for f in farms.values() if f.get("business_id") == args.id]
    if assigned_farms:
        print(json.dumps({
            "error": f"Cannot delete business with {len(assigned_farms)} assigned farms",
            "farm_count": len(assigned_farms)
        }))
        return 1

    business_name = businesses[args.id].get("name", args.id)
    del businesses[args.id]

    log_transaction(config, "delete", "business", args.id, business_name, "")
    save_config(config)

    print(json.dumps({
        "success": True,
        "business_id": args.id,
        "message": f"Deleted business '{business_name}'"
    }))
    return 0


# =============================================================================
# CROP COMMANDS
# =============================================================================


def cmd_add_crop(args: argparse.Namespace) -> int:
    """Add a new crop type."""
    crops_data = load_crops()
    crops = crops_data.setdefault("crops", {})

    crop_id = generate_id(args.name)

    if crop_id in crops:
        print(json.dumps({"error": f"Crop '{crop_id}' already exists"}))
        return 1

    # Parse stages from JSON string if provided
    stages = []
    if args.stages:
        try:
            stages = json.loads(args.stages)
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid stages JSON format"}))
            return 1

    crops[crop_id] = {
        "name": args.name,
        "typical_start_month": args.start_month or 1,
        "typical_end_month": args.end_month or 12,
        "spans_new_year": args.start_month and args.end_month and args.start_month > args.end_month,
        "stages": stages,
        "color": args.color or "#4caf50",
    }

    if not crops_data.get("created"):
        crops_data["created"] = datetime.now().isoformat(timespec="seconds")

    save_crops(crops_data)

    print(json.dumps({
        "success": True,
        "crop_id": crop_id,
        "message": f"Created crop type '{args.name}'"
    }))
    return 0


def cmd_edit_crop(args: argparse.Namespace) -> int:
    """Edit an existing crop type."""
    crops_data = load_crops()
    crops = crops_data.get("crops", {})

    if args.id not in crops:
        print(json.dumps({"error": f"Crop '{args.id}' not found"}))
        return 1

    crop = crops[args.id]
    changes = []

    if args.name is not None:
        crop["name"] = args.name
        changes.append(f"name={args.name}")

    if args.start_month is not None:
        crop["typical_start_month"] = args.start_month
        changes.append(f"start_month={args.start_month}")

    if args.end_month is not None:
        crop["typical_end_month"] = args.end_month
        changes.append(f"end_month={args.end_month}")

    # Update spans_new_year based on months
    if args.start_month is not None or args.end_month is not None:
        start = crop.get("typical_start_month", 1)
        end = crop.get("typical_end_month", 12)
        crop["spans_new_year"] = start > end

    if args.stages is not None:
        try:
            crop["stages"] = json.loads(args.stages)
            changes.append("stages=updated")
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid stages JSON format"}))
            return 1

    if args.color is not None:
        crop["color"] = args.color
        changes.append(f"color={args.color}")

    save_crops(crops_data)

    print(json.dumps({
        "success": True,
        "crop_id": args.id,
        "message": f"Updated crop '{crop['name']}'"
    }))
    return 0


def cmd_delete_crop(args: argparse.Namespace) -> int:
    """Delete a crop type."""
    crops_data = load_crops()
    crops = crops_data.get("crops", {})

    if args.id not in crops:
        print(json.dumps({"error": f"Crop '{args.id}' not found"}))
        return 1

    crop_name = crops[args.id].get("name", args.id)
    del crops[args.id]

    save_crops(crops_data)

    print(json.dumps({
        "success": True,
        "crop_id": args.id,
        "message": f"Deleted crop '{crop_name}'"
    }))
    return 0


def cmd_list_crops(args: argparse.Namespace) -> int:
    """List all crop types."""
    crops_data = load_crops()
    crops = crops_data.get("crops", {})

    crop_list = []
    for crop_id, crop in crops.items():
        crop_list.append({
            "id": crop_id,
            "name": crop.get("name", crop_id),
            "start_month": crop.get("typical_start_month"),
            "end_month": crop.get("typical_end_month"),
            "stage_count": len(crop.get("stages", [])),
            "color": crop.get("color", "#4caf50"),
        })

    print(json.dumps({"crops": crop_list}))
    return 0


def cmd_add_crop_stage(args: argparse.Namespace) -> int:
    """Add a stage to a crop type."""
    crops_data = load_crops()
    crops = crops_data.get("crops", {})

    if args.crop_id not in crops:
        print(json.dumps({"error": f"Crop '{args.crop_id}' not found"}))
        return 1

    crop = crops[args.crop_id]
    stages = crop.setdefault("stages", [])

    stage_id = generate_id(args.name)

    # Check if stage already exists
    if any(s.get("id") == stage_id for s in stages):
        print(json.dumps({"error": f"Stage '{stage_id}' already exists in crop"}))
        return 1

    # Determine order
    max_order = max([s.get("order", 0) for s in stages], default=0)
    order = args.order if args.order else max_order + 1

    stages.append({
        "id": stage_id,
        "name": args.name,
        "order": order,
    })

    # Sort stages by order
    stages.sort(key=lambda s: s.get("order", 0))

    save_crops(crops_data)

    print(json.dumps({
        "success": True,
        "crop_id": args.crop_id,
        "stage_id": stage_id,
        "message": f"Added stage '{args.name}' to crop '{crop['name']}'"
    }))
    return 0


def cmd_delete_crop_stage(args: argparse.Namespace) -> int:
    """Delete a stage from a crop type."""
    crops_data = load_crops()
    crops = crops_data.get("crops", {})

    if args.crop_id not in crops:
        print(json.dumps({"error": f"Crop '{args.crop_id}' not found"}))
        return 1

    crop = crops[args.crop_id]
    stages = crop.get("stages", [])

    # Find and remove stage
    stage_name = args.stage_id
    original_len = len(stages)
    stages[:] = [s for s in stages if s.get("id") != args.stage_id]

    if len(stages) == original_len:
        print(json.dumps({"error": f"Stage '{args.stage_id}' not found in crop"}))
        return 1

    save_crops(crops_data)

    print(json.dumps({
        "success": True,
        "crop_id": args.crop_id,
        "message": f"Deleted stage from crop '{crop['name']}'"
    }))
    return 0


# =============================================================================
# SYSTEM COMMANDS
# =============================================================================


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize the registry system."""
    config = load_config()

    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if config.get("initialized"):
        print(json.dumps({
            "success": True,
            "message": "Registry already initialized",
            "paddock_count": len(config.get("paddocks", {})),
            "bay_count": len(config.get("bays", {})),
            "season_count": len(config.get("seasons", {})),
        }))
        return 0

    # Initialize
    now = datetime.now().isoformat(timespec="seconds")
    config["initialized"] = True
    config["version"] = "1.0.0"
    config.setdefault("paddocks", {})
    config.setdefault("bays", {})
    config.setdefault("seasons", {})
    config.setdefault("transactions", [])
    config["created"] = now
    config["modified"] = now

    save_config(config)

    print(json.dumps({
        "success": True,
        "message": "Farm Registry initialized",
    }))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Return system status."""
    config = load_config()

    paddocks = config.get("paddocks", {})
    bays = config.get("bays", {})
    seasons = config.get("seasons", {})

    # Get active season
    active_season = None
    for sid, s in seasons.items():
        if s.get("active"):
            active_season = sid
            break

    # Count backups
    backup_count = len(list(BACKUP_DIR.glob("*.json"))) if BACKUP_DIR.exists() else 0

    status = {
        "initialized": config.get("initialized", False),
        "config_exists": CONFIG_FILE.exists(),
        "version": config.get("version", "unknown"),
        "total_paddocks": len(paddocks),
        "total_bays": len(bays),
        "total_seasons": len(seasons),
        "active_season": active_season,
        "transaction_count": len(config.get("transactions", [])),
        "backup_count": backup_count,
        "created": config.get("created"),
        "modified": config.get("modified"),
    }

    print(json.dumps(status))
    return 0


def cmd_migrate_from_pwm(args: argparse.Namespace) -> int:
    """Migrate paddock/bay data from PWM to registry."""
    if not PWM_CONFIG_FILE.exists():
        print(json.dumps({"error": "PWM config not found"}))
        return 1

    try:
        pwm_data = json.loads(PWM_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        print(json.dumps({"error": f"Failed to read PWM config: {e}"}))
        return 1

    config = load_config()

    # Create backup before migration
    if CONFIG_FILE.exists():
        create_backup("pre_migration")

    now = datetime.now().isoformat(timespec="seconds")

    # Migrate paddocks (extract registry-relevant fields only)
    pwm_paddocks = pwm_data.get("paddocks", {})
    registry_paddocks = config.setdefault("paddocks", {})

    for pid, paddock in pwm_paddocks.items():
        if pid not in registry_paddocks:
            registry_paddocks[pid] = {
                "farm_id": paddock.get("farm_id", "farm_1"),
                "name": paddock.get("name", pid),
                "bay_prefix": paddock.get("bay_prefix", "B-"),
                "bay_count": paddock.get("bay_count", 0),
                "current_season": paddock.get("current_season", True),
                "created": paddock.get("created", now),
                "modified": now,
            }

    # Migrate bays (extract registry-relevant fields only)
    pwm_bays = pwm_data.get("bays", {})
    registry_bays = config.setdefault("bays", {})

    for bid, bay in pwm_bays.items():
        if bid not in registry_bays:
            registry_bays[bid] = {
                "paddock_id": bay.get("paddock_id", ""),
                "name": bay.get("name", bid),
                "order": bay.get("order", 0),
                "is_last_bay": bay.get("is_last_bay", False),
                "created": bay.get("created", now) if "created" in bay else now,
                "modified": now,
            }

    config["initialized"] = True
    config["version"] = "1.0.0"
    config["created"] = config.get("created", now)
    config["modified"] = now

    log_transaction(
        config, "migrate", "system", "pwm",
        f"Migrated {len(pwm_paddocks)} paddocks, {len(pwm_bays)} bays",
        "From PWM config"
    )
    save_config(config)

    print(json.dumps({
        "success": True,
        "paddocks_migrated": len(pwm_paddocks),
        "bays_migrated": len(pwm_bays),
        "message": "Migration from PWM complete"
    }))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export config to a timestamped backup."""
    if not CONFIG_FILE.exists():
        print(json.dumps({"error": "No config file to export"}))
        return 1

    backup_path = create_backup("export")

    print(json.dumps({
        "success": True,
        "backup_file": str(backup_path.name),
        "message": f"Exported to {backup_path.name}"
    }))
    return 0


def cmd_import_backup(args: argparse.Namespace) -> int:
    """Import config from a backup file."""
    backup_path = BACKUP_DIR / args.filename

    if not backup_path.exists():
        print(json.dumps({"error": f"Backup file '{args.filename}' not found"}))
        return 1

    # Create pre-import backup
    if CONFIG_FILE.exists():
        create_backup("pre_import")

    try:
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        # Validate structure
        if "paddocks" not in backup_data and "bays" not in backup_data:
            print(json.dumps({"error": "Invalid backup file structure"}))
            return 1

        save_config(backup_data)

        print(json.dumps({
            "success": True,
            "message": f"Imported from {args.filename}",
            "paddock_count": len(backup_data.get("paddocks", {})),
            "bay_count": len(backup_data.get("bays", {})),
        }))
        return 0
    except (json.JSONDecodeError, IOError) as e:
        print(json.dumps({"error": f"Failed to import: {e}"}))
        return 1


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset the system (requires confirmation token)."""
    if args.token != "CONFIRM_RESET":
        print(json.dumps({
            "error": "Reset requires --token CONFIRM_RESET",
            "message": "This will delete all paddock, bay, and season data!"
        }))
        return 1

    # Create backup before reset
    if CONFIG_FILE.exists():
        create_backup("pre_reset")

    # Reset to empty state
    now = datetime.now().isoformat(timespec="seconds")
    config = {
        "initialized": True,
        "paddocks": {},
        "bays": {},
        "seasons": {},
        "transactions": [],
        "version": "1.0.0",
        "created": now,
        "modified": now,
    }
    save_config(config)

    print(json.dumps({
        "success": True,
        "message": "Registry reset complete. All paddocks, bays, and seasons deleted."
    }))
    return 0


def cmd_backup_list(args: argparse.Namespace) -> int:
    """List available backup files."""
    if not BACKUP_DIR.exists():
        print(json.dumps({"backups": []}))
        return 0

    backups = sorted(BACKUP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    backup_list = []
    for b in backups[:20]:  # Last 20
        backup_list.append({
            "filename": b.name,
            "size": b.stat().st_size,
            "modified": datetime.fromtimestamp(b.stat().st_mtime).isoformat(timespec="seconds"),
        })

    print(json.dumps({"backups": backup_list}))
    return 0


# =============================================================================
# MAIN
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="Farm Registry Backend")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Paddock commands
    p_add = subparsers.add_parser("add_paddock", help="Add a new paddock")
    p_add.add_argument("--farm", help="Farm ID (default: farm_1)")
    p_add.add_argument("--name", required=True, help="Paddock name")
    p_add.add_argument("--bay_prefix", default="B-", help="Bay prefix (e.g., B-)")
    p_add.add_argument("--bay_count", type=int, required=True, help="Number of bays")
    p_add.add_argument("--current_season", type=lambda x: x.lower() == "true",
                       help="Is paddock in current season (true/false)")
    p_add.add_argument("--brown_area", type=float, help="Brown area (total paddock) in hectares")
    p_add.add_argument("--green_area", type=float, help="Green area (cropped/irrigated) in hectares")

    p_edit = subparsers.add_parser("edit_paddock", help="Edit a paddock")
    p_edit.add_argument("--id", required=True, help="Paddock ID")
    p_edit.add_argument("--name", help="New name")
    p_edit.add_argument("--farm", help="Farm ID")
    p_edit.add_argument("--current_season", type=lambda x: x.lower() == "true",
                        help="Is paddock in current season (true/false)")
    p_edit.add_argument("--brown_area", type=float, help="Brown area (total paddock) in hectares")
    p_edit.add_argument("--green_area", type=float, help="Green area (cropped/irrigated) in hectares")
    # Crop rotation arguments
    p_edit.add_argument("--crop_1_id", help="Crop 1 ID (early season)")
    p_edit.add_argument("--crop_1_start", type=int, help="Crop 1 start month (1-12)")
    p_edit.add_argument("--crop_1_end", type=int, help="Crop 1 end month (1-12)")
    p_edit.add_argument("--crop_2_id", help="Crop 2 ID (late season)")
    p_edit.add_argument("--crop_2_start", type=int, help="Crop 2 start month (1-12)")
    p_edit.add_argument("--crop_2_end", type=int, help="Crop 2 end month (1-12)")

    p_del = subparsers.add_parser("delete_paddock", help="Delete a paddock")
    p_del.add_argument("--id", required=True, help="Paddock ID")

    p_season = subparsers.add_parser("set_current_season", help="Set paddock current_season flag")
    p_season.add_argument("--id", required=True, help="Paddock ID")
    p_season.add_argument("--value", type=lambda x: x.lower() == "true",
                          help="Current season value (true/false); omit to toggle")

    # Bay commands
    b_add = subparsers.add_parser("add_bay", help="Add a bay to a paddock")
    b_add.add_argument("--paddock", required=True, help="Paddock ID")
    b_add.add_argument("--name", required=True, help="Bay name")
    b_add.add_argument("--order", type=int, help="Bay order")
    b_add.add_argument("--is_last", action="store_true", help="Mark as last bay")

    b_edit = subparsers.add_parser("edit_bay", help="Edit bay info")
    b_edit.add_argument("--id", required=True, help="Bay ID")
    b_edit.add_argument("--name", help="New name")
    b_edit.add_argument("--order", type=int, help="New order")
    b_edit.add_argument("--is_last", type=lambda x: x.lower() == "true", help="Is last bay (true/false)")

    b_del = subparsers.add_parser("delete_bay", help="Delete a bay")
    b_del.add_argument("--id", required=True, help="Bay ID")

    # Season commands
    s_add = subparsers.add_parser("add_season", help="Add a season")
    s_add.add_argument("--name", required=True, help="Season name (e.g., CY26)")
    s_add.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    s_add.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    s_add.add_argument("--active", action="store_true", help="Set as active season")

    s_edit = subparsers.add_parser("edit_season", help="Edit a season")
    s_edit.add_argument("--id", required=True, help="Season ID")
    s_edit.add_argument("--name", help="New name")
    s_edit.add_argument("--start", help="New start date")
    s_edit.add_argument("--end", help="New end date")

    s_del = subparsers.add_parser("delete_season", help="Delete a season")
    s_del.add_argument("--id", required=True, help="Season ID")

    s_active = subparsers.add_parser("set_active_season", help="Set active season")
    s_active.add_argument("--id", required=True, help="Season ID")

    # Farm commands
    f_add = subparsers.add_parser("add_farm", help="Add a new farm")
    f_add.add_argument("--name", required=True, help="Farm name")
    f_add.add_argument("--business", help="Business ID to assign farm to")

    f_edit = subparsers.add_parser("edit_farm", help="Edit a farm")
    f_edit.add_argument("--id", required=True, help="Farm ID")
    f_edit.add_argument("--name", help="New name")
    f_edit.add_argument("--business", help="Business ID (use empty string to clear)")

    f_del = subparsers.add_parser("delete_farm", help="Delete a farm")
    f_del.add_argument("--id", required=True, help="Farm ID")

    # Business commands
    b_add = subparsers.add_parser("add_business", help="Add a new business")
    b_add.add_argument("--name", required=True, help="Business name")

    b_edit = subparsers.add_parser("edit_business", help="Edit a business")
    b_edit.add_argument("--id", required=True, help="Business ID")
    b_edit.add_argument("--name", help="New name")

    b_del = subparsers.add_parser("delete_business", help="Delete a business")
    b_del.add_argument("--id", required=True, help="Business ID")

    # Crop commands
    c_add = subparsers.add_parser("add_crop", help="Add a new crop type")
    c_add.add_argument("--name", required=True, help="Crop name")
    c_add.add_argument("--start_month", type=int, help="Typical start month (1-12)")
    c_add.add_argument("--end_month", type=int, help="Typical end month (1-12)")
    c_add.add_argument("--stages", help="JSON array of stages")
    c_add.add_argument("--color", help="Hex color code")

    c_edit = subparsers.add_parser("edit_crop", help="Edit a crop type")
    c_edit.add_argument("--id", required=True, help="Crop ID")
    c_edit.add_argument("--name", help="New name")
    c_edit.add_argument("--start_month", type=int, help="Typical start month (1-12)")
    c_edit.add_argument("--end_month", type=int, help="Typical end month (1-12)")
    c_edit.add_argument("--stages", help="JSON array of stages")
    c_edit.add_argument("--color", help="Hex color code")

    c_del = subparsers.add_parser("delete_crop", help="Delete a crop type")
    c_del.add_argument("--id", required=True, help="Crop ID")

    subparsers.add_parser("list_crops", help="List all crop types")

    cs_add = subparsers.add_parser("add_crop_stage", help="Add a stage to a crop")
    cs_add.add_argument("--crop_id", required=True, help="Crop ID")
    cs_add.add_argument("--name", required=True, help="Stage name")
    cs_add.add_argument("--order", type=int, help="Stage order")

    cs_del = subparsers.add_parser("delete_crop_stage", help="Delete a stage from a crop")
    cs_del.add_argument("--crop_id", required=True, help="Crop ID")
    cs_del.add_argument("--stage_id", required=True, help="Stage ID")

    # System commands
    subparsers.add_parser("init", help="Initialize the system")
    subparsers.add_parser("status", help="Get system status")
    subparsers.add_parser("export", help="Export to backup")
    subparsers.add_parser("migrate_from_pwm", help="Migrate data from PWM config")

    p_import = subparsers.add_parser("import_backup", help="Import from backup")
    p_import.add_argument("--filename", required=True, help="Backup filename")

    p_reset = subparsers.add_parser("reset", help="Reset system (destructive)")
    p_reset.add_argument("--token", required=True, help="Confirmation token")

    subparsers.add_parser("backup_list", help="List backup files")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "add_paddock": cmd_add_paddock,
        "edit_paddock": cmd_edit_paddock,
        "delete_paddock": cmd_delete_paddock,
        "set_current_season": cmd_set_current_season,
        "add_bay": cmd_add_bay,
        "edit_bay": cmd_edit_bay,
        "delete_bay": cmd_delete_bay,
        "add_season": cmd_add_season,
        "edit_season": cmd_edit_season,
        "delete_season": cmd_delete_season,
        "set_active_season": cmd_set_active_season,
        "add_farm": cmd_add_farm,
        "edit_farm": cmd_edit_farm,
        "delete_farm": cmd_delete_farm,
        "add_business": cmd_add_business,
        "edit_business": cmd_edit_business,
        "delete_business": cmd_delete_business,
        "add_crop": cmd_add_crop,
        "edit_crop": cmd_edit_crop,
        "delete_crop": cmd_delete_crop,
        "list_crops": cmd_list_crops,
        "add_crop_stage": cmd_add_crop_stage,
        "delete_crop_stage": cmd_delete_crop_stage,
        "init": cmd_init,
        "status": cmd_status,
        "migrate_from_pwm": cmd_migrate_from_pwm,
        "export": cmd_export,
        "import_backup": cmd_import_backup,
        "reset": cmd_reset,
        "backup_list": cmd_backup_list,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)

    print(json.dumps({"error": f"Unknown command: {args.command}"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
