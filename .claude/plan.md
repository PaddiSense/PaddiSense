# Unified Weather Dashboard Plan

## Objective
Combine the `weather/` and `weather_api/` modules into a single unified weather module with a dynamic dashboard that shows views based on what's configured on each server.

## Current State

### Weather Module (Local Gateway)
- **Source:** Ecowitt Gateway integration (`sensor.ecowittgateway_1_*`)
- **Dashboard views:** Forecast, Temps, Station
- **Key entities:** Delta T, ETo, Degree Days, statistics sensors
- **Requires:** Physical Ecowitt gateway on local network

### Weather API Module (Cloud API)
- **Source:** Ecowitt cloud API via Python sensor
- **Dashboard views:** Overview (4 station slots), Settings
- **Key entities:** `sensor.weather_api_data` + per-station template sensors
- **Requires:** API credentials in secrets.yaml

## Proposed Architecture

### Single Unified Module: `weather/`

```
PaddiSense/weather/
├── VERSION                     # Combined version (e.g., 2.0.0)
├── package.yaml                # All HA config (merged from both)
├── python/
│   ├── weather_api_backend.py  # Station management (from weather_api)
│   └── weather_api_sensor.py   # API fetching (from weather_api)
└── dashboards/
    └── views.yaml              # Unified dashboard
```

### Detection Strategy

Create template binary sensors that detect what's available:

```yaml
# Detect local gateway
binary_sensor.weather_gateway_available:
  state: "{{ states('sensor.ecowittgateway_1_outdoor_temperature') not in ['unavailable', 'unknown'] }}"

# Detect API configured
binary_sensor.weather_api_available:
  state: "{{ state_attr('sensor.weather_api_data', 'station_count') | int(0) > 0 }}"
```

### Dashboard Views

| View | Condition | Source |
|------|-----------|--------|
| **Forecast** | Always shown | BOM forecast entities |
| **Temps** | Always shown | BOM forecast min/max |
| **Local Station** | Gateway available | Ecowitt gateway sensors |
| **API Stations** | API has stations | weather_api_data sensor |
| **Settings** | Always shown | Combined settings |

### Server Configuration (server.yaml)

```yaml
modules:
  weather: true          # Enables entire weather module

weather:
  latitude: -35.0        # For ETo calculations
  elevation: 100         # For ETo calculations
  # Gateway auto-detected via entity availability
  # API auto-detected via sensor state
```

## Implementation Steps

### Phase 1: Create Unified Package

1. **Merge package.yaml files**
   - Copy all template sensors from weather/package.yaml
   - Copy all entities from weather_api/package.yaml
   - Add detection binary sensors
   - Consolidate scripts with prefixes (`weather_local_*`, `weather_api_*`)

2. **Copy Python files to weather/python/**
   - weather_api_backend.py
   - weather_api_sensor.py
   - Update paths in scripts if needed

3. **Update VERSION to 2.0.0**

### Phase 2: Create Unified Dashboard

1. **Combine button_card_templates**
   - Merge templates from both dashboards
   - Ensure no naming conflicts

2. **Create views structure**
   ```yaml
   views:
     - title: Forecast      # Always visible
     - title: Temps         # Always visible
     - title: Local         # Conditional on gateway
     - title: Stations      # Conditional on API
     - title: Settings      # Always visible
   ```

3. **Use conditional sections within views**
   - Views themselves are always present (HA limitation)
   - Content within views uses conditional cards
   - Empty views show "Not configured" message

### Phase 3: Update Install/Update Scripts

1. **Deprecate weather_api module**
   - Remove from server.yaml.example
   - Add migration note to update.sh

2. **Update install.sh**
   - Single weather module handles both sources
   - Create local_data/weather/ directory (for API config)

3. **Update configuration.yaml snippet**
   - Single package include for weather

### Phase 4: Data Migration

1. **Move config files**
   - `local_data/weather_api/config.json` → `local_data/weather/api_config.json`

2. **Backward compatibility**
   - Sensor script checks both locations
   - First run migrates if needed

## Technical Constraints

### HA Dashboard Limitations
- Views cannot be conditionally hidden in YAML dashboards
- All views always appear in navigation
- Solution: Use conditional cards to show "Not available" messages

### Entity Detection
- Use `has_value()` or state checks for entity availability
- Gateway entities: `sensor.ecowittgateway_1_*`
- API entities: `sensor.weather_api_data`

### Conditional Card Syntax
```yaml
- type: conditional
  conditions:
    - entity: binary_sensor.weather_gateway_available
      state: "on"
  card:
    # Content shown when gateway available
```

## File Changes Summary

| Action | File |
|--------|------|
| **Merge** | weather/package.yaml ← weather_api/package.yaml |
| **Create** | weather/python/weather_api_backend.py |
| **Create** | weather/python/weather_api_sensor.py |
| **Replace** | weather/dashboards/views.yaml (unified) |
| **Update** | weather/VERSION → 2.0.0 |
| **Update** | server.yaml.example |
| **Update** | install.sh, update.sh |
| **Delete** | weather_api/ (after migration period) |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing installs | Keep weather_api config paths working |
| Entity name conflicts | Prefix local sensors differently |
| Large package.yaml | Well-organized with comments |
| Views always visible | Show helpful "not configured" messages |

## Decisions Made

1. **Migration:** Remove `weather_api/` immediately after merge (clean break)
2. **BOM Views:** Always show Forecast/Temps views (default for all servers)
3. **View Naming:** Use "Local Station" for the gateway view

## Implementation Order

1. Create unified `weather/package.yaml` with all entities
2. Copy Python files to `weather/python/`
3. Create unified `weather/dashboards/views.yaml`
4. Update `weather/VERSION` to 2.0.0
5. Update `server.yaml.example` (remove weather_api option)
6. Update `install.sh` and `update.sh`
7. Delete `weather_api/` folder
8. Update CLAUDE.md documentation
