#!/usr/bin/env python3
"""
Browser Mod Integration Auto-Setup for PaddiSense
==================================================
Automates the Browser Mod integration setup via HA's config flow API.

Browser Mod has a simple single-step flow that just creates an entry.

Usage:
    python3 browser_mod_setup.py
    python3 browser_mod_setup.py --check  # Check if already configured
"""

import argparse
import json
import os
import sys
import requests

# HA internal API (accessed from within the container)
HA_URL = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


def check_browser_mod_configured():
    """Check if Browser Mod integration is already configured."""
    try:
        response = requests.get(
            f"{HA_URL}/api/config/config_entries/entry",
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        entries = response.json()

        for entry in entries:
            if entry.get("domain") == "browser_mod":
                return {
                    "configured": True,
                    "entry_id": entry.get("entry_id"),
                    "title": entry.get("title"),
                    "state": entry.get("state"),
                }
        return {"configured": False}
    except Exception as e:
        return {"configured": False, "error": str(e)}


def check_browser_mod_installed():
    """Check if Browser Mod custom component is installed."""
    return os.path.exists("/config/custom_components/browser_mod/manifest.json")


def start_config_flow():
    """Start a new config flow for Browser Mod."""
    try:
        response = requests.post(
            f"{HA_URL}/api/config/config_entries/flow",
            headers=HEADERS,
            json={"handler": "browser_mod"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            data = e.response.json()
            if "already_in_progress" in str(data):
                return {"error": "already_in_progress"}
            if "single_instance_allowed" in str(data):
                return {"error": "single_instance_allowed"}
        raise


def submit_flow_step(flow_id, user_input):
    """Submit data to a config flow step."""
    response = requests.post(
        f"{HA_URL}/api/config/config_entries/flow/{flow_id}",
        headers=HEADERS,
        json=user_input,
        timeout=60
    )
    response.raise_for_status()
    return response.json()


def setup_browser_mod():
    """Run the Browser Mod setup flow."""
    print("Starting Browser Mod Integration Setup...")
    print("-" * 40)

    # Check if installed
    if not check_browser_mod_installed():
        print("ERROR: Browser Mod is not installed.")
        print("Install it via HACS first: HACS → Integrations → Browser Mod")
        return {"success": False, "reason": "not_installed"}

    # Check if already configured
    status = check_browser_mod_configured()
    if status.get("configured"):
        print(f"Browser Mod already configured: {status.get('title')}")
        print(f"Entry ID: {status.get('entry_id')}")
        return {"success": True, "reason": "already_configured", "details": status}

    try:
        # Step 1: Start flow
        print("Step 1: Starting config flow...")
        result = start_config_flow()

        if result.get("error") == "already_in_progress":
            return {"success": False, "reason": "flow_in_progress"}
        if result.get("error") == "single_instance_allowed":
            return {"success": True, "reason": "already_configured"}

        flow_id = result.get("flow_id")

        # Browser Mod creates entry immediately on user step
        if result.get("type") == "create_entry":
            print("-" * 40)
            print("SUCCESS! Browser Mod configured.")
            print(f"  Title: {result.get('title')}")
            return {
                "success": True,
                "title": result.get("title"),
                "entry_id": result.get("result", {}).get("entry_id"),
            }

        # If we got a form, submit empty data
        if flow_id and result.get("type") == "form":
            print(f"  Flow ID: {flow_id}")
            print("Step 2: Submitting configuration...")
            result = submit_flow_step(flow_id, {})

            if result.get("type") == "create_entry":
                print("-" * 40)
                print("SUCCESS! Browser Mod configured.")
                print(f"  Title: {result.get('title')}")
                return {
                    "success": True,
                    "title": result.get("title"),
                    "entry_id": result.get("result", {}).get("entry_id"),
                }

        print(f"Unexpected result: {result}")
        return {"success": False, "reason": "unexpected_result", "details": result}

    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = e.response.json()
        except:
            error_detail = e.response.text
        print(f"HTTP Error: {e}")
        print(f"Details: {error_detail}")
        return {"success": False, "reason": "http_error", "details": str(error_detail)}
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "reason": "error", "details": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Setup Browser Mod integration for PaddiSense")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if Browser Mod is already configured"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if args.check:
        installed = check_browser_mod_installed()
        configured = check_browser_mod_configured()
        result = {
            "installed": installed,
            **configured
        }
        if args.json:
            print(json.dumps(result))
        else:
            if not installed:
                print("Browser Mod is NOT installed")
            elif configured.get("configured"):
                print(f"Browser Mod is configured: {configured.get('title')}")
                print(f"State: {configured.get('state')}")
            else:
                print("Browser Mod is installed but NOT configured")
        sys.exit(0 if configured.get("configured") else 1)

    result = setup_browser_mod()

    if args.json:
        print(json.dumps(result))

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
