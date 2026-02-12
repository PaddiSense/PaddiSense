<p align="center">
  <img src="icon.png" alt="PaddiSense Logo" width="200">
</p>

<h1 align="center">PaddiSense Farm Management</h1>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"></a>
  <a href="https://github.com/PaddiSense/PaddiSense/releases"><img src="https://img.shields.io/badge/version-1.0.0--rc.8-blue.svg" alt="Version"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg" alt="Home Assistant"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">
  A modular farm management platform for Home Assistant.<br>
  Built for Australian rice and mixed farming operations.
</p>

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| **Farm Registry** | Central configuration - paddocks, bays, seasons | Core |
| **Weather** | Local gateway and API weather data | RC |
| **Inventory Manager** | Track chemicals, fertilizers, consumables | RC |
| **Asset Service Manager** | Equipment, parts, and service history | RC |
| **Water Management** | Irrigation scheduling and bay monitoring | RC |
| **Real Time Rice** | Crop growth predictions | RC |
| **Stock Tracker** | Livestock inventory and movements | RC |
| **Hey Farmer** | Voice-activated farm event recording | RC |
| **Worker Safety** | Worker check-in/check-out system | Dev |

## Key Features

- **Offline-First** - All data stored locally, works without internet
- **Mobile-Friendly** - Touch-optimized dashboards for field use
- **Modular Design** - Enable only the modules you need
- **Local Data** - Your farm data never leaves your server

## Installation

1. Add this repository to HACS as a custom repository
2. Search for "PaddiSense" and download
3. Restart Home Assistant
4. Go to **Settings** > **Devices & Services** > **Add Integration**
5. Search for "PaddiSense" and follow the setup wizard

## Requirements

- Home Assistant 2024.1.0 or newer
- HACS installed
- Git (included in Home Assistant OS)

## Documentation

- [Installation Guide](https://github.com/PaddiSense/PaddiSense/blob/main/docs/GROWER_INSTALLATION.md)
- [GitHub Issues](https://github.com/PaddiSense/PaddiSense/issues)

## License

MIT License - Free for all users.
