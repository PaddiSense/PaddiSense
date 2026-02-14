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

### UI Locations
- **PSM → Crops view**: Add/edit/delete crop types and stages
- **PSM → Paddocks → Edit**: Crop rotation assignment (Crop 1/Crop 2 with months)
- **HFM**: Paddocks show current crop badge (future enhancement)

### Next Steps (Not Yet Implemented)
- HFM paddock selection: Show crop badge on each paddock button
- HFM crop stage dropdown: Filter stages by paddock's current crop
- Bulk paddock crop assignment ("Quick assign" for common patterns)
