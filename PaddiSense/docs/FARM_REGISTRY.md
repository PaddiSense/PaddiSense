# Farm Registry (Shared Core)

> **Status: Complete** — Available as Home Assistant custom integration with full CRUD operations, services, and custom Lovelace card.

## Purpose

Standalone registry providing Grower → Farm → Paddock → Bay structure used by all PaddiSense modules.

## Installation

See `INSTALLATION.md` for complete setup instructions, or `QUICK_START.md` for a 5-minute guide.

**Quick version:**
1. Restart Home Assistant
2. Add integration: Settings > Devices & Services > Add > PaddiSense
3. Add card resource: `/paddisense/paddisense-registry-card.js`
4. Add card to dashboard

## Rules

- Registry is independent of PWM/IPM/ASM
- IDs are generated automatically (no manual entry)
- UI shows names, not IDs
- All data stored locally (offline-first)

## Data Model

```
Grower (from server.yaml)
  └── Farm
        └── Paddock
              └── Bay (0..N)

Season (independent, one active at a time)
```

- **Grower**: Server/owner info from `server.yaml`
- **Farm**: Contains paddocks, defined in config
- **Paddock**: Contains 0..N bays, has `current_season` flag
- **Bay**: Order, name, `is_last_bay` flag
- **Season**: Name, start/end dates, `active` flag

## Storage

| Data | Location |
|------|----------|
| Farm structure | `/config/local_data/registry/config.json` |
| Backups | `/config/local_data/registry/backups/` |
| Server info | `/config/server.yaml` (read-only) |

Export/import supported for backups and migration between servers.

## Integration Components

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.paddisense_registry` | Farm structure with all attributes |
| `sensor.paddisense_version` | Integration version |

**Registry sensor attributes:**
- `status` — "ready" or "not_initialized"
- `grower` — Server/grower info
- `farms` — All farm definitions
- `paddocks` — All paddocks
- `bays` — All bays
- `seasons` — All seasons
- `hierarchy` — Nested structure for UI
- `active_season` — Current season ID
- `active_season_name` — Current season name
- `total_paddocks`, `total_bays`, `total_seasons`, `total_farms` — Counts

### Services

#### Paddock Management
| Service | Description |
|---------|-------------|
| `paddisense.add_paddock` | Create paddock with bays |
| `paddisense.edit_paddock` | Update paddock settings |
| `paddisense.delete_paddock` | Remove paddock and bays |
| `paddisense.set_current_season` | Toggle paddock season flag |

#### Bay Management
| Service | Description |
|---------|-------------|
| `paddisense.add_bay` | Add bay to paddock |
| `paddisense.edit_bay` | Update bay settings |
| `paddisense.delete_bay` | Remove bay |

#### Season Management
| Service | Description |
|---------|-------------|
| `paddisense.add_season` | Create new season |
| `paddisense.edit_season` | Update season dates |
| `paddisense.delete_season` | Remove season |
| `paddisense.set_active_season` | Set active season |

#### Farm Management
| Service | Description |
|---------|-------------|
| `paddisense.add_farm` | Create new farm |
| `paddisense.edit_farm` | Update farm name |
| `paddisense.delete_farm` | Remove farm (if empty) |

#### System
| Service | Description |
|---------|-------------|
| `paddisense.export_registry` | Create backup file |
| `paddisense.import_registry` | Restore from backup |

### Custom Lovelace Card

**Card type:** `custom:paddisense-registry-card`

```yaml
type: custom:paddisense-registry-card
entity: sensor.paddisense_registry
show_farm_overview: true
show_paddock_list: true
show_season_info: true
show_actions: true
```

Features:
- Farm overview with counts
- Active season badge
- Paddock list with toggle/delete actions
- Add paddock/season dialogs
- Mobile-first design (60px+ touch targets)

## Service Examples

### Add a Paddock

```yaml
service: paddisense.add_paddock
data:
  name: "SW7"
  bay_count: 5
  bay_prefix: "B-"
  farm_id: "farm_1"
  current_season: true
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

### Toggle Paddock Season Status

```yaml
service: paddisense.set_current_season
data:
  paddock_id: "sw7"
  # value: true  # Optional - omit to toggle
```

## Template Examples

### Get Paddock Count

```jinja
{{ state_attr('sensor.paddisense_registry', 'total_paddocks') }}
```

### List All Paddock Names

```jinja
{% set paddocks = state_attr('sensor.paddisense_registry', 'paddocks') %}
{% for id, p in paddocks.items() %}
- {{ p.name }}
{% endfor %}
```

### Get Active Season Name

```jinja
{{ state_attr('sensor.paddisense_registry', 'active_season_name') }}
```

### Check if Paddock in Current Season

```jinja
{% set paddocks = state_attr('sensor.paddisense_registry', 'paddocks') %}
{{ paddocks.sw7.current_season }}
```

## Migration from Package-Based Setup

If you previously used the shell_command/script-based registry:

1. Your existing data in `local_data/registry/config.json` is preserved
2. The integration setup wizard detects and imports this data
3. Choose "Import existing data" when prompted
4. Old scripts/shell_commands can be replaced with services
5. Update any automations to use new service names

**Service mapping:**
| Old | New |
|-----|-----|
| `script.registry_add_paddock` | `paddisense.add_paddock` |
| `script.registry_delete_paddock` | `paddisense.delete_paddock` |
| `shell_command.registry_backend` | Use services directly |

## UI Design

Dashboard cards follow the **PaddiSense UI Style Guide** for consistency:
- Dark header (#1e1e1e)
- Slate info blocks (#546e7a)
- Green for positive actions (#28a745)
- Red for destructive actions (#dc3545)
- Blue for primary actions (#0066cc)
- Minimum 60px touch targets

See `reference/UI_STYLE_GUIDE.md` for complete styling reference.
