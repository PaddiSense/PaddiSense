# PWM — Precision Water Management

> **UI Note:** Dashboard cards should follow the **IPM card style** for consistency. See `docs/ARCHITECTURE.md` and `reference/UI_STYLE_GUIDE.md`.

## Scope
- Paddock/bay irrigation automation modes (Off/Flush/Pond/Drain)
- Device assignment and bay configuration
- Offline-first automation
- Dynamic entity generation for scalability

## Architecture Overview

PWM uses **Farm Registry as the source of truth** for paddock/bay structure, adding only PWM-specific settings.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Dashboard UI                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Registry:    │  │ Assign Device│  │ Generate & Reload    │  │
│  │ Add Paddock  │  │ (PWM-only)   │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python Backend Scripts                        │
│  ┌──────────────────┐         ┌────────────────────────────┐   │
│  │ pwm_backend.py   │         │ pwm_generator.py           │   │
│  │ - PWM settings   │         │ - Reads Registry (struct)  │   │
│  │ - Device assign  │         │ - Reads PWM (settings)     │   │
│  └────────┬─────────┘         │ - Generates YAML entities  │   │
│           │                   └─────────────┬──────────────┘   │
└───────────┼─────────────────────────────────┼───────────────────┘
            │                                 │
            ▼                                 ▼
┌─────────────────────────┐  ┌────────────────────────────────────┐
│ local_data/registry/    │  │ local_data/pwm/                    │
│ └── config.json         │  │ └── config.json (PWM settings)    │
│     (STRUCTURE)         │  │     (enabled, devices, levels)    │
│     - paddocks          │  └────────────────────────────────────┘
│     - bays              │
│     - seasons           │
└─────────────────────────┘
            │
            └──────────────────┐
                               ▼
                 ┌────────────────────────────────────┐
                 │ PaddiSense/pwm/generated/          │
                 │ └── pwm_paddock_*.yaml             │
                 │ └── pwm_bay_*_b_*.yaml             │
                 └────────────────────────────────────┘
                               │
                               ▼ (symlinks)
                 ┌────────────────────────────────────┐
                 │ PaddiSense/packages/               │
                 │ └── pwm_gen_*.yaml → generated/    │
                 └────────────────────────────────────┘
```

## Data Separation

| Source | Contains | Managed By |
|--------|----------|------------|
| **Farm Registry** | Paddock/bay structure (ID, name, order, farm_id) | Registry UI |
| **PWM Config** | PWM settings (enabled, device assignments, water levels) | PWM UI |
| **server.yaml** | Farm definitions (location, water source) | Manual/Install |

## Control Contract (Critical)
- HA/PWM controls **valves/actuators only**
- Never control raw relays directly from HA
- Two-actuator devices are logically paired
- Door control states: Close, Open, HoldOne, HoldTwo

## Grower Workflow (No YAML Required)

### 1. Add a Paddock
1. Go to **PWM Dashboard → Settings**
2. Enter paddock name and number of bays
3. Toggle "Individual Bay Mode" if each bay should have separate automation
4. Click **Add Paddock**

### 2. Assign Devices (Wizard)
1. In **Settings**, find the **Device Assignment Wizard** section
2. Click a paddock card to open the configuration wizard
3. The popup shows all bays with their current device status
4. Click a bay to configure:
   - **Supply 1/2**: Primary and secondary supply door devices
   - **Drain 1/2**: Primary and secondary drain door devices
   - **Level Sensor**: Water level sensor device name
   - **Water Level Settings**: Min/max levels, offset, flush time
5. Click **Save Bay** to save the configuration

### 3. Generate Entities
1. Click **Generate Entities** (generates YAML files)
2. Click **Generate & Reload** to activate immediately
3. All input helpers, sensors, timers, and automations are created automatically

### 4. Operate
1. Select automation mode for paddock or individual bays
2. Monitor water levels on dashboard
3. System automatically controls doors based on mode

## Automation Modes

| Mode | Behavior |
|------|----------|
| **Off** | No automation; manual control only |
| **Flush** | Fill to min level → start timer → release when timer expires |
| **Pond** | Maintain water between min/max levels continuously |
| **Drain** | Open drain, keep supply closed until empty |

## Entity Generator

The generator (`pwm_generator.py`) creates all necessary entities from config.json:

### Generated Per Paddock
- `input_select.<paddock>_automation_state`
- `input_select.<paddock>_drain_door_control`
- `input_number.<paddock>_supply_waterleveloffset`
- `timer.<paddock>_flushclosesupply`
- `sensor.pwm_<paddock>_supply_water_depth`
- `sensor.pwm_<paddock>_version`
- Automations: door control, state propagation, all-bays-off

### Generated Per Bay
- `input_select.<paddock>_b_<nn>_door_control`
- `input_select.<paddock>_b_<nn>_automation_state`
- `input_number.<paddock>_b_<nn>_waterlevelmin/max/offset`
- `input_boolean.<paddock>_b_<nn>_flushactive`
- `timer.<paddock>_b_<nn>_flushtimeonwater`
- `sensor.pwm_<paddock>_b_<nn>_water_depth`
- Automations: irrigation logic, setup, flush timer start/end, deactivate

### CLI Usage
```bash
# List paddocks
python3 pwm_generator.py list

# Generate all enabled paddocks
python3 pwm_generator.py generate

# Generate specific paddock
python3 pwm_generator.py generate --paddock sw5

# Remove all generated files
python3 pwm_generator.py clean
```

## Data Files

### config.json Structure
```json
{
  "initialized": true,
  "version": "1.0.0",
  "paddocks": {
    "sw5": {
      "name": "SW5",
      "farm_id": "farm_1",
      "bay_count": 5,
      "enabled": true,
      "automation_state_individual": false
    }
  },
  "bays": {
    "sw5_b_01": {
      "paddock_id": "sw5",
      "name": "B-01",
      "order": 1,
      "supply_1": { "device": "rb_040", "type": "door" },
      "settings": {
        "water_level_min": 5,
        "water_level_max": 15
      }
    }
  }
}
```

## Fault Handling
- Watchdog enabled on ESPHome devices
- On fault: alert + mark unavailable
- No forced stop/recovery from HA (manual intervention required)

## Versioning
- Module VERSION file: `pwm/VERSION`
- Version sensor: `sensor.pwm_<paddock>_version`
- Generated files include version header

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `script.pwm_add_paddock` | Add paddock via UI |
| `script.pwm_delete_paddock` | Remove paddock |
| `script.pwm_assign_device` | Assign device to bay slot |
| `script.pwm_generate_entities` | Generate YAML files |
| `script.pwm_generate_and_reload` | Generate and reload all domains |
| `script.pwm_refresh_data` | Refresh sensor data |
| `script.pwm_export_data` | Create backup |
| `script.pwm_wizard_open_paddock` | Open device assignment wizard for paddock |
| `script.pwm_wizard_edit_bay` | Open bay device editor popup |
| `script.pwm_wizard_save_bay` | Save bay device assignments |

## Shell Commands

| Command | Purpose |
|---------|---------|
| `shell_command.pwm_generate_all` | Generate all YAML |
| `shell_command.pwm_generate_paddock` | Generate for specific paddock |
| `shell_command.pwm_clean_generated` | Remove generated files |

################ working dashboard from Production Server
button_card_templates:
  template_wifi_access_points:
    variables:
      var_entity: entity.name
      var_name: Access Point Name
    name: '[[[ return variables var.name]]]'
    color_type: card
    state:
      - value: Adoption Failed
        color: rgb(255,0,0)
        icon: mdi:wifi-alert
      - value: Disconnected
        color: rgb(255,0,0)
        icon: mdi:wifi-alert
      - value: connected
        color: rgb(0,255,0)
        icon: mdi:wifi
      - value: Isolated
        color: rgb(255, 255, 0)
        icon: mdi:wifi-alert
    action: more-info
    styles:
      card:
        - height: 100px
      icon:
        - height: 50px
        - width: 50px
      name:
        - font-size: 16px
    tap_action:
      action: toggle
    hold_action:
      action: more-info
    show_name: true
    show_icon: true
    show_state: false
    show_label: true
    size: 30%
    label: |
      [[[
         var name = entity.entity_id
         if (states[name].state === "Adoption Failed")
         return "Maintenance Required";
         if (states[name].state === "Disconnected")
         return "Maintenance Required";
         if (states[name].state === "Isolated")
         return "Maintenance Required";
         else if (states[name].state === "connected")
         return "OK";
       ]]]
  template_switch_on_off:
    variables:
      var_entity: entity.name
      var_name: LocationName
    label: |
      [[[
      var name = entity.entity_id
      if (states[name].state === "on")
      return "On";
      else if (states[name].state === "off")
      return "Off";
      ]]]
    state:
      - value: 'off'
        color: rgb(255,0, 0)
        icon: mdi:engine-off
      - value: 'on'
        color: rgb(0,255,0)
        icon: mdi:engine
    color_type: card
    styles:
      card:
        - height: 100px
      icon:
        - height: 30px
        - width: 30px
      name:
        - font-size: 12px
    tap_action:
      action: toggle
    hold_action:
      action: more-info
    show_name: true
    show_icon: true
    show_state: false
    show_label: true
    size: 30%
  template_titleblock:
    variables:
      var_name: Name
    color_type: label-card
    color: rgb(200,250, 55)
    name: '[[[return variables.var_name]]]'
    styles:
      card:
        - height: 20px
  template_textblock:
    variables:
      var_name: Name
    color_type: label-card
    color: rgb(162, 55, 250)
    name: '[[[return variables.var_name]]]'
    styles:
      card:
        - height: 20px
  template_channel_autostate:
    variables:
      var_name: LocationName
    label: |
      [[[
        const entity_id = entity.entity_id;
        const stateObj = states[entity_id];
        if (!stateObj) {
          return "Entity not found";
        }

        switch (stateObj.state) {
          case "Off":
            return "Off";
          case "Manual":
            return "Manual";
          case "Auto":
            return "Auto";
          default:
            return "Current State: " + stateObj.state;
        }
      ]]]
    tap_action:
      action: call-service
      service: input_select.select_next
      service_data:
        entity_id: '[[[ return entity.entity_id ]]]'
    data:
      cycle: true
    state:
      - value: 'Off'
        color: rgb(255, 0, 0)
        icon: mdi:arrow-collapse-down
      - value: Auto
        color: rgb(0, 255, 0)
        icon: mdi:door-open
      - value: Manual
        color: rgb(128, 128, 128)
        icon: mdi:pause
    color_type: card
    styles:
      card:
        - height: 120px
      icon:
        - height: 50px
        - width: 50px
      name:
        - font-size: 18px
    show_name: true
    show_icon: true
    show_state: false
    show_label: true
  template_buttoncard_openclose_old:
    variables:
      var_name: LocationName
    label: |-
      [[[
        // door control entity_id variables
        const entity_id = entity.entity_id;
        const stateObj = states[entity_id];

        if (!stateObj) {
          return "Entity Not Found";
        }
        
        switch (stateObj.state) {
          case "Open":
            return "Open";
          case "Close":
            return "Closed";
          case "HoldOne":
          case "HoldTwo":
            return "Hold Position";
          default:
            return "Current State: " + stateObj.state;
        }
      ]]]
    tap_action:
      action: call-service
      service: input_select.select_next
      service_data:
        entity_id: '[[[ return entity.entity_id ]]]'
    data:
      cycle: true
    state:
      - value: Close
        color: rgb(255, 0, 0)
        icon: mdi:arrow-collapse-down
      - value: Open
        color: rgb(50, 100, 230)
        icon: mdi:door-open
      - value: HoldOne
        color: rgb(128, 128, 128)
        icon: mdi:pause
      - value: HoldTwo
        color: rgb(128, 128, 128)
        icon: mdi:pause
    color_type: card
    styles:
      card:
        - height: 120px
      icon:
        - height: 50px
        - width: 50px
      name:
        - font-size: 18px
    show_name: true
    show_icon: true
    show_state: false
    show_label: true
  template_buttoncard_openclose:
    variables:
      var_name: LocationName
      status_label: |-
        [[[
          // --- helpers -------------------------------------------------------------
          const slugify = (s) => (s ?? '')
            .toString().trim().toLowerCase()
            .replace(/\s+/g, '_')
            .replace(/[^a-z0-9_]/g, '')
            .replace(/_+/g, '_');

          const pdk = String(variables.paddock_var ?? '');
          const bay = String(variables.bay_var ?? '');

          // --- resolve devId from paddock array -----------------------------------
          const paddocks = hass.states['sensor.pwm_paddock_list']?.attributes?.paddocks || {};
          const arr = paddocks?.[pdk];
          let devId = '';
          let devRaw = '';

          if (Array.isArray(arr)) {
            for (const obj of arr) {
              if (!obj || typeof obj !== 'object') continue;
              for (const [k, v] of Object.entries(obj)) {
                // Match bay exactly or as prefix so "B-04" matches "B-04 Drain"
                const match = (k === bay) || k.toLowerCase().startsWith(bay.toLowerCase());
                if (!match) continue;
                devRaw = String(v?.device ?? '').trim();
                if (devRaw) devId = slugify(devRaw);
                break;
              }
              if (devRaw) break;
            }
          }

          // --- 1) UNSET if device unset or missing --------------------------------
          if (!devRaw || devRaw.toLowerCase() === 'unset') {
            return 'UNSET';
          }

          // --- 2) OFFLINE if online binary sensor is not online --------------------
          // If you know the exact pattern, you can construct:
          // const onlineEid = `binary_sensor.${devId}_${devId}_online`;
          // But because name parts can differ, we search for any binary_sensor.*online containing devId.

          const keys = Object.keys(hass.states || {});
          const onlineKeys = keys
            .filter(k => k.startsWith('binary_sensor.'))
            .filter(k => /(^|_)online($|_)/i.test(k));

          const reDev = new RegExp(devId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
          const candidates = onlineKeys.filter(k => reDev.test(k));

          // Choose the first candidate (or broaden if none found)
          const onlineEid = candidates[0] || null;

          // Define what counts as "online"
          const onlineStates = new Set(['on', 'connected', 'online', 'true', 'available']);
          const onlineState = onlineEid ? hass.states[onlineEid]?.state : undefined;
          const isOnline = onlineStates.has(String(onlineState ?? '').toLowerCase());

          if (!isOnline) {
            return 'OFFLINE';
          }

          // --- 3) Otherwise return the door entity's mapped state ------------------
          const stateObj = entity; // button-card provides current entity as 'entity'
          if (!stateObj) {
            return 'Entity Not Found';
          }

          const s = String(stateObj.state || '').toLowerCase();
          if (s === 'open') return 'Open';
          if (s === 'close' || s === 'closed') return 'Closed';
          if (['holdone','holdtwo','hold'].includes(s)) return 'Hold Position';
          return `Current State: ${stateObj.state}`;
        ]]]
    label: '[[[ return variables.status_label ]]]'
    tap_action:
      action: call-service
      service: input_select.select_next
      service_data:
        entity_id: '[[[ return entity.entity_id ]]]'
    data:
      cycle: true
    state:
      - value: Close
        color: rgb(255, 0, 0)
        icon: mdi:arrow-collapse-down
      - value: Open
        color: rgb(50, 100, 230)
        icon: mdi:door-open
      - value: HoldOne
        color: rgb(128, 128, 128)
        icon: mdi:pause
      - value: HoldTwo
        color: rgb(128, 128, 128)
        icon: mdi:pause
    color_type: card
    styles:
      card:
        - height: 120px
        - background-color: |-
            [[[
              const s = String(variables.status_label || '');

              // Grey if UNSET or OFFLINE
              if (s === 'UNSET' || s === 'OFFLINE') {
                return 'rgb(240, 240, 240)';
              }

              // Otherwise color by the entity's current state
              const es = String(entity?.state || '');
              if (es === 'Close')        return 'rgb(255, 0, 0)';
              if (es === 'Open')         return 'rgb(50, 100, 230)';
              if (es === 'HoldOne' || es === 'HoldTwo') return 'rgb(128, 128, 128)';

              // Default (no custom background)
              return '';
            ]]]
      icon:
        - height: 50px
        - width: 50px
        - color: |-
            [[[
              const s = String(variables.status_label || '');
              
              if (s === 'UNSET' || s === 'OFFLINE') {
                return 'rgb(0, 0, 0)';
              }
            ]]]
      name:
        - font-size: 18px
        - color: |-
            [[[
              const s = String(variables.status_label || '');
              
              if (s === 'UNSET' || s === 'OFFLINE') {
                return 'rgb(0, 0, 0)';
              }
            ]]]
      label:
        - color: |-
            [[[
              const s = String(variables.status_label || '');
              
              if (s === 'UNSET' || s === 'OFFLINE') {
                return 'rgb(0, 0, 0)';
              }
            ]]]
    show_name: true
    show_icon: true
    show_state: false
    show_label: true
  template_inputselect_automationstate:
    variables:
      var_name: LocationName
      paddock_var: test_field
    label: |
      [[[
        var entity_id = entity.entity_id;  // Access the entity ID
        if (!states[entity_id]) {
          return "Entity not found";  // Handle missing entity
        }
        return "\n" + states[entity_id].state;  // Add a blank line before the state
      ]]]
    tap_action:
      action: call-service
      service: input_select.select_next
      service_data:
        entity_id: '[[[ return entity.entity_id ]]]'
      confirmation:
        text: Are you sure?
    data:
      cycle: true
    state:
      - value: 'Off'
        color: rgb(128,128,128)
        icon: mdi:autorenew-off
      - value: Flush
        color: rgb(230, 119, 230)
        icon: mdi:auto-mode
      - value: Maintain
        color: rgb(29,171,222)
        icon: mdi:auto-mode
      - value: Drain
        color: rgb(222,171,29)
        icon: mdi:auto-download
      - value: Pond
        color: rgb(29,171,222)
        icon: mdi:waves
      - value: Saturate
        color: rgb(106,247,177)
        icon: mdi:water-sync
    color_type: card
    styles:
      icon:
        - height: 50px
        - width: 50px
      name:
        - font-size: 16px
        - white-space: normal
        - text-align: center
      state:
        - margin-top: 10px
        - text-align: center
      card:
        - height: 120px
        - display: |
            [[[
              const paddock = variables.paddock_var;
              const s = hass.states['sensor.pwm_paddock_list'];
              const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
              return item && item.automation_state_individual === true ? 'none' : null;
            ]]]
    show_name: true
    show_icon: true
    show_state: true
    show_label: false
  template_timer_on_off:
    state:
      - value: 'off'
        color: rgb(255,0, 0)
        icon: mdi:timer-off
      - value: 'on'
        color: rgb(0,255,0)
        icon: mdi:clock-start
    color_type: card
    styles:
      card:
        - height: 100px
      icon:
        - height: 30px
        - width: 30px
      name:
        - font-size: 12px
    tap_action:
      action: toggle
    hold_action:
      action: more-info
    show_name: true
    show_icon: true
    show_state: false
    show_label: true
    size: 30%
  template_paddockconfigbutton:
    variables:
      paddock_config_var: test_field
    name: Paddock Config
    icon: mdi:land-fields
    color: orange
    color_type: card
    styles:
      card:
        - height: 120px
    tap_action:
      action: fire-dom-event
      browser_mod:
        service: browser_mod.sequence
        data:
          sequence:
            - service: input_text.set_value
              data:
                entity_id: input_text.pwm_paddock_config_pointer
                value: '[[[ return variables.paddock_config_var ]]]'
            - service: browser_mod.delay
              data:
                time: 250
            - service: browser_mod.popup
              data:
                title: |-
                  [[[
                    const sel = variables.paddock_config_var || '';
                    const pretty = sel
                      .replace(/[_]+/g, ' ')       // underscores/hyphens to spaces
                      .replace(/\s+/g, ' ')         // collapse spaces
                      .trim()
                      .split(' ')
                      .join(' ');
                    return pretty.toUpperCase() + ' Config';
                  ]]]
                tag: paddockconfig
                icon: mdi:help-circle-outline
                icon_title: Help
                icon_close: false
                icon_action:
                  service: browser_mod.popup
                  data:
                    title: Paddock Config Help
                    tag: paddockhelp
                    icon: mdi:help-circle-outline
                    icon_close: false
                    dismiss_icon: mdi:chevron-left
                    content: >
                      ------ UPDATED HELP TEXT REQUIRED ------   This page
                      allows you to change what device is controlling a  
                      certain water control structure. Once confirming which
                      device   is in place at which structure, check to see if
                      the correct device is assigned it. If a change is required
                      tap on the bay's name, and a popup will appear allowing
                      you to change the device. Select the correct device in the
                      dropdown menu, and press save to confirm that change. This
                      will close this popup, where you can confirm the new set
                      device is correct. Pressing the back arrow on the "Set
                      Device" popup returns you to the paddock config page.

                      Press the back arrow to return to the paddock config page.
                content:
                  type: vertical-stack
                  cards:
                    - type: custom:button-card
                      template: template_titleblock
                      name: Time On Water
                    - type: custom:auto-entities
                      card:
                        type: custom:layout-card
                        layout_type: custom:grid-layout
                      filter:
                        template: >-
                          {% set pdk_sel =
                          states('input_text.pwm_paddock_config_pointer') %} {%
                          set data = state_attr('sensor.pwm_paddock_list',
                          'paddocks') | default({}, true) %}

                          {% set row = namespace(cards=[]) %}

                          {% set bays = data[pdk_sel] 
                            | rejectattr('enabled', 'defined')
                            | rejectattr('automation_state_individual', 'defined')
                            | default([], true) 
                            | list %} 

                          {% for b in bays %}
                            {% set bay_name = (b | list | first) %}
                            {% if 'Drain' not in bay_name %}
                              {% set bay_key = bay_name | slugify %}
                              {% set time_on_water_entity = 'timer.' ~ pdk_sel ~ '_' ~ bay_key ~ '_flushtimeonwater' %}
                              {% set autostate_entity = 'input_select.'~ pdk_sel ~ '_' ~ bay_key ~ '_automation_state' %}
                              {% set state = states(time_on_water_entity) %}
                              {% set column = '1' if loop.index is odd else '2' %}

                              {% if state not in ['unknown', 'unavailable'] %}
                                {% if states(autostate_entity) == 'Flush' %}
                                  {% set timer_row = {
                                    "type": "custom:circular-timer-card",
                                    "entity": time_on_water_entity,
                                    "name": bay_name ~ " Time On",
                                    "bins": "36",
                                    "direction": "countdown",
                                    "layout": "circular",
                                    "color": [
                                      "#1e7843",
                                      "#a9bdbb",
                                      "#ee7256"
                                    ],
                                    "tap_action": { "action": "more-info" },
                                    "primary_info":"timer",
                                    "secondary_info_size": "20%",
                                    "view_layout": {
                                      "grid-column": column ~ " / span 1"
                                    }
                                  } %}
                                  {% set timer_row_f = {
                                    "type": "custom:circular-timer-card",
                                    "entity": time_on_water_entity

                                  } %}

                                  {% set row.cards = row.cards + [timer_row_f] %}
                                {% endif %}
                              {% endif %}
                            {% endif %}
                          {% endfor %}

                          {{ row.cards | to_json(pretty_print=true,
                          ensure_ascii=true) }}                          
                    - type: custom:button-card
                      template: template_titleblock
                      name: Water Depths
                    - type: custom:auto-entities
                      card:
                        type: vertical-stack
                      card_param: cards
                      filter:
                        template: >-
                          {% set pdk_sel =
                          states('input_text.pwm_paddock_config_pointer') %} {%
                          set data = state_attr('sensor.pwm_paddock_list',
                          'paddocks') | default({}, true) %}

                          {% set row = namespace(cards=[]) %}

                          {% set bays = data[pdk_sel] 
                            | rejectattr('enabled', 'defined')
                            | rejectattr('automation_state_individual', 'defined')
                            | default([], true) 
                            | list %}

                          {% for b in bays %}
                            {% set bay_name = (b | list | first) %}
                            {% if 'Drain' not in bay_name %}
                              {% set bay_key = bay_name | slugify %}
                              {% set min_entity = 'input_number.' ~ pdk_sel ~ '_' ~ bay_key ~ '_waterlevelmin' %}
                              {% set max_entity = 'input_number.' ~ pdk_sel ~ '_' ~ bay_key ~ '_waterlevelmax' %}
                              {% set min_state = states(min_entity) %}
                              {% set max_state = states(max_entity) %}

                              {% if min_state not in ['unknown', 'unavailable'] or max_state not in ['unknown', 'unavailable'] %}
                                {% set header_row = {
                                  "type": "custom:mushroom-title-card",
                                  "title": bay_name
                                } %}
                                
                                {% set min_row = {
                                  "type": "custom:mushroom-number-card",
                                  "entity": min_entity,
                                  "name": "Min Water Depth",
                                  "display_mode": "buttons"
                                } %}

                                {% set max_row = {
                                  "type": "custom:mushroom-number-card",
                                  "entity": max_entity,
                                  "name": "Max Water Depth",
                                  "display_mode": "buttons"
                                } %}
                                {% set levels_row = {
                                  "type": "horizontal-stack",
                                  "cards": [min_row, max_row]
                                } %}

                                {% set row.cards = row.cards + [header_row, levels_row] %}
                              {% endif %}
                            {% endif %}
                          {% endfor %}

                          {{ row.cards | to_json(pretty_print=true,
                          ensure_ascii=true) }}
                    - type: custom:button-card
                      template: template_titleblock
                      name: Bay Devices
                    - type: custom:auto-entities
                      card:
                        type: entities
                      filter:
                        template: >-
                          {% set pdk_list =
                          state_attr('sensor.pwm_paddock_list', 'paddocks') |
                          default({}, true) %}   {# gets the data from the
                          paddock list json file #}   {% set pdk_sel  =
                          states('input_text.pwm_paddock_config_pointer') %}  
                          {# finds what paddock is selected #}    {% set
                          bays     = pdk_list[pdk_sel] 
                            | rejectattr('enabled', 'defined') 
                            | rejectattr('automation_state_individual', 'defined') 
                            | default([], true) %}

                          {# generates list of bays (and their devices) from
                          selected paddock #}    {% set out      =
                          namespace(list=[]) %}    {# output list #}  {% for bay
                          in bays %}    {# loop through generated bay list (bay
                          is variable to call inside loop for current bay being
                          looped in) #}
                            {% set bay_name = (bay | list | first) %} {# name of current bay #}
                            {% set bay_dev  = bay[bay_name] | default({}, true) %} {# get bay #}
                            {% set device   = bay_dev.device | default('unset') %} {# device for current bay #}
                            {% set dev_id   = device_id(device | slugify | replace('_', '-') | upper) | default('unset') %}
                            {% set is_set   = device not in ['unset', 'none'] %} {# device is 'unset' when not configured or newly generated #}
                            {% set colour   = 'green' if is_set else 'red' %} {# set colour for icon, red if device is unset #}
                            
                            {% set pdk_slug = pdk_sel | slugify %}
                            {% set bay_slug = bay_name | slugify %}
                            
                            {# get list of entities for current bay, filtering out everything aside from water depth offset #}
                            {% set bay_ents = states
                              | selectattr('entity_id', 'search', pdk_slug) 
                              | selectattr('entity_id', 'search', bay_slug)
                              | selectattr('entity_id', 'search', 'water')
                              | rejectattr('entity_id', 'search', 'flushtimeonewater')
                              | selectattr('entity_id', 'search', 'offset|depth')
                              | list %} 
                            
                            {# generate cards for device congig popup #}
                            {% set deviceid = bay[bay_name]['device'] | default('unset', true) %}

                            {% set dev_slug = deviceid | slugify %}
                            {% set title = deviceid | upper | replace('_', '-') %}

                            {% set use_open_flag   = 'input_boolean.' ~ dev_slug ~ '_flag_use_time_open' %}
                            {% set open_duration   = 'input_number.'  ~ dev_slug ~ '_duration_open_sec' %}
                            {% set use_close_flag  = 'input_boolean.' ~ dev_slug ~ '_flag_use_time_close' %}
                            {% set close_duration  = 'input_number.'  ~ dev_slug ~ '_duration_close_sec' %}
                            {% set max_close_dur   = 'input_number.'  ~ dev_slug ~ '_duration_full_close_sec' %}
                            
                            {% set offset_entity = 'input_number.' ~ pdk_slug ~ '_' ~ bay_slug ~ '_waterleveloffset' %}
                            {% set depth_entity = 'sensor.pwm_' ~ pdk_slug ~ '_' ~ bay_slug ~ '_water_depth' %}
                            {% set offset_state = states(offset_entity) %}
                            {% set depth_state = states(depth_entity) %}

                            {% set adv_bay = namespace(cards=[]) %}
                            {% if offset_state not in ['unknown', 'unavailable'] and depth_state not in ['unknown', 'unavailable'] %}
                              {% set adv_bay.cards = adv_bay.cards + [
                                {
                                  "type": "vertical-stack",
                                  "cards": [
                                    {
                                      "type": "custom:button-card",
                                      "template": "template_textblock",
                                      "name": "Bay Config"
                                    },
                                    {
                                      "type": "horizontal-stack",
                                      "cards": [
                                        {
                                          "type": "custom:mushroom-number-card",
                                          "entity": offset_entity,
                                          "name": "Water Level Offset",
                                          "display_mode": "buttons"
                                        },
                                        {
                                          "type": "custom:mushroom-entity-card",
                                          "entity": depth_entity,
                                          "name": "Current Depth",
                                          "fill_container": "true"
                                        }
                                      ]
                                    }
                                  ]
                                }
                              ] %}
                            {% endif %}
                            
                            {% set adv_dev = namespace(cards=[]) %}

                            {% set adv_dev.cards = adv_dev.cards + [
                              {
                                "type": "custom:button-card",
                                "template": "template_textblock",
                                "name": title ~ " Config"
                              }
                            ] %}
                            
                            {# two columns in a horizontal stack #}
                            {% set adv_dev.cards = adv_dev.cards + [
                              {
                                "type": "horizontal-stack",
                                "cards": [
                                  {
                                    "type": "vertical-stack",
                                    "cards": [
                                      {
                                        "type": "custom:button-card",
                                        "entity": use_open_flag,
                                        "name": "Use Open Timer",
                                        "template": "template_timer_on_off"
                                      },
                                      {
                                        "type": "custom:mushroom-number-card",
                                        "entity": open_duration,
                                        "name": "Open Timer Duration",
                                        "layout": "vertical",
                                        "display_mode": "buttons"
                                      }
                                    ]
                                  },
                                  {
                                    "type": "vertical-stack",
                                    "cards": [
                                      {
                                        "type": "custom:button-card",
                                        "entity": use_close_flag,
                                        "name": "Use Close Timer",
                                        "template": "template_timer_on_off"
                                      },
                                      {
                                        "type": "custom:mushroom-number-card",
                                        "entity": close_duration,
                                        "name": "Close Timer Duration",
                                        "layout": "vertical",
                                        "display_mode": "buttons"
                                      }
                                    ]
                                  }
                                ]
                              }
                            ] %}
                            
                            {# bottom number card #}
                            {% set adv_dev.cards = adv_dev.cards + [
                              {
                                "type": "custom:mushroom-number-card",
                                "entity": max_close_dur,
                                "name": "Max Duration",
                                "layout": "vertical",
                                "display_mode": "buttons"
                              }
                            ] %}

                            {# card_mod style for paddock config popup entities card rows, used to set icon colour dependent on if device is set or not #}
                            {% set style %}
                              :host {
                                --card-mod-icon-color: {{ colour }};
                                --paper-item-icon-color: {{ colour }};
                                --state-icon-active-color: {{ colour }};
                              } ha-icon { color: {{ colour }} !important; }
                            {% endset %}
                            
                            {# set row for current bay #}
                            {# json array as each row is complex, with popups on tap_action, icon_action and left_button_action #}

                            {# initial popups content shows a row for each bay of the paddock being configured, which the current device or 'unset' as the state #}
                            {# on tap action a form popup appears allowing user to change device for that bay, with the change finalising on 'save' button press #}
                            {# save closes popup returning to outer popup showing each bay #}
                            {# on left button press 'advanced', user can configure extra settings, currently bay level water depth offset #}
                            {# and device configuration options like open, close and max duration, use open time flag, etc #}

                            {# on icon press a help popup opens showing tips on how to use the system #}

                            {# refer to browser_mod HACS addon documentation to understand further #}
                            {% set row = {
                              "type": "custom:template-entity-row",
                              "name": bay_name,
                              "state": device,
                              "secondary": "Click to Change Device",
                              "icon": "mdi:land-rows-vertical" if is_set else "mdi:alert",
                              "card_mod": {
                                "style": style
                              },
                              "tap_action": {
                                "action": "fire-dom-event",
                                "browser_mod": {
                                  "service": "browser_mod.popup",
                                  "data": {
                                    "title": "Set Device for " ~ bay_name,
                                    "tag": "bayconfig",
                                    "right_button": "Save",
                                    "left_button": "Advanced",
                                    "content": [
                                      {
                                        "name": "new_device",
                                        "label": "Device",
                                        "default": dev_id if is_set else "",
                                        "selector": {
                                          "device": {
                                            "filter": {
                                              "integration": "esphome"
                                            }
                                          }
                                        }
                                      }
                                    ],
                                    "right_button_action": {
                                      "service": "script.pwm_update_bay_device",
                                      "data": {
                                        "paddock": pdk_sel,
                                        "bay": bay_name
                                      }
                                    },
                                    "right_button_variant": "brand",
                                    "right_button_appearance": "accent",
                                    "left_button_action": {
                                      "service": "browser_mod.popup",
                                        "data": {
                                          "title": bay_name ~ " Config",
                                          "tag": "advancedbayconfig",
                                          "icon": "mdi:help-circle-outline",
                                          "icon_close": "false",
                                          "icon_action": {
                                            "service": "browser_mod.popup",
                                            "data": {
                                              "title": "Help",
                                              "tag": "advancedconfighelp",
                                              "icon": "mdi:help-circle-outline",
                                              "dismiss_icon": "mdi:chevron-left",
                                              "icon_close": "false",
                                              "content": "INSERT HELP TEXT HERE"
                                            }
                                          },
                                          "content": {
                                            "type": "vertical-stack",
                                            "cards": [
                                              {
                                                "type": "vertical-stack",
                                                "cards": adv_bay.cards
                                              },
                                              {
                                                "type": "vertical-stack",
                                                "cards": adv_dev.cards
                                              }
                                            ]
                                          },
                                          "dismiss_icon": "mdi:chevron-left"
                                        }
                                    },
                                    "left_button_variant": "brand",
                                    "left_button_appearance": "plain",
                                    "left_button_close": "false",
                                    "dismissable": "false",
                                    "dismiss_icon": "mdi:chevron-left"
                                  }  
                                }
                              }
                            } %}
                            {% set out.list = out.list + [row] %} 
                            {# set output list to what the content of the list currently is plus the new row #}
                          {% endfor %}    {{ out.list | tojson(indent=2) }}  {#
                          output as json so auto-entities card reads and
                          generates rows properly #}
                    - type: custom:button-card
                      template: template_titleblock
                      name: Supply Channel
                    - type: custom:auto-entities
                      card:
                        type: vertical-stack
                      card_param: cards
                      filter:
                        template: >-
                          {% set pdk_sel  =
                          states('input_text.pwm_paddock_config_pointer') %}  {%
                          set supply_level_id = 'sensor.pwm_' ~ pdk_sel ~
                          '_supply_water_depth' %} {% set supply_offset_id =
                          'input_number.' ~ pdk_sel ~ '_supply_waterleveloffset'
                          %} 

                          {% set level_card = {
                            "type": "custom:mushroom-entity-card",
                            "entity": supply_level_id,
                            "name": "Current Depth",
                            "fill_container": "true"
                          } %}

                          {% set offset_card = {
                            "type": "custom:mushroom-number-card",
                            "entity": supply_offset_id,
                            "name": "Offset",
                            "display_mode": "buttons"
                          } %} 

                          {% set supply_row = {
                            "type": "horizontal-stack",
                            "cards": [level_card, offset_card]
                          } %}

                          {{ [supply_row] | to_json(pretty_print=true,
                          ensure_ascii=true) }}
                    - type: custom:auto-entities
                      card:
                        type: vertical-stack
                      card_param: cards
                      filter:
                        template: >-
                          {% set pdk_sel =
                          states('input_text.pwm_paddock_config_pointer') %} {%
                          set fcs_timer_entity =
                          'timer.'~pdk_sel~'_flushclosesupplytimer' %} {% set
                          fcs_timer_state = states(fcs_timer_entity) %} 

                          {{
                            [
                              {
                                "type": "vertical-stack",
                                "cards": [
                                  {
                                    "type": "custom:button-card",
                                    "template": "template_titleblock",
                                    "name": (pdk_sel | upper) ~ ' Flush Close Supply Timer'
                                  },
                                  {
                                    "type": "custom:circular-timer-card",
                                    "entity": fcs_timer_entity,
                                    "name": (pdk_sel | upper) ~ " Close Supply",
                                    "bins": "48",
                                    "direction": "countdown",
                                    "layout": "circle",
                                    "color": [
                                      "#1e7843",
                                      "#a9bdbb",
                                      "#ee7256"
                                    ],
                                    "secondary_info_size": "40%"
                                  }
                                ]
                              } 
                            ]
                          }}
views:
  - title: SW4-E
    path: sw4-e
    type: masonry
    cards:
      - type: picture-elements
        image: /api/image/serve/40028b37696208ff8d2724fe970f0ec2/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.spur_channel_water_depth
            style:
              top: 77%
              left: 39%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw4_e_b_01_water_depth
            style:
              top: 58%
              left: 36%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw4_e_b_02_water_depth
            style:
              top: 35%
              left: 37%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw4_e_b_03_water_depth
            style:
              top: 10%
              left: 39%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
      - type: custom:restriction-card
        restrictions:
          confirm: true
          block: null
        exemptions: null
        duration: 400
        card:
          type: vertical-stack
          cards:
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_titleblock
                  name: SPUR CHANNEL
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_buttoncard_openclose_old
                  entity: input_select.sw4_spur_actuator_state
                  name: SPUR CHANNEL
                - type: custom:button-card
                  template: template_channel_autostate
                  entity: input_select.sw4_spur_automation_state
                  name: Spur Automation
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: SW4-E - 8KPa Triger
          - type: custom:button-card
            template: template_inputselect_automationstate
            entity: input_select.sw4_e_automation_state
            name: SW4-E Automation State
            variables:
              paddock_var: sw4_e
          - type: custom:button-card
            template: template_titleblock
            name: SW4-E Inlet Controls
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw4_e_b_01_door_control
                name: B-01 SUPPLY
                variables:
                  paddock_var: sw4_e
                  bay_var: B-01
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw4_e_b_01_automation_state
                name: B-01 Automation State
                variables:
                  paddock_var: sw4_e
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw4_e_b_02_door_control
                name: B-02 SUPPLY
                variables:
                  paddock_var: sw4_e
                  bay_var: B-02
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw4_e_b_02_automation_state
                name: B-02 Automation State
                variables:
                  paddock_var: sw4_e
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw4_e_b_03_door_control
                name: B-03 SUPPLY
                variables:
                  paddock_var: sw4_e
                  bay_var: B-03
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw4_e_b_03_automation_state
                name: B-03 Automation State
                variables:
                  paddock_var: sw4_e
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:button-card
            template: template_buttoncard_openclose
            entity: input_select.sw4_e_drain_door_control
            name: B-03 DRAIN
            variables:
              paddock_var: sw4_e
              bay_var: B-03 Drain
      - type: custom:button-card
        template: template_paddockconfigbutton
        variables:
          paddock_config_var: sw4_e
      - type: button
        name: Extra Data
        icon: mdi:database
        show_name: true
        show_icon: true
        tap_action:
          action: navigate
          navigation_path: /farms-fields/sw4-e-extra
        hold_action:
          action: none
        icon_height: 80px
        show_state: true
    visible:
      - user: 85d777eb3f9a48339c59a83a9530125b
      - user: 61623853e7294d7e9d25da6f3655df64
      - user: 12b754841ac5445b9f0f8c34344d1b07
      - user: 3c3b8622f8214a8690cd346ea12fd76d
      - user: cbff2ae980fa4702be672ef1bb5e44ad
      - user: 747950f6125b46bd806b7ab4f4a490ba
      - user: 978d36a2ba4d4ca8b79033ee81a57f88
  - title: SW4-E Extra Data
    type: masonry
    path: sw4-e-extra
    subview: true
    cards:
      - type: custom:apexcharts-card
        header:
          show: true
          title: Soil Moisture B1 East 8Kpa Trigger
          show_states: true
          colorize_states: true
        graph_span: 72h
        now:
          show: true
          label: Now
        experimental:
          color_threshold: true
        yaxis:
          - min: -35
            max: 0
            decimals: 1
        series:
          - entity: sensor.sw4_e_b_01_soil_moisture_temp_comp
            name: Watermark Sensor (Temp Comp)
            type: line
            curve: smooth
            stroke_width: 4
            group_by:
              func: avg
              duration: 5min
            show:
              header_color_threshold: true
            color_threshold:
              - value: -999
                color: red
              - value: -35
                color: yellow
              - value: -8
                color: blue
      - type: custom:apexcharts-card
        header:
          show: true
          title: Soil Moisture B2 East 8 Kpa Trigger
          show_states: true
          colorize_states: true
        graph_span: 72h
        now:
          show: true
          label: Now
        experimental:
          color_threshold: true
        yaxis:
          - min: -35
            max: 0
            decimals: 1
        series:
          - entity: sensor.sw4_e_b_02_soil_moisture_temp_comp
            name: Watermark Sensor
            type: line
            curve: smooth
            stroke_width: 4
            group_by:
              func: avg
              duration: 5min
            show:
              header_color_threshold: true
            color_threshold:
              - value: -100
                color: red
              - value: -25
                color: yellow
              - value: -15
                color: blue
      - type: entities
        entities:
          - type: custom:template-entity-row
            entity: input_boolean.sw4_e_b_01_flushactive
            secondary: '{{ states(''input_select.sw4_e_b_01_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw4_e_b_02_flushactive
            secondary: '{{ states(''input_select.sw4_e_b_02_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw4_e_b_03_flushactive
            secondary: '{{ states(''input_select.sw4_e_b_03_automation_state'') }}'
  - title: SW1
    path: sw1-field
    cards:
      - type: picture-elements
        image: /api/image/serve/4156dd5ff5b1b17340875db9bdef7d07/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.sw6_b1_water_depth
            style:
              top: 48%
              left: 76%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.sw6_b2_water_depth
            style:
              top: 22%
              left: 69%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.sw6_b6_water_depth
            style:
              top: 20%
              left: 36%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.sw6_b5_water_depth
            style:
              top: 42%
              left: 41%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.sw6_b4_water_depth
            style:
              top: 20%
              left: 53.4%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.sw6_b3_water_depth
            style:
              top: 46%
              left: 59%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.riceboard_7_water_depth
            style:
              top: 70%
              left: 85%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.sw6_b7_water_depth
            style:
              top: 1%
              left: 9%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
        title: Add your field picture here
      - type: custom:restriction-card
        restrictions:
          confirm: true
          block: null
        exemptions: null
        duration: 600
        card:
          type: vertical-stack
          cards:
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_titleblock
                  name: Sheepwash 6
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_inputselect_automationstate
                  entity: input_select.automation_state
                  name: Test Field Automation State
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_titleblock
                  name: SW6 Inlet Controls
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_buttoncard_openclose
                  entity: input_select.test_01_position
                  name: B1 SUPPLY (30)
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_buttoncard_openclose
                  entity: input_select.test_01_position
                  name: B2 SUPPLY (34)
      - type: conditional
        conditions:
          - condition: state
            entity: input_boolean.sw5_bx01_flushactive
            state: 'on'
        card:
          type: vertical-stack
          cards:
            - type: custom:button-card
              template: template_titleblock
              name: SCHEDULED FLUSH TIME
            - type: custom:button-card
              entity: input_datetime.sw5_bx01_flushscheduledtime
              name: SET FLUSH START TIME
              state_color: false
              show_name: true
              show_icon: false
              show_state: true
              show_label: true
              styles:
                card:
                  - height: 120px
                icon:
                  - height: 50px
                  - width: 50px
                name:
                  - font-size: 18px
                  - color: rgb(255, 28, 21)
            - type: vertical-stack
              cards:
                - type: custom:button-card
                  template: template_titleblock
                  name: WATER DEPTH LIMITS
                - type: custom:mushroom-number-card
                  name: Min Water Depth
                  icon: mdi:water
                  icon_color: red
                  layout: horizontal
                  fill_container: true
                  icon_type: icon
                  display_mode: buttons
                  primary_info: state
                  secondary_info: name
                  tap_action:
                    action: none
                  hold_action:
                    action: none
                  double_tap_action:
                    action: none
                  entity: input_number.sw5_bx01_waterlevelmin
                  card_mod:
                    style: |
                      ha-card {
                        --ha-card-background: none;
                        --color: var(--primary-color);
                        min-height: 100px;

                              }

                               }
                - type: custom:mushroom-number-card
                  name: High Water Level
                  icon: mdi:arrow-oscillating-off
                  icon_color: blue
                  layout: horizontal
                  fill_container: true
                  icon_type: icon
                  display_mode: buttons
                  primary_info: state
                  secondary_info: name
                  tap_action:
                    action: none
                  hold_action:
                    action: none
                  double_tap_action:
                    action: none
                  entity: input_number.sw5_bx01_waterlevelmax
                  card_mod:
                    style: |
                      ha-card {
                        --ha-card-background: none
                        color: var(--primary-color);
                        min-height: 100px;
      - type: conditional
        conditions:
          - condition: state
            entity: input_select.sw5_bx01_automation_state
            state: Maintain Bays
        card:
          type: vertical-stack
          cards:
            - type: vertical-stack
              cards:
                - type: custom:button-card
                  template: template_titleblock
                  name: WATER DEPTH LIMITS
                - type: custom:mushroom-number-card
                  name: Low Water Depth
                  icon: mdi:water
                  icon_color: red
                  layout: horizontal
                  fill_container: true
                  icon_type: icon
                  display_mode: buttons
                  primary_info: state
                  secondary_info: name
                  tap_action:
                    action: none
                  hold_action:
                    action: none
                  double_tap_action:
                    action: none
                  entity: input_number.sw5_bx01_waterlevelmin
                  card_mod:
                    style: |
                      ha-card {
                        --ha-card-background: none;
                        --color: var(--primary-color);
                        min-height: 100px;

                              }

                               }
                - type: custom:mushroom-number-card
                  name: High Water Depth
                  icon: mdi:arrow-oscillating-off
                  icon_color: blue
                  layout: horizontal
                  fill_container: true
                  icon_type: icon
                  display_mode: buttons
                  primary_info: state
                  secondary_info: name
                  tap_action:
                    action: none
                  hold_action:
                    action: none
                  double_tap_action:
                    action: none
                  entity: input_number.sw5_bx01_waterlevelmax
                  card_mod:
                    style: |
                      ha-card {
                        --ha-card-background: none
                        color: var(--primary-color);
                        min-height: 100px;
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: navigate
          navigation_path: /farms-fields/sw1-field-extra
        icon: mdi:database
        hold_action:
          action: none
        name: Extra Data
        icon_height: 80px
        show_state: true
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: navigate
          navigation_path: /farms-fields/sw1-field-config
        icon: mdi:file-link
        hold_action:
          action: none
        name: Configuration
        icon_height: 80px
        show_state: false
    type: masonry
    visible: []
  - type: sections
    max_columns: 4
    title: SW1 Field Extra Data
    path: sw1-field-extra
    subview: true
    dense_section_placement: true
    sections:
      - type: grid
        cards:
          - type: heading
            heading: New section
    cards: []
  - title: SW4-W
    path: sw4-w
    type: masonry
    cards:
      - type: picture-elements
        image: /api/image/serve/c2b822e0a7ad3298a747a5b4dd970be9/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.spur_channel_water_depth
            style:
              top: 77%
              left: 35%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw4_w_b_01_water_depth
            style:
              top: 58%
              left: 25%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw4_w_b_02_water_depth
            style:
              top: 34%
              left: 27%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw4_w_b_03_water_depth
            style:
              top: 08%
              left: 30%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
      - type: custom:restriction-card
        restrictions:
          confirm: true
          block: null
        exemptions: null
        duration: 400
        card:
          type: vertical-stack
          cards:
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_titleblock
                  name: SPUR CHANNEL
            - type: horizontal-stack
              cards:
                - type: custom:button-card
                  template: template_buttoncard_openclose_old
                  entity: input_select.sw4_spur_actuator_state
                  name: SPUR CHANNEL
                - type: custom:button-card
                  template: template_channel_autostate
                  entity: input_select.sw4_spur_automation_state
                  name: Spur Automation
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: SW4-W - 15kPa Trigger
          - type: custom:button-card
            template: template_inputselect_automationstate
            entity: input_select.sw4_w_automation_state
            name: SW4-W Automation State
            variables:
              paddock_var: sw4_w
          - type: custom:button-card
            template: template_titleblock
            name: SW4-W Inlet Controls
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw4_w_b_01_door_control
                name: B-01 SUPPLY
                variables:
                  paddock_var: sw4_w
                  bay_var: B-01
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw4_w_b_01_automation_state
                name: B-01 Automation State
                variables:
                  paddock_var: sw4_w
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw4_w_b_02_door_control
                name: B-02 SUPPLY
                variables:
                  paddock_var: sw4_w
                  bay_var: B-02
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw4_w_b_02_automation_state
                name: B-02 Automation State
                variables:
                  paddock_var: sw4_w
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw4_w_b_03_door_control
                name: B-03 SUPPLY
                variables:
                  paddock_var: sw4_w
                  bay_var: B-03
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw4_w_b_03_automation_state
                name: B-03 Automation State
                variables:
                  paddock_var: sw4_w
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:button-card
            template: template_buttoncard_openclose
            entity: input_select.sw4_w_drain_door_control
            name: B-03 DRAIN
            variables:
              paddock_var: sw4_w
              bay_var: B-03 Drain
      - type: custom:button-card
        template: template_paddockconfigbutton
        variables:
          paddock_config_var: sw4_w
      - type: button
        name: Extra Data
        icon: mdi:database
        show_name: true
        show_icon: true
        tap_action:
          action: navigate
          navigation_path: /farms-fields/sw4-w-extra
        hold_action:
          action: none
        icon_height: 80px
        show_state: true
  - title: SW4-W Extra Data
    type: masonry
    path: sw4-w-extra
    subview: true
    cards:
      - type: custom:apexcharts-card
        header:
          show: true
          title: Soil Moisture B1 West 15 Kpa Trigger
          show_states: true
          colorize_states: true
        graph_span: 72h
        now:
          show: true
          label: Now
        experimental:
          color_threshold: true
        yaxis:
          - min: -35
            max: 0
            decimals: 1
        series:
          - entity: sensor.sw4_w_b_01_soil_moisture_temp_comp
            name: Watermark Sensor
            type: line
            curve: smooth
            stroke_width: 4
            group_by:
              func: avg
              duration: 5min
            show:
              header_color_threshold: true
            color_threshold:
              - value: -100
                color: red
              - value: -25
                color: yellow
              - value: -8
                color: blue
      - type: custom:apexcharts-card
        header:
          show: true
          title: Soil Moisture B2 West 15 Kpa Trigger
          show_states: true
          colorize_states: true
        graph_span: 72h
        now:
          show: true
          label: Now
        experimental:
          color_threshold: true
        yaxis:
          - min: -40
            max: 0
            decimals: 1
        series:
          - entity: sensor.sw4_w_b_02_soil_moisture_temp_comp
            name: Watermark Sensor
            type: line
            curve: smooth
            stroke_width: 4
            group_by:
              func: avg
              duration: 5min
            show:
              header_color_threshold: true
            color_threshold:
              - value: -100
                color: red
              - value: -25
                color: yellow
              - value: -15
                color: blue
      - type: custom:apexcharts-card
        header:
          show: true
          title: Soil Moisture B2 West
          show_states: true
          colorize_states: true
        graph_span: 48h
        now:
          show: true
          label: Now
        experimental:
          color_threshold: true
        yaxis:
          - min: 0
            max: 100
            decimals: 0
        series:
          - entity: sensor.ecowittgateway_5_soil_moisture_1
            name: Water Content Sensor
            type: line
            curve: smooth
            stroke_width: 4
            group_by:
              func: avg
              duration: 5min
            show:
              header_color_threshold: true
            color_threshold:
              - value: 0
                color: brown
              - value: 25
                color: red
              - value: 40
                color: orange
              - value: 55
                color: green
              - value: 70
                color: blue
      - type: custom:apexcharts-card
        header:
          show: true
          title: Soil Moisture B3 West
          show_states: true
          colorize_states: true
        graph_span: 72h
        now:
          show: true
          label: Now
        experimental:
          color_threshold: true
        yaxis:
          - min: -40
            max: 0
            decimals: 1
        series:
          - entity: sensor.sw4_w_b_03_soil_moisture_temp_comp
            name: Watermark Sensor
            type: line
            curve: smooth
            stroke_width: 4
            group_by:
              func: avg
              duration: 5min
            show:
              header_color_threshold: true
            color_threshold:
              - value: -999
                color: brown
              - value: -35
                color: red
              - value: -25
                color: orange
              - value: -15
                color: green
              - value: -8
                color: blue
      - type: entities
        entities:
          - type: custom:template-entity-row
            entity: input_boolean.sw4_w_b_01_flushactive
            secondary: '{{ states(''input_select.sw4_w_b_01_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw4_w_b_02_flushactive
            secondary: '{{ states(''input_select.sw4_w_b_02_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw4_w_b_03_flushactive
            secondary: '{{ states(''input_select.sw4_w_b_03_automation_state'') }}'
  - title: SW5
    path: sw5
    type: masonry
    cards:
      - type: picture-elements
        image: /api/image/serve/dd915a365a0ce2d7c597a89b6f0b922e/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw5_supply_water_depth
            style:
              top: 20%
              left: 80%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw5_b_01_water_depth
            style:
              top: 50%
              left: 72%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw5_b_02_water_depth
            style:
              top: 37%
              left: 54%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw5_b_03_water_depth
            style:
              top: 50%
              left: 36%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw5_b_04_water_depth
            style:
              top: 31%
              left: 22%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_sw5_b_05_water_depth
            style:
              top: 50%
              left: 7%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(0.8)
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: SW5
          - type: custom:button-card
            template: template_inputselect_automationstate
            entity: input_select.sw5_automation_state
            name: SW5 Automation State
            variables:
              paddock_var: sw5
          - type: custom:button-card
            template: template_titleblock
            name: SW5 Inlet Controls
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw5_b_01_door_control
                name: B-01 SUPPLY
                variables:
                  paddock_var: sw5
                  bay_var: B-01
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw5_b_01_automation_state
                name: B-01 Automation State
                variables:
                  paddock_var: sw5
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw5_b_02_door_control
                name: B-02 SUPPLY
                variables:
                  paddock_var: sw5
                  bay_var: B-02
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw5_b_02_automation_state
                name: B-02 Automation State
                variables:
                  paddock_var: sw5
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw5_b_03_door_control
                name: B-03 SUPPLY
                variables:
                  paddock_var: sw5
                  bay_var: B-03
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw5_b_03_automation_state
                name: B-03 Automation State
                variables:
                  paddock_var: sw5
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw5_b_04_door_control
                name: B-04 SUPPLY
                variables:
                  paddock_var: sw5
                  bay_var: B-04
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw5_b_04_automation_state
                name: B-04 Automation State
                variables:
                  paddock_var: sw5
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.sw5_b_05_door_control
                name: B-05 SUPPLY
                variables:
                  paddock_var: sw5
                  bay_var: B-05
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.sw5_b_05_automation_state
                name: B-05 Automation State
                variables:
                  paddock_var: sw5
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:button-card
            template: template_buttoncard_openclose
            entity: input_select.sw5_drain_door_control
            name: B-05 DRAIN
            variables:
              paddock_var: sw5
              bay_var: B-05 Drain
      - type: custom:button-card
        template: template_paddockconfigbutton
        variables:
          paddock_config_var: sw5
      - type: button
        name: Extra Data
        icon: mdi:database
        show_name: true
        show_icon: true
        tap_action:
          action: navigate
          navigation_path: /farms-fields/sw5-extra
        hold_action:
          action: none
        icon_height: 80px
        show_state: true
  - title: SW5 Extra Data
    type: masonry
    path: sw5-extra
    subview: true
    cards:
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: Soil Moistures and Temps
          - type: custom:apexcharts-card
            header:
              show: true
              title: Soil Moisture - VWC
              show_states: true
              colorize_states: true
            series:
              - entity: sensor.ecowittgateway_7_soil_moisture_1
                name: B-02
              - entity: sensor.ecowittgateway_7_soil_moisture_2
                name: B-03
              - entity: sensor.ecowittgateway_6_soil_moisture_4
                name: B-04
              - entity: sensor.ecowittgateway_6_soil_moisture_3
                name: B-05
            apex_config:
              legend:
                show: false
          - type: custom:apexcharts-card
            header:
              show: true
              title: Soil Temp
              show_states: true
              colorize_states: true
            series:
              - entity: sensor.gw1200c_soil_temperature_1
                name: B-04
            apex_config:
              legend:
                show: false
      - type: entities
        entities:
          - type: custom:template-entity-row
            entity: input_boolean.sw5_b_01_flushactive
            secondary: '{{ states(''input_select.sw5_b_01_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw5_b_02_flushactive
            secondary: '{{ states(''input_select.sw5_b_02_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw5_b_03_flushactive
            secondary: '{{ states(''input_select.sw5_b_03_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw5_b_04_flushactive
            secondary: '{{ states(''input_select.sw5_b_04_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.sw5_b_05_flushactive
            secondary: '{{ states(''input_select.sw5_b_05_automation_state'') }}'
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: Scaled Soil Moistures
          - type: gauge
            entity: sensor.sw5_b2_vwc_normalised
            name: B-02 Soil Moisture
            needle: true
            segments:
              - from: 0
                color: '#db4437'
              - from: 30
                color: '#ffa600'
              - from: 60
                color: '#43a047'
              - from: 90
                color: '#0040FF'
          - type: gauge
            entity: sensor.sw5_b3_vwc_normalised
            name: B-03 Soil Moisture
            needle: true
            segments:
              - from: 0
                color: '#db4437'
              - from: 30
                color: '#ffa600'
              - from: 60
                color: '#43a047'
              - from: 90
                color: '#0040FF'
          - type: horizontal-stack
            cards:
              - type: gauge
                entity: sensor.sw5_b5_vwc_normalised
                name: B-04 Soil Moisture
                needle: true
                segments:
                  - from: 0
                    color: '#db4437'
                  - from: 30
                    color: '#ffa600'
                  - from: 60
                    color: '#43a047'
                  - from: 90
                    color: '#0040FF'
        visibility:
          - condition: user
            users:
              - cbff2ae980fa4702be672ef1bb5e44ad
              - 61623853e7294d7e9d25da6f3655df64
              - 3c3b8622f8214a8690cd346ea12fd76d
              - 747950f6125b46bd806b7ab4f4a490ba
  - title: W17
    path: w17
    type: masonry
    cards:
      - type: picture-elements
        image: /api/image/serve/c8732da46e614b0299c23840406802ac/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w17_supply_water_depth
            style:
              top: 75%
              left: 55%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w17_b_01_water_depth
            style:
              top: 25%
              left: 70%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w17_b_02_water_depth
            style:
              top: 50%
              left: 59%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w17_b_03_water_depth
            style:
              top: 25%
              left: 48%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w17_b_04_water_depth
            style:
              top: 50%
              left: 37%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w17_b_05_water_depth
            style:
              top: 25%
              left: 20%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.ward_pit_depth_adjusted
            style:
              top: 70%
              left: 85%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              '--label-badge-background-color': '#2196F3'
              transform: scale(0.8)
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: W17
          - type: custom:button-card
            template: template_inputselect_automationstate
            entity: input_select.w17_automation_state
            name: W17 Automation State
            variables:
              paddock_var: w17
          - type: custom:button-card
            template: template_titleblock
            name: W17 SPUR CHANNEL
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose_old
                entity: input_select.rb_002_actuator_state
                name: Ward 17 Spur
              - type: custom:button-card
                template: template_channel_autostate
                entity: input_select.ward_17_spur_channel
                name: Ward 17 Spur Mode
          - type: custom:button-card
            template: template_titleblock
            name: W17 Inlet Controls
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: horizontal-stack
                cards:
                  - type: custom:button-card
                    template: template_buttoncard_openclose
                    entity: input_select.w17_b_01_door_control
                    name: B-01 SUPPLY
                    variables:
                      paddock_var: w17
                      bay_var: B-01
                  - type: custom:button-card
                    template: template_buttoncard_openclose
                    entity: input_select.w17_b_01_nml_door_control
                    name: NML DRAIN
                    variables:
                      paddock_var: w17
                      bay_var: B-01 NML
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w17_b_01_automation_state
                name: B-01 Automation State
                variables:
                  paddock_var: w17
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w17_b_02_door_control
                name: B-02 SUPPLY
                variables:
                  paddock_var: w17
                  bay_var: B-02
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w17_b_02_automation_state
                name: B-02 Automation State
                variables:
                  paddock_var: w17
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: horizontal-stack
                cards:
                  - type: custom:button-card
                    template: template_buttoncard_openclose
                    entity: input_select.w17_b_03_door_control
                    name: B-03 SUPPLY
                    variables:
                      paddock_var: w17
                      bay_var: B-03
                  - type: custom:button-card
                    template: template_buttoncard_openclose
                    entity: input_select.w17_b_03_channel_supply_door_control
                    name: B-03 Channel SUPPLY
                    variables:
                      paddock_var: w17
                      bay_var: B-03 Channel Supply
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w17_b_03_automation_state
                name: B-03 Automation State
                variables:
                  paddock_var: w17
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w17_b_04_door_control
                name: B-04 SUPPLY
                variables:
                  paddock_var: w17
                  bay_var: B-04
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w17_b_04_automation_state
                name: B-04 Automation State
                variables:
                  paddock_var: w17
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w17_b_05_door_control
                name: B-05 SUPPLY
                variables:
                  paddock_var: w17
                  bay_var: B-05
          - type: custom:button-card
            template: template_buttoncard_openclose
            entity: input_select.w17_drain_door_control
            name: B-05 DRAIN
            variables:
              paddock_var: w17
              bay_var: B-05 Drain
      - type: custom:button-card
        template: template_paddockconfigbutton
        variables:
          paddock_config_var: w17
      - type: button
        name: Extra Data
        icon: mdi:database
        show_name: true
        show_icon: true
        tap_action:
          action: navigate
          navigation_path: /farms-fields/w17-extra
        hold_action:
          action: none
        icon_height: 80px
        show_state: true
  - title: W17 Extra Data
    type: masonry
    path: w17-extra
    subview: true
    cards:
      - type: entities
        entities:
          - type: custom:template-entity-row
            entity: input_boolean.w17_b_01_flushactive
            secondary: '{{ states(''input_select.w17_b_01_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.w17_b_02_flushactive
            secondary: '{{ states(''input_select.w17_b_02_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.w17_b_03_flushactive
            secondary: '{{ states(''input_select.w17_b_03_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.w17_b_04_flushactive
            secondary: '{{ states(''input_select.w17_b_04_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.w17_b_05_flushactive
            secondary: '{{ states(''input_select.w17_b_05_automation_state'') }}'
  - title: W18
    path: w18
    type: masonry
    cards:
      - type: picture-elements
        image: /api/image/serve/3d93668d86246b8e387c1449b373eea8/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w19_supply_water_depth
            style:
              top: 72%
              left: 80%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w18_b_01_water_depth
            style:
              top: 35%
              left: 75%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w18_b_02_water_depth
            style:
              top: 60%
              left: 55%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w18_b_03_water_depth
            style:
              top: 35%
              left: 38%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w18_b_04_water_depth
            style:
              top: 55%
              left: 25%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w18_b_05_water_depth
            style:
              top: 35%
              left: 10%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 10px
              transform: scale(1)
          - type: state-badge
            entity: sensor.ward_pit_depth_adjusted
            tap_action:
              action: more-info
            style:
              top: 85%
              left: 25%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              '--label-badge-background-color': '#2196F3'
              transform: scale(0.8)
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: W18
          - type: custom:button-card
            template: template_inputselect_automationstate
            entity: input_select.w18_automation_state
            name: W18 Automation State
            variables:
              paddock_var: w18
          - type: custom:button-card
            template: template_titleblock
            name: W18 Inlet Controls
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w18_b_01_door_control
                name: B-01 SUPPLY
                variables:
                  paddock_var: w18
                  bay_var: B-01
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w18_b_01_automation_state
                name: B-01 Automation State
                variables:
                  paddock_var: w18
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w18_b_02_door_control
                name: B-02 SUPPLY
                variables:
                  paddock_var: w18
                  bay_var: B-02
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w18_b_02_automation_state
                name: B-02 Automation State
                variables:
                  paddock_var: w18
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w18_b_03_door_control
                name: B-03 SUPPLY
                variables:
                  paddock_var: w18
                  bay_var: B-03
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w18_b_03_automation_state
                name: B-03 Automation State
                variables:
                  paddock_var: w18
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w18_b_04_door_control
                name: B-04 SUPPLY
                variables:
                  paddock_var: w18
                  bay_var: B-04
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w18_b_04_automation_state
                name: B-04 Automation State
                variables:
                  paddock_var: w18
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w18_b_05_door_control
                name: B-05 SUPPLY
                variables:
                  paddock_var: w18
                  bay_var: B-05
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w18_b_05_automation_state
                name: B-05 Automation State
                variables:
                  paddock_var: w18
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:button-card
            template: template_buttoncard_openclose
            entity: input_select.w18_drain_door_control
            name: B-05 DRAIN
            variables:
              paddock_var: w18
              bay_var: B-05 Drain
      - type: custom:button-card
        template: template_paddockconfigbutton
        variables:
          paddock_config_var: w18
      - type: button
        name: Extra Data
        icon: mdi:database
        show_name: true
        show_icon: true
        tap_action:
          action: navigate
          navigation_path: /farms-fields/w18-extra
        hold_action:
          action: none
        icon_height: 80px
        show_state: true
  - title: W18 Extra Data
    type: masonry
    path: w18-extra
    subview: true
    cards:
      - type: vertical-stack
        cards:
          - type: entities
            entities:
              - type: custom:template-entity-row
                entity: input_boolean.w18_b_01_flushactive
                secondary: '{{ states(''input_select.w18_b_01_automation_state'') }}'
              - type: custom:template-entity-row
                entity: input_boolean.w18_b_02_flushactive
                secondary: '{{ states(''input_select.w18_b_02_automation_state'') }}'
              - type: custom:template-entity-row
                entity: input_boolean.w18_b_03_flushactive
                secondary: '{{ states(''input_select.w18_b_03_automation_state'') }}'
              - type: custom:template-entity-row
                entity: input_boolean.w18_b_04_flushactive
                secondary: '{{ states(''input_select.w18_b_04_automation_state'') }}'
              - type: custom:template-entity-row
                entity: input_boolean.w18_b_05_flushactive
                secondary: '{{ states(''input_select.w18_b_05_automation_state'') }}'
          - type: custom:apexcharts-card
            header:
              show: true
              title: ApexCharts-Card
              show_states: true
              colorize_states: true
            series:
              - entity: sensor.pwm_w18_b_01_water_depth
              - entity: sensor.pwm_w18_b_02_water_depth
              - entity: sensor.pwm_w18_b_03_water_depth
              - entity: sensor.pwm_w18_b_04_water_depth
              - entity: sensor.pwm_w18_b_05_water_depth
            apex_config:
              legend:
                show: false
  - title: W19
    path: w19
    type: masonry
    cards:
      - type: picture-elements
        image: /api/image/serve/a85fbcf2420578cffb090b5c06a6bb62/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w19_supply_water_depth
            style:
              top: 0%
              left: 75%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w19_b_01_water_depth
            style:
              top: 50%
              left: 62%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w19_b_02_water_depth
            style:
              top: 20%
              left: 50%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w19_b_03_water_depth
            style:
              top: 50%
              left: 36%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_w19_b_04_water_depth
            style:
              top: 20%
              left: 25%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.8)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.ward_pit_depth_adjusted
            style:
              top: 10%
              left: 5%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              '--label-badge-background-color': '#2196F3'
              transform: scale(0.8)
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: W19
          - type: custom:button-card
            template: template_inputselect_automationstate
            entity: input_select.w19_automation_state
            name: W19 Automation State
            variables:
              paddock_var: w19
          - type: custom:button-card
            template: template_titleblock
            name: W19 Inlet Controls
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w19_b_01_door_control
                name: B-01 SUPPLY
                variables:
                  paddock_var: w19
                  bay_var: B-01
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w19_b_01_automation_state
                name: B-01 Automation State
                variables:
                  paddock_var: w19
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w19_b_02_door_control
                name: B-02 SUPPLY
                variables:
                  paddock_var: w19
                  bay_var: B-02
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w19_b_02_automation_state
                name: B-02 Automation State
                variables:
                  paddock_var: w19
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w19_b_03_door_control
                name: B-03 SUPPLY
                variables:
                  paddock_var: w19
                  bay_var: B-03
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w19_b_03_automation_state
                name: B-03 Automation State
                variables:
                  paddock_var: w19
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:layout-card
            layout_type: custom:horizontal-layout
            layout:
              margin: 0px 0px 0px 0px
              padding: 0px 0px 0px 0px
              card_margin: 0px 0px 0px 0px
            cards:
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.w19_b_04_door_control
                name: B-04 SUPPLY
                variables:
                  paddock_var: w19
                  bay_var: B-04
              - type: custom:button-card
                template: template_inputselect_automationstate
                entity: input_select.w19_b_04_automation_state
                name: B-04 Automation State
                variables:
                  paddock_var: w19
                styles:
                  card:
                    - display: |
                        [[[
                          const paddock = variables.paddock_var;
                          const s = hass.states['sensor.pwm_paddock_list'];
                          const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                          return item && item.automation_state_individual === false ? 'none' : null;
                        ]]]
          - type: custom:button-card
            template: template_buttoncard_openclose
            entity: input_select.w19_drain_door_control
            name: B-04 DRAIN
            variables:
              paddock_var: w19
              bay_var: B-04 Drain
      - type: custom:button-card
        template: template_paddockconfigbutton
        variables:
          paddock_config_var: w19
      - type: button
        name: Extra Data
        icon: mdi:database
        show_name: true
        show_icon: true
        tap_action:
          action: navigate
          navigation_path: /farms-fields/w19-extra
        hold_action:
          action: none
        icon_height: 80px
        show_state: true
  - title: W19 Extra Data
    type: masonry
    path: w19-extra
    subview: true
    cards:
      - type: entities
        entities:
          - type: custom:template-entity-row
            entity: input_boolean.w19_b_01_flushactive
            secondary: '{{ states(''input_select.w19_b_01_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.w19_b_02_flushactive
            secondary: '{{ states(''input_select.w19_b_02_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.w19_b_03_flushactive
            secondary: '{{ states(''input_select.w19_b_03_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.w19_b_04_flushactive
            secondary: '{{ states(''input_select.w19_b_04_automation_state'') }}'
  - title: Test Field
    path: test-field
    type: masonry
    cards:
      - type: picture-elements
        image: /api/image/serve/4156dd5ff5b1b17340875db9bdef7d07/512x512
        elements:
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_test_field_b_01_water_depth
            style:
              top: 48%
              left: 76%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_test_field_b_02_water_depth
            style:
              top: 22%
              left: 69%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_test_field_b_03_water_depth
            style:
              top: 20%
              left: 36%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
          - type: state-badge
            tap_action:
              action: more-info
            entity: sensor.pwm_test_field_b_04_water_depth
            style:
              top: 42%
              left: 41%
              '--ha-label-badge-title-font-size': 0em
              '--paper-font-subhead_-_font-size': 8px
              transform: scale(0.6)
        title: Add your field picture here
      - type: vertical-stack
        cards:
          - type: custom:button-card
            template: template_titleblock
            name: Test Field
          - type: custom:button-card
            template: template_inputselect_automationstate
            entity: input_select.test_field_automation_state
            name: Test Field Automation State
            variables:
              paddock_var: test_field
          - type: custom:button-card
            template: template_titleblock
            name: Test Field Inlet Controls
          - type: vertical-stack
            cards:
              - type: custom:layout-card
                layout_type: custom:horizontal-layout
                layout:
                  margin: 0px 0px 0px 0px
                  padding: 0px 0px 0px 0px
                  card_margin: 0px 0px 0px 0px
                cards:
                  - type: custom:button-card
                    template: template_buttoncard_openclose
                    entity: input_select.test_field_b_01_door_control
                    name: B-01 SUPPLY
                    variables:
                      paddock_var: test_field
                      bay_var: B-01
                  - type: custom:button-card
                    template: template_inputselect_automationstate
                    entity: input_select.test_field_b_01_automation_state
                    name: B-01 Automation State
                    variables:
                      paddock_var: test_field
                    styles:
                      card:
                        - display: |
                            [[[
                              const paddock = variables.paddock_var;
                              const s = hass.states['sensor.pwm_paddock_list'];
                              const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                              return item && item.automation_state_individual === false ? 'none' : null;
                            ]]]
              - type: custom:layout-card
                layout_type: custom:horizontal-layout
                layout:
                  margin: 0px 0px 0px 0px
                  padding: 0px 0px 0px 0px
                  card_margin: 0px 0px 0px 0px
                cards:
                  - type: custom:button-card
                    entity: input_select.test_field_b_02_door_control
                    name: B-02 SUPPLY
                    color_type: card
                    state:
                      - value: Close
                        color: rgb(255, 0, 0)
                        icon: mdi:arrow-collapse-down
                      - value: Open
                        color: rgb(50, 100, 230)
                        icon: mdi:door-open
                      - value: HoldOne
                        color: rgb(128, 128, 128)
                        icon: mdi:pause
                      - value: HoldTwo
                        color: rgb(128, 128, 128)
                        icon: mdi:pause
                    tap_action:
                      action: call-service
                      service: input_select.select_next
                      service_data:
                        entity_id: '[[[ return entity.entity_id ]]]'
                    hold_action:
                      action: fire-dom-event
                      browser_mod:
                        service: browser_mod.more_info
                        data:
                          entity: valve.rb_003_rb_003_actuator_1
                    styles:
                      card:
                        - height: 120px
                        - background-color: |-
                            [[[
                              const s = String(variables.status_label || '');

                              // Grey if UNSET or OFFLINE
                              if (s === 'UNSET' || s === 'OFFLINE') {
                                return 'rgb(240, 240, 240)';
                              }

                              // Otherwise color by the entity's current state
                              const es = String(entity?.state || '');
                              if (es === 'Close')        return 'rgb(255, 0, 0)';
                              if (es === 'Open')         return 'rgb(50, 100, 230)';
                              if (es === 'HoldOne' || es === 'HoldTwo') return 'rgb(128, 128, 128)';

                              // Default (no custom background)
                              return '';
                            ]]]
                      icon:
                        - height: 50px
                        - width: 50px
                        - color: |-
                            [[[
                              const s = String(variables.status_label || '');
                              
                              if (s === 'UNSET' || s === 'OFFLINE') {
                                return 'rgb(0, 0, 0)';
                              }
                            ]]]
                      name:
                        - font-size: 18px
                        - color: |-
                            [[[
                              const s = String(variables.status_label || '');
                              
                              if (s === 'UNSET' || s === 'OFFLINE') {
                                return 'rgb(0, 0, 0)';
                              }
                            ]]]
                      label:
                        - color: |-
                            [[[
                              const s = String(variables.status_label || '');
                              
                              if (s === 'UNSET' || s === 'OFFLINE') {
                                return 'rgb(0, 0, 0)';
                              }
                            ]]]
                    variables:
                      var_name: LocationName
                      paddock_var: test_field
                      bay_var: B-02
                      status_label: |-
                        [[[
                          // --- helpers -------------------------------------------------------------
                          const slugify = (s) => (s ?? '')
                            .toString().trim().toLowerCase()
                            .replace(/\s+/g, '_')
                            .replace(/[^a-z0-9_]/g, '')
                            .replace(/_+/g, '_');

                          const pdk = String(variables.paddock_var ?? '');
                          const bay = String(variables.bay_var ?? '');

                          // --- resolve devId from paddock array -----------------------------------
                          const paddocks = hass.states['sensor.pwm_paddock_list']?.attributes?.paddocks || {};
                          const arr = paddocks?.[pdk];
                          let devId = '';
                          let devRaw = '';

                          if (Array.isArray(arr)) {
                            for (const obj of arr) {
                              if (!obj || typeof obj !== 'object') continue;
                              for (const [k, v] of Object.entries(obj)) {
                                // Match bay exactly or as prefix so "B-04" matches "B-04 Drain"
                                const match = (k === bay) || k.toLowerCase().startsWith(bay.toLowerCase());
                                if (!match) continue;
                                devRaw = String(v?.device ?? '').trim();
                                if (devRaw) devId = slugify(devRaw);
                                break;
                              }
                              if (devRaw) break;
                            }
                          }

                          // --- 1) UNSET if device unset or missing --------------------------------
                          if (!devRaw || devRaw.toLowerCase() === 'unset') {
                            return 'UNSET';
                          }

                          // --- 2) OFFLINE if online binary sensor is not online --------------------
                          // If you know the exact pattern, you can construct:
                          // const onlineEid = `binary_sensor.${devId}_${devId}_online`;
                          // But because name parts can differ, we search for any binary_sensor.*online containing devId.

                          const keys = Object.keys(hass.states || {});
                          const onlineKeys = keys
                            .filter(k => k.startsWith('binary_sensor.'))
                            .filter(k => /(^|_)online($|_)/i.test(k));

                          const reDev = new RegExp(devId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
                          const candidates = onlineKeys.filter(k => reDev.test(k));

                          // Choose the first candidate (or broaden if none found)
                          const onlineEid = candidates[0] || null;

                          // Define what counts as "online"
                          const onlineStates = new Set(['on', 'connected', 'online', 'true', 'available']);
                          const onlineState = onlineEid ? hass.states[onlineEid]?.state : undefined;
                          const isOnline = onlineStates.has(String(onlineState ?? '').toLowerCase());

                          if (!isOnline) {
                            return 'OFFLINE';
                          }

                          // --- 3) Otherwise return the door entity's mapped state ------------------
                          const stateObj = entity; // button-card provides current entity as 'entity'
                          if (!stateObj) {
                            return 'Entity Not Found';
                          }

                          const valveID = `valve.${devId}_${devId}_actuator_1`;
                          const valveState = hass.states[valveID]?.state;
                          const valvePos = hass.states[valveID]?.attributes?.current_position;
                          if (['opening', 'closing',].includes(valveState) || valvePos == 0 || valvePos == 100) {
                            return valveState.toUpperCase();
                          } else {
                            return valveState.toUpperCase() + ' (' + valvePos + '%)';
                          };
                        ]]]
                    label: '[[[ return variables.status_label ]]]'
                    show_name: true
                    show_icon: true
                    show_state: false
                    show_label: true
                  - type: custom:button-card
                    template: template_inputselect_automationstate
                    entity: input_select.test_field_b_02_automation_state
                    name: B-02 Automation State
                    variables:
                      paddock_var: test_field
                    styles:
                      card:
                        - display: |
                            [[[
                              const paddock = variables.paddock_var;
                              const s = hass.states['sensor.pwm_paddock_list'];
                              const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                              return item && item.automation_state_individual === false ? 'none' : null;
                            ]]]
              - type: custom:layout-card
                layout_type: custom:horizontal-layout
                layout:
                  margin: 0px 0px 0px 0px
                  padding: 0px 0px 0px 0px
                  card_margin: 0px 0px 0px 0px
                cards:
                  - type: custom:button-card
                    template: template_buttoncard_openclose
                    entity: input_select.test_field_b_03_door_control
                    name: B-03 SUPPLY
                    variables:
                      paddock_var: test_field
                      bay_var: B-0
                  - type: custom:button-card
                    template: template_inputselect_automationstate
                    entity: input_select.test_field_b_03_automation_state
                    name: B-03 Automation State
                    variables:
                      paddock_var: test_field
                    styles:
                      card:
                        - display: |
                            [[[
                              const paddock = variables.paddock_var;
                              const s = hass.states['sensor.pwm_paddock_list'];
                              const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                              return item && item.automation_state_individual === false ? 'none' : null;
                            ]]]
              - type: custom:layout-card
                layout_type: custom:horizontal-layout
                layout:
                  margin: 0px 0px 0px 0px
                  padding: 0px 0px 0px 0px
                  card_margin: 0px 0px 0px 0px
                cards:
                  - type: custom:button-card
                    template: template_buttoncard_openclose
                    entity: input_select.test_field_b_04_door_control
                    name: B-04 SUPPLY
                    variables:
                      paddock_var: test_field
                      bay_var: B-0
                  - type: custom:button-card
                    template: template_inputselect_automationstate
                    entity: input_select.test_field_b_04_automation_state
                    name: B-04 Automation State
                    variables:
                      paddock_var: test_field
                    styles:
                      card:
                        - display: |
                            [[[
                              const paddock = variables.paddock_var;
                              const s = hass.states['sensor.pwm_paddock_list'];
                              const item = s?.attributes?.paddocks?.[paddock]?.find(o => o.automation_state_individual !== undefined);
                              return item && item.automation_state_individual === false ? 'none' : null;
                            ]]]
              - type: custom:button-card
                template: template_buttoncard_openclose
                entity: input_select.test_field_drain_door_control
                name: B-04 DRAIN
                variables:
                  paddock_var: test_field
                  bay_var: B-04 DRAIN
      - type: custom:button-card
        template: template_paddockconfigbutton
        variables:
          paddock_config_var: test_field
      - type: button
        name: Extra Data
        icon: mdi:database
        show_name: true
        show_icon: true
        tap_action:
          action: navigate
          navigation_path: /farms-fields/test-field-extra
        hold_action:
          action: none
        icon_height: 80px
        show_state: true
      - type: entities
        entities:
          - type: custom:template-entity-row
            entity: input_boolean.test_field_b_01_flushactive
            secondary: '{{ states(''input_select.test_field_b_01_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.test_field_b_02_flushactive
            secondary: '{{ states(''input_select.test_field_b_02_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.test_field_b_03_flushactive
            secondary: '{{ states(''input_select.test_field_b_03_automation_state'') }}'
          - type: custom:template-entity-row
            entity: input_boolean.test_field_b_04_flushactive
            secondary: '{{ states(''input_select.test_field_b_04_automation_state'') }}'
  - title: Test Field Extra Data
    type: masonry
    path: test-field-extra
    subview: true
    cards:
      - show_state: true
        show_name: true
        camera_view: auto
        fit_mode: cover
        type: picture-entity
        entity: camera.esp32_cam_05_camera_05
        image: https://demo.home-assistant.io/stub_config/bedroom.png
