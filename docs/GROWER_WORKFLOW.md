# PaddiSense Grower Workflow

Complete end-to-end process for growers from installation to licensed modules.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GROWER JOURNEY                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. INSTALL          2. REGISTER         3. USE BASIC              │
│  ─────────────       ──────────────      ─────────────             │
│  Run installer  ───► Submit Basic   ───► Weather, IPM,             │
│  via SSH             registration        RTR, Hey Farmer,          │
│                      (GitHub issue)      ASM, Stock Tracker        │
│                                                                     │
│                           │                                         │
│                           ▼                                         │
│                                                                     │
│  4. REQUEST PWM      5. RECEIVE KEY      6. ACTIVATE PWM           │
│  ───────────────     ──────────────      ──────────────            │
│  Submit PWM     ───► Admin emails   ───► Add key to               │
│  license request     license key         secrets.yaml              │
│                                                                     │
│                           │                                         │
│                           ▼                                         │
│                                                                     │
│  7. REQUEST WSS      8. APPROVAL         9. ACTIVATE WSS           │
│  ───────────────     ──────────────      ──────────────            │
│  Submit WSS     ───► Case-by-case   ───► Add key to               │
│  license request     review + key        secrets.yaml              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Installation

### Prerequisites
- Home Assistant OS running
- SSH Add-on or Terminal Add-on installed
- Internet connection for initial download

### Run Installer
```bash
curl -sSL https://raw.githubusercontent.com/PaddiSense/PaddiSense/main/scripts/install.sh | bash
```

### What Gets Created
```
/config/
├── PaddiSense/              # Git repository (managed by updates)
│   ├── packages/            # Module YAML packages
│   ├── dashboards/          # Lovelace dashboard configs
│   ├── scripts/             # Install/update scripts
│   └── VERSION              # Current version
├── local_data/              # Runtime data (NEVER overwritten)
│   ├── weather/
│   ├── ipm/
│   ├── pwm/
│   └── ...
├── packages/                # Symlinks to PaddiSense/packages/
├── server.yaml              # Grower's configuration (NEVER overwritten)
└── secrets.yaml             # License keys (NEVER overwritten)
```

---

## Step 2: Register (Basic - Free)

### Submit Registration
Go to: https://github.com/PaddiSense/registrations/issues/new?template=basic-registration.yml

Fill in:
- Email address
- Farm name
- Location (country/region)
- Home Assistant experience level
- Farm type (optional)

### What Happens
1. Issue created in private registrations repo
2. Admin reviews (typically within 24 hours)
3. Admin closes issue as "approved"
4. Grower receives welcome email with tips

**No license key needed** - Basic modules work immediately after installation.

---

## Step 3: Use Basic Modules

After restart, these modules are active:

| Module | Purpose |
|--------|---------|
| **Weather** | BOM forecasts, conditions, alerts |
| **IPM** | Integrated Pest Management tracking |
| **RTR** | Real-Time Reporting |
| **Hey Farmer** | Notifications and reminders |
| **ASM** | Asset Service Manager |
| **Stock Tracker** | Inventory management |

### Verify Installation
Check these sensors exist:
- `sensor.paddisense_version`
- `sensor.weather_module_version`
- `sensor.ipm_module_version`

---

## Step 4: Request PWM License

### When Ready for Irrigation Control
Go to: https://github.com/PaddiSense/registrations/issues/new?template=pwm-license-request.yml

Fill in:
- Email address
- Farm name
- Basic registration issue number (e.g., #12)
- Irrigation setup details
- Number of zones
- ESPHome experience

### What Happens
1. Issue created with `license-request`, `pwm`, `pending` labels
2. Admin reviews requirements
3. Admin may contact for clarification
4. Admin generates license key
5. License key emailed to grower

---

## Step 5: Activate PWM

### Add License Key
Edit `/config/secrets.yaml`:
```yaml
pwm_license_key: "eyJlbWFpbCI6Imdyb3dlckBleGFtcGxlLmNvbSIsImV4cGlyZXMi..."
```

### Enable Module
Edit `/config/server.yaml`:
```yaml
paddisense:
  modules:
    pwm:
      enabled: true
```

### Restart
```bash
ha core restart
```

### Verify
Check `sensor.pwm_module_version` exists and shows valid license.

---

## Step 6: Request WSS License (Optional)

### Important: Legal Considerations
WSS (Water Supply System) has regulatory implications. Each request is reviewed case-by-case.

### Submit Request
Go to: https://github.com/PaddiSense/registrations/issues/new?template=wss-license-request.yml

Fill in:
- All PWM fields plus:
- Detailed location (for regulatory assessment)
- Water sources
- Water rights/licenses held
- Intended use case
- Compliance requirements

### What Happens
1. Issue created with `requires-review` label
2. Admin reviews regulatory considerations
3. Admin contacts grower for detailed discussion
4. If approved: license generated and emailed
5. If declined: explanation provided

---

## Step 7: Activate WSS

Same process as PWM:

```yaml
# secrets.yaml
wss_license_key: "eyJlbWFpbCI6Imdyb3dlckBleGFtcGxlLmNvbSIsImV4cGlyZXMi..."

# server.yaml
paddisense:
  modules:
    wss:
      enabled: true
```

Restart Home Assistant.

---

## Updates

### Automatic Notification
PaddiSense checks for updates daily. A persistent notification appears when updates are available.

### Manual Update
```bash
/config/PaddiSense/scripts/update.sh
```

Or:
```bash
curl -sSL https://raw.githubusercontent.com/PaddiSense/PaddiSense/main/scripts/update.sh | bash
```

### What's Preserved
Updates NEVER touch:
- `/config/secrets.yaml`
- `/config/server.yaml`
- `/config/local_data/*`
- License keys
- Grower configurations

---

## Troubleshooting

### "License Invalid" Error
1. Check key copied exactly (no extra spaces/newlines)
2. Verify key is for correct module (PWM vs WSS)
3. Check key hasn't expired: `python3 /config/PaddiSense/scripts/validate_license.py "KEY"`

### Module Not Loading
1. Check `server.yaml` has module enabled
2. Verify package symlinks exist in `/config/packages/`
3. Check Home Assistant logs for errors

### Update Conflicts
1. Check for local modifications: `cd /config/PaddiSense && git status`
2. Stash changes: `git stash`
3. Re-run update

---

## Support Channels

- **Issues:** https://github.com/PaddiSense/PaddiSense/issues
- **Documentation:** https://github.com/PaddiSense/PaddiSense/tree/main/docs
- **Registration Help:** Submit issue in registrations repo
