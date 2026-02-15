#!/usr/bin/env python3
"""
HACS Dependency Checker for PaddiSense
Checks if required HACS frontend components are installed.
"""

import json
import os
import sys

LOVELACE_RESOURCES = "/config/.storage/lovelace_resources"

# Required HACS frontend components for PaddiSense
REQUIRED_COMPONENTS = {
    "button-card": {
        "name": "Button Card",
        "search": "button-card",
        "hacs_repo": "custom-cards/button-card",
        "required": True  # Core dependency - blocks all dashboards
    },
    "auto-entities": {
        "name": "Auto Entities",
        "search": "auto-entities",
        "hacs_repo": "thomasloven/lovelace-auto-entities",
        "required": False
    },
    "card-mod": {
        "name": "Card Mod",
        "search": "card-mod",
        "hacs_repo": "thomasloven/lovelace-card-mod",
        "required": False
    },
    "mushroom": {
        "name": "Mushroom Cards",
        "search": "mushroom",
        "hacs_repo": "piitaya/lovelace-mushroom",
        "required": False
    },
    "apexcharts-card": {
        "name": "ApexCharts Card",
        "search": "apexcharts-card",
        "hacs_repo": "RomRider/apexcharts-card",
        "required": False
    }
}


def check_lovelace_resources():
    """Check installed lovelace resources for HACS components."""
    installed = {}

    if not os.path.exists(LOVELACE_RESOURCES):
        return installed

    try:
        with open(LOVELACE_RESOURCES, 'r') as f:
            data = json.load(f)

        items = data.get("data", {}).get("items", [])
        urls = [item.get("url", "") for item in items]

        for comp_id, comp_info in REQUIRED_COMPONENTS.items():
            search_term = comp_info["search"]
            installed[comp_id] = any(search_term in url for url in urls)

    except Exception:
        pass

    return installed


def check_hacs_installed():
    """Check if HACS integration is installed."""
    return os.path.exists("/config/custom_components/hacs")


def main():
    """Output JSON status of HACS dependencies."""
    hacs_installed = check_hacs_installed()
    installed = check_lovelace_resources()

    # Check required components
    required_ok = all(
        installed.get(comp_id, False)
        for comp_id, info in REQUIRED_COMPONENTS.items()
        if info.get("required", False)
    )

    # Build missing list
    missing = []
    missing_required = []
    for comp_id, info in REQUIRED_COMPONENTS.items():
        if not installed.get(comp_id, False):
            missing.append(info["name"])
            if info.get("required", False):
                missing_required.append(info["name"])

    # Overall status
    if not hacs_installed:
        status = "hacs_missing"
    elif not required_ok:
        status = "deps_missing"
    else:
        status = "ready"

    output = {
        "status": status,
        "hacs_installed": hacs_installed,
        "ready": status == "ready",
        "required_ok": required_ok,
        "components": {
            comp_id: {
                "name": info["name"],
                "installed": installed.get(comp_id, False),
                "required": info.get("required", False),
                "hacs_repo": info["hacs_repo"]
            }
            for comp_id, info in REQUIRED_COMPONENTS.items()
        },
        "missing": missing,
        "missing_required": missing_required,
        "missing_count": len(missing),
        "missing_required_count": len(missing_required)
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
