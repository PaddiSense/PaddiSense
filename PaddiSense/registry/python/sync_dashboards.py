#!/usr/bin/env python3
"""
PaddiSense Dashboard Sync
=========================
Synchronizes lovelace_dashboards.yaml with installed modules.

Reads modules.json for dashboard metadata and adds/updates entries
in lovelace_dashboards.yaml for all installed modules.

This script is ADDITIVE - it adds missing dashboards but preserves
existing custom dashboards not defined in modules.json.

Usage:
    python3 sync_dashboards.py          # Sync dashboards
    python3 sync_dashboards.py --check  # Check only, don't modify
    python3 sync_dashboards.py --json   # Output JSON status
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Paths
CONFIG_DIR = Path("/config")
PADDISENSE_DIR = CONFIG_DIR / "PaddiSense"
MODULES_JSON = PADDISENSE_DIR / "modules.json"
LOVELACE_FILE = CONFIG_DIR / "lovelace_dashboards.yaml"


def load_modules_json() -> dict:
    """Load modules.json."""
    try:
        if MODULES_JSON.exists():
            return json.loads(MODULES_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading modules.json: {e}", file=sys.stderr)
    return {"modules": {}}


def is_module_installed(module_id: str) -> bool:
    """Check if a module is installed (has package.yaml)."""
    module_dir = PADDISENSE_DIR / module_id
    package_file = module_dir / "package.yaml"
    return package_file.exists()


def get_installed_modules(modules_data: dict) -> list[dict]:
    """Get list of installed modules with their dashboard info."""
    installed = []
    all_modules = modules_data.get("modules", {})

    for module_id, module_info in all_modules.items():
        if not is_module_installed(module_id):
            continue

        # Check if module has dashboard config
        dashboard_slug = module_info.get("dashboard_slug")
        dashboard_file = module_info.get("dashboard_file")

        if not dashboard_slug or not dashboard_file:
            continue

        # Verify dashboard file exists
        dashboard_path = PADDISENSE_DIR / dashboard_file
        if not dashboard_path.exists():
            print(f"Warning: Dashboard file missing for {module_id}: {dashboard_file}", file=sys.stderr)
            continue

        installed.append({
            "id": module_id,
            "slug": dashboard_slug,
            "title": module_info.get("dashboard_title", module_info.get("name", module_id)),
            "icon": module_info.get("icon", "mdi:puzzle"),
            "file": dashboard_file,
        })

    return installed


def parse_lovelace_yaml() -> tuple[list[str], dict[str, dict]]:
    """
    Parse existing lovelace_dashboards.yaml.
    Returns (header_lines, dashboards_dict).
    """
    header_lines = []
    dashboards = {}

    if not LOVELACE_FILE.exists():
        return header_lines, dashboards

    try:
        content = LOVELACE_FILE.read_text(encoding="utf-8")
        lines = content.splitlines()

        current_slug = None
        current_entry = {}

        for line in lines:
            # Header comments at the start
            if not dashboards and not current_slug:
                if line.startswith("#") or line.strip() == "":
                    header_lines.append(line)
                    continue

            # Dashboard entry start (no leading whitespace, ends with :)
            match = re.match(r"^([a-zA-Z0-9_-]+):$", line)
            if match:
                # Save previous entry
                if current_slug:
                    dashboards[current_slug] = current_entry

                current_slug = match.group(1)
                current_entry = {"_raw_lines": [line]}
                continue

            # Property within dashboard entry
            if current_slug and line.startswith("  "):
                current_entry["_raw_lines"].append(line)
                # Parse key: value
                prop_match = re.match(r"^  ([a-zA-Z_]+):\s*(.*)$", line)
                if prop_match:
                    key = prop_match.group(1)
                    value = prop_match.group(2).strip()
                    # Handle quoted strings
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    # Handle booleans
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    current_entry[key] = value

        # Save last entry
        if current_slug:
            dashboards[current_slug] = current_entry

    except IOError:
        pass

    return header_lines, dashboards


def generate_dashboard_entry(mod: dict) -> list[str]:
    """Generate YAML lines for a dashboard entry."""
    return [
        f"{mod['slug']}:",
        "  mode: yaml",
        f"  title: {mod['title']}",
        f"  icon: {mod['icon']}",
        "  show_in_sidebar: true",
        f"  filename: PaddiSense/{mod['file']}",
    ]


def sync_dashboards(check_only: bool = False, json_output: bool = False) -> int:
    """Sync lovelace_dashboards.yaml with installed modules."""
    modules_data = load_modules_json()
    installed = get_installed_modules(modules_data)

    # Sort: registry first, then alphabetically
    def sort_key(m):
        if m["id"] == "registry":
            return "0_registry"
        return f"1_{m['id']}"

    installed.sort(key=sort_key)

    # Parse existing file
    header_lines, existing_dashboards = parse_lovelace_yaml()

    # Build expected slug set
    expected_slugs = {m["slug"] for m in installed}
    current_slugs = set(existing_dashboards.keys())

    missing = expected_slugs - current_slugs
    # Extra dashboards are kept (additive mode)

    if json_output:
        result = {
            "status": "ok" if not missing else "needs_sync",
            "installed_modules": [m["id"] for m in installed],
            "expected_dashboards": sorted(expected_slugs),
            "current_dashboards": sorted(current_slugs),
            "missing": sorted(missing),
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0 if not missing else 1

    if not missing:
        print("All module dashboards are registered.")
        return 0

    print(f"Missing dashboards: {', '.join(sorted(missing))}")

    if check_only:
        print("\nRun without --check to add missing dashboards.")
        return 1

    # Use default header if file was empty
    if not header_lines:
        header_lines = [
            "# Auto-generated by PaddiSense",
            "# Do not edit manually - changes may be overwritten",
            "# Manage modules via PaddiSense Manager",
            "",
        ]

    # Build new content: header + all dashboards (existing updated + new added)
    output_lines = header_lines.copy()

    # Track which modules we've output
    output_slugs = set()

    # First, output all installed modules in order
    for mod in installed:
        slug = mod["slug"]
        output_lines.extend(generate_dashboard_entry(mod))
        output_slugs.add(slug)

    # Then, preserve any existing dashboards not in modules.json
    for slug, entry in existing_dashboards.items():
        if slug not in output_slugs:
            # Keep existing entry as-is
            output_lines.extend(entry.get("_raw_lines", []))
            output_slugs.add(slug)

    # Write file
    try:
        content = "\n".join(output_lines) + "\n"
        LOVELACE_FILE.write_text(content, encoding="utf-8")
        print(f"\nUpdated {LOVELACE_FILE}")
        print(f"Added: {', '.join(sorted(missing))}")
        return 0
    except IOError as e:
        print(f"Error writing lovelace_dashboards.yaml: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync PaddiSense dashboards")
    parser.add_argument("--check", action="store_true", help="Check only, don't modify")
    parser.add_argument("--json", action="store_true", help="Output JSON status")
    args = parser.parse_args()

    return sync_dashboards(check_only=args.check, json_output=args.json)


if __name__ == "__main__":
    sys.exit(main())
