#!/usr/bin/env python3
"""
HFM Backend - Hey Farmer Module
Voice-assisted farm event recording module.

Commands:
  init              Initialize HFM with default config
  add_event         Add a new farm event
  edit_event        Edit an existing event
  delete_event      Delete an event
  confirm_event     Confirm a pending event
  add_crop_stage    Add a custom crop stage
  delete_crop_stage Delete a crop stage
  add_device        Add/update a device-to-user mapping
  delete_device     Remove a device mapping
  export            Export events to backup file
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import secrets
import string

# Paths
DATA_DIR = Path("/config/local_data/hfm")
CONFIG_FILE = DATA_DIR / "config.json"
EVENTS_FILE = DATA_DIR / "events.json"
BACKUPS_DIR = DATA_DIR / "backups"
VERSION_FILE = Path("/config/PaddiSense/hfm/VERSION")
REGISTRY_FILE = Path("/config/local_data/registry/config.json")
IPM_CONFIG_FILE = Path("/config/local_data/ipm/config.json")


def get_version() -> str:
    """Get module version."""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except (IOError, FileNotFoundError):
        return "unknown"


def generate_event_id() -> str:
    """Generate a unique event ID."""
    chars = string.ascii_lowercase + string.digits
    suffix = ''.join(secrets.choice(chars) for _ in range(8))
    return f"evt_{suffix}"


def now_iso() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def today_date() -> str:
    """Return today's date."""
    return datetime.now().strftime("%Y-%m-%d")


def load_json(path: Path, default: Any = None) -> Any:
    """Load JSON file, returning default if not found or invalid."""
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return default


def save_json(path: Path, data: Any) -> bool:
    """Save data to JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except IOError as e:
        print(f"ERROR: Failed to save {path}: {e}", file=sys.stderr)
        return False


def load_config() -> dict:
    """Load HFM config."""
    return load_json(CONFIG_FILE, {})


def save_config(config: dict) -> bool:
    """Save HFM config."""
    config["modified"] = now_iso()
    return save_json(CONFIG_FILE, config)


def load_events() -> dict:
    """Load events data."""
    return load_json(EVENTS_FILE, {"events": [], "modified": None})


def save_events(data: dict) -> bool:
    """Save events data."""
    data["modified"] = now_iso()
    return save_json(EVENTS_FILE, data)


def load_registry() -> dict:
    """Load registry to get paddocks."""
    return load_json(REGISTRY_FILE, {})


def load_ipm_config() -> dict:
    """Load IPM config to get products."""
    return load_json(IPM_CONFIG_FILE, {})


def get_default_config() -> dict:
    """Return default HFM configuration."""
    return {
        "version": get_version(),
        "crop_stages": [
            {"id": "germination", "name": "Germination", "order": 1},
            {"id": "tillering", "name": "Tillering", "order": 2},
            {"id": "panicle_init", "name": "Panicle Initiation", "order": 3},
            {"id": "flowering", "name": "Flowering", "order": 4},
            {"id": "maturity", "name": "Maturity", "order": 5},
        ],
        "application_methods": [
            {"id": "boom_spray", "name": "Boom Spray"},
            {"id": "broadcast", "name": "Broadcast"},
            {"id": "aerial", "name": "Aerial"},
            {"id": "fertigation", "name": "Fertigation"},
            {"id": "seed_treatment", "name": "Seed Treatment"},
            {"id": "foliar", "name": "Foliar"},
        ],
        "irrigation_types": [
            {"id": "flush", "name": "Flush"},
            {"id": "permanent_water", "name": "Permanent Water"},
            {"id": "drain", "name": "Drain"},
        ],
        "devices": {},
        "voice_enabled": False,
        "created": now_iso(),
        "modified": now_iso(),
    }


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize HFM with default config."""
    # Create directories
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    # Create config if not exists
    if not CONFIG_FILE.exists():
        config = get_default_config()
        if not save_config(config):
            return 1
        print("OK:config_created")
    else:
        print("OK:config_exists")

    # Create events file if not exists
    if not EVENTS_FILE.exists():
        events_data = {"events": [], "modified": now_iso()}
        if not save_events(events_data):
            return 1
        print("OK:events_created")
    else:
        print("OK:events_exists")

    return 0


def cmd_add_event(args: argparse.Namespace) -> int:
    """Add a new farm event."""
    config = load_config()
    if not config:
        print("ERROR: HFM not initialized. Run init first.", file=sys.stderr)
        return 1

    # Validate event type
    valid_types = ["nutrient", "chemical", "irrigation", "crop_stage"]
    if args.event_type not in valid_types:
        print(f"ERROR: Invalid event_type '{args.event_type}'. Must be one of: {valid_types}", file=sys.stderr)
        return 1

    # Parse paddocks (JSON array)
    try:
        paddocks = json.loads(args.paddocks) if args.paddocks else []
    except json.JSONDecodeError:
        # Try as comma-separated string
        paddocks = [p.strip() for p in args.paddocks.split(",") if p.strip()]

    if not paddocks:
        print("ERROR: At least one paddock is required.", file=sys.stderr)
        return 1

    # Validate paddocks against registry
    registry = load_registry()
    reg_paddocks = registry.get("paddocks", {})
    for pid in paddocks:
        if pid not in reg_paddocks:
            print(f"ERROR: Unknown paddock '{pid}'. Check Farm Registry.", file=sys.stderr)
            return 1

    # Parse products (JSON array)
    products = []
    if args.products:
        try:
            products = json.loads(args.products) if args.products else []
        except json.JSONDecodeError:
            print("ERROR: Invalid products JSON.", file=sys.stderr)
            return 1

    # Validate products for nutrient/chemical events
    if args.event_type in ["nutrient", "chemical"] and not products:
        print("ERROR: Products required for nutrient/chemical events.", file=sys.stderr)
        return 1

    # Validate irrigation type
    irrigation_type = None
    if args.event_type == "irrigation":
        if not args.irrigation_type:
            print("ERROR: irrigation_type required for irrigation events.", file=sys.stderr)
            return 1
        valid_irrigation = [it["id"] for it in config.get("irrigation_types", [])]
        if args.irrigation_type not in valid_irrigation:
            print(f"ERROR: Invalid irrigation_type '{args.irrigation_type}'.", file=sys.stderr)
            return 1
        irrigation_type = args.irrigation_type

    # Validate crop stage
    crop_stage = None
    if args.crop_stage:
        valid_stages = [cs["id"] for cs in config.get("crop_stages", [])]
        if args.crop_stage not in valid_stages:
            print(f"ERROR: Invalid crop_stage '{args.crop_stage}'.", file=sys.stderr)
            return 1
        crop_stage = args.crop_stage

    # Validate application method
    application_method = None
    if args.application_method:
        valid_methods = [am["id"] for am in config.get("application_methods", [])]
        if args.application_method not in valid_methods:
            print(f"ERROR: Invalid application_method '{args.application_method}'.", file=sys.stderr)
            return 1
        application_method = args.application_method

    # Determine event date
    event_date = args.event_date if args.event_date else today_date()

    # Create event
    event_id = generate_event_id()
    event = {
        "id": event_id,
        "event_type": args.event_type,
        "event_date": event_date,
        "recorded_at": now_iso(),
        "recorded_by_device": args.device_id or "unknown",
        "paddocks": paddocks,
        "products": products,
        "application_method": application_method,
        "crop_stage": crop_stage,
        "irrigation_type": irrigation_type,
        "notes": args.notes or "",
        "confirmation_status": "confirmed" if not args.pending else "pending",
        "voice_transcript": args.voice_transcript or None,
        "voice_source": args.voice_source or None,
    }

    # Save event
    data = load_events()
    data["events"].append(event)
    if not save_events(data):
        return 1

    print(f"OK:event_added:{event_id}")
    return 0


def cmd_edit_event(args: argparse.Namespace) -> int:
    """Edit an existing event."""
    data = load_events()
    events = data.get("events", [])

    # Find event
    event_idx = None
    for i, evt in enumerate(events):
        if evt.get("id") == args.event_id:
            event_idx = i
            break

    if event_idx is None:
        print(f"ERROR: Event '{args.event_id}' not found.", file=sys.stderr)
        return 1

    event = events[event_idx]
    config = load_config()

    # Update fields if provided
    if args.event_date:
        event["event_date"] = args.event_date

    if args.paddocks:
        try:
            paddocks = json.loads(args.paddocks)
        except json.JSONDecodeError:
            paddocks = [p.strip() for p in args.paddocks.split(",") if p.strip()]
        if paddocks:
            registry = load_registry()
            reg_paddocks = registry.get("paddocks", {})
            for pid in paddocks:
                if pid not in reg_paddocks:
                    print(f"ERROR: Unknown paddock '{pid}'.", file=sys.stderr)
                    return 1
            event["paddocks"] = paddocks

    if args.products:
        try:
            products = json.loads(args.products)
            event["products"] = products
        except json.JSONDecodeError:
            print("ERROR: Invalid products JSON.", file=sys.stderr)
            return 1

    if args.application_method:
        valid_methods = [am["id"] for am in config.get("application_methods", [])]
        if args.application_method not in valid_methods:
            print(f"ERROR: Invalid application_method.", file=sys.stderr)
            return 1
        event["application_method"] = args.application_method

    if args.crop_stage:
        valid_stages = [cs["id"] for cs in config.get("crop_stages", [])]
        if args.crop_stage not in valid_stages:
            print(f"ERROR: Invalid crop_stage.", file=sys.stderr)
            return 1
        event["crop_stage"] = args.crop_stage

    if args.irrigation_type:
        valid_irrigation = [it["id"] for it in config.get("irrigation_types", [])]
        if args.irrigation_type not in valid_irrigation:
            print(f"ERROR: Invalid irrigation_type.", file=sys.stderr)
            return 1
        event["irrigation_type"] = args.irrigation_type

    if args.notes is not None:
        event["notes"] = args.notes

    event["modified_at"] = now_iso()
    events[event_idx] = event
    data["events"] = events

    if not save_events(data):
        return 1

    print(f"OK:event_edited:{args.event_id}")
    return 0


def cmd_delete_event(args: argparse.Namespace) -> int:
    """Delete an event."""
    data = load_events()
    events = data.get("events", [])

    # Find and remove event
    new_events = [e for e in events if e.get("id") != args.event_id]
    if len(new_events) == len(events):
        print(f"ERROR: Event '{args.event_id}' not found.", file=sys.stderr)
        return 1

    data["events"] = new_events
    if not save_events(data):
        return 1

    print(f"OK:event_deleted:{args.event_id}")
    return 0


def cmd_confirm_event(args: argparse.Namespace) -> int:
    """Confirm a pending event."""
    data = load_events()
    events = data.get("events", [])

    for event in events:
        if event.get("id") == args.event_id:
            event["confirmation_status"] = "confirmed"
            event["confirmed_at"] = now_iso()
            if not save_events(data):
                return 1
            print(f"OK:event_confirmed:{args.event_id}")
            return 0

    print(f"ERROR: Event '{args.event_id}' not found.", file=sys.stderr)
    return 1


def cmd_add_crop_stage(args: argparse.Namespace) -> int:
    """Add a custom crop stage."""
    config = load_config()
    if not config:
        print("ERROR: HFM not initialized.", file=sys.stderr)
        return 1

    stages = config.get("crop_stages", [])

    # Check for duplicate ID
    for stage in stages:
        if stage["id"] == args.stage_id:
            print(f"ERROR: Crop stage '{args.stage_id}' already exists.", file=sys.stderr)
            return 1

    # Determine order (add to end)
    max_order = max((s.get("order", 0) for s in stages), default=0)

    stages.append({
        "id": args.stage_id,
        "name": args.name,
        "order": max_order + 1,
    })

    config["crop_stages"] = stages
    if not save_config(config):
        return 1

    print(f"OK:crop_stage_added:{args.stage_id}")
    return 0


def cmd_delete_crop_stage(args: argparse.Namespace) -> int:
    """Delete a crop stage."""
    config = load_config()
    if not config:
        print("ERROR: HFM not initialized.", file=sys.stderr)
        return 1

    stages = config.get("crop_stages", [])
    new_stages = [s for s in stages if s["id"] != args.stage_id]

    if len(new_stages) == len(stages):
        print(f"ERROR: Crop stage '{args.stage_id}' not found.", file=sys.stderr)
        return 1

    config["crop_stages"] = new_stages
    if not save_config(config):
        return 1

    print(f"OK:crop_stage_deleted:{args.stage_id}")
    return 0


def cmd_add_device(args: argparse.Namespace) -> int:
    """Add or update a device-to-user mapping."""
    config = load_config()
    if not config:
        print("ERROR: HFM not initialized.", file=sys.stderr)
        return 1

    devices = config.get("devices", {})
    devices[args.device_id] = {
        "name": args.device_name or args.device_id,
        "user_name": args.user_name,
    }

    config["devices"] = devices
    if not save_config(config):
        return 1

    print(f"OK:device_added:{args.device_id}")
    return 0


def cmd_delete_device(args: argparse.Namespace) -> int:
    """Remove a device mapping."""
    config = load_config()
    if not config:
        print("ERROR: HFM not initialized.", file=sys.stderr)
        return 1

    devices = config.get("devices", {})
    if args.device_id not in devices:
        print(f"ERROR: Device '{args.device_id}' not found.", file=sys.stderr)
        return 1

    del devices[args.device_id]
    config["devices"] = devices
    if not save_config(config):
        return 1

    print(f"OK:device_deleted:{args.device_id}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export events to backup file."""
    data = load_events()
    config = load_config()

    # Create export package
    export_data = {
        "export_type": "hfm_events",
        "exported_at": now_iso(),
        "version": get_version(),
        "config": config,
        "events": data.get("events", []),
    }

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hfm_export_{timestamp}.json"
    export_path = BACKUPS_DIR / filename

    if not save_json(export_path, export_data):
        return 1

    print(f"OK:exported:{export_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="HFM Backend")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    subparsers.add_parser("init", help="Initialize HFM")

    # add_event
    add_event_p = subparsers.add_parser("add_event", help="Add a farm event")
    add_event_p.add_argument("--event_type", required=True, help="Event type: nutrient, chemical, irrigation, crop_stage")
    add_event_p.add_argument("--event_date", help="Event date (YYYY-MM-DD)")
    add_event_p.add_argument("--paddocks", required=True, help="Paddock IDs (JSON array or comma-separated)")
    add_event_p.add_argument("--products", help="Products JSON array")
    add_event_p.add_argument("--application_method", help="Application method ID")
    add_event_p.add_argument("--crop_stage", help="Crop stage ID")
    add_event_p.add_argument("--irrigation_type", help="Irrigation type ID")
    add_event_p.add_argument("--notes", help="Optional notes")
    add_event_p.add_argument("--device_id", help="Recording device ID")
    add_event_p.add_argument("--pending", action="store_true", help="Mark as pending confirmation")
    add_event_p.add_argument("--voice_transcript", help="Voice transcript (for voice-recorded events)")
    add_event_p.add_argument("--voice_source", help="Voice source provider")

    # edit_event
    edit_event_p = subparsers.add_parser("edit_event", help="Edit an event")
    edit_event_p.add_argument("--event_id", required=True, help="Event ID to edit")
    edit_event_p.add_argument("--event_date", help="New event date")
    edit_event_p.add_argument("--paddocks", help="New paddock IDs")
    edit_event_p.add_argument("--products", help="New products JSON")
    edit_event_p.add_argument("--application_method", help="New application method")
    edit_event_p.add_argument("--crop_stage", help="New crop stage")
    edit_event_p.add_argument("--irrigation_type", help="New irrigation type")
    edit_event_p.add_argument("--notes", help="New notes")

    # delete_event
    delete_event_p = subparsers.add_parser("delete_event", help="Delete an event")
    delete_event_p.add_argument("--event_id", required=True, help="Event ID to delete")

    # confirm_event
    confirm_event_p = subparsers.add_parser("confirm_event", help="Confirm a pending event")
    confirm_event_p.add_argument("--event_id", required=True, help="Event ID to confirm")

    # add_crop_stage
    add_stage_p = subparsers.add_parser("add_crop_stage", help="Add a crop stage")
    add_stage_p.add_argument("--stage_id", required=True, help="Unique stage ID")
    add_stage_p.add_argument("--name", required=True, help="Display name")

    # delete_crop_stage
    del_stage_p = subparsers.add_parser("delete_crop_stage", help="Delete a crop stage")
    del_stage_p.add_argument("--stage_id", required=True, help="Stage ID to delete")

    # add_device
    add_device_p = subparsers.add_parser("add_device", help="Add device mapping")
    add_device_p.add_argument("--device_id", required=True, help="Device ID")
    add_device_p.add_argument("--device_name", help="Device display name")
    add_device_p.add_argument("--user_name", required=True, help="User name")

    # delete_device
    del_device_p = subparsers.add_parser("delete_device", help="Remove device mapping")
    del_device_p.add_argument("--device_id", required=True, help="Device ID to remove")

    # export
    subparsers.add_parser("export", help="Export events to backup")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "init": cmd_init,
        "add_event": cmd_add_event,
        "edit_event": cmd_edit_event,
        "delete_event": cmd_delete_event,
        "confirm_event": cmd_confirm_event,
        "add_crop_stage": cmd_add_crop_stage,
        "delete_crop_stage": cmd_delete_crop_stage,
        "add_device": cmd_add_device,
        "delete_device": cmd_delete_device,
        "export": cmd_export,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
