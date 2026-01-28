# IPM — Inventory Product Manager

## Scope
- Consumables tracked by location.
- Stock tracked in units (kg/L/ea etc), not containers.
- Offline-first; local JSON backing store.

## Data
- Primary data: `local_data/ipm/`
  - `inventory.json`
  - `config.json`
  - `backups/`

## User Flows
- Add/edit product
- Adjust/consume stock
- Move stock between locations
- Reporting (by location, by season)
- Settings CRUD: categories/subcategories/locations/actives/groups/storage unit, application unit, container size
- Backup/restore/reset
- User able to modify lists
- customs list stored in local data and not tracked

## Multi-user Considerations
- Allow concurrent stock moves if safe.
- Protect/lock master list edits.

## Versioning
- Module VERSION
- Schema versioning (config/inventory)
- Version sensor exposed

## Entities & Services

### Sensors

| Entity ID | Type | Description |
|-----------|------|-------------|
| `sensor.ipm_products` | command_line | Main data sensor with all product/config data |
| `sensor.ipm_report_data` | command_line | Report data sensor (populated when reports generated) |
| `sensor.ipm_filtered_products` | template | Filtered products based on current filter selections |
| `sensor.ipm_selected_product` | template | Currently selected product ID |
| `sensor.ipm_version` | template | IPM module version |
| `binary_sensor.ipm_low_stock_alert` | template | Alert when products below min stock |

### Main Sensor Attributes (`sensor.ipm_products`)

| Attribute | Description |
|-----------|-------------|
| `products` | Dictionary of all products keyed by ID |
| `product_names` | List of product names for dropdowns |
| `product_locations` | Map of product ID to locations list |
| `categories` | List of category names |
| `category_subcategories` | Map of category to subcategory list |
| `chemical_groups` | List of chemical group codes |
| `units` | Dictionary with `product`, `container`, `application`, `concentration` unit lists |
| `locations` | List of storage locations |
| `active_names` | List of active constituent names |
| `low_stock_count` | Count of products below minimum |
| `low_stock_products` | List of low stock product details |
| `version` | Current IPM version |

### Input Helpers

**Filters (Movement/Overview views):**
- `input_select.ipm_category` — Category filter
- `input_select.ipm_subcategory` — Subcategory filter
- `input_select.ipm_product` — Product selector
- `input_select.ipm_location` — Location selector
- `input_select.ipm_active_filter` — Active constituent filter
- `input_text.ipm_search` — Text search

**Editor (Product Editor view):**
- `input_select.ipm_editor_mode` — "Add New Product" or "Edit Existing Product"
- `input_text.ipm_edit_name` — Product name
- `input_select.ipm_edit_category` — Category
- `input_select.ipm_edit_subcategory` — Subcategory
- `input_select.ipm_edit_location` — Default location
- `input_select.ipm_edit_unit` — Product unit (L, kg, ea)
- `input_select.ipm_edit_container` — Container size
- `input_select.ipm_edit_app_unit` — Application unit
- `input_number.ipm_edit_initial_stock` — Initial stock (add mode)
- `input_number.ipm_edit_min_stock` — Minimum stock threshold
- `input_select.ipm_active_X_name` — Active constituent name (1-6)
- `input_number.ipm_active_X_conc` — Active concentration (1-6)
- `input_select.ipm_active_X_unit` — Concentration unit (1-6)
- `input_select.ipm_active_X_group` — Chemical group (1-6)

**Reports:**
- `input_select.ipm_report_season` — Season/period selector
- `input_datetime.ipm_report_start` — Report start date
- `input_datetime.ipm_report_end` — Report end date
- `input_select.ipm_report_action` — Action filter (All, stock_in, stock_out)

**Settings:**
- `input_text.ipm_new_location` — New location name
- `input_select.ipm_manage_location` — Location to remove
- `input_text.ipm_new_active` — New active name
- `input_text.ipm_new_active_groups` — Groups for new active
- `input_select.ipm_manage_active` — Active to remove
- `input_text.ipm_new_category` — New category name
- `input_select.ipm_manage_category` — Category to remove
- `input_text.ipm_new_subcategory` — New subcategory name
- `input_select.ipm_manage_subcategory_parent` — Parent category for subcategory
- `input_text.ipm_new_chemical_group` — New chemical group
- `input_select.ipm_manage_chemical_group` — Group to remove
- `input_boolean.ipm_confirm_reset` — Confirm system reset

### Scripts

| Script | Description |
|--------|-------------|
| `script.ipm_save_movement` | Save stock movement (+/- adjustment) |
| `script.ipm_add_product` | Add new product to inventory |
| `script.ipm_save_product` | Save edits to existing product |
| `script.ipm_delete_selected_product` | Delete the currently loaded product |
| `script.ipm_load_product` | Load product data into editor form |
| `script.ipm_clear_form` | Reset editor form to defaults |
| `script.ipm_clear_active_X` | Clear active constituent X (1-6) |
| `script.ipm_generate_report` | Generate usage report to file |
| `script.ipm_add_new_location` | Add storage location |
| `script.ipm_remove_selected_location` | Remove storage location |
| `script.ipm_add_new_active` | Add active constituent |
| `script.ipm_remove_selected_active` | Remove active constituent |
| `script.ipm_add_new_category` | Add category |
| `script.ipm_remove_selected_category` | Remove category |
| `script.ipm_add_new_subcategory` | Add subcategory |
| `script.ipm_remove_selected_subcategory` | Remove subcategory |
| `script.ipm_add_new_chemical_group` | Add chemical group |
| `script.ipm_remove_selected_chemical_group` | Remove chemical group |
| `script.ipm_create_backup` | Create data backup |
| `script.ipm_restore_backup` | Restore from backup |
| `script.ipm_reset_system` | Reset all IPM data (danger) |
| `script.ipm_initialize_system` | Initialize/repair IPM system |

## Backend / Tooling

### CLI Entry Point

All backend operations go through `ipm_backend.py`:

```bash
python3 /config/PaddiSense/ipm/python/ipm_backend.py <command> [options]
```

### Product Commands

```bash
# Add product
python3 ipm_backend.py add_product \
  --name "Roundup PowerMax" \
  --category "Chemical" \
  --subcategory "Herbicide" \
  --location "Chem Shed" \
  --unit "L" \
  --container-size "20" \
  --min-stock "40" \
  --app-unit "L/ha" \
  --initial-stock "100" \
  --actives '[{"name":"Glyphosate","concentration":540,"unit":"g/L","group":"9"}]'

# Edit product
python3 ipm_backend.py edit_product \
  --id "ROUNDUP_POWERMAX" \
  --name "Roundup PowerMax II" \
  --min-stock "60"

# Delete product
python3 ipm_backend.py delete_product --id "ROUNDUP_POWERMAX"

# Move stock
python3 ipm_backend.py move_stock \
  --id "ROUNDUP_POWERMAX" \
  --location "Chem Shed" \
  --delta "-20" \
  --action "stock_out"
```

### Config Commands

```bash
# Add/remove locations
python3 ipm_backend.py add_location --name "New Shed"
python3 ipm_backend.py remove_location --name "Old Shed"

# Add/remove categories
python3 ipm_backend.py add_category --name "Equipment"
python3 ipm_backend.py remove_category --name "Equipment"

# Add/remove subcategories
python3 ipm_backend.py add_subcategory --category "Chemical" --name "Insecticide"
python3 ipm_backend.py remove_subcategory --category "Chemical" --name "Insecticide"

# Add/remove chemical groups
python3 ipm_backend.py add_chemical_group --code "23"
python3 ipm_backend.py remove_chemical_group --code "23"

# Add/remove active constituents
python3 ipm_backend.py add_active --name "Imidacloprid" --groups "4A"
python3 ipm_backend.py remove_active --name "Imidacloprid"

# Add/remove units
python3 ipm_backend.py add_unit --type "product" --value "mL"
python3 ipm_backend.py remove_unit --type "product" --value "mL"
```

### Report Commands

```bash
# Generate usage report (JSON to stdout)
python3 ipm_backend.py usage_report \
  --start "2026-01-01" \
  --end "2026-01-31"

# Get transaction history
python3 ipm_backend.py transaction_history \
  --start "2026-01-01" \
  --end "2026-01-31" \
  --product "ROUNDUP_POWERMAX" \
  --action "stock_out" \
  --limit 50

# Generate report data to file (for dashboard)
python3 ipm_backend.py generate_report_file \
  --output "/config/local_data/ipm/report_data.json" \
  --start "2026-01-01" \
  --end "2026-01-31" \
  --action "stock_out"
```

### System Commands

```bash
# Initialize system (creates default config/database)
python3 ipm_backend.py init

# Check system status
python3 ipm_backend.py status

# Migrate config (upgrade schema)
python3 ipm_backend.py migrate_config

# Export data
python3 ipm_backend.py export --output "/path/to/export.json"

# Import data
python3 ipm_backend.py import --input "/path/to/export.json"

# Reset system (danger - deletes all data)
python3 ipm_backend.py reset --confirm
```

### Lock Commands (for concurrent editing)

```bash
# Acquire lock
python3 ipm_backend.py lock_acquire \
  --type "product" \
  --id "ROUNDUP_POWERMAX" \
  --session "user123"

# Release lock
python3 ipm_backend.py lock_release \
  --type "product" \
  --id "ROUNDUP_POWERMAX" \
  --session "user123"

# Check lock status
python3 ipm_backend.py lock_check \
  --type "product" \
  --id "ROUNDUP_POWERMAX"

# Cleanup expired locks
python3 ipm_backend.py lock_cleanup

# List all locks
python3 ipm_backend.py lock_list
```

### Sensor Script

The sensor script provides data to Home Assistant:

```bash
python3 /config/PaddiSense/ipm/python/ipm_sensor.py
```

Returns JSON with all product data, config, and computed attributes for the `sensor.ipm_products` entity.
