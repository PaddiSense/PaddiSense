# PaddiSense Farm Management

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/paddisense/paddisense-ha)](https://github.com/paddisense/paddisense-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Home Assistant integration for farm management. Manage paddocks, bays, and seasons for precision agriculture.

## Features

- **Farm Registry** - Manage farms, paddocks, bays, and seasons
- **16 Services** - Full CRUD operations via Home Assistant services
- **Custom Lovelace Card** - Mobile-friendly dashboard card
- **Offline-First** - All data stored locally on your server
- **Migration Support** - Import existing PaddiSense data

---

## Installation via HACS

### Step 1: Add Custom Repository

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click **⋮** (three dots menu) → **Custom repositories**
4. Add:
   - **Repository**: `https://github.com/paddisense/paddisense-ha`
   - **Category**: Integration
5. Click **Add**

### Step 2: Download

1. In HACS Integrations, click **+ Explore & Download Repositories**
2. Search for "**PaddiSense**"
3. Click **Download**
4. **Restart Home Assistant**

### Step 3: Configure

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "**PaddiSense**"
4. Follow the setup wizard

### Step 4: Add Dashboard Card

1. Go to **Settings** → **Dashboards** → **Resources**
2. Add: `/paddisense/paddisense-registry-card.js` (JavaScript Module)
3. Refresh browser (Ctrl+F5)
4. Add card to your dashboard:

```yaml
type: custom:paddisense-registry-card
entity: sensor.paddisense_registry
```

---

## Manual Installation

1. Download the [latest release](https://github.com/paddisense/paddisense-ha/releases)
2. Extract and copy `custom_components/paddisense/` to your HA `config/custom_components/`
3. Restart Home Assistant
4. Follow Steps 3-4 above

---

## Entities

| Entity | Description |
|--------|-------------|
| `sensor.paddisense_registry` | Farm structure with paddocks, bays, seasons |
| `sensor.paddisense_version` | Integration version |

## Services

| Service | Description |
|---------|-------------|
| `paddisense.add_paddock` | Create paddock with bays |
| `paddisense.edit_paddock` | Update paddock settings |
| `paddisense.delete_paddock` | Remove paddock and its bays |
| `paddisense.add_bay` | Add bay to paddock |
| `paddisense.edit_bay` | Update bay settings |
| `paddisense.delete_bay` | Remove bay |
| `paddisense.add_season` | Create new season |
| `paddisense.edit_season` | Update season dates |
| `paddisense.delete_season` | Remove season |
| `paddisense.set_active_season` | Set the active season |
| `paddisense.set_current_season` | Toggle paddock in/out of season |
| `paddisense.add_farm` | Create new farm |
| `paddisense.edit_farm` | Update farm name |
| `paddisense.delete_farm` | Remove empty farm |
| `paddisense.export_registry` | Backup to file |
| `paddisense.import_registry` | Restore from backup |

---

## Card Configuration

```yaml
type: custom:paddisense-registry-card
entity: sensor.paddisense_registry
show_farm_overview: true    # Show paddock/bay counts
show_paddock_list: true     # Show list of paddocks
show_season_info: true      # Show active season
show_actions: true          # Show add buttons
```

---

## Example Service Calls

### Add a Paddock

```yaml
service: paddisense.add_paddock
data:
  name: "SW7"
  bay_count: 5
  bay_prefix: "B-"
```

### Add a Season

```yaml
service: paddisense.add_season
data:
  name: "CY26"
  start_date: "2025-04-01"
  end_date: "2026-03-31"
  active: true
```

---

## Data Storage

All data is stored locally in `/config/local_data/registry/`:
- `config.json` - Farm structure
- `backups/` - Automatic backups

Data is never sent to external servers.

---

## License

MIT License - see [LICENSE](LICENSE)
