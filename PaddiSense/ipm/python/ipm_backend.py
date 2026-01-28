#!/usr/bin/env python3
"""
IPM Backend - Inventory Product Manager
PaddiSense Farm Management System

This script handles all write operations for the inventory system:
  - add_product: Add a new product to the inventory
  - edit_product: Update an existing product's details
  - move_stock: Adjust stock levels at a specific location
  - Configuration management (categories, actives, groups, units)

Data is stored in: /config/local_data/ipm/inventory.json
Config is stored in: /config/local_data/ipm/config.json (v2.0.0 format)
This file is NOT tracked in git - each farm maintains their own inventory.

Usage:
  python3 ipm_backend.py add_product --name "Urea" --category "Fertiliser" ...
  python3 ipm_backend.py edit_product --id "UREA" --name "Urea Granular" ...
  python3 ipm_backend.py move_stock --id "UREA" --location "Silo 1" --delta -50
  python3 ipm_backend.py add_category --name "NewCategory"
  python3 ipm_backend.py migrate_config
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Data file locations (outside of git-tracked folders)
DATA_DIR = Path("/config/local_data/ipm")
DATA_FILE = DATA_DIR / "inventory.json"
CONFIG_FILE = DATA_DIR / "config.json"
BACKUP_DIR = DATA_DIR / "backups"
LOCK_DIR = DATA_DIR / "locks"

# Current config version
CONFIG_VERSION = "2.0.0"

# Lock settings
LOCK_TIMEOUT_SECONDS = 300  # 5 minutes

# Default locations (used when creating initial config)
DEFAULT_LOCATIONS = [
    "Chem Shed",
    "Seed Shed",
    "Oil Shed",
]

# Default categories with subcategories
DEFAULT_CATEGORIES = {
    "Chemical": [
        "Adjuvant",
        "Fungicide",
        "Herbicide",
        "Insecticide",
        "Pesticide",
        "Rodenticide",
        "Seed Treatment",
    ],
    "Fertiliser": [
        "Nitrogen",
        "Phosphorus",
        "Potassium",
        "NPK Blend",
        "Trace Elements",
        "Organic",
    ],
    "Seed": [
        "Wheat",
        "Barley",
        "Canola",
        "Rice",
        "Oats",
        "Pasture",
        "Other",
    ],
    "Hay": [
        "Barley",
        "Wheat",
        "Clover",
        "Lucerne",
        "Vetch",
        "Other",
    ],
    "Lubricant": [
        "Engine Oil",
        "Hydraulic Oil",
        "Grease",
        "Gear Oil",
        "Transmission Fluid",
        "Coolant",
    ],
}

# Default chemical groups
DEFAULT_CHEMICAL_GROUPS = [
    "None", "N/A", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "11", "12", "13", "14", "15", "22", "M"
]

# Default units organized by type
DEFAULT_UNITS = {
    "product": ["None", "L", "kg", "ea", "t", "mL"],
    "container": ["1", "5", "10", "20", "110", "200", "400", "1000", "bulk"],
    "application": ["L/ha", "mL/ha", "kg/ha", "g/ha", "t/ha", "mL/100L", "g/100L"],
    "concentration": ["g/L", "g/kg", "mL/L", "%"],
}

# Standard active constituents list (merged into config on init/migration)
DEFAULT_ACTIVES = [
    # Herbicides
    {"name": "2,4-D", "common_groups": ["4"]},
    {"name": "Atrazine", "common_groups": ["5"]},
    {"name": "Bromoxynil", "common_groups": ["6"]},
    {"name": "Carfentrazone-ethyl", "common_groups": ["14"]},
    {"name": "Clethodim", "common_groups": ["1"]},
    {"name": "Clodinafop-propargyl", "common_groups": ["1"]},
    {"name": "Clopyralid", "common_groups": ["4"]},
    {"name": "Dicamba", "common_groups": ["4"]},
    {"name": "Diflufenican", "common_groups": ["12"]},
    {"name": "Diquat", "common_groups": ["22"]},
    {"name": "Fenoxaprop-P-ethyl", "common_groups": ["1"]},
    {"name": "Florasulam", "common_groups": ["2"]},
    {"name": "Fluazifop-P-butyl", "common_groups": ["1"]},
    {"name": "Flumetsulam", "common_groups": ["2"]},
    {"name": "Fluroxypyr", "common_groups": ["4"]},
    {"name": "Glufosinate-ammonium", "common_groups": ["10"]},
    {"name": "Glyphosate", "common_groups": ["9"]},
    {"name": "Haloxyfop", "common_groups": ["1"]},
    {"name": "Imazamox", "common_groups": ["2"]},
    {"name": "Imazapic", "common_groups": ["2"]},
    {"name": "Imazapyr", "common_groups": ["2"]},
    {"name": "Imazethapyr", "common_groups": ["2"]},
    {"name": "MCPA", "common_groups": ["4"]},
    {"name": "Mesotrione", "common_groups": ["27"]},
    {"name": "Metolachlor", "common_groups": ["15"]},
    {"name": "Metsulfuron-methyl", "common_groups": ["2"]},
    {"name": "Paraquat", "common_groups": ["22"]},
    {"name": "Pendimethalin", "common_groups": ["3"]},
    {"name": "Picloram", "common_groups": ["4"]},
    {"name": "Pinoxaden", "common_groups": ["1"]},
    {"name": "Propaquizafop", "common_groups": ["1"]},
    {"name": "Prosulfocarb", "common_groups": ["15"]},
    {"name": "Pyroxasulfone", "common_groups": ["15"]},
    {"name": "Pyroxsulam", "common_groups": ["2"]},
    {"name": "Quizalofop-P-ethyl", "common_groups": ["1"]},
    {"name": "Sethoxydim", "common_groups": ["1"]},
    {"name": "Simazine", "common_groups": ["5"]},
    {"name": "Sulfometuron-methyl", "common_groups": ["2"]},
    {"name": "Sulfosulfuron", "common_groups": ["2"]},
    {"name": "Terbuthylazine", "common_groups": ["5"]},
    {"name": "Triallate", "common_groups": ["8"]},
    {"name": "Tribenuron-methyl", "common_groups": ["2"]},
    {"name": "Triclopyr", "common_groups": ["4"]},
    {"name": "Trifluralin", "common_groups": ["3"]},
    {"name": "Trifloxysulfuron", "common_groups": ["2"]},
    # Fungicides
    {"name": "Azoxystrobin", "common_groups": ["11"]},
    {"name": "Bixafen", "common_groups": ["7"]},
    {"name": "Boscalid", "common_groups": ["7"]},
    {"name": "Carbendazim", "common_groups": ["1"]},
    {"name": "Chlorothalonil", "common_groups": ["M"]},
    {"name": "Cyproconazole", "common_groups": ["3"]},
    {"name": "Difenoconazole", "common_groups": ["3"]},
    {"name": "Epoxiconazole", "common_groups": ["3"]},
    {"name": "Fludioxonil", "common_groups": ["12"]},
    {"name": "Fluopyram", "common_groups": ["7"]},
    {"name": "Flutriafol", "common_groups": ["3"]},
    {"name": "Fluxapyroxad", "common_groups": ["7"]},
    {"name": "Iprodione", "common_groups": ["2"]},
    {"name": "Isopyrazam", "common_groups": ["7"]},
    {"name": "Mancozeb", "common_groups": ["M"]},
    {"name": "Metalaxyl", "common_groups": ["4"]},
    {"name": "Propiconazole", "common_groups": ["3"]},
    {"name": "Prothioconazole", "common_groups": ["3"]},
    {"name": "Pyraclostrobin", "common_groups": ["11"]},
    {"name": "Tebuconazole", "common_groups": ["3"]},
    {"name": "Thiram", "common_groups": ["M"]},
    {"name": "Triadimefon", "common_groups": ["3"]},
    {"name": "Triadimenol", "common_groups": ["3"]},
    {"name": "Trifloxystrobin", "common_groups": ["11"]},
    # Insecticides
    {"name": "Abamectin", "common_groups": ["6"]},
    {"name": "Acetamiprid", "common_groups": ["4A"]},
    {"name": "Alpha-cypermethrin", "common_groups": ["3A"]},
    {"name": "Bifenthrin", "common_groups": ["3A"]},
    {"name": "Chlorantraniliprole", "common_groups": ["28"]},
    {"name": "Chlorpyrifos", "common_groups": ["1B"]},
    {"name": "Clothianidin", "common_groups": ["4A"]},
    {"name": "Cyantraniliprole", "common_groups": ["28"]},
    {"name": "Cypermethrin", "common_groups": ["3A"]},
    {"name": "Deltamethrin", "common_groups": ["3A"]},
    {"name": "Dimethoate", "common_groups": ["1B"]},
    {"name": "Emamectin benzoate", "common_groups": ["6"]},
    {"name": "Esfenvalerate", "common_groups": ["3A"]},
    {"name": "Fipronil", "common_groups": ["2B"]},
    {"name": "Imidacloprid", "common_groups": ["4A"]},
    {"name": "Indoxacarb", "common_groups": ["22A"]},
    {"name": "Lambda-cyhalothrin", "common_groups": ["3A"]},
    {"name": "Malathion", "common_groups": ["1B"]},
    {"name": "Methomyl", "common_groups": ["1A"]},
    {"name": "Omethoate", "common_groups": ["1B"]},
    {"name": "Pirimicarb", "common_groups": ["1A"]},
    {"name": "Spinetoram", "common_groups": ["5"]},
    {"name": "Spinosad", "common_groups": ["5"]},
    {"name": "Sulfoxaflor", "common_groups": ["4C"]},
    {"name": "Thiacloprid", "common_groups": ["4A"]},
    {"name": "Thiamethoxam", "common_groups": ["4A"]},
    # Seed Treatments
    {"name": "Ipconazole", "common_groups": ["3"]},
    {"name": "Metalaxyl-M", "common_groups": ["4"]},
    {"name": "Sedaxane", "common_groups": ["7"]},
    {"name": "Triticonazole", "common_groups": ["3"]},
    # Fertiliser Elements
    {"name": "Boron", "common_groups": []},
    {"name": "Calcium", "common_groups": []},
    {"name": "Copper", "common_groups": []},
    {"name": "Iron", "common_groups": []},
    {"name": "Magnesium", "common_groups": []},
    {"name": "Manganese", "common_groups": []},
    {"name": "Molybdenum", "common_groups": []},
    {"name": "Nitrogen", "common_groups": []},
    {"name": "Phosphorus", "common_groups": []},
    {"name": "Potassium", "common_groups": []},
    {"name": "Sulfur", "common_groups": []},
    {"name": "Zinc", "common_groups": []},
    # Adjuvants
    {"name": "Alcohol ethoxylate", "common_groups": []},
    {"name": "Ammonium sulfate", "common_groups": []},
    {"name": "Methylated seed oil", "common_groups": []},
    {"name": "Organosilicone", "common_groups": []},
    {"name": "Paraffin oil", "common_groups": []},
    {"name": "Petroleum oil", "common_groups": []},
]


def generate_id(name: str) -> str:
    """Generate a clean product ID from the name."""
    # Convert to uppercase, replace non-alphanumeric with underscore
    clean = re.sub(r"[^A-Z0-9]+", "_", name.upper())
    # Remove leading/trailing underscores and collapse multiples
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean[:20] if clean else "UNKNOWN"


def load_inventory() -> dict[str, Any]:
    """Load inventory from JSON file, or return empty structure."""
    if not DATA_FILE.exists():
        return {"products": {}, "transactions": []}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {"products": {}, "transactions": []}


def save_inventory(data: dict[str, Any]) -> None:
    """Save inventory to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def load_config() -> dict[str, Any]:
    """Load config from JSON file, or return default v2.0.0 structure."""
    if not CONFIG_FILE.exists():
        return create_default_config()
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # Check if migration is needed
        if config.get("version") != CONFIG_VERSION:
            return config  # Return as-is, caller should migrate
        return config
    except (json.JSONDecodeError, IOError):
        return create_default_config()


def create_default_config() -> dict[str, Any]:
    """Create a new default config with v2.0.0 structure."""
    return {
        "version": CONFIG_VERSION,
        "categories": DEFAULT_CATEGORIES.copy(),
        "chemical_groups": DEFAULT_CHEMICAL_GROUPS.copy(),
        "actives": [a.copy() for a in DEFAULT_ACTIVES],
        "locations": DEFAULT_LOCATIONS.copy(),
        "units": {k: v.copy() for k, v in DEFAULT_UNITS.items()},
        "created": datetime.now().isoformat(timespec="seconds"),
        "modified": datetime.now().isoformat(timespec="seconds"),
    }


def save_config(config: dict[str, Any]) -> None:
    """Save config to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config["modified"] = datetime.now().isoformat(timespec="seconds")
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def ensure_migrated_config() -> dict[str, Any]:
    """Load config, migrating if necessary. Always returns v2.0.0 format."""
    if not CONFIG_FILE.exists():
        config = create_default_config()
        save_config(config)
        return config

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if config.get("version") == CONFIG_VERSION:
        return config

    # Migration needed
    return migrate_config_internal(config)


def migrate_config_internal(old_config: dict[str, Any]) -> dict[str, Any]:
    """Migrate old config format to v2.0.0."""
    # Preserve existing data
    old_locations = old_config.get("locations", DEFAULT_LOCATIONS.copy())
    old_custom_actives = old_config.get("custom_actives", [])

    # Build merged actives list
    actives = [a.copy() for a in DEFAULT_ACTIVES]
    existing_names = {a["name"].lower() for a in actives}

    # Add custom actives that aren't duplicates
    for custom in old_custom_actives:
        if isinstance(custom, dict) and custom.get("name"):
            name = custom["name"]
            if name.lower() not in existing_names:
                actives.append({
                    "name": name,
                    "common_groups": custom.get("common_groups", []),
                })
                existing_names.add(name.lower())

    # Sort actives alphabetically
    actives.sort(key=lambda x: x["name"].lower())

    new_config = {
        "version": CONFIG_VERSION,
        "categories": DEFAULT_CATEGORIES.copy(),
        "chemical_groups": DEFAULT_CHEMICAL_GROUPS.copy(),
        "actives": actives,
        "locations": old_locations,
        "units": {k: v.copy() for k, v in DEFAULT_UNITS.items()},
        "created": old_config.get("created", datetime.now().isoformat(timespec="seconds")),
        "modified": datetime.now().isoformat(timespec="seconds"),
    }

    return new_config


# =========================================================================
# LOCKING FUNCTIONS
# =========================================================================

def get_lock_file(entity_type: str, entity_id: str) -> Path:
    """Get the lock file path for an entity."""
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", entity_id)
    return LOCK_DIR / f"{entity_type}_{safe_id}.lock"


def is_lock_expired(lock_data: dict[str, Any]) -> bool:
    """Check if a lock has expired."""
    expires_at = lock_data.get("expires_at", "")
    if not expires_at:
        return True
    try:
        expiry_time = datetime.fromisoformat(expires_at)
        return datetime.now() > expiry_time
    except ValueError:
        return True


def load_lock(entity_type: str, entity_id: str) -> dict[str, Any] | None:
    """Load lock data for an entity, or None if no valid lock exists."""
    lock_file = get_lock_file(entity_type, entity_id)
    if not lock_file.exists():
        return None
    try:
        lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
        if is_lock_expired(lock_data):
            # Clean up expired lock
            lock_file.unlink(missing_ok=True)
            return None
        return lock_data
    except (json.JSONDecodeError, IOError):
        return None


def acquire_lock(
    entity_type: str,
    entity_id: str,
    session_id: str,
    lock_type: str = "edit"
) -> tuple[bool, str]:
    """
    Attempt to acquire a lock on an entity.
    Returns (success, message).
    """
    LOCK_DIR.mkdir(parents=True, exist_ok=True)

    existing = load_lock(entity_type, entity_id)
    if existing:
        if existing.get("session_id") == session_id:
            # Same session - refresh the lock
            pass
        else:
            # Locked by someone else
            locked_by = existing.get("session_id", "unknown")
            locked_at = existing.get("locked_at", "unknown")
            return False, f"Locked by {locked_by} since {locked_at}"

    # Create or refresh lock
    now = datetime.now()
    lock_data = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "session_id": session_id,
        "lock_type": lock_type,
        "locked_at": now.isoformat(timespec="seconds"),
        "expires_at": (now + timedelta(seconds=LOCK_TIMEOUT_SECONDS)).isoformat(timespec="seconds"),
    }

    lock_file = get_lock_file(entity_type, entity_id)
    lock_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

    return True, "Lock acquired"


def release_lock(entity_type: str, entity_id: str, session_id: str) -> tuple[bool, str]:
    """
    Release a lock on an entity.
    Only the session that acquired the lock can release it.
    Returns (success, message).
    """
    existing = load_lock(entity_type, entity_id)
    if not existing:
        return True, "No lock exists"

    if existing.get("session_id") != session_id:
        return False, "Lock owned by different session"

    lock_file = get_lock_file(entity_type, entity_id)
    lock_file.unlink(missing_ok=True)

    return True, "Lock released"


def check_lock(entity_type: str, entity_id: str) -> dict[str, Any]:
    """
    Check the lock status of an entity.
    Returns lock info or {"locked": False}.
    """
    existing = load_lock(entity_type, entity_id)
    if not existing:
        return {"locked": False}

    return {
        "locked": True,
        "session_id": existing.get("session_id", ""),
        "lock_type": existing.get("lock_type", ""),
        "locked_at": existing.get("locked_at", ""),
        "expires_at": existing.get("expires_at", ""),
    }


def require_lock(entity_type: str, entity_id: str, session_id: str) -> tuple[bool, str]:
    """
    Check if a session holds the lock on an entity.
    Used before edit operations to ensure proper locking.
    Returns (has_lock, message).
    """
    if not session_id:
        # No session provided - allow edit but warn
        return True, "No session - edit allowed"

    existing = load_lock(entity_type, entity_id)
    if not existing:
        # No lock - auto-acquire
        return acquire_lock(entity_type, entity_id, session_id)

    if existing.get("session_id") == session_id:
        return True, "Lock held by this session"

    return False, f"Locked by {existing.get('session_id', 'unknown')}"


def cleanup_expired_locks() -> int:
    """Remove all expired lock files. Returns count of removed locks."""
    if not LOCK_DIR.exists():
        return 0

    removed = 0
    for lock_file in LOCK_DIR.glob("*.lock"):
        try:
            lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
            if is_lock_expired(lock_data):
                lock_file.unlink()
                removed += 1
        except (json.JSONDecodeError, IOError):
            # Invalid lock file - remove it
            lock_file.unlink(missing_ok=True)
            removed += 1

    return removed


def get_categories(config: dict[str, Any]) -> dict[str, list[str]]:
    """Get categories dict from config."""
    return config.get("categories", DEFAULT_CATEGORIES)


def log_transaction(
    data: dict,
    action: str,
    product_id: str,
    product_name: str,
    location: str = "",
    delta: float = 0,
    note: str = "",
) -> None:
    """Append a transaction record for audit trail."""
    data.setdefault("transactions", []).append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "product_id": product_id,
        "product_name": product_name,
        "location": location,
        "delta": delta,
        "note": note,
    })


# =========================================================================
# VALIDATION FUNCTIONS
# =========================================================================

def validate_category_removal(config: dict[str, Any], category: str) -> tuple[bool, str]:
    """Check if category can be removed (no products use it)."""
    data = load_inventory()
    products = data.get("products", {})

    using = []
    for product_id, product in products.items():
        if product.get("category", "").lower() == category.lower():
            using.append(product.get("name", product_id))

    if using:
        return False, f"Used by: {', '.join(using[:3])}"
    return True, ""


def validate_subcategory_removal(config: dict[str, Any], category: str, subcategory: str) -> tuple[bool, str]:
    """Check if subcategory can be removed (no products use it)."""
    data = load_inventory()
    products = data.get("products", {})

    using = []
    for product_id, product in products.items():
        if (product.get("category", "").lower() == category.lower() and
            product.get("subcategory", "").lower() == subcategory.lower()):
            using.append(product.get("name", product_id))

    if using:
        return False, f"Used by: {', '.join(using[:3])}"
    return True, ""


def validate_active_removal(config: dict[str, Any], active_name: str) -> tuple[bool, str]:
    """Check if active constituent can be removed (no products use it)."""
    data = load_inventory()
    products = data.get("products", {})

    using = []
    for product_id, product in products.items():
        actives = product.get("active_constituents", [])
        if isinstance(actives, list):
            for active in actives:
                if isinstance(active, dict):
                    if active.get("name", "").lower() == active_name.lower():
                        using.append(product.get("name", product_id))
                        break

    if using:
        return False, f"Used by: {', '.join(using[:3])}"
    return True, ""


def validate_chemical_group_removal(config: dict[str, Any], group: str) -> tuple[bool, str]:
    """Check if chemical group can be removed (no products use it)."""
    data = load_inventory()
    products = data.get("products", {})

    using = []
    for product_id, product in products.items():
        actives = product.get("active_constituents", [])
        if isinstance(actives, list):
            for active in actives:
                if isinstance(active, dict):
                    if active.get("group", "") == group:
                        using.append(product.get("name", product_id))
                        break

    if using:
        return False, f"Used by: {', '.join(using[:3])}"
    return True, ""


def validate_unit_removal(config: dict[str, Any], unit_type: str, value: str) -> tuple[bool, str]:
    """Check if unit can be removed (no products use it)."""
    data = load_inventory()
    products = data.get("products", {})

    using = []
    for product_id, product in products.items():
        if unit_type == "product":
            if product.get("unit", "") == value:
                using.append(product.get("name", product_id))
        elif unit_type == "container":
            if str(product.get("container_size", "")) == value:
                using.append(product.get("name", product_id))
        elif unit_type == "application":
            if product.get("application_unit", "") == value:
                using.append(product.get("name", product_id))
        elif unit_type == "concentration":
            actives = product.get("active_constituents", [])
            if isinstance(actives, list):
                for active in actives:
                    if isinstance(active, dict):
                        if active.get("unit", "") == value:
                            using.append(product.get("name", product_id))
                            break

    if using:
        return False, f"Used by: {', '.join(using[:3])}"
    return True, ""


# =========================================================================
# PRODUCT COMMANDS
# =========================================================================

def cmd_add_product(args: argparse.Namespace) -> int:
    """Add a new product to the inventory."""
    config = ensure_migrated_config()
    data = load_inventory()
    products = data.setdefault("products", {})

    # Generate ID from name
    product_id = generate_id(args.name)

    # Check if product already exists
    if product_id in products:
        print(f"ERROR: Product '{product_id}' already exists", file=sys.stderr)
        return 1

    # Validate category
    categories = get_categories(config)
    category = args.category.strip()

    # Case-insensitive category match
    matched_category = None
    for cat in categories:
        if cat.lower() == category.lower():
            matched_category = cat
            break

    if not matched_category:
        print(f"ERROR: Invalid category '{category}'", file=sys.stderr)
        return 1

    category = matched_category

    # Validate subcategory belongs to category
    subcategory = args.subcategory.strip() if args.subcategory else ""
    if subcategory:
        valid_subs = categories.get(category, [])
        matched_sub = None
        for sub in valid_subs:
            if sub.lower() == subcategory.lower():
                matched_sub = sub
                break
        if not matched_sub:
            print(f"ERROR: Subcategory '{subcategory}' not valid for {category}", file=sys.stderr)
            return 1
        subcategory = matched_sub

    # Parse active constituents if provided (for Chemical/Fertiliser)
    active_constituents = []
    if args.actives and args.actives.strip() and args.actives.strip() != "[]":
        try:
            parsed = json.loads(args.actives)
            if isinstance(parsed, list):
                for a in parsed:
                    name = a.get("name", "").strip() if isinstance(a.get("name"), str) else ""
                    if name:
                        conc = a.get("concentration", 0)
                        if isinstance(conc, (int, float)):
                            conc_val = float(conc)
                        else:
                            try:
                                conc_val = float(str(conc).strip()) if conc else 0
                            except ValueError:
                                conc_val = 0
                        unit = a.get("unit", "g/L").strip() if isinstance(a.get("unit"), str) else "g/L"
                        group = a.get("group", "").strip() if isinstance(a.get("group"), str) else ""
                        active_constituents.append({
                            "name": name,
                            "concentration": conc_val,
                            "unit": unit,
                            "group": group
                        })
        except json.JSONDecodeError:
            pass

    # Create product record
    product = {
        "id": product_id,
        "name": args.name.strip(),
        "category": category,
        "subcategory": subcategory,
        "unit": args.unit.strip() if args.unit else "L",
        "container_size": args.container_size or "",
        "min_stock": float(args.min_stock) if args.min_stock else 0,
        "application_unit": args.application_unit.strip() if args.application_unit else "",
        "active_constituents": active_constituents if category in ["Chemical", "Fertiliser"] else [],
        "stock_by_location": {},
        "created": datetime.now().isoformat(timespec="seconds"),
    }

    # Add initial stock if provided
    if args.initial_stock and args.initial_stock > 0 and args.location:
        location = args.location.strip()
        product["stock_by_location"][location] = float(args.initial_stock)
        log_transaction(
            data,
            action="initial_stock",
            product_id=product_id,
            product_name=product["name"],
            location=location,
            delta=float(args.initial_stock),
            note="Initial stock on product creation",
        )

    products[product_id] = product
    save_inventory(data)

    print(f"OK:{product_id}")
    return 0


def cmd_edit_product(args: argparse.Namespace) -> int:
    """Edit an existing product's details (not stock levels)."""
    config = ensure_migrated_config()
    data = load_inventory()
    products = data.get("products", {})

    product_id = args.id.strip().upper()
    if product_id not in products:
        print(f"ERROR: Product '{product_id}' not found", file=sys.stderr)
        return 1

    # Check lock if session provided
    session_id = getattr(args, 'session', '') or ''
    if session_id:
        has_lock, lock_msg = require_lock("product", product_id, session_id)
        if not has_lock:
            print(f"ERROR: {lock_msg}", file=sys.stderr)
            return 1

    product = products[product_id]
    categories = get_categories(config)

    # Update fields if provided
    if args.name:
        product["name"] = args.name.strip()

    if args.category:
        category = args.category.strip()
        matched_category = None
        for cat in categories:
            if cat.lower() == category.lower():
                matched_category = cat
                break
        if not matched_category:
            print(f"ERROR: Invalid category '{category}'", file=sys.stderr)
            return 1
        product["category"] = matched_category

    if args.subcategory is not None:
        subcategory = args.subcategory.strip()
        category = product.get("category", "Chemical")
        if subcategory:
            valid_subs = categories.get(category, [])
            matched_sub = None
            for sub in valid_subs:
                if sub.lower() == subcategory.lower():
                    matched_sub = sub
                    break
            if not matched_sub:
                print(f"ERROR: Subcategory '{subcategory}' not valid for {category}", file=sys.stderr)
                return 1
            subcategory = matched_sub
        product["subcategory"] = subcategory

    if args.unit:
        product["unit"] = args.unit.strip()

    if args.container_size is not None:
        product["container_size"] = args.container_size

    if args.min_stock is not None:
        product["min_stock"] = float(args.min_stock)

    if args.application_unit is not None:
        product["application_unit"] = args.application_unit.strip()

    # Handle active constituents
    if args.actives is not None and args.actives.strip():
        category = product.get("category", "")
        if category in ["Chemical", "Fertiliser"]:
            try:
                parsed = json.loads(args.actives)
                if isinstance(parsed, list):
                    active_constituents = []
                    for a in parsed:
                        name = a.get("name", "").strip() if isinstance(a.get("name"), str) else ""
                        if name:
                            conc = a.get("concentration", 0)
                            if isinstance(conc, (int, float)):
                                conc_val = float(conc)
                            else:
                                try:
                                    conc_val = float(str(conc).strip()) if conc else 0
                                except ValueError:
                                    conc_val = 0
                            unit = a.get("unit", "g/L").strip() if isinstance(a.get("unit"), str) else "g/L"
                            group = a.get("group", "").strip() if isinstance(a.get("group"), str) else ""
                            active_constituents.append({
                                "name": name,
                                "concentration": conc_val,
                                "unit": unit,
                                "group": group
                            })
                    product["active_constituents"] = active_constituents
            except json.JSONDecodeError:
                pass

    product["modified"] = datetime.now().isoformat(timespec="seconds")

    log_transaction(
        data,
        action="edit_product",
        product_id=product_id,
        product_name=product["name"],
        note="Product details updated",
    )

    save_inventory(data)
    print(f"OK:{product_id}")
    return 0


def cmd_move_stock(args: argparse.Namespace) -> int:
    """Move stock in or out of a location."""
    data = load_inventory()
    products = data.get("products", {})

    product_id = args.id.strip().upper()
    if product_id not in products:
        print(f"ERROR: Product '{product_id}' not found", file=sys.stderr)
        return 1

    product = products[product_id]
    location = args.location.strip()
    delta = float(args.delta)

    if delta == 0:
        print("OK:0")
        return 0

    # Get current stock at location
    stock_by_location = product.setdefault("stock_by_location", {})
    current = float(stock_by_location.get(location, 0))

    # Calculate new stock (cannot go below 0)
    new_stock = max(0, current + delta)

    # Update or remove location
    if new_stock > 0:
        stock_by_location[location] = new_stock
    elif location in stock_by_location:
        del stock_by_location[location]

    # Log the transaction
    log_transaction(
        data,
        action="stock_in" if delta > 0 else "stock_out",
        product_id=product_id,
        product_name=product["name"],
        location=location,
        delta=delta,
        note=args.note or "",
    )

    save_inventory(data)
    print(f"OK:{new_stock}")
    return 0


def cmd_delete_product(args: argparse.Namespace) -> int:
    """Delete a product from the inventory."""
    data = load_inventory()
    products = data.get("products", {})

    product_id = args.id.strip().upper()
    if product_id not in products:
        print(f"ERROR: Product '{product_id}' not found", file=sys.stderr)
        return 1

    product_name = products[product_id].get("name", product_id)
    del products[product_id]

    log_transaction(
        data,
        action="delete_product",
        product_id=product_id,
        product_name=product_name,
        note="Product deleted",
    )

    save_inventory(data)
    print(f"OK:deleted")
    return 0


# =========================================================================
# CATEGORY COMMANDS
# =========================================================================

def cmd_add_category(args: argparse.Namespace) -> int:
    """Add a new category."""
    name = args.name.strip()
    if not name:
        print("ERROR: Category name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    categories = config.get("categories", {})

    # Check if already exists (case-insensitive)
    if any(cat.lower() == name.lower() for cat in categories):
        print(f"ERROR: Category '{name}' already exists", file=sys.stderr)
        return 1

    categories[name] = []
    config["categories"] = categories
    save_config(config)

    print(f"OK:{name}")
    return 0


def cmd_remove_category(args: argparse.Namespace) -> int:
    """Remove a category (only if unused)."""
    name = args.name.strip()
    if not name:
        print("ERROR: Category name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    categories = config.get("categories", {})

    # Find exact match (case-insensitive)
    matching = [cat for cat in categories if cat.lower() == name.lower()]
    if not matching:
        print(f"ERROR: Category '{name}' not found", file=sys.stderr)
        return 1

    actual_name = matching[0]

    # Check if in use
    can_remove, reason = validate_category_removal(config, actual_name)
    if not can_remove:
        print(f"ERROR: Cannot remove '{actual_name}' - {reason}", file=sys.stderr)
        return 1

    del categories[actual_name]
    config["categories"] = categories
    save_config(config)

    print(f"OK:removed:{actual_name}")
    return 0


def cmd_add_subcategory(args: argparse.Namespace) -> int:
    """Add a subcategory to a category."""
    category = args.category.strip()
    name = args.name.strip()

    if not category or not name:
        print("ERROR: Category and subcategory name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    categories = config.get("categories", {})

    # Find category (case-insensitive)
    matching = [cat for cat in categories if cat.lower() == category.lower()]
    if not matching:
        print(f"ERROR: Category '{category}' not found", file=sys.stderr)
        return 1

    actual_category = matching[0]
    subcats = categories[actual_category]

    # Check if already exists (case-insensitive)
    if any(sub.lower() == name.lower() for sub in subcats):
        print(f"ERROR: Subcategory '{name}' already exists in {actual_category}", file=sys.stderr)
        return 1

    subcats.append(name)
    categories[actual_category] = subcats
    config["categories"] = categories
    save_config(config)

    print(f"OK:{name}")
    return 0


def cmd_remove_subcategory(args: argparse.Namespace) -> int:
    """Remove a subcategory from a category (only if unused)."""
    category = args.category.strip()
    name = args.name.strip()

    if not category or not name:
        print("ERROR: Category and subcategory name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    categories = config.get("categories", {})

    # Find category
    matching_cat = [cat for cat in categories if cat.lower() == category.lower()]
    if not matching_cat:
        print(f"ERROR: Category '{category}' not found", file=sys.stderr)
        return 1

    actual_category = matching_cat[0]
    subcats = categories[actual_category]

    # Find subcategory
    matching_sub = [sub for sub in subcats if sub.lower() == name.lower()]
    if not matching_sub:
        print(f"ERROR: Subcategory '{name}' not found in {actual_category}", file=sys.stderr)
        return 1

    actual_sub = matching_sub[0]

    # Check if in use
    can_remove, reason = validate_subcategory_removal(config, actual_category, actual_sub)
    if not can_remove:
        print(f"ERROR: Cannot remove '{actual_sub}' - {reason}", file=sys.stderr)
        return 1

    categories[actual_category] = [sub for sub in subcats if sub != actual_sub]
    config["categories"] = categories
    save_config(config)

    print(f"OK:removed:{actual_sub}")
    return 0


# =========================================================================
# CHEMICAL GROUP COMMANDS
# =========================================================================

def cmd_add_chemical_group(args: argparse.Namespace) -> int:
    """Add a new chemical group."""
    name = args.name.strip()
    if not name:
        print("ERROR: Group name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    groups = config.get("chemical_groups", [])

    # Check if already exists
    if name in groups:
        print(f"ERROR: Chemical group '{name}' already exists", file=sys.stderr)
        return 1

    groups.append(name)
    config["chemical_groups"] = groups
    save_config(config)

    print(f"OK:{name}")
    return 0


def cmd_remove_chemical_group(args: argparse.Namespace) -> int:
    """Remove a chemical group (only if unused)."""
    name = args.name.strip()
    if not name:
        print("ERROR: Group name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    groups = config.get("chemical_groups", [])

    if name not in groups:
        print(f"ERROR: Chemical group '{name}' not found", file=sys.stderr)
        return 1

    # Check if in use
    can_remove, reason = validate_chemical_group_removal(config, name)
    if not can_remove:
        print(f"ERROR: Cannot remove '{name}' - {reason}", file=sys.stderr)
        return 1

    config["chemical_groups"] = [g for g in groups if g != name]
    save_config(config)

    print(f"OK:removed:{name}")
    return 0


# =========================================================================
# UNIT COMMANDS
# =========================================================================

def cmd_add_unit(args: argparse.Namespace) -> int:
    """Add a new unit to a unit type."""
    unit_type = args.type.strip()
    value = args.value.strip()

    if not unit_type or not value:
        print("ERROR: Unit type and value cannot be empty", file=sys.stderr)
        return 1

    if unit_type not in ["product", "container", "application", "concentration"]:
        print(f"ERROR: Invalid unit type '{unit_type}'", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    units = config.get("units", DEFAULT_UNITS.copy())

    if unit_type not in units:
        units[unit_type] = []

    unit_list = units[unit_type]

    # Check if already exists
    if value in unit_list:
        print(f"ERROR: Unit '{value}' already exists in {unit_type}", file=sys.stderr)
        return 1

    unit_list.append(value)
    config["units"] = units
    save_config(config)

    print(f"OK:{value}")
    return 0


def cmd_remove_unit(args: argparse.Namespace) -> int:
    """Remove a unit from a unit type (only if unused)."""
    unit_type = args.type.strip()
    value = args.value.strip()

    if not unit_type or not value:
        print("ERROR: Unit type and value cannot be empty", file=sys.stderr)
        return 1

    if unit_type not in ["product", "container", "application", "concentration"]:
        print(f"ERROR: Invalid unit type '{unit_type}'", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    units = config.get("units", {})

    if unit_type not in units or value not in units[unit_type]:
        print(f"ERROR: Unit '{value}' not found in {unit_type}", file=sys.stderr)
        return 1

    # Check if in use
    can_remove, reason = validate_unit_removal(config, unit_type, value)
    if not can_remove:
        print(f"ERROR: Cannot remove '{value}' - {reason}", file=sys.stderr)
        return 1

    units[unit_type] = [u for u in units[unit_type] if u != value]
    config["units"] = units
    save_config(config)

    print(f"OK:removed:{value}")
    return 0


# =========================================================================
# ACTIVE CONSTITUENT COMMANDS
# =========================================================================

def cmd_list_actives(args: argparse.Namespace) -> int:
    """List all active constituents."""
    config = ensure_migrated_config()
    actives = config.get("actives", [])

    result = {
        "total": len(actives),
        "actives": actives,
    }

    print(json.dumps(result))
    return 0


def cmd_add_active(args: argparse.Namespace) -> int:
    """Add an active constituent."""
    name = args.name.strip()
    if not name:
        print("ERROR: Active name cannot be empty", file=sys.stderr)
        return 1

    # Parse common groups if provided
    common_groups = []
    if args.groups and args.groups.strip():
        common_groups = [g.strip() for g in args.groups.split(",") if g.strip()]

    config = ensure_migrated_config()
    actives = config.get("actives", [])

    # Check if already exists (case-insensitive)
    if any(a.get("name", "").lower() == name.lower() for a in actives):
        print(f"ERROR: Active '{name}' already exists", file=sys.stderr)
        return 1

    # Add new active
    actives.append({
        "name": name,
        "common_groups": common_groups,
    })

    # Sort alphabetically
    actives.sort(key=lambda x: x.get("name", "").lower())
    config["actives"] = actives
    save_config(config)

    print(f"OK:{name}")
    return 0


def cmd_remove_active(args: argparse.Namespace) -> int:
    """Remove an active constituent (only if unused)."""
    name = args.name.strip()
    if not name:
        print("ERROR: Active name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    actives = config.get("actives", [])

    # Find the active
    matching = [a for a in actives if a.get("name", "").lower() == name.lower()]
    if not matching:
        print(f"ERROR: Active '{name}' not found", file=sys.stderr)
        return 1

    actual_name = matching[0].get("name", name)

    # Check if in use
    can_remove, reason = validate_active_removal(config, actual_name)
    if not can_remove:
        print(f"ERROR: Cannot remove '{actual_name}' - {reason}", file=sys.stderr)
        return 1

    # Remove the active
    config["actives"] = [a for a in actives if a.get("name", "").lower() != actual_name.lower()]
    save_config(config)

    print(f"OK:removed:{actual_name}")
    return 0


# =========================================================================
# LOCATION COMMANDS
# =========================================================================

def cmd_add_location(args: argparse.Namespace) -> int:
    """Add a new storage location."""
    location = args.name.strip()
    if not location:
        print("ERROR: Location name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    locations = config.get("locations", [])

    # Check if already exists (case-insensitive)
    if any(loc.lower() == location.lower() for loc in locations):
        print(f"ERROR: Location '{location}' already exists", file=sys.stderr)
        return 1

    locations.append(location)
    config["locations"] = locations
    save_config(config)

    print(f"OK:{location}")
    return 0


def cmd_remove_location(args: argparse.Namespace) -> int:
    """Remove a storage location (only if no stock there)."""
    location = args.name.strip()
    if not location:
        print("ERROR: Location name cannot be empty", file=sys.stderr)
        return 1

    config = ensure_migrated_config()
    locations = config.get("locations", [])

    # Find exact match
    matching = [loc for loc in locations if loc.lower() == location.lower()]
    if not matching:
        print(f"ERROR: Location '{location}' not found", file=sys.stderr)
        return 1

    actual_location = matching[0]

    # Check if any products have stock at this location
    data = load_inventory()
    products = data.get("products", {})
    for product_id, product in products.items():
        stock = product.get("stock_by_location", {}).get(actual_location, 0)
        if stock and float(stock) > 0:
            print(f"ERROR: Cannot remove '{actual_location}' - has stock for {product.get('name', product_id)}", file=sys.stderr)
            return 1

    # Remove location
    config["locations"] = [loc for loc in locations if loc != actual_location]
    save_config(config)

    print(f"OK:removed:{actual_location}")
    return 0


# =========================================================================
# LOCK COMMANDS
# =========================================================================

def cmd_lock_acquire(args: argparse.Namespace) -> int:
    """Acquire a lock on an entity."""
    entity_type = args.type.strip()
    entity_id = args.id.strip()
    session_id = args.session.strip()

    if not entity_type or not entity_id or not session_id:
        print("ERROR: type, id, and session are required", file=sys.stderr)
        return 1

    success, message = acquire_lock(entity_type, entity_id, session_id)
    if success:
        lock_info = check_lock(entity_type, entity_id)
        print(json.dumps({"status": "acquired", "lock": lock_info}))
        return 0
    else:
        print(json.dumps({"status": "failed", "message": message}))
        return 1


def cmd_lock_release(args: argparse.Namespace) -> int:
    """Release a lock on an entity."""
    entity_type = args.type.strip()
    entity_id = args.id.strip()
    session_id = args.session.strip()

    if not entity_type or not entity_id or not session_id:
        print("ERROR: type, id, and session are required", file=sys.stderr)
        return 1

    success, message = release_lock(entity_type, entity_id, session_id)
    if success:
        print(json.dumps({"status": "released"}))
        return 0
    else:
        print(json.dumps({"status": "failed", "message": message}))
        return 1


def cmd_lock_check(args: argparse.Namespace) -> int:
    """Check lock status of an entity."""
    entity_type = args.type.strip()
    entity_id = args.id.strip()

    if not entity_type or not entity_id:
        print("ERROR: type and id are required", file=sys.stderr)
        return 1

    lock_info = check_lock(entity_type, entity_id)
    print(json.dumps(lock_info))
    return 0


def cmd_lock_cleanup(args: argparse.Namespace) -> int:
    """Clean up expired locks."""
    removed = cleanup_expired_locks()
    print(json.dumps({"status": "ok", "removed": removed}))
    return 0


def cmd_lock_list(args: argparse.Namespace) -> int:
    """List all active locks."""
    locks = []

    if LOCK_DIR.exists():
        for lock_file in LOCK_DIR.glob("*.lock"):
            try:
                lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
                if not is_lock_expired(lock_data):
                    locks.append(lock_data)
            except (json.JSONDecodeError, IOError):
                pass

    print(json.dumps({"total": len(locks), "locks": locks}))
    return 0


# =========================================================================
# SYSTEM COMMANDS
# =========================================================================

def cmd_status(args: argparse.Namespace) -> int:
    """Return system status as JSON."""
    status = {
        "database_exists": DATA_FILE.exists(),
        "config_exists": CONFIG_FILE.exists(),
        "config_version": "",
        "needs_migration": False,
        "status": "not_initialized",
        "product_count": 0,
        "transaction_count": 0,
        "location_count": 0,
        "category_count": 0,
        "active_count": 0,
        "locations_with_stock": [],
    }

    # Check config
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            status["config_version"] = config.get("version", "1.0.0")
            status["needs_migration"] = config.get("version") != CONFIG_VERSION
            status["location_count"] = len(config.get("locations", []))
            status["category_count"] = len(config.get("categories", {}))
            status["active_count"] = len(config.get("actives", []))
        except Exception:
            status["status"] = "error"
            status["error"] = "Config file corrupted"
            print(json.dumps(status))
            return 0

    # Check database
    if DATA_FILE.exists():
        try:
            data = load_inventory()
            products = data.get("products", {})
            status["product_count"] = len(products)
            status["transaction_count"] = len(data.get("transactions", []))

            # Find locations with stock
            locations_with_stock = set()
            for product in products.values():
                for loc, qty in product.get("stock_by_location", {}).items():
                    if qty and float(qty) > 0:
                        locations_with_stock.add(loc)
            status["locations_with_stock"] = sorted(locations_with_stock)

            status["status"] = "ready"
        except Exception as e:
            status["status"] = "error"
            status["error"] = f"Database file corrupted: {e}"
    elif CONFIG_FILE.exists():
        # Config exists but no database - still considered initialized
        status["status"] = "ready"

    print(json.dumps(status))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize the IPM system - create config and database files."""
    created = []
    migrated = False

    # Create directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create or migrate config
    if not CONFIG_FILE.exists():
        config = create_default_config()
        save_config(config)
        created.append("config")
    else:
        # Check if migration needed
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if config.get("version") != CONFIG_VERSION:
                # Backup old config
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                backup_file = BACKUP_DIR / f"config_pre_migration_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
                backup_file.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")

                # Migrate
                new_config = migrate_config_internal(config)
                save_config(new_config)
                migrated = True
        except (json.JSONDecodeError, IOError):
            config = create_default_config()
            save_config(config)
            created.append("config")

    # Create empty inventory if missing
    if not DATA_FILE.exists():
        data = {"products": {}, "transactions": []}
        save_inventory(data)
        created.append("database")

    if migrated:
        print("OK:migrated")
    elif created:
        print(f"OK:created:{','.join(created)}")
    else:
        print("OK:already_initialized")
    return 0


def cmd_migrate_config(args: argparse.Namespace) -> int:
    """Explicitly migrate config to v2.0.0 format."""
    if not CONFIG_FILE.exists():
        print("ERROR: No config file to migrate", file=sys.stderr)
        return 1

    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        print(f"ERROR: Cannot read config: {e}", file=sys.stderr)
        return 1

    if config.get("version") == CONFIG_VERSION:
        print("OK:already_migrated")
        return 0

    # Backup old config
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_file = BACKUP_DIR / f"config_pre_migration_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    backup_file.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")

    # Migrate
    new_config = migrate_config_internal(config)
    save_config(new_config)

    print(f"OK:migrated:{backup_file.name}")
    return 0


# =========================================================================
# DATA MANAGEMENT COMMANDS
# =========================================================================

def cmd_export(args: argparse.Namespace) -> int:
    """Export inventory and config to a timestamped backup file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_file = BACKUP_DIR / f"inventory_{timestamp}.json"

    inventory = load_inventory()
    config = ensure_migrated_config()

    backup_data = {
        "version": CONFIG_VERSION,
        "created": datetime.now().isoformat(timespec="seconds"),
        "type": "ipm_backup",
        "inventory": inventory,
        "config": config,
    }

    backup_file.write_text(
        json.dumps(backup_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"OK:{backup_file.name}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """Import inventory and config from a backup file."""
    filename = args.filename.strip()
    if not filename:
        print("ERROR: Filename cannot be empty", file=sys.stderr)
        return 1

    backup_file = BACKUP_DIR / filename
    if not backup_file.exists():
        print(f"ERROR: Backup file '{filename}' not found", file=sys.stderr)
        return 1

    try:
        backup_data = json.loads(backup_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in backup file: {e}", file=sys.stderr)
        return 1

    if backup_data.get("type") != "ipm_backup":
        print("ERROR: File is not a valid IPM backup", file=sys.stderr)
        return 1

    inventory = backup_data.get("inventory")
    config = backup_data.get("config")

    if not isinstance(inventory, dict) or "products" not in inventory:
        print("ERROR: Backup contains invalid inventory data", file=sys.stderr)
        return 1

    # Create pre-import backup
    current_inventory = load_inventory()
    current_config = ensure_migrated_config()

    pre_import_backup = {
        "version": CONFIG_VERSION,
        "created": datetime.now().isoformat(timespec="seconds"),
        "type": "ipm_backup",
        "note": "Pre-import automatic backup",
        "inventory": current_inventory,
        "config": current_config,
    }

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    pre_import_file = BACKUP_DIR / f"pre_import_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    pre_import_file.write_text(
        json.dumps(pre_import_backup, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # Import the data
    save_inventory(inventory)
    if config and isinstance(config, dict):
        # Ensure imported config is v2.0.0
        if config.get("version") != CONFIG_VERSION:
            config = migrate_config_internal(config)
        save_config(config)

    product_count = len(inventory.get("products", {}))
    print(f"OK:imported:{product_count}:{pre_import_file.name}")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset all IPM data (requires confirmation token)."""
    token = args.token.strip() if args.token else ""

    if token != "CONFIRM_RESET":
        print("ERROR: Invalid confirmation token. Use --token CONFIRM_RESET", file=sys.stderr)
        return 1

    # Create backup before reset
    current_inventory = load_inventory()
    current_config = ensure_migrated_config()

    if current_inventory.get("products") or current_config.get("actives"):
        pre_reset_backup = {
            "version": CONFIG_VERSION,
            "created": datetime.now().isoformat(timespec="seconds"),
            "type": "ipm_backup",
            "note": "Pre-reset automatic backup",
            "inventory": current_inventory,
            "config": current_config,
        }

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        pre_reset_file = BACKUP_DIR / f"pre_reset_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        pre_reset_file.write_text(
            json.dumps(pre_reset_backup, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    # Reset to empty state
    empty_inventory = {"products": {}, "transactions": []}
    save_inventory(empty_inventory)

    # Reset config to defaults
    reset_config = create_default_config()
    save_config(reset_config)

    print("OK:reset")
    return 0


def cmd_backup_list(args: argparse.Namespace) -> int:
    """List available backup files with metadata."""
    backups = []

    if BACKUP_DIR.exists():
        for backup_file in sorted(BACKUP_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(backup_file.read_text(encoding="utf-8"))
                product_count = len(data.get("inventory", {}).get("products", {}))
                backups.append({
                    "filename": backup_file.name,
                    "created": data.get("created", ""),
                    "note": data.get("note", ""),
                    "product_count": product_count,
                    "size_kb": round(backup_file.stat().st_size / 1024, 1),
                })
            except (json.JSONDecodeError, IOError):
                backups.append({
                    "filename": backup_file.name,
                    "created": "",
                    "note": "Unable to read",
                    "product_count": 0,
                    "size_kb": round(backup_file.stat().st_size / 1024, 1),
                })

    result = {
        "total": len(backups),
        "backups": backups,
    }

    print(json.dumps(result))
    return 0


# =========================================================================
# REPORT COMMANDS
# =========================================================================

def cmd_usage_report(args: argparse.Namespace) -> int:
    """Generate usage report filtered by date range."""
    data = load_inventory()
    transactions = data.get("transactions", [])

    # Parse date filters
    start_date = None
    end_date = None

    if args.start:
        try:
            start_date = datetime.fromisoformat(args.start.strip())
        except ValueError:
            print(f"ERROR: Invalid start date format: {args.start}", file=sys.stderr)
            return 1

    if args.end:
        try:
            end_date = datetime.fromisoformat(args.end.strip())
            # Include the entire end day
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            print(f"ERROR: Invalid end date format: {args.end}", file=sys.stderr)
            return 1

    # Filter transactions by date
    filtered_txns = []
    for txn in transactions:
        try:
            txn_date = datetime.fromisoformat(txn.get("timestamp", ""))
            if start_date and txn_date < start_date:
                continue
            if end_date and txn_date > end_date:
                continue
            filtered_txns.append(txn)
        except ValueError:
            continue

    # Build usage summary by product
    usage_by_product: dict[str, dict] = {}
    for txn in filtered_txns:
        product_id = txn.get("product_id", "")
        product_name = txn.get("product_name", product_id)
        action = txn.get("action", "")
        delta = float(txn.get("delta", 0))

        if product_id not in usage_by_product:
            usage_by_product[product_id] = {
                "id": product_id,
                "name": product_name,
                "stock_in": 0,
                "stock_out": 0,
                "net_change": 0,
                "transaction_count": 0,
            }

        usage_by_product[product_id]["transaction_count"] += 1
        usage_by_product[product_id]["net_change"] += delta

        if action == "stock_in" or delta > 0:
            usage_by_product[product_id]["stock_in"] += abs(delta)
        elif action == "stock_out" or delta < 0:
            usage_by_product[product_id]["stock_out"] += abs(delta)

    # Convert to list sorted by usage (stock_out)
    usage_list = sorted(
        usage_by_product.values(),
        key=lambda x: x["stock_out"],
        reverse=True
    )

    # Build category summary
    category_summary: dict[str, dict] = {}
    products = data.get("products", {})
    for item in usage_list:
        product = products.get(item["id"], {})
        category = product.get("category", "Unknown")

        if category not in category_summary:
            category_summary[category] = {
                "category": category,
                "stock_in": 0,
                "stock_out": 0,
                "net_change": 0,
                "product_count": 0,
            }

        category_summary[category]["stock_in"] += item["stock_in"]
        category_summary[category]["stock_out"] += item["stock_out"]
        category_summary[category]["net_change"] += item["net_change"]
        category_summary[category]["product_count"] += 1

    result = {
        "period": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
        "total_transactions": len(filtered_txns),
        "products_affected": len(usage_by_product),
        "usage_by_product": usage_list,
        "usage_by_category": sorted(
            category_summary.values(),
            key=lambda x: x["stock_out"],
            reverse=True
        ),
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_transaction_history(args: argparse.Namespace) -> int:
    """Get transaction history with optional filters."""
    data = load_inventory()
    transactions = data.get("transactions", [])

    # Parse filters
    start_date = None
    end_date = None
    product_filter = args.product.strip().upper() if args.product else None
    action_filter = args.action.strip() if args.action else None
    limit = int(args.limit) if args.limit else 100

    if args.start:
        try:
            start_date = datetime.fromisoformat(args.start.strip())
        except ValueError:
            pass

    if args.end:
        try:
            end_date = datetime.fromisoformat(args.end.strip())
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            pass

    # Filter transactions
    filtered = []
    for txn in reversed(transactions):  # Most recent first
        try:
            txn_date = datetime.fromisoformat(txn.get("timestamp", ""))
            if start_date and txn_date < start_date:
                continue
            if end_date and txn_date > end_date:
                continue
        except ValueError:
            continue

        if product_filter and txn.get("product_id") != product_filter:
            continue

        if action_filter and txn.get("action") != action_filter:
            continue

        filtered.append(txn)

        if len(filtered) >= limit:
            break

    result = {
        "total": len(filtered),
        "limit": limit,
        "transactions": filtered,
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_generate_report_file(args: argparse.Namespace) -> int:
    """Generate comprehensive report data to a JSON file for dashboard display."""
    data = load_inventory()
    transactions = data.get("transactions", [])
    products = data.get("products", {})

    # Parse date filters
    start_date = None
    end_date = None

    if args.start:
        try:
            start_date = datetime.fromisoformat(args.start.strip())
        except ValueError:
            print(f"ERROR: Invalid start date format: {args.start}", file=sys.stderr)
            return 1

    if args.end:
        try:
            end_date = datetime.fromisoformat(args.end.strip())
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            print(f"ERROR: Invalid end date format: {args.end}", file=sys.stderr)
            return 1

    # Parse action filter
    action_filter = args.action.strip() if args.action else None

    # Filter transactions by date and action
    filtered_txns = []
    for txn in transactions:
        try:
            txn_date = datetime.fromisoformat(txn.get("timestamp", ""))
            if start_date and txn_date < start_date:
                continue
            if end_date and txn_date > end_date:
                continue
        except ValueError:
            continue

        if action_filter and txn.get("action") != action_filter:
            continue

        filtered_txns.append(txn)

    # Build usage summary by product
    usage_by_product: dict[str, dict] = {}
    total_stock_in = 0.0
    total_stock_out = 0.0

    for txn in filtered_txns:
        product_id = txn.get("product_id", "")
        product_name = txn.get("product_name", product_id)
        action = txn.get("action", "")
        delta = float(txn.get("delta", 0))

        # Get category from product data
        product = products.get(product_id, {})
        category = product.get("category", "Unknown")

        if product_id not in usage_by_product:
            usage_by_product[product_id] = {
                "id": product_id,
                "name": product_name,
                "category": category,
                "stock_in": 0.0,
                "stock_out": 0.0,
                "net": 0.0,
                "transactions": 0,
            }

        usage_by_product[product_id]["transactions"] += 1
        usage_by_product[product_id]["net"] += delta

        if action == "stock_in" or delta > 0:
            usage_by_product[product_id]["stock_in"] += abs(delta)
            total_stock_in += abs(delta)
        elif action == "stock_out" or delta < 0:
            usage_by_product[product_id]["stock_out"] += abs(delta)
            total_stock_out += abs(delta)

    # Build category summary
    category_summary: dict[str, dict] = {}
    for item in usage_by_product.values():
        category = item["category"]
        if category not in category_summary:
            category_summary[category] = {
                "category": category,
                "stock_in": 0.0,
                "stock_out": 0.0,
                "net": 0.0,
                "products": 0,
            }
        category_summary[category]["stock_in"] += item["stock_in"]
        category_summary[category]["stock_out"] += item["stock_out"]
        category_summary[category]["net"] += item["net"]
        category_summary[category]["products"] += 1

    # Get recent transactions (most recent first, limited to 50)
    recent_txns = sorted(
        filtered_txns,
        key=lambda x: x.get("timestamp", ""),
        reverse=True
    )[:50]

    # Build result structure
    result = {
        "summary": {
            "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
            "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
            "total_transactions": len(filtered_txns),
            "products_affected": len(usage_by_product),
            "total_stock_in": round(total_stock_in, 2),
            "total_stock_out": round(total_stock_out, 2),
            "net_change": round(total_stock_in - total_stock_out, 2),
        },
        "by_category": sorted(
            category_summary.values(),
            key=lambda x: x["stock_out"],
            reverse=True
        ),
        "by_product": sorted(
            usage_by_product.values(),
            key=lambda x: x["stock_out"],
            reverse=True
        ),
        "transactions": recent_txns,
        "generated_at": datetime.now().isoformat(),
    }

    # Write to output file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"OK: Report generated to {output_path}")
    return 0


# =========================================================================
# ARGUMENT PARSER
# =========================================================================

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ipm_backend.py",
        description="IPM Inventory Backend - PaddiSense"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ----- Product Commands -----
    add_p = subparsers.add_parser("add_product", help="Add a new product")
    add_p.add_argument("--name", required=True, help="Product name")
    add_p.add_argument("--category", required=True, help="Category")
    add_p.add_argument("--subcategory", default="", help="Subcategory")
    add_p.add_argument("--unit", default="L", help="Unit (L, kg, t)")
    add_p.add_argument("--container_size", default="", help="Container size")
    add_p.add_argument("--min_stock", type=float, default=0, help="Minimum stock level")
    add_p.add_argument("--application_unit", default="", help="Application unit")
    add_p.add_argument("--location", default="", help="Initial stock location")
    add_p.add_argument("--initial_stock", type=float, default=0, help="Initial stock quantity")
    add_p.add_argument("--actives", default="", help="Active constituents as JSON array")
    add_p.set_defaults(func=cmd_add_product)

    edit_p = subparsers.add_parser("edit_product", help="Edit product details")
    edit_p.add_argument("--id", required=True, help="Product ID")
    edit_p.add_argument("--session", default="", help="Session ID for locking")
    edit_p.add_argument("--name", help="New product name")
    edit_p.add_argument("--category", help="New category")
    edit_p.add_argument("--subcategory", help="New subcategory")
    edit_p.add_argument("--unit", help="New unit")
    edit_p.add_argument("--container_size", help="New container size")
    edit_p.add_argument("--min_stock", type=float, help="New minimum stock")
    edit_p.add_argument("--application_unit", help="New application unit")
    edit_p.add_argument("--actives", help="Active constituents as JSON array")
    edit_p.set_defaults(func=cmd_edit_product)

    move_p = subparsers.add_parser("move_stock", help="Adjust stock at a location")
    move_p.add_argument("--id", required=True, help="Product ID")
    move_p.add_argument("--location", required=True, help="Storage location")
    move_p.add_argument("--delta", type=float, required=True, help="Change amount (+/-)")
    move_p.add_argument("--note", default="", help="Optional note")
    move_p.set_defaults(func=cmd_move_stock)

    del_p = subparsers.add_parser("delete_product", help="Delete a product")
    del_p.add_argument("--id", required=True, help="Product ID")
    del_p.set_defaults(func=cmd_delete_product)

    # ----- Category Commands -----
    add_cat_p = subparsers.add_parser("add_category", help="Add a category")
    add_cat_p.add_argument("--name", required=True, help="Category name")
    add_cat_p.set_defaults(func=cmd_add_category)

    rem_cat_p = subparsers.add_parser("remove_category", help="Remove a category")
    rem_cat_p.add_argument("--name", required=True, help="Category name")
    rem_cat_p.set_defaults(func=cmd_remove_category)

    add_sub_p = subparsers.add_parser("add_subcategory", help="Add a subcategory")
    add_sub_p.add_argument("--category", required=True, help="Parent category")
    add_sub_p.add_argument("--name", required=True, help="Subcategory name")
    add_sub_p.set_defaults(func=cmd_add_subcategory)

    rem_sub_p = subparsers.add_parser("remove_subcategory", help="Remove a subcategory")
    rem_sub_p.add_argument("--category", required=True, help="Parent category")
    rem_sub_p.add_argument("--name", required=True, help="Subcategory name")
    rem_sub_p.set_defaults(func=cmd_remove_subcategory)

    # ----- Chemical Group Commands -----
    add_grp_p = subparsers.add_parser("add_chemical_group", help="Add a chemical group")
    add_grp_p.add_argument("--name", required=True, help="Group name")
    add_grp_p.set_defaults(func=cmd_add_chemical_group)

    rem_grp_p = subparsers.add_parser("remove_chemical_group", help="Remove a chemical group")
    rem_grp_p.add_argument("--name", required=True, help="Group name")
    rem_grp_p.set_defaults(func=cmd_remove_chemical_group)

    # ----- Unit Commands -----
    add_unit_p = subparsers.add_parser("add_unit", help="Add a unit")
    add_unit_p.add_argument("--type", required=True, help="Unit type (product/container/application/concentration)")
    add_unit_p.add_argument("--value", required=True, help="Unit value")
    add_unit_p.set_defaults(func=cmd_add_unit)

    rem_unit_p = subparsers.add_parser("remove_unit", help="Remove a unit")
    rem_unit_p.add_argument("--type", required=True, help="Unit type")
    rem_unit_p.add_argument("--value", required=True, help="Unit value")
    rem_unit_p.set_defaults(func=cmd_remove_unit)

    # ----- Active Constituents Commands -----
    list_act_p = subparsers.add_parser("list_actives", help="List all active constituents")
    list_act_p.set_defaults(func=cmd_list_actives)

    add_act_p = subparsers.add_parser("add_active", help="Add an active constituent")
    add_act_p.add_argument("--name", required=True, help="Active name")
    add_act_p.add_argument("--groups", default="", help="Common chemical groups (comma-separated)")
    add_act_p.set_defaults(func=cmd_add_active)

    rem_act_p = subparsers.add_parser("remove_active", help="Remove an active constituent")
    rem_act_p.add_argument("--name", required=True, help="Active name")
    rem_act_p.set_defaults(func=cmd_remove_active)

    # ----- Location Commands -----
    add_loc_p = subparsers.add_parser("add_location", help="Add a storage location")
    add_loc_p.add_argument("--name", required=True, help="Location name")
    add_loc_p.set_defaults(func=cmd_add_location)

    rem_loc_p = subparsers.add_parser("remove_location", help="Remove a storage location")
    rem_loc_p.add_argument("--name", required=True, help="Location name")
    rem_loc_p.set_defaults(func=cmd_remove_location)

    # ----- System Commands -----
    status_p = subparsers.add_parser("status", help="Get system status")
    status_p.set_defaults(func=cmd_status)

    init_p = subparsers.add_parser("init", help="Initialize IPM system")
    init_p.set_defaults(func=cmd_init)

    migrate_p = subparsers.add_parser("migrate_config", help="Migrate config to v2.0.0")
    migrate_p.set_defaults(func=cmd_migrate_config)

    # ----- Data Management Commands -----
    export_p = subparsers.add_parser("export", help="Export data to backup file")
    export_p.set_defaults(func=cmd_export)

    import_p = subparsers.add_parser("import_backup", help="Import data from backup file")
    import_p.add_argument("--filename", required=True, help="Backup filename to import")
    import_p.set_defaults(func=cmd_import)

    reset_p = subparsers.add_parser("reset", help="Reset all data (requires confirmation)")
    reset_p.add_argument("--token", required=True, help="Confirmation token (CONFIRM_RESET)")
    reset_p.set_defaults(func=cmd_reset)

    backup_list_p = subparsers.add_parser("backup_list", help="List available backups")
    backup_list_p.set_defaults(func=cmd_backup_list)

    # ----- Report Commands -----
    usage_report_p = subparsers.add_parser("usage_report", help="Generate usage report")
    usage_report_p.add_argument("--start", help="Start date (YYYY-MM-DD)")
    usage_report_p.add_argument("--end", help="End date (YYYY-MM-DD)")
    usage_report_p.set_defaults(func=cmd_usage_report)

    txn_history_p = subparsers.add_parser("transaction_history", help="Get transaction history")
    txn_history_p.add_argument("--start", help="Start date (YYYY-MM-DD)")
    txn_history_p.add_argument("--end", help="End date (YYYY-MM-DD)")
    txn_history_p.add_argument("--product", help="Filter by product ID")
    txn_history_p.add_argument("--action", help="Filter by action (stock_in, stock_out, etc.)")
    txn_history_p.add_argument("--limit", type=int, default=100, help="Max records to return")
    txn_history_p.set_defaults(func=cmd_transaction_history)

    gen_report_p = subparsers.add_parser("generate_report_file", help="Generate report data to JSON file")
    gen_report_p.add_argument("--output", required=True, help="Output file path")
    gen_report_p.add_argument("--start", help="Start date (YYYY-MM-DD)")
    gen_report_p.add_argument("--end", help="End date (YYYY-MM-DD)")
    gen_report_p.add_argument("--action", help="Filter by action type")
    gen_report_p.set_defaults(func=cmd_generate_report_file)

    # ----- Lock Commands -----
    lock_acquire_p = subparsers.add_parser("lock_acquire", help="Acquire a lock on an entity")
    lock_acquire_p.add_argument("--type", required=True, help="Entity type (product, category, etc.)")
    lock_acquire_p.add_argument("--id", required=True, help="Entity ID")
    lock_acquire_p.add_argument("--session", required=True, help="Session ID")
    lock_acquire_p.set_defaults(func=cmd_lock_acquire)

    lock_release_p = subparsers.add_parser("lock_release", help="Release a lock on an entity")
    lock_release_p.add_argument("--type", required=True, help="Entity type")
    lock_release_p.add_argument("--id", required=True, help="Entity ID")
    lock_release_p.add_argument("--session", required=True, help="Session ID")
    lock_release_p.set_defaults(func=cmd_lock_release)

    lock_check_p = subparsers.add_parser("lock_check", help="Check lock status of an entity")
    lock_check_p.add_argument("--type", required=True, help="Entity type")
    lock_check_p.add_argument("--id", required=True, help="Entity ID")
    lock_check_p.set_defaults(func=cmd_lock_check)

    lock_cleanup_p = subparsers.add_parser("lock_cleanup", help="Clean up expired locks")
    lock_cleanup_p.set_defaults(func=cmd_lock_cleanup)

    lock_list_p = subparsers.add_parser("lock_list", help="List all active locks")
    lock_list_p.set_defaults(func=cmd_lock_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
