# PaddiSense 1.0.0 Release Preparation Plan

**Created:** 2026-02-15
**Target:** Stable 1.0.0 release
**Current:** 1.0.0-pr.1 (all modules)

---

## Phase 1: Repository & Git Hygiene

### 1.1 Main Repo Status
- [x] Confirm `dev` branch is clean
- [x] Review untracked files (currently: `registrations/` - expected, separate repo)
- [x] Check all modules have matching VERSION files (all at 1.0.0-pr.1)
- [x] Verify `modules.json` is accurate
- [x] Fixed: const.py VERSION synced to 1.0.0-pr.1
- [x] Fixed: Removed leftover `/config/PaddiSense/github-repo/` folder

### 1.2 Registrations Repo (Private)
- [x] Verify `registrations/` repo is up-to-date
- [x] Confirm license-tools work correctly (generate_keys.py, generate_license.py, validate_license.py)
- [x] Test license generation flow (Ed25519 signing verified)
- [x] Public key deployed to `/config/custom_components/paddisense/keys/public.pem`
- [x] Fixed: get_allowed_modules() now checks for license-granted modules
- [x] Fixed: install_module() now blocks LOCKED_MODULES without license

---

## Phase 2: New Grower Install Flow (Full Test)

### 2.1 Pre-Install Requirements
- [x] Fresh HAOS install documented (README.md)
- [x] HACS installation steps verified (Install HACS button in Settings)
- [x] Required HACS frontend cards listed (12 cards in const.py)
- [x] Required HACS integrations listed (Browser Mod, BOM)

### 2.2 Config Flow Wizard (Code Review - VERIFIED)
- [x] Step 1: Welcome screen - fresh/upgrade/import detection
- [x] Step 2: Registration (name + email) - validates and stores locally
- [x] Step 3: License (optional) - currently skipped, all modules free
- [x] Step 4: Git check - verifies git availability
- [x] Step 5: Clone repository - clean install with local_data preservation
- [x] Step 6: Installation completes - registry initialized
- [x] Telemetry fires on registration (report_registration)
- [x] HACS cards auto-install attempted during clone

### 2.3 Post-Install First Run
- [ ] PaddiSense Manager dashboard accessible
- [ ] Default modules installed (IPM, ASM)
- [ ] Farm Registry ready to configure
- [ ] Add first Business > Farm > Paddock flow works

---

## Phase 3: Module UI Review

Review each module for:
- 70px button heights
- Yellow title headers (#E9E100)
- Consistent color standards
- Mobile-first responsive layout
- No broken entities or scripts

### 3.1 Registry (PaddiSense Manager)
- [ ] Farms view (Business CRUD, Farm CRUD)
- [ ] Paddocks view (Paddock CRUD, crop assignment)
- [ ] Bays view (Bay CRUD)
- [ ] Seasons view
- [ ] Crops view (Crop types, stages)
- [ ] Settings/Config view

### 3.2 IPM (Inventory Manager)
- [ ] Products list view
- [ ] Add/Edit product flow
- [ ] Stock management (add/remove stock)
- [ ] Low stock alerts
- [ ] Settings/Initialize view

### 3.3 ASM (Asset Service Manager)
- [ ] Equipment list
- [ ] Add/Edit equipment
- [ ] Service records
- [ ] Parts inventory
- [ ] Settings view

### 3.4 Weather
- [ ] Station overview
- [ ] Current conditions display
- [ ] Local vs API station handling
- [ ] Settings view

### 3.5 PWM (Water Management)
- [ ] Bay monitoring dashboard
- [ ] Irrigation scheduling
- [ ] ESPHome device integration
- [ ] Settings view

### 3.6 RTR (Real Time Rice)
- [ ] Paddock predictions display
- [ ] Color-coding by moisture
- [ ] Sort by moisture (highest first)
- [ ] Settings view

### 3.7 STR (Stock Tracker)
- [ ] Mob list
- [ ] Add/Edit mob
- [ ] Movement records
- [ ] Settings view

### 3.8 HFM (Hey Farmer)
- [ ] Event wizard flow
- [ ] Paddock selection (farm filter, multi-select)
- [ ] Product selection (IPM integration)
- [ ] Weather capture
- [ ] Draft save/restore
- [ ] Event history
- [ ] Settings view

### 3.9 WSS (Worker Safety)
- [ ] Worker list
- [ ] Check-in/check-out flow
- [ ] Escalation alerts
- [ ] Settings view

---

## Phase 4: Registration & Licensing Review

### 4.1 Registration Flow
- [ ] Local registration creates `/config/local_data/registration.json`
- [ ] Server ID generated correctly (unique per install)
- [ ] Email validation works
- [ ] Registration persists across restarts

### 4.2 Telemetry (Optional)
- [ ] GitHub issue creation works (when configured)
- [ ] Fire-and-forget (failures don't block)
- [ ] Privacy-respecting (no farm data sent)

### 4.3 License System
- [x] License generation tool works (`registrations/license-tools/`)
- [x] License validation (offline, Ed25519 crypto-based)
- [x] Free modules accessible without license
- [x] PWM/WSS locked without valid license (install_module checks)
- [x] License saved locally for offline use (`/config/local_data/paddisense/credentials.json`)

### 4.4 Email to Repo Recording
- [ ] Does registration create GitHub issue? (if telemetry enabled)
- [ ] What triggers the issue creation?
- [ ] Is grower info recorded in registrations repo?

---

## Phase 5: Documentation

### 5.1 Required Docs
- [ ] README.md - Installation instructions (exists)
- [ ] DEPLOYMENT.md - Server setup guide (missing?)
- [ ] GETTING_STARTED.md - First grower guide (missing?)
- [ ] MariaDB setup guide - Recommended for Weather/PWM users (document in DEPLOYMENT.md)

### 5.2 Per-Module Docs
- [ ] docs/ARCHITECTURE.md
- [ ] docs/IPM.md, ASM.md, etc.
- [ ] reference/UI_STYLE_GUIDE.md

---

## Phase 6: Final Release Steps

### 6.1 Version Bump
- [ ] Update all VERSION files to 1.0.0
- [ ] Update modules.json version
- [ ] Update status from "pr" to "stable"

### 6.2 Release Branch
- [ ] Merge dev to main
- [ ] Create release tag v1.0.0
- [ ] Update CHANGELOG.md

### 6.3 Distribution
- [ ] HACS repository updated
- [ ] GitHub release created
- [ ] Release notes published

---

## Current Blockers / Issues Found

### Registration Telemetry - FIXED
- [x] `report_update_check()` already wired to check_for_updates service
- [x] Added `report_registration()` function to telemetry.py
- [x] Wired registration telemetry in config_flow.py
- Now: Growers recorded on BOTH registration AND update checks

### HACS Installation System - ADDED
- [x] Created `/config/PaddiSense/scripts/install_hacs.sh` - Downloads & installs HACS
- [x] Added shell command `paddisense_install_hacs` to registry package
- [x] Added "Install HACS" button to Settings dashboard
- [x] Added "Install HACS Cards" button (installs all 12 cards)
- [x] Added "Install BOM Integration" button (Weather module)
- [x] Updated HACS dependencies display (categorized: Core/PWM/Weather)

### HACS Dependencies (12 cards + 2 integrations)
| Category | Cards |
|----------|-------|
| Core (8) | button-card, card-mod, auto-entities, mushroom, apexcharts-card, mini-graph-card, flex-table-card, restriction-card |
| PWM (2) | circular-timer-card, flipdown-timer-card |
| Weather (2) | windrose-card, weather-radar-card |
| Integrations | Browser Mod (Core), Bureau of Meteorology (Weather) |

### UI Issues Found

#### Weather Module
- [x] Wind data card on Local Station view: Wind rose and wind chart are on same row
  - **Fixed:** Changed to vertical-stack, full width
- [x] ETO calculation shows many decimal places
  - **Fixed:** Added state_display with toFixed(1)

#### UI Reference Standard
- **IPM Stock Movement view** - Button sizing in this view is the gold standard
  - Large touch targets, good for fat thumbs
  - Use this as reference when reviewing other modules

#### Button Height Issues (< 70px minimum) - FIXED

| Module | File | Status |
|--------|------|--------|
| registry | manager.yaml | Fixed (56px → 70px) |
| hfm | views.yaml | Fixed (60px → 70px, 6 instances) |
| asm | views.yaml | Fixed (56px/60px → 70px, 12 instances) |
| ipm | inventory.yaml | Fixed (60px → 70px, 2 instances; 35px/45px → 70px, 6 instances) |
| pwm | views.yaml | Fixed (60px → 70px, 4 instances) |
| wss | views.yaml | Fixed (60px → 70px, 5 instances) |
| registry | config.yaml | Fixed (60px → 70px, 1 instance) |
| weather | views.yaml | Fixed (42px → 70px, 15 station buttons) |

**Note:** 50px title bars, weather forecast tiles (56px), and form section headers (36-40px) are intentionally smaller (not action buttons).

#### Crop Rotation UI Simplification - DONE
- [x] Season-locked crop rotation model implemented
- [x] Crop 1 start month: Auto-derived from season start (hidden from UI)
- [x] Crop 1 end month: User selects (visible)
- [x] Crop 2 start month: Auto-derived as Crop 1 end + 1 (hidden from UI)
- [x] Crop 2 end month: Auto-derived from season end (hidden from UI)
- [x] Updated labels: "CROP 1 (From Season Start)" and "CROP 2 (To Season End)"
- [x] Files modified: manager.yaml (UI), package.yaml (save scripts)

### Git/Repo Status
- [x] main and dev branches synced (same commit 4cd5c73)
- [x] All VERSION files consistent (1.0.0-pr.1)
- [x] Origin is up to date
- [x] `registrations/` is separate private repo (correct)

---

## Notes

- `registrations/` is a separate private repo (correct, contains license private key)
- All modules currently at `1.0.0-pr.1` status
- HFM depends on IPM (documented in modules.json)
- Free modules: ipm, asm, weather, rtr, str, hfm
- Licensed modules: pwm, wss

---

## PWM Development Notes (Future)

### Sensor Data Architecture

PWM water depth sensors come from ESPHome devices. For proper data retention:

**ESPHome Sensor Configuration (Required)**
```yaml
sensor:
  - platform: ultrasonic  # or adc, etc.
    name: "Bay 1 Water Depth"
    state_class: measurement  # REQUIRED for HA Long-Term Statistics
    unit_of_measurement: "mm"
    device_class: distance
```

**Data Storage Strategy**

| Data Type | Storage | Retention | Notes |
|-----------|---------|-----------|-------|
| Raw water depth readings | HA Long-Term Statistics | Forever (hourly min/max/mean) | Automatic if `state_class: measurement` set |
| Irrigation events | `/config/local_data/pwm/irrigation_events.json` | Forever | Start/stop times, duration, bay, operator |
| Irrigation schedules | `/config/local_data/pwm/schedules.json` | Forever | Planned vs actual comparison |
| Daily bay summaries | `/config/local_data/pwm/daily_summaries.json` | Forever | Avg depth, fill/drain cycles, water usage |

**Key Principle:** Let HA handle raw sensor history via LTS. PaddiSense stores farm operational data (events, schedules, summaries) that HA doesn't track natively.

**MariaDB Recommendation**
For growers using PWM (high-frequency sensor data), recommend MariaDB with:
```yaml
recorder:
  db_url: mysql://user:password@core-mariadb/homeassistant?charset=utf8mb4
  purge_keep_days: 30
  commit_interval: 5
```
- 30 days of detailed data is sufficient (LTS keeps hourly forever)
- MariaDB handles high write loads better than SQLite
- Document setup in DEPLOYMENT.md
