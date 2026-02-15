#!/usr/bin/env python3
"""
BOM Integration Auto-Setup for PaddiSense
==========================================
Automates the Bureau of Meteorology integration setup via HA's config flow API.

This script:
1. Starts a config flow for bureau_of_meteorology
2. Submits the required data for each step
3. Completes the flow with standard "home" naming

Usage:
    python3 bom_setup.py
    python3 bom_setup.py --observations-basename "Farm"
    python3 bom_setup.py --check  # Check if BOM is already configured
"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path

# HA internal API (accessed from within the container)
HA_URL = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")

# Fallback to long-lived token if running outside supervisor
if not HA_TOKEN:
    token_file = Path("/config/.storage/auth_tokens")
    if token_file.exists():
        # Can't easily extract, will need user to provide
        pass

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# All observation sensor keys (from const.py)
ALL_OBSERVATION_SENSORS = [
    "temp",
    "temp_feels_like",
    "max_temp",
    "min_temp",
    "rain_since_9am",
    "humidity",
    "wind_speed_kilometre",
    "wind_speed_knot",
    "wind_direction",
    "gust_speed_kilometre",
    "gust_speed_knot",
    "dew_point",
]

# All forecast sensor keys
ALL_FORECAST_SENSORS = [
    "temp_max",
    "temp_min",
    "extended_text",
    "icon_descriptor",
    "mdi_icon",
    "short_text",
    "uv_category",
    "uv_max_index",
    "uv_start_time",
    "uv_end_time",
    "uv_forecast",
    "rain_amount_min",
    "rain_amount_max",
    "rain_amount_range",
    "rain_chance",
    "fire_danger",
    "now_now_label",
    "now_temp_now",
    "now_later_label",
    "now_temp_later",
    "astronomical_sunrise_time",
    "astronomical_sunset_time",
]

# Essential sensors for PaddiSense
ESSENTIAL_OBSERVATION_SENSORS = [
    "temp",
    "temp_feels_like",
    "humidity",
    "wind_speed_kilometre",
    "gust_speed_kilometre",
    "wind_direction",
    "rain_since_9am",
    "dew_point",
]

ESSENTIAL_FORECAST_SENSORS = [
    "temp_max",
    "temp_min",
    "rain_amount_min",
    "rain_amount_max",
    "rain_chance",
    "icon_descriptor",
    "short_text",
    "uv_category",
]


def check_bom_configured():
    """Check if BOM integration is already configured."""
    try:
        response = requests.get(
            f"{HA_URL}/api/config/config_entries/entry",
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        entries = response.json()

        for entry in entries:
            if entry.get("domain") == "bureau_of_meteorology":
                return {
                    "configured": True,
                    "entry_id": entry.get("entry_id"),
                    "title": entry.get("title"),
                    "state": entry.get("state"),
                }
        return {"configured": False}
    except Exception as e:
        return {"configured": False, "error": str(e)}


def get_ha_location():
    """Get Home Assistant's configured location."""
    try:
        response = requests.get(
            f"{HA_URL}/api/config",
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        config = response.json()
        return {
            "latitude": config.get("latitude", -33.8688),
            "longitude": config.get("longitude", 151.2093),
            "location_name": config.get("location_name", "Home"),
        }
    except Exception as e:
        print(f"Warning: Could not get HA location: {e}", file=sys.stderr)
        return {"latitude": -33.8688, "longitude": 151.2093, "location_name": "Home"}


def start_config_flow():
    """Start a new config flow for BOM."""
    try:
        response = requests.post(
            f"{HA_URL}/api/config/config_entries/flow",
            headers=HEADERS,
            json={"handler": "bureau_of_meteorology"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            # Check if it's already in progress
            data = e.response.json()
            if "already_in_progress" in str(data):
                return {"error": "already_in_progress"}
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


def setup_bom(
    basename="home",
    observations=True,
    forecasts=True,
    warnings=True,
    forecast_days=6,
    essential_only=False
):
    """Run the full BOM setup flow."""
    print("Starting BOM Integration Setup...")
    print("-" * 40)

    # Check if already configured
    status = check_bom_configured()
    if status.get("configured"):
        print(f"BOM already configured: {status.get('title')}")
        print(f"Entry ID: {status.get('entry_id')}")
        print("To reconfigure, delete the existing integration first.")
        return {"success": False, "reason": "already_configured", "details": status}

    # Get HA location
    location = get_ha_location()
    print(f"Using location: {location['latitude']}, {location['longitude']}")

    # Select sensors
    obs_sensors = ESSENTIAL_OBSERVATION_SENSORS if essential_only else ALL_OBSERVATION_SENSORS
    fcst_sensors = ESSENTIAL_FORECAST_SENSORS if essential_only else ALL_FORECAST_SENSORS

    try:
        # Step 1: Start flow
        print("Step 1: Starting config flow...")
        result = start_config_flow()

        if result.get("error") == "already_in_progress":
            return {"success": False, "reason": "flow_in_progress"}

        flow_id = result["flow_id"]
        print(f"  Flow ID: {flow_id}")

        # Step 2: Submit location (user step)
        print("Step 2: Submitting location...")
        result = submit_flow_step(flow_id, {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        })

        if result.get("type") == "form" and result.get("step_id") == "weather_name":
            print(f"  BOM location found: {result.get('description_placeholders', {})}")

        # Step 3: Weather name
        print(f"Step 3: Setting weather name to '{basename}'...")
        result = submit_flow_step(flow_id, {
            "weather_name": basename,
        })

        # Step 4: Sensors to create
        print("Step 4: Selecting sensor types...")
        result = submit_flow_step(flow_id, {
            "observations_create": observations,
            "forecasts_create": forecasts,
            "warnings_create": warnings,
        })

        # Step 5: Observations (if enabled)
        if observations and result.get("step_id") == "observations_monitored":
            print(f"Step 5: Configuring observations (basename: {basename})...")
            result = submit_flow_step(flow_id, {
                "observations_basename": basename,
                "observations_monitored": obs_sensors,
            })

        # Step 6: Forecasts (if enabled)
        if forecasts and result.get("step_id") == "forecasts_monitored":
            print(f"Step 6: Configuring forecasts ({forecast_days} days)...")
            result = submit_flow_step(flow_id, {
                "forecasts_basename": basename,
                "forecasts_monitored": fcst_sensors,
                "forecasts_days": forecast_days,
            })

        # Step 7: Warnings basename (if enabled)
        if warnings and result.get("step_id") == "warnings_basename":
            print("Step 7: Configuring warnings...")
            result = submit_flow_step(flow_id, {
                "warnings_basename": basename,
            })

        # Check final result
        if result.get("type") == "create_entry":
            print("-" * 40)
            print("SUCCESS! BOM Integration configured.")
            print(f"  Title: {result.get('title')}")
            print(f"  Entry ID: {result.get('result', {}).get('entry_id')}")
            print("")
            print("Sensor naming pattern:")
            print(f"  Observations: sensor.{basename}_observations_*")
            print(f"  Forecasts:    sensor.{basename}_forecast_*")
            print(f"  Warnings:     sensor.{basename}_warnings")
            return {
                "success": True,
                "title": result.get("title"),
                "entry_id": result.get("result", {}).get("entry_id"),
            }
        else:
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
    parser = argparse.ArgumentParser(description="Setup BOM integration for PaddiSense")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if BOM is already configured"
    )
    parser.add_argument(
        "--basename",
        default="home",
        help="Base name for sensors (default: home)"
    )
    parser.add_argument(
        "--no-observations",
        action="store_true",
        help="Skip observation sensors"
    )
    parser.add_argument(
        "--no-forecasts",
        action="store_true",
        help="Skip forecast sensors"
    )
    parser.add_argument(
        "--no-warnings",
        action="store_true",
        help="Skip warning sensors"
    )
    parser.add_argument(
        "--forecast-days",
        type=int,
        default=6,
        help="Number of forecast days (0-7, default: 6)"
    )
    parser.add_argument(
        "--essential-only",
        action="store_true",
        help="Only enable essential sensors for PaddiSense"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if args.check:
        result = check_bom_configured()
        if args.json:
            print(json.dumps(result))
        else:
            if result.get("configured"):
                print(f"BOM is configured: {result.get('title')}")
                print(f"State: {result.get('state')}")
            else:
                print("BOM is not configured")
        sys.exit(0 if result.get("configured") else 1)

    result = setup_bom(
        basename=args.basename,
        observations=not args.no_observations,
        forecasts=not args.no_forecasts,
        warnings=not args.no_warnings,
        forecast_days=args.forecast_days,
        essential_only=args.essential_only,
    )

    if args.json:
        print(json.dumps(result))

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
