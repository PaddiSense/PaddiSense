# PaddiSense Farm Management

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.0--rc.1-blue.svg)](https://github.com/paddisense/paddisense-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular Home Assistant integration for farm management. Built for Australian rice and mixed farming operations.

> **Pre-Release Notice**: Version 1.0.0-rc.1 is a release candidate. Core features are complete but still undergoing testing.

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| **Farm Registry** | Central configuration - paddocks, bays, seasons | RC |
| **Inventory Manager (IPM)** | Track chemicals, fertilizers, consumables | RC |
| **Asset Service Manager (ASM)** | Equipment, parts, and service history | RC |
| **Weather Stations** | Local gateway and API weather data | RC |
| **Water Management (PWM)** | Irrigation scheduling and bay monitoring | RC |
| **Real Time Rice (RTR)** | Crop growth predictions integration | RC |
| **Stock Tracker (STR)** | Livestock inventory and movements | RC |
| **Hey Farmer (HFM)** | Farm event recording wizard | RC |
| **Worker Safety (WSS)** | Worker check-in/check-out system | Dev |

## Key Features

- **Offline-First** - All data stored locally, works without internet
- **Mobile-Friendly** - Touch-optimized dashboards for field use
- **Modular Design** - Enable only the modules you need
- **Local Data** - Your farm data never leaves your server
- **YAML Packages** - Easy to customize and extend

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
