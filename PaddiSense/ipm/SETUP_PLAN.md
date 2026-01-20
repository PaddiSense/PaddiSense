# IPM Configuration Dashboard - Implementation Plan

## Overview
Add a Settings/Configuration view to IPM that allows non-technical users to:
- Initialize the system on first use
- Manage storage locations
- Manage active constituents list
- Export/import data for backup

## Phase 1: System Status + Initialize + Locations Manager ✅ COMPLETE

### 1.1 Backend Commands (ipm_backend.py)

Add new commands:

```
status          - Return system health as JSON
init            - Create database structure if missing
add_location    - Add a new storage location to config
remove_location - Remove a location (only if no stock there)
list_locations  - Return current locations list
```

**New config file**: `/config/local_data/ipm/config.json`
```json
{
  "locations": ["Chem Shed", "Seed Shed", "Oil Shed", "Silo 1", ...],
  "custom_actives": [],
  "created": "2026-01-16T...",
  "modified": "2026-01-16T..."
}
```

### 1.2 Sensor Updates (ipm_sensor.py)

Add to output:
- `system_status`: "ready" | "not_initialized" | "error"
- `database_exists`: true/false
- `config_exists`: true/false
- `locations`: read from config.json instead of hardcoded
- `location_stock_map`: which locations have stock (for delete protection)

### 1.3 Package.yaml Additions

**New Helpers:**
- `input_text.ipm_new_location` - For adding new location
- `input_select.ipm_manage_location` - For selecting location to remove
- `input_boolean.ipm_confirm_delete_location` - Confirmation toggle

**New Scripts:**
- `script.ipm_initialize_system` - Call backend init command
- `script.ipm_add_location` - Add new location
- `script.ipm_remove_location` - Remove selected location

**New Shell Commands:**
- `shell_command.ipm_status`
- `shell_command.ipm_init`
- `shell_command.ipm_add_location`
- `shell_command.ipm_remove_location`

### 1.4 Dashboard View (inventory.yaml)

Add new view: **Settings** (icon: mdi:cog)

Cards:
1. **System Status Card**
   - Conditional: Show "Initialize" button if not ready
   - Show: Database status, product count, transaction count
   - Repair button (always available)

2. **Locations Manager Card**
   - Grid showing all current locations
   - Each location shows stock count (if any)
   - Add Location: text input + button
   - Remove Location: dropdown + button (disabled if stock exists)

---

## Phase 2: Active Constituents Manager ✅ COMPLETE

### 2.1 Backend Commands
```
add_active      - Add custom active constituent to list
remove_active   - Remove custom active (only if unused)
list_actives    - Return merged list (standard + custom)
```

### 2.2 Config Structure
```json
{
  "custom_actives": [
    {"name": "Custom Chemical", "common_groups": ["2", "4"]}
  ]
}
```

### 2.3 Sensor Output (new attributes)
- `custom_actives_count`: Number of custom actives
- `all_actives_list`: Merged list with type (standard/custom) and common_groups
- `active_products_map`: Maps active name → list of products using it

### 2.4 Dashboard
- Summary showing standard + custom active counts
- Table of custom actives with "Used By" count
- Add custom active form (name + optional groups)
- Remove unused custom actives (dropdown + button)

### 2.5 Implementation Order (Phase 2)
1. ✅ Add `STANDARD_ACTIVES` list to `ipm_backend.py`
2. ✅ Add commands: `list_actives`, `add_active`, `remove_active`
3. ✅ Update `ipm_sensor.py` with new attributes
4. ✅ Add shell commands to `package.yaml`
5. ✅ Add input helpers: `ipm_new_active`, `ipm_new_active_groups`, `ipm_manage_active`
6. ✅ Add scripts: `ipm_add_new_active`, `ipm_remove_selected_active`, `ipm_refresh_actives`
7. ✅ Add Active Constituents Manager section to Settings dashboard
8. ✅ Test full flow: add custom active → use in product → remove blocked

### 2.6 Testing Checklist (Phase 2) ✅ ALL PASSED
- [x] Settings view shows standard active count
- [x] Add custom active: Appears in manage dropdown
- [x] Custom active available in product editor active dropdowns
- [x] Remove custom active: Works for unused actives
- [x] Remove custom active: Blocked if used by a product
- [x] Cannot add duplicate active (standard or custom)

---

## Phase 3: Data Management (Export/Import/Reset) ✅ COMPLETE

### 3.1 Backend Commands
```
export          - Export inventory and config to timestamped backup file
import_backup   - Import from backup file (with validation, creates pre-import backup)
reset           - Clear all data (requires CONFIRM_RESET token, creates pre-reset backup)
backup_list     - List available backups with metadata
```

### 3.2 Backup Location
`/config/local_data/ipm/backups/inventory_YYYY-MM-DD_HHMMSS.json`

Backup file structure:
```json
{
  "version": "1.0",
  "created": "2026-01-16T14:30:22",
  "type": "ipm_backup",
  "note": "Optional note (e.g., Pre-import automatic backup)",
  "inventory": { "products": {...}, "transactions": [...] },
  "config": { "locations": [...], "custom_actives": [...] }
}
```

### 3.3 Sensor Attributes (new)
- `backup_count`: Number of available backups
- `last_backup`: Last backup info (filename, created, product_count)
- `backup_filenames`: List of backup filenames for dropdown

### 3.4 Package.yaml Additions
**Shell Commands:**
- `shell_command.ipm_export`
- `shell_command.ipm_import_backup` (with filename parameter)
- `shell_command.ipm_reset` (with token parameter)
- `shell_command.ipm_backup_list`

**Input Helpers:**
- `input_select.ipm_import_backup` - Backup file selection
- `input_boolean.ipm_confirm_reset` - Reset confirmation toggle

**Scripts:**
- `script.ipm_export_backup` - Create timestamped backup
- `script.ipm_refresh_backups` - Refresh backup dropdown
- `script.ipm_import_selected_backup` - Import selected backup
- `script.ipm_reset_system` - Reset all data (with confirmation)

### 3.5 Dashboard (Settings view)
- **Data Management** section showing:
  - Backup count and last backup info
  - "Create Backup" button (green)
  - Backup dropdown and "Restore Backup" button
- **Danger Zone** section with:
  - Warning message
  - Confirmation checkbox
  - "Reset System" button (red)

### 3.6 Safety Features
- Pre-import backup: Created automatically before importing
- Pre-reset backup: Created automatically before reset
- Two-step reset: Requires checkbox confirmation
- Token validation: Reset requires `CONFIRM_RESET` token

### 3.7 Implementation Order (Phase 3)
1. ✅ Add backup directory constant to backend and sensor
2. ✅ Add commands: export, import_backup, reset, backup_list
3. ✅ Update sensor with backup info attributes
4. ✅ Add shell commands to package.yaml
5. ✅ Add input helpers: ipm_import_backup, ipm_confirm_reset
6. ✅ Add scripts: ipm_export_backup, ipm_refresh_backups, ipm_import_selected_backup, ipm_reset_system
7. ✅ Add Data Management section to Settings dashboard
8. ✅ Test full flow: export → import → reset

### 3.8 Testing Checklist (Phase 3) ✅ ALL PASSED
- [x] Export creates backup file in correct location
- [x] Backup list shows available backups
- [x] Import dropdown populates with backup files
- [x] Import restores products and config
- [x] Pre-import backup is created automatically
- [x] Reset requires confirmation checkbox
- [x] Pre-reset backup is created automatically
- [x] Reset clears products and custom actives
- [x] Reset preserves default locations

---

## Phase 4: Future Enhancements

### 4.1 Category Customization
- Add custom subcategories to existing categories
- Possibly add entirely new categories (advanced)

### 4.2 Unit Management
- Customize available units (L, kg, t, etc.)
- Set default units per category

### 4.3 Multi-Farm Support
- Switch between farm profiles
- Separate inventories per farm

---

## File Changes Summary

| File | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| `ipm_backend.py` | status, init, add_location, remove_location | STANDARD_ACTIVES, list_actives, add_active, remove_active | export, import_backup, reset, backup_list |
| `ipm_sensor.py` | system_status, load config.json | custom_actives_count, all_actives_list, active_products_map | backup_count, last_backup, backup_filenames |
| `package.yaml` | helpers, scripts for locations | helpers, scripts for actives | helpers, scripts for backup/restore/reset |
| `inventory.yaml` | Settings view with status + locations | Active Constituents Manager section | Data Management + Danger Zone sections |

## New Files

| File | Purpose |
|------|---------|
| `/config/local_data/ipm/config.json` | User configuration (locations, custom actives) |
| `/config/local_data/ipm/backups/*.json` | Backup files (timestamped) |

---

## Implementation Order (Phase 1)

1. ✅ Create this plan document
2. ✅ Update `ipm_backend.py` with new commands (status, init, add_location, remove_location)
3. ✅ Config structure handled by backend (created on init)
4. ✅ Update `ipm_sensor.py` to read config and report status
5. ✅ Add helpers and scripts to `package.yaml`
6. ✅ Add Settings view to `inventory.yaml`
7. ✅ Test full flow: init → add location → remove location
8. ✅ Update CLAUDE.md with new architecture

---

## Testing Checklist (Phase 1) ✅ ALL PASSED

- [x] Fresh install: Settings shows "Not Initialized" status
- [x] Click Initialize: Creates config.json and inventory.json
- [x] Status updates to "Ready" after init
- [x] Add Location: New location appears in dropdown
- [x] New location available in Stock Movement view
- [x] Remove Location: Works for empty locations
- [x] Remove Location: Blocked for locations with stock
- [x] Sensor refresh picks up config changes
