# PaddiSense Farm Management

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.0--rc.8-blue.svg)](https://github.com/PaddiSense/PaddiSense/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular Home Assistant integration for farm management. Built for Australian rice and mixed farming operations.

> **Pre-Release Notice**: Version 1.0.0-rc.8 is a release candidate. Core features are complete but still undergoing testing.

## Modules

| Module | Description | Status | Dependencies |
|--------|-------------|--------|--------------|
| **Farm Registry** | Central configuration - paddocks, bays, seasons | RC | Core |
| **Inventory Manager (IPM)** | Track chemicals, fertilizers, consumables | RC | None |
| **Asset Service Manager (ASM)** | Equipment, parts, and service history | RC | None |
| **Weather Stations** | Local gateway and API weather data | RC | None |
| **Water Management (PWM)** | Irrigation scheduling and bay monitoring | RC | None |
| **Real Time Rice (RTR)** | Crop growth predictions integration | RC | None |
| **Stock Tracker (STR)** | Livestock inventory and movements | RC | None |
| **Hey Farmer (HFM)** | Farm event recording wizard | RC | IPM |
| **Worker Safety (WSS)** | Worker check-in/check-out system | Dev | None |

## Key Features

- **Offline-First** - All data stored locally, works without internet
- **Mobile-Friendly** - Touch-optimized dashboards for field use
- **Modular Design** - Enable only the modules you need
- **Local Data** - Your farm data never leaves your server
- **YAML Packages** - Easy to customize and extend
- **Dependency Management** - Modules with dependencies are automatically blocked until requirements are met

---

## Prerequisites

### Required HACS Frontend Cards

Before installing PaddiSense, install these cards via HACS:

1. **Button Card** - `custom-cards/button-card`
2. **Card Mod** - `thomasloven/lovelace-card-mod`

Or after installing PaddiSense, call the service:
```yaml
service: paddisense.install_hacs_cards
```

---

## Installation via HACS

### Step 1: Add Custom Repository

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click **⋮** (three dots menu) → **Custom repositories**
4. Add:
   - **Repository**: `https://github.com/PaddiSense/PaddiSense`
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
4. Follow the setup wizard:
   - Enter your grower name and email (for registration)
   - Select modules to install
   - Configure initial settings

### Step 4: Access Dashboards

After restart, module dashboards appear in the sidebar automatically:
- **PaddiSense Manager** - Install/remove modules, check updates
- **Inventory Manager** - Manage products and stock
- **Stock Tracker** - Track livestock
- etc.

---

## Manual Installation

1. Download the [latest release](https://github.com/PaddiSense/PaddiSense/releases)
2. Copy `custom_components/paddisense/` to your HA `config/custom_components/`
3. Copy `PaddiSense/` folder to your HA `config/` directory
4. Restart Home Assistant
5. Follow Steps 3-4 above

---

## Module Management

### Installing Modules

1. Open **PaddiSense Manager** dashboard
2. Find module in **Available Modules** section
3. Click **Install** → Confirm
4. Home Assistant restarts automatically

### Removing Modules

1. Open **PaddiSense Manager** dashboard
2. Find module in **Installed Modules** section
3. Click **Remove** → Confirm
4. Home Assistant restarts automatically

**Note:** Your data is preserved when removing modules. Reinstalling will restore access to your data.

### Dependencies

Some modules require others:
- **Hey Farmer (HFM)** requires **Inventory Manager (IPM)**

If dependencies are missing, the Install button shows "Blocked" with a message showing required modules.

---

## Entities

| Entity | Description |
|--------|-------------|
| `sensor.paddisense_registry` | Farm structure with paddocks, bays, seasons |
| `sensor.paddisense_version` | Integration version and module status |
| `sensor.paddisense_rtr` | Real Time Rice data (if configured) |
| `sensor.ipm_products` | Inventory products (if IPM installed) |
| `sensor.str_mobs` | Livestock mobs (if STR installed) |

## Core Services

| Service | Description |
|---------|-------------|
| `paddisense.install_module` | Install a module |
| `paddisense.remove_module` | Remove a module (preserves data) |
| `paddisense.check_for_updates` | Check for PaddiSense updates |
| `paddisense.update_paddisense` | Update to latest version |
| `paddisense.create_backup` | Create configuration backup |
| `paddisense.install_hacs_cards` | Install required HACS frontend cards |

## Registry Services

| Service | Description |
|---------|-------------|
| `paddisense.add_paddock` | Create paddock with bays |
| `paddisense.edit_paddock` | Update paddock settings |
| `paddisense.delete_paddock` | Remove paddock and its bays |
| `paddisense.add_bay` | Add bay to paddock |
| `paddisense.edit_bay` | Update bay settings |
| `paddisense.delete_bay` | Remove bay |
| `paddisense.add_season` | Create new season |
| `paddisense.set_active_season` | Set the active season |
| `paddisense.add_farm` | Create new farm |
| `paddisense.export_registry` | Backup to file |
| `paddisense.import_registry` | Restore from backup |

---

## Data Storage

All data is stored locally:

```
/config/
├── local_data/
│   ├── registry/     # Farm structure
│   ├── ipm/          # Inventory data
│   ├── str/          # Stock tracker data
│   ├── hfm/          # Farm events
│   └── ...
└── PaddiSense/
    ├── packages/     # Module symlinks
    └── modules.json  # Module metadata
```

**Data is never sent to external servers** unless you explicitly enable data-sharing features.

---

## Troubleshooting

### Dashboards Not Appearing
1. Clear browser cache (Ctrl+F5)
2. Check **Developer Tools** → **YAML** → **Reload Dashboards**
3. Verify module is installed in PaddiSense Manager

### Module Won't Install
1. Check dependencies - install required modules first
2. Check Home Assistant logs for errors
3. Verify YAML syntax in package files

### Cards Not Rendering
1. Install required HACS cards (button-card, card-mod)
2. Call `paddisense.install_hacs_cards` service
3. Refresh browser after installing cards

---

## Support

- **Issues**: [GitHub Issues](https://github.com/PaddiSense/PaddiSense/issues)
- **Documentation**: [docs/](https://github.com/PaddiSense/PaddiSense/tree/main/docs)

---

## License

MIT License - see [LICENSE](LICENSE)
