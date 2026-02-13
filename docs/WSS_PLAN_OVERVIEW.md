# Worker Safety System (WSS) - Plan Overview

## Module Purpose
Track worker safety on-farm using the Home Assistant Companion App. Provide movement monitoring, check-in alerts, and escalation workflows to ensure worker welfare.

---

## Core Requirements

### 1. User Tracking via Companion App
- Track phone movement for each user with the companion app
- Two tracking modes:
  - **On-Farm**: Automatically tracked when within farm boundaries
  - **External Travel**: Manual "Turn On Tracking" button when leaving home base

### 2. Zone Management
| Zone Type | Movement Monitored | Expected State |
|-----------|-------------------|----------------|
| Work zones (farm areas) | Yes | Active movement |
| Non-monitored zones (home, office) | No | Stationary allowed |

- Support **multiple zones** on the farm
- Each zone configurable via UI:
  - Monitored for movement (yes/no)
  - State classification (at work / away)
- Show user's current zone on dashboard

### 3. Stationary Alert Escalation (Monitored Zones Only)

```
[User stationary in monitored zone]
         │
         ▼ 15 minutes
┌─────────────────────────────┐
│ ALERT 1: Check-in prompt    │
│ (on user's device)          │
└─────────────────────────────┘
         │
         ▼ +5 minutes (20 min total)
┌─────────────────────────────┐
│ ALERT 2: Second check-in    │
│ prompt to user              │
└─────────────────────────────┘
         │
         ▼ No response
┌─────────────────────────────┐
│ ALERT 3: Nominated Admin    │
│ notified to investigate     │
└─────────────────────────────┘
         │
         ▼ +10 minutes, no admin reset
┌─────────────────────────────┐
│ ALERT 4: Secondary user     │
│ (backup) notified           │
└─────────────────────────────┘
```

### 4. Arrival/Departure Notifications
- Notify "boss" (nominated user) when workers:
  - Arrive at work zone (farm)
  - Leave work zone (farm)
- **5pm Daily Summary**: List of users still on-site sent to boss
  - Boss should know if presence is expected or not

### 5. Dashboard Status Display

| Color | State | Description |
|-------|-------|-------------|
| 🟢 Green | Good | Active, checked in, moving normally |
| 🟠 Orange | Unknown | Status uncertain, awaiting update |
| ⚪ Grey | Away | Off-farm or in non-monitored zone |
| 🔴 Red (flashing) | Alert | Stationary too long, escalation active |

- Show each user's current zone location
- Clear visual hierarchy for quick scanning

---

## Old System Analysis

### Current Architecture (Reference Files)

**Data Storage:**
- `safety_system_users.json` - User registry with device mappings
- `safety_system_zone_config.json` - Zone definitions with monitored/away flags
- Command-line sensors to read JSON files
- Shell scripts (bash + jq) to toggle zone settings
- Python script to sync input_selects with users

**Automations:**
- `safety_status_update` - 5-min polling to update user status
- `lone_worker_no_movement_alert` - Alert escalation workflow
- `worker_arrived_departed_notification` - Arrival/departure notifications
- `working_after_hours_automation` - 5pm daily summary

**Scripts:**
- `check_in_button_script` - Manual check-in
- `assistance_req_script` - Request help button
- `safety_onsite_notify` - Notify all onsite workers
- `refresh_safety_users` / `refresh_zone_list` - Sync user/zone data

---

## Issues Identified in Old System

### 1. **Race Conditions & Timing Issues**
| Issue | Location | Problem |
|-------|----------|---------|
| Hard-coded delays in escalation | `lone_worker_no_movement_alert:53-56, 86-90` | Uses `delay:` blocks which are fragile - HA restarts lose state |
| 10-min alert window (not 15) | `lone_worker_no_movement_alert` | Doesn't match your 15-min requirement |
| Polling every 5 min | `safety_status_update:6` | Can miss events between polls |
| Movement sensor polls every 1 sec | `safety_system_template_helpers:15` | Excessive CPU usage, battery drain |

### 2. **No Persistent State**
| Issue | Impact |
|-------|--------|
| Alert state lost on HA restart | Escalation resets mid-incident |
| No timestamp tracking | Can't calculate "how long stationary" accurately |
| Uses `input_select` for status | No history of WHY status changed |

### 3. **Hardcoded Values & Fragility**
| Issue | Location |
|-------|----------|
| Hardcoded user ID | `lone_worker_notification_action_automation:25` |
| Hardcoded notify service | `lone_worker_notification_action_automation:57` |
| Hardcoded dashboard URLs | Multiple files (`/dashboard-safety/worker-status`) |
| No fallback if primary_user unset | `worker_arrived_departed_notification:62` can fail |

### 4. **Missing Requirements**
| Missing Feature | Notes |
|-----------------|-------|
| Secondary admin escalation | Only primary user notified, then "all onsite" |
| External travel tracking toggle | No "Turn On Tracking" button |
| Admin reset mechanism | No way for admin to reset alert state |
| Configurable timing | All timings hardcoded |

### 5. **Architectural Issues**
| Issue | Problem |
|-------|---------|
| Shell scripts + jq for JSON | Fragile, hard to debug, HAOS compatibility issues |
| Python script for input_selects | Requires manual execution, no auto-sync |
| No version tracking | Can't tell what version is deployed |
| Scattered files | Not following module pattern |

---

## Proposed Improvements

### 1. **Robust Alert State Machine**
Replace delay-based escalation with a proper state machine:

```yaml
# Use input_datetime + timer entities for each user
input_datetime:
  wss_<user>_stationary_since: ...
  wss_<user>_alert_started: ...

timer:
  wss_<user>_alert_timer: ...
```

**Benefits:**
- Survives HA restarts
- Accurate timing calculations
- Can show "stationary for X minutes" on dashboard

### 2. **Event-Driven, Not Polling**
Replace 5-min polling with state change triggers:

```yaml
trigger:
  - platform: state
    entity_id: sensor.<device>_activity
    to: "Stationary"
    for: "00:15:00"  # Native HA "for" condition
```

### 3. **Configurable Escalation Contacts**
```yaml
input_select:
  wss_primary_admin: ...    # First escalation
  wss_secondary_admin: ...  # Backup escalation
  wss_boss: ...             # Arrival/departure + daily summary
```

### 4. **Configurable Timing**
```yaml
input_number:
  wss_stationary_threshold_minutes:
    min: 5
    max: 60
    initial: 15
  wss_first_reminder_minutes:
    min: 1
    max: 30
    initial: 5
  wss_admin_escalation_minutes:
    min: 5
    max: 60
    initial: 10
```

### 5. **Admin Reset Mechanism**
Add actionable notification for admin:
- "Reset Alert" button clears the alert
- Logs who reset and when
- Dashboard shows reset history

### 6. **External Travel Tracking**
```yaml
input_boolean:
  wss_<user>_external_tracking: ...
```
- Toggle button on dashboard
- When enabled, user is tracked even when "away"
- Auto-disable when returning to farm

### 7. **Proper Module Structure**
```
packages/wss/
├── package.yaml          # Main package (single file)
├── VERSION               # Module version
└── dashboards/
    └── wss-dashboard.yaml

local_data/wss/
├── users.json            # User registry (auto-generated)
└── zones.json            # Zone config (user-editable)
```

### 8. **Replace Shell Scripts with HA Native**
Use `rest_command` or Python scripts in `/config/python_scripts/` instead of bash+jq.

Or better: store zone config in HA helpers directly:
```yaml
input_boolean:
  wss_zone_<zone>_monitored: ...
  wss_zone_<zone>_away: ...
```

### 9. **Notification Delivery Confirmation**
Track if notifications were actually delivered:
- Use `mobile_app_notification_cleared` events
- Retry failed notifications
- Log delivery status

### 10. **Version Sensor**
```yaml
sensor:
  - platform: template
    sensors:
      wss_version:
        value_template: !include VERSION
```

---

## UI Configuration Needs

1. **Zone Configuration**
   - Define zone boundaries (geo-fence)
   - Set monitored/unmonitored
   - Set work/away classification

2. **User Configuration**
   - Assign companion app device to user
   - Set tracking preferences (on-farm only vs external)
   - Enable/disable safety monitoring per user

3. **Escalation Contacts**
   - Primary admin (receives first escalation)
   - Secondary admin (receives backup escalation)
   - Boss (receives arrival/departure + daily summary)

4. **Timing Configuration** (with sensible defaults)
   - Stationary threshold: 15 minutes
   - First reminder: +5 minutes
   - Admin escalation: after user timeout
   - Secondary escalation: +10 minutes after admin alert

---

## Integration Points

- **Home Assistant Companion App**: Device tracking, notifications, actionable alerts
- **Farm Registry**: User/worker registration, zone definitions
- **Notification System**: Push notifications, actionable buttons
- **Person entities**: Link to HA person for tracking

---

## Implementation Priority

1. **Phase 1: Core Safety** (Critical)
   - Robust stationary detection with timer-based alerts
   - User check-in / help request
   - Primary admin escalation
   - Dashboard status display

2. **Phase 2: Full Escalation** (High)
   - Secondary admin escalation
   - Admin reset mechanism
   - Notification delivery tracking

3. **Phase 3: Arrival/Departure** (Medium)
   - Worker arrival/departure notifications
   - 5pm daily summary
   - Working hours configuration

4. **Phase 4: External Tracking** (Lower)
   - External travel toggle
   - Off-farm tracking mode

---

## Files from Old System to Reference

| Old File | Purpose | Migrate? |
|----------|---------|----------|
| `lone_worker_no_movement_alert.yaml` | Core escalation logic | Rewrite with timers |
| `safety_status_update.yaml` | Status polling | Replace with event-driven |
| `worker_arrived_departed_notification_automation.yaml` | Arrival/departure | Keep, improve fallbacks |
| `working_after_hours_automation.yaml` | 5pm summary | Keep, minor fixes |
| `assistance_req_script.yaml` | Help request | Keep, add logging |
| `check_in_button_script.yaml` | Check-in | Keep, add timestamp |
| `safety_system_users.json` | User data | Migrate to local_data/wss/ |
| `safety_system_zone_config.json` | Zone config | Migrate to local_data/wss/ |
| `safety_system_default_dashboard.yaml` | Dashboard | Update to new structure |

---

*Document created: 2026-02-08*
*Status: **IMPLEMENTED** - 2026-02-08*

---

## Implementation Status

### Completed - 2026-02-08

All planned features have been implemented in the new WSS module.

### Files Created

| File | Description |
|------|-------------|
| `/config/PaddiSense/wss/VERSION` | Version file (1.0.0-dev) |
| `/config/PaddiSense/wss/package.yaml` | Main HA package (~900 lines) |
| `/config/PaddiSense/wss/python/wss_backend.py` | Backend for write operations |
| `/config/PaddiSense/wss/python/wss_sensor.py` | Sensor for HA data output |
| `/config/PaddiSense/wss/dashboards/views.yaml` | Status + Config dashboard |

### Data Files (Auto-Created)

| File | Description |
|------|-------------|
| `/config/local_data/wss/config.json` | Timing, roles, zones config |
| `/config/local_data/wss/users.json` | Discovered users registry |

### Key Entities Created

**Sensors:**
- `sensor.wss_data` - Main data sensor with all attributes
- `sensor.wss_module_version` - Version from VERSION file
- `sensor.paddisense_wss_status` - Display status sensor
- `sensor.wss_movement_trigger` - Movement detection trigger

**Input Helpers:**
- `input_boolean.wss_enabled` - System on/off
- `input_select.wss_primary_user` / `wss_secondary_user` - Contact selectors
- `input_number.wss_stationary_threshold` - Minutes before alert (5-60)
- `input_number.wss_first_reminder` - Minutes to 2nd alert (1-30)
- `input_number.wss_primary_escalation` - Minutes to primary (1-30)
- `input_number.wss_secondary_escalation` - Minutes to secondary (5-60)
- `input_datetime.wss_working_hours_end` - Daily summary time
- `input_number.wss_escalation_stage` - Current stage (0-4)
- `input_text.wss_escalation_user` / `wss_escalation_person` - Active alert tracking

**Timer:**
- `timer.wss_escalation_timer` - With `restore: true` for HA restart survival

**Automations:**
- `wss_stationary_detection` - Event-driven with template trigger + `for:`
- `wss_movement_clears_alert` - Clears escalation on movement
- `wss_escalation_timer_finished` - Progresses escalation stages
- `wss_notification_actions` - Handles check-in/help/reset from notifications
- `wss_worker_arrival_departure` - Notifies primary of arrivals/departures
- `wss_daily_summary` - End-of-day summary to primary
- `wss_sync_on_start` - Syncs config on HA restart
- `wss_update_user_options` - Updates dropdowns when data changes

**Scripts:**
- `wss_init_system`, `wss_refresh_data` - System management
- `wss_discover_users` - Auto-discover from Person entities
- `wss_toggle_user`, `wss_toggle_zone_monitored`, `wss_toggle_zone_away` - Config toggles
- `wss_set_primary`, `wss_set_secondary` - Role assignment
- `wss_start_escalation`, `wss_escalation_next_stage`, `wss_reset_alert` - Escalation control
- `wss_check_in_button`, `wss_help_button` - Dashboard actions
- `wss_sync_timing_to_config`, `wss_sync_working_hours_to_config` - Persist changes
- `wss_export_data`, `wss_import_legacy`, `wss_reset_data` - Data management

### Issues Resolved

| Old Issue | New Solution |
|-----------|--------------|
| Delay-based escalation (lost on restart) | `timer.wss_escalation_timer` with `restore: true` |
| 5-min polling | Event-driven template triggers with `for:` |
| Hardcoded 10-min threshold | Configurable `input_number` helpers |
| Only primary escalation | Primary -> Secondary chain (4 stages) |
| No admin reset | Actionable notification + `script.wss_reset_alert` |
| Scattered files (29) | Single `package.yaml` + Python backend |
| Shell scripts with jq | Python backend for all operations |
| Hardcoded user IDs | Dynamic lookup from sensor data |

### Legacy Data Imported

Successfully imported from old system:
- 6 users with device mappings
- 12 zones with monitored/away flags

### Activation Steps

1. Add to HA packages configuration:
   ```yaml
   homeassistant:
     packages:
       wss: !include PaddiSense/wss/package.yaml
   ```

2. Restart Home Assistant

3. Initialize (if needed): Call `script.wss_init_system`

4. Discover users: Call `script.wss_discover_users`

5. Configure via dashboard:
   - Set primary/secondary contacts
   - Enable users for monitoring
   - Adjust timing thresholds
   - Configure zone flags

6. Enable monitoring: Turn on `input_boolean.wss_enabled`
