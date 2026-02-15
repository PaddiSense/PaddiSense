# CLAUDE.md — PaddiSense Core Rules (Minimal)

PaddiSense is a modular farm-management platform for **Home Assistant OS (HAOS)** built as **packages + dashboards** with **local JSON data**.

## Non-negotiables
- **HAOS only**
- **Offline-first:** core workflows must run without internet.
- **Local-only by default:** secrets and operational data stay on the server unless explicitly exported.
- **Updates must not overwrite local state:** never touch `secrets.yaml`, `server.yaml`, `local_data/`, or `.storage` unless a deliberate migration exists.
- **Mobile-first UI:** large touch targets, high contrast, dark-mode compatible; avoid hardcoded colors where feasible.

## Repository boundaries
- Repo contains: packages (YAML), dashboards, scripts/tools, default schemas/templates.
- Per-server local files (protected): `server.yaml`, `secrets.yaml`, `local_data/**`, `.storage/**`.

## Module design standard
Each module is **self-contained**:
- One module folder (e.g. `ipm/`, `asm/`, `weather/`, `pwm/`)
- Prefer **single `package.yaml`** per module (avoid duplicate root YAML keys).
- Runtime data stored under `/config/local_data/<module>/` (not tracked in git).
- Each module has a `VERSION` file and exposes a **version sensor** in HA.

## Shared Core: Farm Registry
- Farm Registry is **standalone** and consumed by all modules.
- IDs are **generated only** (no manual ID entry); UI shows names, not IDs.
- Support export/import for backups and migration between servers.

## PWM / ESPHome control contract
- HA/PWM controls **valves/actuators only** (never raw relays).
- Devices may have 1–2 actuators; if 2, they are logically paired (same role).
- Watchdog/faults: raise alert + mark unavailable; **do not force stop**.

## Git hygiene
- No secrets in git.
- Preserve entity IDs unless MAJOR bump + migration notes.
- Keep `main` always releasable; use feature/fix branches and PRs.

## Where detailed docs live
This file stays minimal. Put implementation details in repo docs, e.g.:
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/IPM.md`, `docs/ASM.md`, `docs/WEATHER.md`, `docs/PWM.md`, `docs/WSS.md`
- `reference/` for schemas and command docs
- `reference/UI_STYLE_GUIDE.md` for dashboard styling standards

## UI/UX Development Standards (Learned Best Practices)

### Mobile-First Design
- **70px minimum button height** - "fat thumbs and bad eyes" for outdoor field use
- **Yellow title headers** (`#E9E100`) - visual segregation on mobile screens, black text
- **Hold-to-clear pattern** - tap to action, hold to clear (reduces button clutter)
- **Auto-expanding grids** - support unlimited items via CSS `display: none` conditional

### Button-Card Patterns
- **Never use onclick in custom_fields HTML** - use native `tap_action` with `call-service`
- **Always use try-catch in JavaScript templates** - prevents dashboard crashes
- **triggers_update** - ensures reactive updates when entity changes
- **Template inheritance** - define module templates (e.g., `hfm_title`, `hfm_action`)

### IMPORTANT: UI Styling Consistency
**When touching any dashboard UI:**
1. **Check existing templates** - use `template_titleblock`, `template_action`, `template_success`, `template_danger`, `template_secondary`
2. **Verify 70px button height** - all action buttons must be minimum 70px
3. **Title bars use yellow** (`#E9E100`) with black text
4. **Match HFM patterns** - refer to `/config/PaddiSense/hfm/dashboards/views.yaml` for standard templates
5. **Card styling** - use consistent border-radius (12px), shadows, padding

### Weather/Sensor Integration
- **Local station first, BOM fallback** - always check local sensors before external APIs
- **Capture all fields**: wind speed, gust, direction, delta T, humidity, rain chance
- **Markdown tables for data display** - compact, readable, mobile-friendly
- **BOM Auto-Setup** - automated configuration via PSM Settings (see Weather Module section below)

### Multi-Select Patterns
- **Draft system for multi-user** - device-based drafts allow concurrent recording
- **Paddock selection**: Farm selector → filtered paddock grid → All/Clear/Season buttons
- **Toggle pattern**: tap paddock button to add/remove from selection array

### Dashboard Structure
- **Conditional cards** - show/hide based on wizard step or event type
- **Horizontal-stack for button rows** - consistent spacing
- **Vertical-stack for card groups** - logical grouping

### Color Standards
| Purpose | Hex |
|---------|-----|
| Headers/Titles | `#E9E100` (yellow, black text) |
| Primary Action | `#0066cc` (blue) |
| Success/Confirm | `#28a745` (green) |
| Danger/Clear | `#dc3545` (red) |
| Warning/Season | `#e6a700` (yellow) |
| Secondary | `#555555` (gray) |

## Weather Module & BOM Integration (Updated 2026-02-15)

### Overview
The Weather module integrates Bureau of Meteorology (BOM) data and local Ecowitt stations for Australian farm weather.

### BOM Setup Status
- **HACS Integration:** `bureau_of_meteorology` installed in `/config/custom_components/`
- **Config Entry:** Auto-configured via `bom_setup.py` with "home" basename
- **Location:** Uses HA's configured lat/lon (auto-detected)

### BOM Auto-Setup
PaddiSense now supports automatic BOM integration configuration:

**Setup Flow:**
1. **Install BOM Integration** - PSM → Settings → "Install BOM Integration" button (installs via HACS)
2. **Configure BOM** - PSM → Settings → "Configure BOM Weather" button (auto-configures with "home" naming)
3. **Verify** - Weather dashboard shows BOM data

**Key Files:**
| File | Purpose |
|------|---------|
| `weather/python/bom_setup.py` | Auto-configuration script using HA config flow API |
| `weather/package.yaml` | Shell commands, scripts, binary sensors for BOM |
| `registry/dashboards/manager.yaml` | PSM Settings UI with setup buttons |

**Shell Commands:**
```bash
# Auto-configure BOM with standard "home" naming
shell_command.weather_bom_setup

# Check if BOM is already configured
shell_command.weather_bom_check
```

**Sensors:**
- `binary_sensor.bom_integration_configured` - True when BOM config entry exists
- `binary_sensor.bom_observations_available` - True when BOM observation entities exist
- `sensor.bom_detected_prefix` - Auto-detects BOM entity prefix (usually "home")

**BOM Entity Naming Convention (CRITICAL - Updated 2026-02-15):**
The BOM HACS integration uses **simple naming without "observations_" or "forecast_" prefixes**:

| Type | Entity Pattern | Examples |
|------|----------------|----------|
| Observations | `sensor.{prefix}_{metric}` | `sensor.home_temp`, `sensor.home_humidity`, `sensor.home_wind_speed_kilometre` |
| Forecasts | `sensor.{prefix}_{metric}_{day}` | `sensor.home_temp_min_0`, `sensor.home_rain_chance_0`, `sensor.home_fire_danger_0` |
| Warnings | `sensor.{prefix}_warnings` | `sensor.home_warnings` |

**Common Observation Sensors:**
- `sensor.home_temp` - Current temperature
- `sensor.home_temp_feels_like` - Feels like temperature
- `sensor.home_humidity` - Relative humidity
- `sensor.home_dew_point` - Dew point
- `sensor.home_wind_speed_kilometre` - Wind speed
- `sensor.home_gust_speed_kilometre` - Wind gust
- `sensor.home_wind_direction` - Wind direction
- `sensor.home_rain_since_9am` - Rain since 9am

**Common Forecast Sensors (day 0-6):**
- `sensor.home_temp_min_0` - Minimum temperature
- `sensor.home_temp_max_0` - Maximum temperature
- `sensor.home_rain_amount_min_0` / `_max_0` - Rain amount range
- `sensor.home_rain_chance_0` - Rain probability %
- `sensor.home_uv_max_index_0` - UV index
- `sensor.home_fire_danger_0` - Fire danger rating
- `sensor.home_icon_descriptor_0` - Weather icon (sunny, cloudy, etc.)

**Template Sensor Pattern:**
PaddiSense template sensors use dynamic prefix detection:
```yaml
{% set prefix = states('sensor.bom_detected_prefix') %}
{{ states('sensor.' ~ prefix ~ '_temp') }}
```

### Local Weather Stations
Support for Ecowitt gateways and API stations with automatic entity prefix detection.

### Troubleshooting: Template Sensor unique_id Stability
**IMPORTANT:** When editing template sensors in `weather/package.yaml`:
- **Never change `unique_id` values** - HA uses these to track entities
- If unique_id changes, HA creates a NEW entity (with `_2` suffix) instead of updating
- Orphaned entities must be manually removed from `/config/.storage/core.entity_registry`
- After entity registry edits, **restart HA** to apply changes

## Crop Management System (Implemented 2026-02-14)

### Overview
Comprehensive crop tracking integrated into Farm Registry and HFM:
- **Crop Types** with per-crop growth stages (Rice, Fallow, Wheat)
- **Paddock Crop Rotations** with 2-crop per paddock support
- **Current Crop Detection** based on today's month

### Data Model
- **Crops file:** `/config/local_data/registry/crops.json`
- **Paddock crops:** Stored as `crop_1` and `crop_2` fields on each paddock in `config.json`
- Each crop has: `start_month`, `end_month`, `stages[]`, `color`

### Key Files Modified
| File | Changes |
|------|---------|
| `registry/python/registry_backend.py` | Added crop CRUD commands, extended edit_paddock |
| `registry/python/registry_sensor.py` | Added crops, current_crops, crop_names to output |
| `registry/package.yaml` | Shell commands, input helpers, scripts for crops |
| `registry/dashboards/manager.yaml` | New "Crops" view (View 5), extended paddock edit |
| `hfm/python/hfm_sensor.py` | Added paddocks_with_crops attribute |
| `hfm/package.yaml` | Added paddocks_with_crops to json_attributes |

### Backend Commands
```bash
# Crop type management
registry_backend.py add_crop --name "Barley" --start_month 5 --end_month 11
registry_backend.py edit_crop --id barley --color "#8B4513"
registry_backend.py delete_crop --id barley
registry_backend.py list_crops
registry_backend.py add_crop_stage --crop_id rice --name "Heading"
registry_backend.py delete_crop_stage --crop_id rice --stage_id heading

# Paddock crop assignment (extends edit_paddock)
registry_backend.py edit_paddock --id sw5 \
  --crop_1_id fallow --crop_1_start 5 --crop_1_end 9 \
  --crop_2_id rice --crop_2_start 10 --crop_2_end 5
```

### Current Crop Logic
```python
def is_in_month_range(current_month, start_month, end_month):
    if start_month <= end_month:
        return start_month <= current_month <= end_month
    else:  # Wraps around year (e.g., Oct-May)
        return current_month >= start_month or current_month <= end_month
```

### Sensor Attributes
- `sensor.farm_registry_data`:
  - `crops` - All crop type definitions
  - `crop_names` - List for dropdowns
  - `current_crops` - Paddock ID → current crop info mapping

- `sensor.hfm_events`:
  - `paddocks_with_crops` - Paddock data with current_crop field

### Season-Locked Crop Rotation UI (Simplified 2026-02-15)
The paddock crop rotation form uses **season-locked months** for simplicity:
- **Crop 1 start**: Auto-derived from active season start (hidden from user)
- **Crop 1 end**: User selects (visible as "Ends In" dropdown)
- **Crop 2 start**: Auto-derived as Crop 1 end + 1 (hidden from user)
- **Crop 2 end**: Auto-derived from active season end (hidden from user)

**UI Labels**: "CROP 1 (From Season Start)" and "CROP 2 (To Season End)"

**Example for CY26 (May 2025 - April 2026):**
- User selects: Crop 1 = Rice, Ends In = October
- System auto-calculates: Rice (May→Oct), Fallow (Nov→Apr)

### UI Locations
- **PSM → Crops view**: Add/edit/delete crop types and stages
- **PSM → Paddocks → Edit**: Simplified crop rotation (crop selector + end month only)
- **HFM**: Paddocks show current crop badge (future enhancement)

### Next Steps (Not Yet Implemented)
- HFM paddock selection: Show crop badge on each paddock button
- HFM crop stage dropdown: Filter stages by paddock's current crop
- Bulk paddock crop assignment ("Quick assign" for common patterns)

## Business Entity System (Implemented 2026-02-14)

### Overview
Business is a parent entity to Farms, creating a hierarchy: **Business → Farm → Paddock**
- Businesses group farms under a single organization
- Farms can be filtered by business in the UI
- Farm cards display their assigned business

### Data Model
- **Businesses:** Stored in `businesses: {}` dict in `/config/local_data/registry/config.json`
- **Farm assignment:** `business_id` field on each farm record
- Each business has: `name`, `created`, `modified`

### Key Files Modified
| File | Changes |
|------|---------|
| `registry/python/registry_backend.py` | Added business CRUD commands, extended add_farm/edit_farm with --business |
| `registry/python/registry_sensor.py` | Added businesses, business_names to output |
| `registry/package.yaml` | Shell commands, input helpers, scripts, automations for businesses |
| `registry/dashboards/manager.yaml` | Business management section in Farms view, filter, farm card display |

### Backend Commands
```bash
# Business management
registry_backend.py add_business --name "Smith Farms Pty Ltd"
registry_backend.py edit_business --id smith_farms_pty_ltd --name "Smith Agricultural"
registry_backend.py delete_business --id smith_farms_pty_ltd  # blocked if farms assigned

# Farm with business assignment
registry_backend.py add_farm --name "North Block" --business smith_farms_pty_ltd
registry_backend.py edit_farm --id north_block --business smith_farms_pty_ltd
registry_backend.py edit_farm --id north_block --business ""  # clear assignment
```

### Sensor Attributes
- `sensor.farm_registry_data`:
  - `businesses` - All business definitions
  - `business_names` - Sorted list for dropdowns
  - `total_businesses` - Count

### Input Helpers
| Entity | Purpose |
|--------|---------|
| `input_select.registry_business_editor_mode` | Add/Edit mode toggle |
| `input_select.registry_business` | Select business for editing |
| `input_select.registry_farm_business_filter` | Filter farms by business |
| `input_select.registry_new_farm_business` | Assign farm to business (Add/Edit) |
| `input_text.registry_new_business_name` | New business name input |
| `input_text.registry_edit_business_name` | Edit business name input |
| `input_text.registry_edit_business_pointer` | Tracks selected business ID |

### UI Locations
- **PSM → Farms view**: Business Management section at top (Add/Edit toggle)
- **PSM → Farms view**: Business filter dropdown filters farm selector
- **PSM → Farms → Add/Edit**: Business assignment dropdown
- **Farm cards**: Show business name under farm name with mdi:domain icon

### Automations
- `registry_update_business_dropdowns` - Updates dropdowns when sensor changes
- `registry_load_business_on_select` - Loads form when business selected
- `registry_filter_farms_by_business` - Filters farm dropdown when business filter changes

## CSV Import/Export System (Implemented 2026-02-15)

### Overview
Growers can import farm structure from CSV (Excel-compatible) and export templates.

### CSV Template Columns
| Column | Required | Description |
|--------|----------|-------------|
| Business Name | Yes | Creates business if not exists |
| Farm Name | Yes | Creates farm under business |
| Paddock Name | Yes | Creates paddock under farm |
| Brown Area (ha) | No | Paddock brown area |
| Green Area (ha) | No | Paddock green area |
| Crop 1 | No | First crop name (must match existing crop type) |
| Crop 1 Start Month | No | 1-12 |
| Crop 1 End Month | No | 1-12 |
| Crop 2 | No | Second crop name |
| Crop 2 Start Month | No | 1-12 |
| Crop 2 End Month | No | 1-12 |

### Services
- `paddisense.export_registry_template` - Creates `/config/paddisense_import_template.csv`
- `paddisense.import_from_excel` - Imports from CSV file in /config

### UI Location
- **PSM → Farms view**: "Import from CSV" button (top)
- **PSM → Settings view**: Import section with template download button
