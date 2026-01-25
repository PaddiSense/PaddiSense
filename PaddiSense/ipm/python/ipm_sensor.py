#!/usr/bin/env python3
"""
IPM Sensor - Read-only data output for Home Assistant
PaddiSense Farm Management System

This script reads the inventory and outputs JSON for the HA command_line sensor.
It provides:
  - Product list with stock totals
  - Unique product names for selection dropdowns
  - Location lists per product (for multi-location products)
  - Category/subcategory relationships (from config)
  - Chemical groups (from config)
  - Active constituents (from config)
  - Units by type (from config)

Output format:
{
  "total_products": 25,
  "products": { "PRODUCT_ID": { ... } },
  "product_names": ["Glyphosate 450", "Urea", ...],
  "product_locations": { "PRODUCT_ID": ["Silo 1", "Silo 3"], ... },
  "categories": ["Chemical", "Fertiliser", ...],
  "category_subcategories": { "Chemical": [...], ... },
  "locations": ["Chem Shed", "Seed Shed", ...],
  "chemical_groups": ["None", "1", "2", ...],
  "actives": [{"name": "...", "common_groups": [...]}, ...],
  "active_names": ["Glyphosate", "2,4-D", ...],
  "units": {"product": [...], "container": [...], ...}
}

Data source: /config/local_data/ipm/inventory.json
Config source: /config/local_data/ipm/config.json (v2.0.0)
"""

import json
from pathlib import Path

DATA_DIR = Path("/config/local_data/ipm")
DATA_FILE = DATA_DIR / "inventory.json"
CONFIG_FILE = DATA_DIR / "config.json"
BACKUP_DIR = DATA_DIR / "backups"

# Version file location (in module directory)
VERSION_FILE = Path("/config/PaddiSense/ipm/VERSION")

# Current config version
CONFIG_VERSION = "2.0.0"

# Default values (used if config doesn't exist or is pre-v2.0.0)
DEFAULT_CATEGORIES = {
    "Chemical": [
        "Adjuvant", "Fungicide", "Herbicide", "Insecticide",
        "Pesticide", "Rodenticide", "Seed Treatment",
    ],
    "Fertiliser": [
        "Nitrogen", "Phosphorus", "Potassium", "NPK Blend",
        "Trace Elements", "Organic",
    ],
    "Seed": [
        "Wheat", "Barley", "Canola", "Rice", "Oats", "Pasture", "Other",
    ],
    "Hay": [
        "Barley", "Wheat", "Clover", "Lucerne", "Vetch", "Other",
    ],
    "Lubricant": [
        "Engine Oil", "Hydraulic Oil", "Grease", "Gear Oil",
        "Transmission Fluid", "Coolant",
    ],
}

DEFAULT_LOCATIONS = [
    "Chem Shed", "Seed Shed", "Oil Shed",
]

DEFAULT_CHEMICAL_GROUPS = [
    "None", "N/A", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "11", "12", "13", "14", "15", "22", "M"
]

DEFAULT_UNITS = {
    "product": ["None", "L", "kg", "ea", "t", "mL"],
    "container": ["1", "5", "10", "20", "110", "200", "400", "1000", "bulk"],
    "application": ["L/ha", "mL/ha", "kg/ha", "g/ha", "t/ha", "mL/100L", "g/100L"],
    "concentration": ["g/L", "g/kg", "mL/L", "%"],
}


def get_version() -> str:
    """Read module version from VERSION file."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip()
    except IOError:
        pass
    return "unknown"


def load_config() -> dict:
    """Load config from JSON file, handling both v1 and v2 formats."""
    if not CONFIG_FILE.exists():
        return {
            "version": None,
            "categories": DEFAULT_CATEGORIES,
            "chemical_groups": DEFAULT_CHEMICAL_GROUPS,
            "actives": [],
            "locations": DEFAULT_LOCATIONS,
            "units": DEFAULT_UNITS,
        }

    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

        # Check if v2.0.0 format
        if config.get("version") == CONFIG_VERSION:
            return config

        # v1 format - return with defaults for missing fields
        return {
            "version": config.get("version"),
            "categories": DEFAULT_CATEGORIES,
            "chemical_groups": DEFAULT_CHEMICAL_GROUPS,
            "actives": [],  # Will be built from custom_actives if present
            "locations": config.get("locations", DEFAULT_LOCATIONS),
            "units": DEFAULT_UNITS,
            "custom_actives": config.get("custom_actives", []),  # v1 field
        }

    except (json.JSONDecodeError, IOError):
        return {
            "version": None,
            "categories": DEFAULT_CATEGORIES,
            "chemical_groups": DEFAULT_CHEMICAL_GROUPS,
            "actives": [],
            "locations": DEFAULT_LOCATIONS,
            "units": DEFAULT_UNITS,
        }


def get_backup_info() -> dict:
    """Get information about available backups."""
    backups = []
    last_backup = None
    backup_filenames = []

    if BACKUP_DIR.exists():
        for backup_file in sorted(BACKUP_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(backup_file.read_text(encoding="utf-8"))
                product_count = len(data.get("inventory", {}).get("products", {}))
                backup_info = {
                    "filename": backup_file.name,
                    "created": data.get("created", ""),
                    "note": data.get("note", ""),
                    "product_count": product_count,
                }
                backups.append(backup_info)
                backup_filenames.append(backup_file.name)

                # First one (newest) is the last backup
                if last_backup is None:
                    last_backup = backup_info
            except (json.JSONDecodeError, IOError):
                # Include file even if we can't read it
                backups.append({
                    "filename": backup_file.name,
                    "created": "",
                    "note": "Unable to read",
                    "product_count": 0,
                })
                backup_filenames.append(backup_file.name)

    return {
        "backup_count": len(backups),
        "last_backup": last_backup,
        "backups": backups,
        "backup_filenames": backup_filenames,
    }


def main():
    # Load config
    config = load_config()

    # Get values from config (v2.0.0 format)
    config_version = config.get("version")
    needs_migration = config_version != CONFIG_VERSION if config_version else True

    # Categories and subcategories
    categories = config.get("categories", DEFAULT_CATEGORIES)
    category_list = list(categories.keys())

    # Chemical groups
    chemical_groups = config.get("chemical_groups", DEFAULT_CHEMICAL_GROUPS)

    # Locations
    locations = config.get("locations", DEFAULT_LOCATIONS)

    # Units
    units = config.get("units", DEFAULT_UNITS)

    # Actives - handle both v1 and v2 format
    if config_version == CONFIG_VERSION:
        # v2.0.0 - actives is a list of dicts with name and common_groups
        actives = config.get("actives", [])
    else:
        # v1 format - no actives in config, just custom_actives
        # For v1, output empty list (automations will handle with fallback)
        actives = []

    # Build active names list for dropdowns
    active_names_from_config = [a.get("name", "") for a in actives if a.get("name")]

    # Determine system status
    config_exists = CONFIG_FILE.exists()
    database_exists = DATA_FILE.exists()

    if config_exists or database_exists:
        system_status = "ready"
    else:
        system_status = "not_initialized"

    # Get backup info
    backup_info = get_backup_info()

    # Get version
    version = get_version()

    # Default empty output
    empty_output = {
        "total_products": 0,
        "products": {},
        "product_names": [],
        "product_locations": {},
        "categories": category_list,
        "category_subcategories": categories,
        "locations": locations,
        "chemical_groups": chemical_groups,
        "actives": actives,
        "active_names": [],
        "active_names_from_config": active_names_from_config,
        "units": units,
        "system_status": system_status,
        "config_exists": config_exists,
        "database_exists": database_exists,
        "config_version": config_version or "1.0.0",
        "needs_migration": needs_migration,
        "locations_with_stock": [],
        "active_products_map": {},
        "backup_count": backup_info["backup_count"],
        "last_backup": backup_info["last_backup"],
        "backup_filenames": backup_info["backup_filenames"],
        "version": version,
        # Low stock alerts
        "low_stock_count": 0,
        "low_stock_products": [],
    }

    if not DATA_FILE.exists():
        print(json.dumps(empty_output))
        return

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        empty_output["system_status"] = "error"
        print(json.dumps(empty_output))
        return

    products = data.get("products", {})

    # Build output structures
    product_names = []
    product_locations = {}
    active_names_in_use = set()
    all_locations_with_stock = set()
    active_products_map = {}  # Maps active name to list of product names using it

    for product_id, product in products.items():
        name = product.get("name", product_id)
        product_names.append(name)

        # Get locations where this product has stock
        stock_by_location = product.get("stock_by_location", {})
        locations_with_stock = [
            loc for loc, qty in stock_by_location.items()
            if qty and float(qty) > 0
        ]

        # Track all locations that have any stock
        all_locations_with_stock.update(locations_with_stock)

        # Calculate total stock
        total_stock = sum(
            float(qty) for qty in stock_by_location.values()
            if qty
        )
        product["total_stock"] = round(total_stock, 2)

        # Store locations for this product
        if locations_with_stock:
            product_locations[product_id] = sorted(locations_with_stock)

        # Collect active constituent names and build active -> products map
        product_actives = product.get("active_constituents", [])
        if isinstance(product_actives, list):
            for active in product_actives:
                if isinstance(active, dict):
                    active_name = active.get("name", "")
                    if active_name and isinstance(active_name, str):
                        active_name = active_name.strip()
                        active_names_in_use.add(active_name)
                        # Add to products map
                        if active_name not in active_products_map:
                            active_products_map[active_name] = []
                        if name not in active_products_map[active_name]:
                            active_products_map[active_name].append(name)

    # Build low stock alerts
    low_stock_products = []
    for product_id, product in products.items():
        min_stock = float(product.get("min_stock", 0))
        total_stock = product.get("total_stock", 0)
        if min_stock > 0 and total_stock < min_stock:
            low_stock_products.append({
                "id": product_id,
                "name": product.get("name", product_id),
                "category": product.get("category", ""),
                "total_stock": total_stock,
                "min_stock": min_stock,
                "unit": product.get("unit", ""),
                "deficit": round(min_stock - total_stock, 2),
            })

    # Sort by deficit (largest first)
    low_stock_products.sort(key=lambda x: x["deficit"], reverse=True)

    output = {
        "total_products": len(products),
        "products": products,
        "product_names": sorted(product_names),
        "product_locations": product_locations,
        "categories": category_list,
        "category_subcategories": categories,
        "locations": locations,
        "chemical_groups": chemical_groups,
        "actives": actives,
        "active_names": sorted(active_names_in_use),  # Active names currently used by products
        "active_names_from_config": active_names_from_config,  # All active names from config
        "units": units,
        "system_status": "ready",
        "config_exists": config_exists,
        "database_exists": database_exists,
        "config_version": config_version or "1.0.0",
        "needs_migration": needs_migration,
        "locations_with_stock": sorted(all_locations_with_stock),
        "active_products_map": active_products_map,
        "backup_count": backup_info["backup_count"],
        "last_backup": backup_info["last_backup"],
        "backup_filenames": backup_info["backup_filenames"],
        "version": version,
        # Low stock alerts
        "low_stock_count": len(low_stock_products),
        "low_stock_products": low_stock_products,
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
