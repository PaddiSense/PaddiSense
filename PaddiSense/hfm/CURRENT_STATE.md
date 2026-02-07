# HFM Module - Current State

**Version:** 1.0.0-rc.1
**Status:** Release Candidate
**Last Updated:** 2026-02-07

## Summary

Hey Farmer Module (HFM) is an event recording system for tracking farm activities including nutrient/chemical applications, irrigation events, and crop stage changes. Features a wizard-based event entry system with edit capabilities.

## Features

### Completed

- **Event Recording**: 4 event types (Nutrient, Chemical, Irrigation, Crop Stage)
- **6-Step Wizard**: Guided event entry with progress indicator
- **Event History**: View all events with status indicators (pending/confirmed)
- **Edit Events**: Load existing events for modification
- **Confirm/Delete**: Manage pending events
- **Export**: Backup events to JSON files
- **Product Integration**: Pulls products from IPM module by category
- **Paddock Integration**: Uses Farm Registry paddocks

### Not Yet Implemented

- Voice recording (planned for future)
- Device-to-user mapping (infrastructure ready)
- Multi-paddock selection per event

## Dashboard Views

| View | Path | Description |
|------|------|-------------|
| Overview | `/hfm-heyfarm/hfm` | Stats, events by type, quick actions |
| New Event | `/hfm-heyfarm/hfm-new` | 6-step wizard for recording events |
| History | `/hfm-heyfarm/hfm-history` | View/edit/delete/confirm events |
| Settings | `/hfm-heyfarm/hfm-settings` | System status, crop stages, export |

## Data Storage

```
/config/local_data/hfm/
├── config.json      # Crop stages, methods, irrigation types
├── events.json      # All recorded events
└── backups/         # JSON exports with timestamps
```

## Dependencies

- **Farm Registry**: Provides paddock list
- **IPM Module**: Provides product list (filtered by category)
- **button-card**: Custom card for styled UI

## Files

```
/config/PaddiSense/hfm/
├── VERSION              # Module version
├── CURRENT_STATE.md     # This file
├── package.yaml         # HA configuration (entities, automations, scripts)
├── dashboards/
│   └── views.yaml       # All dashboard views
└── python/
    ├── hfm_backend.py   # CLI for data operations
    └── hfm_sensor.py    # Sensor data provider
```

## Configuration Entities

### Input Helpers
- `input_select.hfm_event_type` - Event type selection
- `input_select.hfm_when` - Date selection (Today/Yesterday/Specific)
- `input_select.hfm_selected_paddock` - Paddock dropdown
- `input_select.hfm_selected_product` - Product dropdown
- `input_select.hfm_application_method` - Application method
- `input_select.hfm_crop_stage` - Crop stage selection
- `input_select.hfm_irrigation_type` - Irrigation type
- `input_select.hfm_edit_event` - Event selection for editing
- `input_number.hfm_wizard_step` - Current wizard step (1-6)
- `input_boolean.hfm_edit_mode` - Edit vs new mode flag
- `input_text.hfm_*` - Various text inputs

### Sensors
- `sensor.hfm_events` - Main sensor with all event data
- `sensor.hfm_version` - Module version
- `sensor.hfm_system_status` - System status
- `sensor.hfm_events_today` - Today's event count
- `sensor.hfm_pending_events` - Pending event count

## Scripts

| Script | Purpose |
|--------|---------|
| `script.hfm_init` | Initialize module (create config/directories) |
| `script.hfm_wizard_next` | Navigate to next wizard step |
| `script.hfm_wizard_prev` | Navigate to previous wizard step |
| `script.hfm_wizard_reset` | Clear form and reset to step 1 |
| `script.hfm_submit_event` | Save new event or update existing |
| `script.hfm_load_event_for_edit` | Load event data into form |
| `script.hfm_confirm_event` | Confirm pending event |
| `script.hfm_delete_event` | Delete selected event |
| `script.hfm_export` | Export events to backup file |
| `script.hfm_add_crop_stage` | Add custom crop stage |

## Changelog

### 1.0.0-rc.1 (2026-02-07)
- Fixed ButtonCardJS template errors with try-catch wrappers
- Fixed navigation paths (changed from lovelace-paddisense to hfm-heyfarm)
- Fixed Edit button using proper call-service action
- Removed event ID from dropdown display
- Updated event lookup to use date+type+paddock matching
- Redesigned Settings view with styled status card
- Styled crop stages list (removed ugly markdown)
- Removed unused Device Mappings section
- Fixed Confirm button color on review step
