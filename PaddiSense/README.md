# PaddiSense Farm Management

A modular farm management platform for Home Assistant. Built for Australian rice and mixed farming operations.

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

## Requirements

- Home Assistant 2024.1.0 or newer
- HACS (see installation below)
- Git (included in Home Assistant OS)

---

## Installation

### Step 1: Install HACS (if not already installed)

HACS (Home Assistant Community Store) is required to install PaddiSense and its frontend cards.

1. Open Home Assistant in your browser
2. Go to **Settings → Devices & Services**
3. Click the blue **+ ADD INTEGRATION** button (bottom right)
4. Search for **HACS** and select it
5. Accept the terms and follow the GitHub authorization flow
6. Restart Home Assistant when prompted

**Alternative method (Terminal/SSH):**
```bash
wget -O - https://get.hacs.xyz | bash -
```
Then restart Home Assistant and add HACS via Settings → Integrations.

For more details: [HACS Download Guide](https://hacs.xyz/docs/use/download/download)

---

### Step 2: Install Required Frontend Cards

PaddiSense dashboards require these HACS frontend cards:

1. Open **HACS → Frontend**
2. Click **Explore & Download Repositories**
3. Search and install each card:

| Card | Search Term | Required |
|------|-------------|----------|
| Button Card | `button-card` | **Yes** |
| Card Mod | `card-mod` | **Yes** |
| Auto Entities | `auto-entities` | Recommended |
| ApexCharts Card | `apexcharts-card` | Recommended |

4. Restart Home Assistant after installing cards

---

### Step 3: Install PaddiSense

1. Open **HACS → Integrations**
2. Click the three-dot menu (top right) → **Custom repositories**
3. Add: `https://github.com/PaddiSense/PaddiSense`
4. Select category: **Integration**
5. Click **Add**
6. Find "PaddiSense" and click **Download**
7. Restart Home Assistant

---

### Step 4: Configure PaddiSense

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "PaddiSense" and follow the setup wizard

---

## Documentation

Full documentation is available in the [PaddiSense Documentation](https://github.com/PaddiSense/documentation) repository:

- [Installation Guide](https://github.com/PaddiSense/documentation/blob/main/getting-started/INSTALLATION.md)
- [Quick Start](https://github.com/PaddiSense/documentation/blob/main/getting-started/QUICK_START.md)
- [Module Documentation](https://github.com/PaddiSense/documentation/tree/main/modules)
- [GitHub Issues](https://github.com/PaddiSense/PaddiSense/issues)

## License

MIT License - Free for all users.
