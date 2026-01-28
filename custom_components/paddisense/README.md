# PaddiSense Farm Management

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/paddisense/paddisense-ha.svg)](https://github.com/paddisense/paddisense-ha/releases)

A Home Assistant integration for farm management. Manage paddocks, bays, and seasons for precision agriculture.

## Features

- **Farm Registry** - Manage farms, paddocks, bays, and seasons
- **16 Services** - Full CRUD operations via Home Assistant services
- **Custom Lovelace Card** - Mobile-friendly dashboard card
- **Offline-First** - All data stored locally
- **Migration Support** - Import existing PaddiSense data

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) → **Custom repositories**
3. Add repository URL: `https://github.com/paddisense/paddisense-ha`
4. Select category: **Integration**
5. Click **Add**
6. Search for "PaddiSense" in HACS
7. Click **Download**
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/paddisense` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "PaddiSense"
4. Follow the setup wizard

## Adding the Dashboard Card

1. Go to **Settings** → **Dashboards** → **Resources**
2. Add resource: `/paddisense/paddisense-registry-card.js` (JavaScript Module)
3. Refresh your browser
4. Add card to dashboard:

```yaml
type: custom:paddisense-registry-card
entity: sensor.paddisense_registry
```

## Services

| Service | Description |
|---------|-------------|
| `paddisense.add_paddock` | Create paddock with bays |
| `paddisense.edit_paddock` | Update paddock |
| `paddisense.delete_paddock` | Remove paddock and bays |
| `paddisense.add_bay` | Add bay to paddock |
| `paddisense.add_season` | Create season |
| `paddisense.set_active_season` | Set active season |
| `paddisense.export_registry` | Backup data |
| `paddisense.import_registry` | Restore data |

See full documentation for all 16 services.

## Entities

| Entity | Description |
|--------|-------------|
| `sensor.paddisense_registry` | Farm structure and counts |
| `sensor.paddisense_version` | Integration version |

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Quick Start](docs/QUICK_START.md)
- [Farm Registry Reference](docs/FARM_REGISTRY.md)

## License

MIT License - See LICENSE file
