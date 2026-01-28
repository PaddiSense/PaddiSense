#!/usr/bin/env python3
"""
PWM Generator - Auto-generate YAML entities for paddocks
PaddiSense Farm Management System

This script reads paddock/bay STRUCTURE from Farm Registry and PWM-specific
SETTINGS from PWM config, then generates all necessary YAML files:
  - Input helpers (input_select, input_number, input_boolean)
  - Template sensors (water depth)
  - Timers
  - Automations (irrigation logic, door control, state propagation)

Data Sources:
  - Farm Registry (local_data/registry/config.json): paddock/bay structure
  - PWM Config (local_data/pwm/config.json): enabled, devices, water levels

Usage:
  python3 pwm_generator.py generate              # Generate all YAML
  python3 pwm_generator.py generate --paddock sw5  # Generate for specific paddock
  python3 pwm_generator.py clean                 # Remove generated files
  python3 pwm_generator.py list                  # List what would be generated
  python3 pwm_generator.py dashboard             # Generate dashboard views

Output:
  /config/PaddiSense/pwm/generated/pwm_paddock_<id>.yaml
  /config/PaddiSense/pwm/generated/pwm_bay_<paddock>_<bay>.yaml
  /config/PaddiSense/pwm/dashboards/views.yaml  (updated with paddock views)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Paths
REGISTRY_FILE = Path("/config/local_data/registry/config.json")
PWM_CONFIG_FILE = Path("/config/local_data/pwm/config.json")
OUTPUT_DIR = Path("/config/PaddiSense/pwm/generated")
PACKAGES_DIR = Path("/config/PaddiSense/packages")
VERSION = "2026.01.1"

# Automation modes
AUTOMATION_MODES = ["Off", "Flush", "Pond", "Drain"]
DOOR_STATES = ["Close", "Open", "HoldOne", "HoldTwo"]


def slugify(name: str) -> str:
    """Convert name to valid entity ID slug."""
    s = re.sub(r"[^a-z0-9]+", "_", name.lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:50] if s else "unknown"


def load_registry() -> dict[str, Any]:
    """Load Farm Registry config (paddock/bay structure)."""
    if not REGISTRY_FILE.exists():
        print(f"[ERROR] Registry file not found: {REGISTRY_FILE}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in registry: {e}", file=sys.stderr)
        sys.exit(1)


def load_pwm_config() -> dict[str, Any]:
    """Load PWM-specific config (settings, device assignments)."""
    if not PWM_CONFIG_FILE.exists():
        # Return empty config if PWM config doesn't exist yet
        return {"paddock_settings": {}, "bay_settings": {}}
    try:
        return json.loads(PWM_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[WARN] Invalid JSON in PWM config: {e}", file=sys.stderr)
        return {"paddock_settings": {}, "bay_settings": {}}


def load_merged_config() -> dict[str, Any]:
    """
    Load and merge Registry structure with PWM settings.

    Returns a unified config dict with:
      - paddocks: merged from registry + pwm settings
      - bays: merged from registry + pwm settings
    """
    registry = load_registry()
    pwm = load_pwm_config()

    # Get PWM settings (support both old and new format)
    # Old format: paddocks/bays directly in pwm config
    # New format: paddock_settings/bay_settings
    pwm_paddock_settings = pwm.get("paddock_settings", {})
    pwm_bay_settings = pwm.get("bay_settings", {})

    # Fall back to old format if new format is empty
    if not pwm_paddock_settings and "paddocks" in pwm:
        pwm_paddock_settings = {
            pid: {
                "enabled": p.get("enabled", True),
                "automation_state_individual": p.get("automation_state_individual", False)
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
                "settings": b.get("settings", {})
            }
            for bid, b in pwm.get("bays", {}).items()
        }

    # Merge paddocks: structure from registry + settings from pwm
    merged_paddocks = {}
    for pid, p in registry.get("paddocks", {}).items():
        pwm_settings = pwm_paddock_settings.get(pid, {})
        merged_paddocks[pid] = {
            **p,  # Registry structure (name, farm_id, bay_count, bay_prefix)
            "enabled": pwm_settings.get("enabled", True),
            "automation_state_individual": pwm_settings.get("automation_state_individual", False)
        }

    # Merge bays: structure from registry + settings from pwm
    merged_bays = {}
    for bid, b in registry.get("bays", {}).items():
        pwm_settings = pwm_bay_settings.get(bid, {})
        merged_bays[bid] = {
            **b,  # Registry structure (paddock_id, name, order, is_last_bay)
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
            })
        }

    return {
        "paddocks": merged_paddocks,
        "bays": merged_bays,
        "initialized": registry.get("initialized", False)
    }


def ensure_output_dir():
    """Create output directory if needed."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Create a package include file
    include_file = OUTPUT_DIR / "_include.yaml"
    if not include_file.exists():
        include_file.write_text("# Auto-generated PWM entities - do not edit manually\n")


def get_bay_list(config: dict, paddock_id: str) -> list[dict]:
    """Get sorted list of bays for a paddock."""
    bays = []
    for bay_id, bay_data in config.get("bays", {}).items():
        if bay_data.get("paddock_id") == paddock_id:
            bays.append({"id": bay_id, **bay_data})
    return sorted(bays, key=lambda b: b.get("order", 0))


def generate_paddock_yaml(paddock_id: str, paddock: dict, bays: list[dict]) -> str:
    """Generate YAML for paddock-level entities."""
    name = paddock.get("name", paddock_id)
    name_upper = name.upper()
    bay_count = len(bays)

    # Build list of bay entity IDs for automations
    bay_automation_states = [f"input_select.{paddock_id}_b_{str(i).zfill(2)}_automation_state"
                            for i in range(1, bay_count + 1)]
    bay_door_controls = [f"input_select.{paddock_id}_b_{str(i).zfill(2)}_door_control"
                        for i in range(1, bay_count + 1)]

    yaml_content = f"""# PWM Generated - {name_upper}
# Generated: {datetime.now().isoformat(timespec='seconds')}
# Version: {VERSION}
# DO NOT EDIT - Changes will be overwritten on regeneration

#==============================================================================
# PADDOCK INPUT HELPERS
#==============================================================================
input_select:
  {paddock_id}_automation_state:
    name: "PWM {name_upper} Automation State"
    options: {json.dumps(AUTOMATION_MODES)}
    initial: "Off"
    icon: mdi:water

  {paddock_id}_drain_door_control:
    name: "PWM {name_upper} Drain Door Control"
    options: {json.dumps(DOOR_STATES)}
    initial: "Close"
    icon: mdi:door

input_number:
  {paddock_id}_supply_waterleveloffset:
    name: "PWM {name_upper} Supply Water Level Offset"
    unit_of_measurement: "cm"
    min: -150
    max: 150
    step: 0.1
    mode: box
    icon: mdi:arrow-up-down

timer:
  {paddock_id}_flushclosesupply:
    name: "PWM {name_upper} Flush Close Supply Timer"
    duration: "01:00:00"
    icon: mdi:timer

#==============================================================================
# PADDOCK TEMPLATE SENSORS
#==============================================================================
template:
  - sensor:
      - name: "PWM {name_upper} Version"
        unique_id: "pwm_{paddock_id}_version"
        icon: mdi:tag
        state: "{VERSION}"

      - name: "PWM {name_upper} Supply Water Depth"
        unique_id: "pwm_{paddock_id}_supply_water_depth"
        state_class: measurement
        device_class: distance
        unit_of_measurement: "cm"
        state: >-
          {{% set bays = state_attr('sensor.pwm_data', 'bays') or {{}} %}}
          {{% set bay = bays.get('{paddock_id}_b_01', {{}}) %}}
          {{% set device = bay.get('supply_1', {{}}).get('device', '') %}}
          {{% if not device or device == 'unset' %}}
            unavailable
          {{% else %}}
            {{% set depth_id = 'sensor.' ~ device ~ '_' ~ device ~ '_1m_water_depth' %}}
            {{% set depth = states(depth_id) | float(default=-999) %}}
            {{% set offset = states('input_number.{paddock_id}_supply_waterleveloffset') | float(0) %}}
            {{% if depth == -999 %}}unavailable{{% else %}}{{{{ (depth - offset) | round(1) }}}}{{% endif %}}
          {{% endif %}}

#==============================================================================
# PADDOCK AUTOMATIONS
#==============================================================================
automation:
  #----------------------------------------------------------------------------
  # Door Control - Maps UI door controls to ESPHome devices
  #----------------------------------------------------------------------------
  - id: "pwm_{paddock_id}_door_control"
    alias: "PWM {name_upper} Door Control"
    description: "Maps door control input_selects to ESPHome actuator states"
    mode: parallel
    max: 20
    trigger:
      - platform: state
        entity_id:
          - input_select.{paddock_id}_drain_door_control
"""

    # Add bay door control triggers
    for bay in bays:
        bay_slug = f"b_{str(bay.get('order', 1)).zfill(2)}"
        yaml_content += f"          - input_select.{paddock_id}_{bay_slug}_door_control\n"

    yaml_content += f"""    variables:
      control_entity: "{{{{ trigger.entity_id }}}}"
      control_state: "{{{{ trigger.to_state.state }}}}"
      entity_id_part: "{{{{ control_entity.split('.')[1] }}}}"
      is_drain: "{{{{ '_drain_door_control' in entity_id_part }}}}"
      bay_match: >-
        {{% set bays = state_attr('sensor.pwm_data', 'bays') or {{}} %}}
        {{% if is_drain %}}
          {{% for bid, b in bays.items() if b.paddock_id == '{paddock_id}' and b.get('is_last_bay') %}}
            {{{{ b.get('drain_1', {{}}).get('device', '') }}}}
          {{% endfor %}}
        {{% else %}}
          {{% set bay_num = entity_id_part | regex_findall('_b_(\\d+)_') | first | default('') %}}
          {{% set bay_id = '{paddock_id}_b_' ~ bay_num %}}
          {{% set bay = bays.get(bay_id, {{}}) %}}
          {{{{ bay.get('supply_1', {{}}).get('device', '') }}}}
        {{% endif %}}
      device: "{{{{ bay_match | trim }}}}"
    condition:
      - condition: template
        value_template: "{{{{ device | length > 0 and device != 'unset' }}}}"
    action:
      - service: input_select.select_option
        target:
          entity_id: "input_select.{{{{ device }}}}_actuator_state"
        data:
          option: "{{{{ control_state }}}}"

  #----------------------------------------------------------------------------
  # State Propagation - Paddock state to all bays (when not individual mode)
  #----------------------------------------------------------------------------
  - id: "pwm_{paddock_id}_propagate_state"
    alias: "PWM {name_upper} Propagate State"
    description: "Propagate paddock automation state to all bays unless individual mode"
    mode: single
    trigger:
      - platform: state
        entity_id: input_select.{paddock_id}_automation_state
    condition:
      - condition: template
        value_template: >-
          {{% set paddocks = state_attr('sensor.pwm_data', 'paddocks') or {{}} %}}
          {{% set p = paddocks.get('{paddock_id}', {{}}) %}}
          {{{{ not p.get('automation_state_individual', false) }}}}
    action:
      - service: input_select.select_option
        target:
          entity_id:
"""

    for entity in bay_automation_states:
        yaml_content += f"            - {entity}\n"

    yaml_content += f"""        data:
          option: "{{{{ states('input_select.{paddock_id}_automation_state') }}}}"

  #----------------------------------------------------------------------------
  # All Bays Off - Set paddock to Off when all bays are Off
  #----------------------------------------------------------------------------
  - id: "pwm_{paddock_id}_all_bays_off"
    alias: "PWM {name_upper} All Bays Off"
    description: "Set paddock state to Off when all bay states are Off"
    mode: single
    trigger:
      - platform: state
        entity_id:
"""

    for entity in bay_automation_states:
        yaml_content += f"          - {entity}\n"

    yaml_content += f"""        to: "Off"
    condition:
      - condition: not
        conditions:
          - condition: state
            entity_id: input_select.{paddock_id}_automation_state
            state: "Off"
      - condition: state
        entity_id:
"""

    for entity in bay_automation_states:
        yaml_content += f"          - {entity}\n"

    yaml_content += f"""        state: "Off"
    action:
      - service: input_select.select_option
        target:
          entity_id: input_select.{paddock_id}_automation_state
        data:
          option: "Off"
"""

    return yaml_content


def generate_bay_yaml(paddock_id: str, paddock: dict, bay: dict,
                      prev_bay: dict | None, next_bay: dict | None, is_last: bool) -> str:
    """Generate YAML for bay-level entities."""
    paddock_name = paddock.get("name", paddock_id).upper()
    bay_order = bay.get("order", 1)
    bay_num = str(bay_order).zfill(2)
    bay_slug = f"b_{bay_num}"
    bay_id = f"{paddock_id}_{bay_slug}"
    bay_name = bay.get("name", f"B-{bay_num}")
    display_name = f"PWM {paddock_name} {bay_name.upper()}"

    # Determine next door target (next bay's supply or drain)
    if is_last:
        next_door = f"input_select.{paddock_id}_drain_door_control"
        next_door_name = "Drain"
    else:
        next_num = str(bay_order + 1).zfill(2)
        next_door = f"input_select.{paddock_id}_b_{next_num}_door_control"
        next_door_name = f"B-{next_num}"

    # Previous bay flush active (if exists)
    has_prev = prev_bay is not None
    if has_prev:
        prev_num = str(bay_order - 1).zfill(2)
        prev_flush = f"input_boolean.{paddock_id}_b_{prev_num}_flushactive"

    yaml_content = f"""# PWM Generated - {paddock_name} {bay_name.upper()}
# Generated: {datetime.now().isoformat(timespec='seconds')}
# Version: {VERSION}
# DO NOT EDIT - Changes will be overwritten on regeneration

#==============================================================================
# BAY INPUT HELPERS
#==============================================================================
input_select:
  {bay_id}_door_control:
    name: "{display_name} Door Control"
    options: {json.dumps(DOOR_STATES)}
    initial: "Close"
    icon: mdi:door

  {bay_id}_automation_state:
    name: "{display_name} Automation State"
    options: {json.dumps(AUTOMATION_MODES)}
    initial: "Off"
    icon: mdi:water

input_number:
  {bay_id}_waterlevelmax:
    name: "{display_name} Water Level Max"
    unit_of_measurement: "cm"
    min: 0
    max: 40
    step: 1
    initial: 15
    mode: box
    icon: mdi:water

  {bay_id}_waterlevelmin:
    name: "{display_name} Water Level Min"
    unit_of_measurement: "cm"
    min: -10
    max: 40
    step: 1
    initial: 5
    mode: box
    icon: mdi:water-minus

  {bay_id}_waterleveloffset:
    name: "{display_name} Water Level Offset"
    unit_of_measurement: "cm"
    min: -150
    max: 150
    step: 0.1
    initial: 0
    mode: box
    icon: mdi:arrow-up-down

input_boolean:
  {bay_id}_flushactive:
    name: "{display_name} Flush Active"
    initial: false
    icon: mdi:water-pump

timer:
  {bay_id}_flushtimeonwater:
    name: "{display_name} Flush Time On Water"
    duration: "01:00:00"
    icon: mdi:timer

#==============================================================================
# BAY TEMPLATE SENSORS
#==============================================================================
template:
  - sensor:
      - name: "{display_name} Water Depth"
        unique_id: "pwm_{bay_id}_water_depth"
        state_class: measurement
        device_class: distance
        unit_of_measurement: "cm"
        state: >-
          {{% set bays = state_attr('sensor.pwm_data', 'bays') or {{}} %}}
          {{% set bay = bays.get('{bay_id}', {{}}) %}}
          {{% set device = '' %}}
          {{% if bay.get('is_last_bay') %}}
            {{% set device = bay.get('drain_1', {{}}).get('device', '') %}}
          {{% else %}}
            {{% set next_order = {bay_order} + 1 %}}
            {{% set next_id = '{paddock_id}_b_' ~ '%02d' | format(next_order) %}}
            {{% set next_bay = bays.get(next_id, {{}}) %}}
            {{% set device = next_bay.get('supply_1', {{}}).get('device', '') %}}
            {{% if not device %}}
              {{% set device = bay.get('supply_1', {{}}).get('device', '') %}}
            {{% endif %}}
          {{% endif %}}
          {{% if not device or device == 'unset' %}}
            unavailable
          {{% else %}}
            {{% set depth_id = 'sensor.' ~ device ~ '_' ~ device ~ '_1m_water_depth' %}}
            {{% set depth = states(depth_id) | float(default=-999) %}}
            {{% set offset = states('input_number.{bay_id}_waterleveloffset') | float(0) %}}
            {{% if depth == -999 %}}unavailable{{% else %}}{{{{ (depth - offset) | round(1) }}}}{{% endif %}}
          {{% endif %}}

#==============================================================================
# BAY AUTOMATIONS
#==============================================================================
automation:
  #----------------------------------------------------------------------------
  # Irrigation Automation - Main water control logic
  #----------------------------------------------------------------------------
  - id: "pwm_{bay_id}_irrigation"
    alias: "{display_name} Irrigation"
    description: "Main irrigation automation for {bay_name}"
    mode: restart
    trigger:
      - platform: homeassistant
        event: start
      - platform: state
        entity_id: input_select.{bay_id}_automation_state
        for: "00:02:00"
      - platform: state
        entity_id: input_boolean.{bay_id}_flushactive
"""

    if has_prev:
        yaml_content += f"""      - platform: state
        entity_id: {prev_flush}
"""

    yaml_content += f"""      - platform: state
        entity_id:
          - input_number.{bay_id}_waterlevelmin
          - input_number.{bay_id}_waterlevelmax
        for: "00:05:00"
      - platform: time_pattern
        minutes: "/10"
    condition:
      - condition: not
        conditions:
          - condition: state
            entity_id: input_select.{bay_id}_automation_state
            state: "Off"
    action:
      - variables:
          water_level: "{{{{ states('sensor.pwm_{bay_id}_water_depth') | float(-999) }}}}"
          level_min: "{{{{ states('input_number.{bay_id}_waterlevelmin') | float(5) }}}}"
          level_max: "{{{{ states('input_number.{bay_id}_waterlevelmax') | float(15) }}}}"
          flush_active: "{{{{ is_state('input_boolean.{bay_id}_flushactive', 'on') }}}}"
"""

    if has_prev:
        yaml_content += f"""          prev_flushing: "{{{{ is_state('{prev_flush}', 'on') }}}}"
"""
    else:
        yaml_content += """          prev_flushing: false
"""

    yaml_content += f"""          mode: "{{{{ states('input_select.{bay_id}_automation_state') }}}}"
      - choose:
          #------------------------------------------------------------------
          # FLUSH MODE
          #------------------------------------------------------------------
          - conditions:
              - condition: template
                value_template: "{{{{ mode == 'Flush' }}}}"
            sequence:
              - choose:
                  # Need water - open supply, close drain
                  - conditions:
                      - condition: template
                        value_template: "{{{{ water_level < level_min and not prev_flushing }}}}"
                    sequence:
                      - service: input_select.select_option
                        target:
                          entity_id: {next_door}
                        data:
                          option: "Close"
                      - service: input_select.select_option
                        target:
                          entity_id: input_select.{bay_id}_door_control
                        data:
                          option: "Open"
                  # Water at level and flush active - release water
                  - conditions:
                      - condition: template
                        value_template: "{{{{ water_level >= level_max and flush_active and not prev_flushing }}}}"
                    sequence:
                      - service: input_select.select_option
                        target:
                          entity_id: input_select.{bay_id}_door_control
                        data:
                          option: "Close"
                      - service: input_select.select_option
                        target:
                          entity_id: {next_door}
                        data:
                          option: "Open"
                  # Flush complete - turn off
                  - conditions:
                      - condition: template
                        value_template: "{{{{ not flush_active and not prev_flushing }}}}"
                    sequence:
                      - service: input_select.select_option
                        target:
                          entity_id: {next_door}
                        data:
                          option: "Open"
                      - service: input_select.select_option
                        target:
                          entity_id: input_select.{bay_id}_automation_state
                        data:
                          option: "Off"

          #------------------------------------------------------------------
          # POND MODE - Maintain water level
          #------------------------------------------------------------------
          - conditions:
              - condition: template
                value_template: "{{{{ mode == 'Pond' }}}}"
            sequence:
              - choose:
                  # Below min - add water
                  - conditions:
                      - condition: template
                        value_template: "{{{{ water_level < level_min }}}}"
                    sequence:
                      - service: input_select.select_option
                        target:
                          entity_id: input_select.{bay_id}_door_control
                        data:
                          option: "Open"
"""

    if is_last:
        yaml_content += f"""                      - service: input_select.select_option
                        target:
                          entity_id: {next_door}
                        data:
                          option: "Close"
"""

    yaml_content += f"""                  # Above max - release water
                  - conditions:
                      - condition: template
                        value_template: "{{{{ water_level > level_max }}}}"
                    sequence:
                      - service: input_select.select_option
                        target:
                          entity_id: input_select.{bay_id}_door_control
                        data:
                          option: "Close"
                      - service: input_select.select_option
                        target:
                          entity_id: {next_door}
                        data:
                          option: "Open"
                  # At level - hold
                  - conditions:
                      - condition: template
                        value_template: "{{{{ water_level >= level_min and water_level <= level_max }}}}"
                    sequence:
                      - service: input_select.select_option
                        target:
                          entity_id: input_select.{bay_id}_door_control
                        data:
                          option: "Close"
"""

    if is_last:
        yaml_content += f"""                      - service: input_select.select_option
                        target:
                          entity_id: {next_door}
                        data:
                          option: "Close"
"""

    yaml_content += f"""
          #------------------------------------------------------------------
          # DRAIN MODE - Empty the bay
          #------------------------------------------------------------------
          - conditions:
              - condition: template
                value_template: "{{{{ mode == 'Drain' }}}}"
            sequence:
              - service: input_boolean.turn_off
                target:
                  entity_id: input_boolean.{bay_id}_flushactive
              - service: input_select.select_option
                target:
                  entity_id: input_select.{bay_id}_door_control
                data:
                  option: "Close"
              - service: input_select.select_option
                target:
                  entity_id: {next_door}
                data:
                  option: "Open"

  #----------------------------------------------------------------------------
  # Automation Setup - Initialize bay when mode changes
  #----------------------------------------------------------------------------
  - id: "pwm_{bay_id}_setup"
    alias: "{display_name} Setup"
    description: "Setup bay when automation mode changes from Off"
    mode: restart
    trigger:
      - platform: state
        entity_id: input_select.{bay_id}_automation_state
        from: "Off"
        for: "00:01:00"
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: input_select.{bay_id}_automation_state
                state: "Flush"
            sequence:
              - service: input_boolean.turn_on
                target:
                  entity_id: input_boolean.{bay_id}_flushactive
              - service: input_select.select_option
                target:
                  entity_id: {next_door}
                data:
                  option: "Close"
          - conditions:
              - condition: state
                entity_id: input_select.{bay_id}_automation_state
                state: "Pond"
            sequence:
              - service: input_select.select_option
                target:
                  entity_id: input_select.{bay_id}_door_control
                data:
                  option: "Open"
"""

    if is_last:
        yaml_content += f"""              - service: input_select.select_option
                target:
                  entity_id: {next_door}
                data:
                  option: "Close"
"""

    yaml_content += f"""
  #----------------------------------------------------------------------------
  # Flush Timer Start - Start countdown when water reaches min level
  #----------------------------------------------------------------------------
  - id: "pwm_{bay_id}_flush_timer_start"
    alias: "{display_name} Flush Timer Start"
    mode: restart
    trigger:
      - platform: numeric_state
        entity_id: sensor.pwm_{bay_id}_water_depth
        above: input_number.{bay_id}_waterlevelmin
        for: "00:05:00"
    condition:
      - condition: state
        entity_id: input_boolean.{bay_id}_flushactive
        state: "on"
    action:
      - service: timer.start
        target:
          entity_id: timer.{bay_id}_flushtimeonwater

  #----------------------------------------------------------------------------
  # Flush Timer End - Turn off flush when timer completes
  #----------------------------------------------------------------------------
  - id: "pwm_{bay_id}_flush_timer_end"
    alias: "{display_name} Flush Timer End"
    mode: restart
    trigger:
      - platform: state
        entity_id: timer.{bay_id}_flushtimeonwater
        from: "active"
        to: "idle"
    condition:
      - condition: state
        entity_id: input_select.{bay_id}_automation_state
        state: "Flush"
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.{bay_id}_flushactive

  #----------------------------------------------------------------------------
  # Flush Deactivate - Turn off flush active when leaving Flush mode
  #----------------------------------------------------------------------------
  - id: "pwm_{bay_id}_flush_deactivate"
    alias: "{display_name} Flush Deactivate"
    mode: restart
    trigger:
      - platform: state
        entity_id: input_select.{bay_id}_automation_state
        from: "Flush"
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.{bay_id}_flushactive
      - service: timer.cancel
        target:
          entity_id: timer.{bay_id}_flushtimeonwater
"""

    return yaml_content


def generate_all(paddock_filter: str | None = None):
    """Generate all YAML files."""
    config = load_merged_config()
    ensure_output_dir()

    paddocks = config.get("paddocks", {})
    if not paddocks:
        print("[WARN] No paddocks found in config")
        return

    generated_files = []

    for paddock_id, paddock in paddocks.items():
        # Skip if filter specified and doesn't match
        if paddock_filter and paddock_id != paddock_filter:
            continue

        # Skip disabled paddocks
        if not paddock.get("enabled", True):
            print(f"[SKIP] Paddock '{paddock_id}' is disabled")
            continue

        # Skip paddocks not in current season
        if not paddock.get("current_season", True):
            print(f"[SKIP] Paddock '{paddock_id}' not in current season")
            continue

        bays = get_bay_list(config, paddock_id)
        if not bays:
            print(f"[WARN] No bays found for paddock '{paddock_id}'")
            continue

        # Generate paddock YAML
        paddock_file = OUTPUT_DIR / f"pwm_paddock_{paddock_id}.yaml"
        paddock_yaml = generate_paddock_yaml(paddock_id, paddock, bays)
        paddock_file.write_text(paddock_yaml, encoding="utf-8")
        generated_files.append(paddock_file)
        print(f"[OK] Generated: {paddock_file.name}")

        # Generate bay YAMLs
        for i, bay in enumerate(bays):
            prev_bay = bays[i - 1] if i > 0 else None
            next_bay = bays[i + 1] if i < len(bays) - 1 else None
            is_last = bay.get("is_last_bay", i == len(bays) - 1)

            bay_order = bay.get("order", i + 1)
            bay_slug = f"b_{str(bay_order).zfill(2)}"
            bay_file = OUTPUT_DIR / f"pwm_bay_{paddock_id}_{bay_slug}.yaml"

            bay_yaml = generate_bay_yaml(paddock_id, paddock, bay, prev_bay, next_bay, is_last)
            bay_file.write_text(bay_yaml, encoding="utf-8")
            generated_files.append(bay_file)
            print(f"[OK] Generated: {bay_file.name}")

    # Create symlinks in packages directory
    print("\n[INFO] Creating package symlinks...")
    symlink_count = 0

    for gen_file in generated_files:
        # Create symlink name (prefix with pwm_gen_ to identify generated)
        symlink_name = f"pwm_gen_{gen_file.stem.replace('pwm_', '')}.yaml"
        symlink_path = PACKAGES_DIR / symlink_name

        # Calculate relative path from packages dir to generated file
        rel_path = os.path.relpath(gen_file, PACKAGES_DIR)

        # Remove existing symlink if it exists
        if symlink_path.is_symlink() or symlink_path.exists():
            symlink_path.unlink()

        # Create new symlink
        symlink_path.symlink_to(rel_path)
        symlink_count += 1
        print(f"[LINK] {symlink_name} -> {rel_path}")

    # Clean up orphan symlinks (generated files that no longer exist)
    for symlink in PACKAGES_DIR.glob("pwm_gen_*.yaml"):
        if symlink.is_symlink() and not symlink.resolve().exists():
            print(f"[DEL] Removing orphan symlink: {symlink.name}")
            symlink.unlink()

    # Generate master include file (for reference)
    include_content = f"""# PWM Generated Entities Master Include
# Generated: {datetime.now().isoformat(timespec='seconds')}
# Version: {VERSION}
#
# These files are automatically loaded via symlinks in PaddiSense/packages/
# Symlinks are prefixed with pwm_gen_*
#
# Generated files:
"""

    # Sort files for consistent output
    yaml_files = sorted([f for f in OUTPUT_DIR.glob("pwm_*.yaml")])

    for f in yaml_files:
        include_content += f"#   - {f.name}\n"

    master_file = OUTPUT_DIR / "_master.yaml"
    master_file.write_text(include_content, encoding="utf-8")

    print(f"\n[DONE] Generated {len(generated_files)} files, created {symlink_count} symlinks")
    print(f"[INFO] Reload Home Assistant or call the reload services")


def clean_generated():
    """Remove all generated files and symlinks."""
    count = 0

    # Remove symlinks from packages directory
    for symlink in PACKAGES_DIR.glob("pwm_gen_*.yaml"):
        if symlink.is_symlink():
            symlink.unlink()
            count += 1
            print(f"[DEL] Symlink: {symlink.name}")

    # Remove generated YAML files
    if OUTPUT_DIR.exists():
        for f in OUTPUT_DIR.glob("pwm_*.yaml"):
            f.unlink()
            count += 1
            print(f"[DEL] File: {f.name}")

        # Remove master file
        master = OUTPUT_DIR / "_master.yaml"
        if master.exists():
            master.unlink()
            count += 1
            print(f"[DEL] File: _master.yaml")

    if count == 0:
        print("[INFO] No generated files to clean")
    else:
        print(f"\n[DONE] Removed {count} files and symlinks")


def list_paddocks():
    """List paddocks that would be generated."""
    config = load_merged_config()
    paddocks = config.get("paddocks", {})

    print(f"\nPaddocks in config ({len(paddocks)}):")
    print("-" * 60)

    for paddock_id, paddock in paddocks.items():
        name = paddock.get("name", paddock_id)
        enabled = paddock.get("enabled", True)
        current_season = paddock.get("current_season", True)
        bay_count = paddock.get("bay_count", 0)
        individual = paddock.get("automation_state_individual", False)

        status_parts = []
        if not enabled:
            status_parts.append("DISABLED")
        if not current_season:
            status_parts.append("NOT-IN-SEASON")
        if not status_parts:
            status_parts.append("active")
        status = ", ".join(status_parts)
        mode = "individual" if individual else "paddock"

        print(f"  {paddock_id}: {name} ({bay_count} bays, {mode} mode) [{status}]")

    # Count bays
    bays = config.get("bays", {})
    print(f"\nTotal bays: {len(bays)}")
    print(f"Output directory: {OUTPUT_DIR}")


# =============================================================================
# DASHBOARD GENERATION
# =============================================================================

DASHBOARD_FILE = Path("/config/PaddiSense/pwm/dashboards/views.yaml")
DEFAULT_IMAGE = "/local/paddock_images/default.jpg"


def generate_paddock_view(paddock_id: str, paddock: dict, bays: list[dict]) -> dict:
    """Generate a single paddock view as a Python dict."""
    name = paddock.get("name", paddock_id)
    image_url = paddock.get("image_url") or DEFAULT_IMAGE

    # Build picture elements for bay sensors
    elements = []
    for bay in bays:
        bay_slug = f"b_{str(bay.get('order', 1)).zfill(2)}"
        badge_pos = bay.get("badge_position", {"top": 50, "left": 40})

        elements.append({
            "type": "state-badge",
            "tap_action": {"action": "more-info"},
            "entity": f"sensor.pwm_{paddock_id}_{bay_slug}_water_depth",
            "style": {
                "top": f"{badge_pos.get('top', 50)}%",
                "left": f"{badge_pos.get('left', 40)}%",
                "--ha-label-badge-title-font-size": "0em",
                "--paper-font-subhead_-_font-size": "8px",
                "transform": "scale(0.8)",
            }
        })

    # Build bay control cards
    bay_controls = []
    for bay in bays:
        bay_order = bay.get("order", 1)
        bay_slug = f"b_{str(bay_order).zfill(2)}"
        bay_name = bay.get("name", f"B-{bay_order:02d}")

        bay_controls.append({
            "type": "horizontal-stack",
            "cards": [
                {
                    "type": "custom:button-card",
                    "entity": f"input_select.{paddock_id}_{bay_slug}_door_control",
                    "name": bay_name,
                    "template": "template_buttoncard_openclose_simple",
                },
                {
                    "type": "custom:button-card",
                    "entity": f"input_select.{paddock_id}_{bay_slug}_automation_state",
                    "name": f"{bay_name} Auto",
                    "template": "template_channel_autostate",
                },
            ]
        })

    # Build the view
    view = {
        "title": name,
        "path": paddock_id.replace("_", "-"),
        "type": "masonry",
        "cards": [
            # Picture elements with field map
            {
                "type": "picture-elements",
                "image": image_url,
                "elements": elements,
            },
            # Paddock automation state
            {
                "type": "custom:button-card",
                "template": "template_titleblock",
                "variables": {"var_name": f"{name.upper()} CONTROLS"},
            },
            {
                "type": "custom:button-card",
                "entity": f"input_select.{paddock_id}_automation_state",
                "name": f"{name} Automation",
                "template": "template_channel_autostate",
            },
            # Bay controls title
            {
                "type": "custom:button-card",
                "template": "template_titleblock",
                "variables": {"var_name": "BAY CONTROLS"},
            },
            # Bay control cards
            *bay_controls,
            # Drain control
            {
                "type": "custom:button-card",
                "entity": f"input_select.{paddock_id}_drain_door_control",
                "name": "Drain",
                "template": "template_buttoncard_openclose_simple",
            },
            # Footer buttons
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "custom:button-card",
                        "template": "template_paddockconfigbutton",
                        "variables": {
                            "paddock_id": paddock_id,
                            "paddock_name": name,
                        },
                    },
                    {
                        "type": "button",
                        "name": "Refresh",
                        "icon": "mdi:refresh",
                        "tap_action": {
                            "action": "call-service",
                            "service": "script.pwm_refresh_data",
                        },
                        "icon_height": "40px",
                    },
                ],
            },
        ],
    }

    return view


def generate_dashboard():
    """Generate dashboard views for all enabled paddocks."""
    import yaml

    config = load_merged_config()
    paddocks = config.get("paddocks", {})

    if not DASHBOARD_FILE.exists():
        print(f"[ERROR] Dashboard file not found: {DASHBOARD_FILE}", file=sys.stderr)
        return

    # Read existing dashboard
    try:
        content = DASHBOARD_FILE.read_text(encoding="utf-8")
        dashboard = yaml.safe_load(content)
    except (yaml.YAMLError, IOError) as e:
        print(f"[ERROR] Failed to parse dashboard: {e}", file=sys.stderr)
        return

    if not dashboard or "views" not in dashboard:
        print("[ERROR] Invalid dashboard structure - missing 'views'", file=sys.stderr)
        return

    existing_views = dashboard.get("views", [])

    # Find Overview and Settings views to preserve
    overview_view = None
    settings_view = None
    other_static_views = []

    for view in existing_views:
        path = view.get("path", "")
        title = view.get("title", "").lower()

        if path == "overview" or title == "overview":
            overview_view = view
        elif path == "settings" or title == "settings":
            settings_view = view
        # Skip per-paddock views - they will be regenerated

    if not overview_view:
        print("[WARN] No Overview view found - creating basic one")
        overview_view = {
            "title": "Overview",
            "path": "overview",
            "icon": "mdi:view-dashboard",
            "type": "masonry",
            "cards": [],
        }

    if not settings_view:
        print("[WARN] No Settings view found - creating basic one")
        settings_view = {
            "title": "Settings",
            "path": "settings",
            "type": "masonry",
            "cards": [],
        }

    # Generate paddock views
    paddock_views = []
    for paddock_id, paddock in sorted(paddocks.items()):
        if not paddock.get("enabled", True):
            print(f"[SKIP] Paddock '{paddock_id}' is disabled")
            continue

        # Skip paddocks not in current season
        if not paddock.get("current_season", True):
            print(f"[SKIP] Paddock '{paddock_id}' not in current season")
            continue

        bays = get_bay_list(config, paddock_id)
        if not bays:
            print(f"[WARN] No bays found for paddock '{paddock_id}'")
            continue

        view = generate_paddock_view(paddock_id, paddock, bays)
        paddock_views.append(view)
        print(f"[OK] Generated view: {paddock_id}")

    # Rebuild views: Overview + Paddocks + Settings
    new_views = [overview_view] + paddock_views + [settings_view]

    # Preserve button_card_templates if present
    new_dashboard = {}
    if "title" in dashboard:
        new_dashboard["title"] = dashboard["title"]
    if "button_card_templates" in dashboard:
        new_dashboard["button_card_templates"] = dashboard["button_card_templates"]

    new_dashboard["views"] = new_views

    # Write updated dashboard
    # Use custom yaml dumper to preserve formatting
    class CustomDumper(yaml.SafeDumper):
        pass

    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    CustomDumper.add_representer(str, str_representer)

    # Backup existing file
    backup_file = DASHBOARD_FILE.with_suffix(".yaml.bak")
    if DASHBOARD_FILE.exists():
        backup_file.write_text(DASHBOARD_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[BACKUP] Saved to: {backup_file.name}")

    # Write new dashboard
    output = yaml.dump(new_dashboard, Dumper=CustomDumper, default_flow_style=False,
                       allow_unicode=True, sort_keys=False, width=120)

    # Add header comment
    header = f"""##############################################################################
# PWM Dashboard - Precision Water Management
# PaddiSense Farm Management System
# Generated: {datetime.now().isoformat(timespec='seconds')}
# Version: {VERSION}
#
# PADDOCK VIEWS ARE AUTO-GENERATED
# Manual edits to paddock views will be overwritten.
# Edit Overview and Settings views safely.
##############################################################################

"""
    DASHBOARD_FILE.write_text(header + output, encoding="utf-8")

    print(f"\n[DONE] Generated {len(paddock_views)} paddock views")
    print(f"[INFO] Dashboard saved to: {DASHBOARD_FILE}")


def main():
    parser = argparse.ArgumentParser(description="PWM YAML Generator")
    parser.add_argument("command", choices=["generate", "clean", "list", "dashboard"],
                       help="Command to run")
    parser.add_argument("--paddock", "-p", help="Generate only for specific paddock")

    args = parser.parse_args()

    if args.command == "generate":
        generate_all(args.paddock)
    elif args.command == "clean":
        clean_generated()
    elif args.command == "list":
        list_paddocks()
    elif args.command == "dashboard":
        generate_dashboard()


if __name__ == "__main__":
    main()
