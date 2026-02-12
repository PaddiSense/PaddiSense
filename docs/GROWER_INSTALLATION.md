# PaddiSense Grower Installation Guide

## Overview

PaddiSense installs as packages and dashboards on Home Assistant OS. This guide covers initial installation, updates, and module activation.

---

## Prerequisites

- Home Assistant OS (HAOS) - required
- SSH or Terminal access (via SSH Add-on or Terminal Add-on)
- Email address for registration

---

## Installation Methods

### Method 1: One-Line Installer (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/PaddiSense/PaddiSense/main/scripts/install.sh | bash
```

This will:
1. Clone PaddiSense to `/config/PaddiSense/`
2. Create symlinks for packages
3. Set up local data directories
4. Prompt for registration

### Method 2: Manual Installation

```bash
# Clone repository
cd /config
git clone https://github.com/PaddiSense/PaddiSense.git

# Run setup
cd PaddiSense
./scripts/setup.sh
```

---

## Post-Installation

### 1. Register for PaddiSense Basic

Go to: https://github.com/PaddiSense/registrations/issues/new?template=basic-registration.yml

Fill in:
- Email address
- Farm name
- Location

No license key needed - Basic modules activate immediately after setup.

### 2. Restart Home Assistant

```bash
ha core restart
```

Or via UI: Settings → System → Restart

### 3. Verify Installation

Check for these entities:
- `sensor.paddisense_version`
- `sensor.weather_module_version`
- `sensor.ipm_module_version`

---

## Module Activation

### Basic Modules (Auto-enabled)
These work immediately after installation:
- Weather
- IPM
- RTR
- Hey Farmer
- Asset Service Manager
- Stock Tracker

### PWM Module (License Required)

1. Request license: https://github.com/PaddiSense/registrations/issues/new?template=pwm-license-request.yml
2. Receive license key via email
3. Add to `secrets.yaml`:
   ```yaml
   pwm_license_key: "YOUR_LICENSE_KEY_HERE"
   ```
4. Enable PWM in configuration:
   ```yaml
   # In configuration.yaml or server.yaml
   paddisense:
     modules:
       pwm:
         enabled: true
   ```
5. Restart Home Assistant

### WSS Module (License Required)

1. Request license: https://github.com/PaddiSense/registrations/issues/new?template=wss-license-request.yml
2. Admin will contact you for discussion
3. If approved, receive license key via email
4. Add to `secrets.yaml`:
   ```yaml
   wss_license_key: "YOUR_LICENSE_KEY_HERE"
   ```
5. Enable WSS in configuration
6. Restart Home Assistant

---

## Updates

### Automatic Update Check
PaddiSense checks for updates daily and creates a notification if available.

### Manual Update

```bash
cd /config/PaddiSense
./scripts/update.sh
```

Or one-liner:
```bash
curl -sSL https://raw.githubusercontent.com/PaddiSense/PaddiSense/main/scripts/update.sh | bash
```

### What Updates Preserve
- `secrets.yaml` - never touched
- `server.yaml` - never touched
- `local_data/` - never touched
- `.storage/` - never touched
- License keys - preserved

---

## Directory Structure

After installation:
```
/config/
├── PaddiSense/              # Cloned repository
│   ├── packages/            # Module packages
│   ├── dashboards/          # Lovelace dashboards
│   ├── scripts/             # Install/update scripts
│   └── ...
├── local_data/              # Local runtime data (preserved)
│   ├── weather/
│   ├── ipm/
│   ├── pwm/
│   └── ...
├── secrets.yaml             # License keys stored here
└── server.yaml              # Server-specific configuration
```

---

## Troubleshooting

### Installation Fails
- Ensure you have SSH/Terminal access
- Check internet connectivity
- Verify HAOS (not Docker/Supervised)

### Modules Not Loading
- Check `sensor.paddisense_version` exists
- Verify packages are symlinked correctly
- Check Home Assistant logs

### License Invalid
- Ensure key is copied exactly (no extra spaces)
- Check key is for correct module (PWM vs WSS)
- Verify key hasn't expired

### Update Fails
- Check git status for conflicts
- Backup and re-clone if needed

---

## Support

- Issues: https://github.com/PaddiSense/PaddiSense/issues
- Documentation: https://github.com/PaddiSense/PaddiSense/docs
