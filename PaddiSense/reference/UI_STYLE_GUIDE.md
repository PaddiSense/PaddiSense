# UI Style Guide

## Reference Implementation
The **IPM dashboard** (`ipm/dashboards/inventory.yaml`) is the canonical reference for card styling across all PaddiSense modules.

## Button Card Templates

All modules should define templates following this pattern (replace `ipm_` prefix with module prefix, e.g., `pwm_`, `asm_`, `registry_`):

### Title Bar
```yaml
<module>_title:
  color_type: card
  color: "#c77f00"   # Dull orange - mobile-friendly visual segregation
  show_icon: false
  show_state: false
  styles:
    card:
      - height: 50px
      - border-radius: 12px
      - padding: 8px
    name:
      - font-size: 18px
      - font-weight: 700
      - text-align: center
      - color: white
```

> **Note:** Title/heading color changed from `#1e1e1e` to dull orange `#c77f00` for better visual segregation on mobile devices (Feb 2026).

### Info Display Block
```yaml
<module>_info_block:
  color_type: card
  color: "#546e7a"
  show_icon: false
  show_state: true
  tap_action:
    action: none
  styles:
    card:
      - height: 80px
      - border-radius: 12px
      - padding: 10px
    state:
      - font-size: 32px
      - font-weight: 800
      - text-align: center
      - color: white
    name:
      - font-size: 14px
      - font-weight: 600
      - text-align: center
      - color: white
```

### Minus Button (Decrement/Remove)
```yaml
<module>_minus:
  variables:
    amount: 1
    label: "-1"
  color_type: card
  color: "#dc3545"
  show_icon: false
  show_name: true
  show_state: false
  name: "[[[ return variables.label ]]]"
  styles:
    card:
      - height: 70px
      - border-radius: 12px
    name:
      - font-size: 20px
      - font-weight: 800
      - color: white
```

### Plus Button (Increment/Add)
```yaml
<module>_plus:
  variables:
    amount: 1
    label: "+1"
  color_type: card
  color: "#28a745"
  show_icon: false
  show_name: true
  show_state: false
  name: "[[[ return variables.label ]]]"
  styles:
    card:
      - height: 70px
      - border-radius: 12px
    name:
      - font-size: 20px
      - font-weight: 800
      - color: white
```

### Primary Action Button
```yaml
<module>_action:
  color_type: card
  color: "#0066cc"
  show_icon: true
  show_name: true
  show_state: false
  styles:
    card:
      - height: 70px
      - border-radius: 12px
    name:
      - font-size: 16px
      - font-weight: 700
      - color: white
    icon:
      - color: white
      - width: 28px
```

### Secondary Action Button
```yaml
<module>_secondary:
  color_type: card
  color: "#555555"
  show_icon: true
  show_name: true
  show_state: false
  styles:
    card:
      - height: 70px   # Standardized to 70px minimum for mobile
      - border-radius: 12px
    name:
      - font-size: 16px
      - font-weight: 700
      - color: white
    icon:
      - color: white
      - width: 28px
```

### Danger Button (Delete/Destructive)
```yaml
<module>_danger:
  color_type: card
  color: "#dc3545"
  show_icon: true
  show_name: true
  show_state: false
  styles:
    card:
      - height: 70px
      - border-radius: 12px
    name:
      - font-size: 16px
      - font-weight: 700
      - color: white
    icon:
      - color: white
      - width: 28px
```

### Stat Chip (Mushroom-style)
```yaml
<module>_stat_chip:
  color_type: card
  color: "#424242"
  show_icon: true
  show_name: true
  show_state: true
  styles:
    card:
      - height: 50px
      - border-radius: 25px
      - padding: 8px 16px
    grid:
      - grid-template-areas: '"i n" "i s"'
      - grid-template-columns: min-content 1fr
    icon:
      - color: white
      - width: 24px
    name:
      - font-size: 12px
      - color: "#aaa"
    state:
      - font-size: 16px
      - font-weight: 700
      - color: white
```

## Color Palette

| Purpose | Hex | Usage |
|---------|-----|-------|
| **Title/Headers** | `#c77f00` | Section headers, title bars (dull orange) |
| Slate/Info | `#546e7a` | Display blocks, read-only info |
| Success/Add | `#28a745` | Plus buttons, positive actions, confirm |
| Danger/Remove | `#dc3545` | Minus/delete, destructive actions, clear |
| Primary/Action | `#0066cc` | Primary CTA buttons, All selection |
| Secondary/Muted | `#555555` | Secondary actions, less emphasis |
| Warning/Season | `#e6a700` | Season selection buttons |
| Chip/Stat | `#424242` | Small stat indicators |

### Button Color Standards (Step 3 Paddock Selection)
| Button | Color | Hex |
|--------|-------|-----|
| All | Blue | `#0066cc` |
| Clear | Red | `#dc3545` |
| Season | Yellow | `#e6a700` |

## Sizing Standards

| Element | Height | Font Size | Border Radius |
|---------|--------|-----------|---------------|
| Title | 50px | 18px bold | 12px |
| Info Block | 80px | 32px state, 14px name | 12px |
| Action Button | 70px | 16-20px bold | 12px |
| Secondary Button | 70px | 16px bold | 12px |
| Nav Button | 70px | 16px bold | 12px |
| Stat Chip | 50px | 12px name, 16px state | 25px (pill) |

> **Standard:** ALL interactive buttons should be minimum 70px height for mobile usability.

## Mobile-First Requirements

- **Minimum touch target:** 70px height (standardized)
- **Primary actions:** 70px+ height
- **High contrast text:** White on dark backgrounds
- **Readable at arm's length:** 16px+ for important text
- **No hover-only interactions**
- **Hold-to-clear pattern:** Tap to capture, hold to clear (reduces button count)
- **Fat fingers, bad eyes:** Design for outdoor field use

## Weather Data Tables (HFM Pattern)

For compact weather data display, use markdown tables with Jinja templating:

```yaml
- type: markdown
  content: |
    {% set device_id = states('input_text.hfm_current_device') %}
    {% set drafts = state_attr('sensor.hfm_drafts', 'drafts') or {} %}
    {% set draft = drafts.get(device_id, {}) %}
    {% set data = draft.get('data', {}) %}
    {% set ws = data.get('weather_start') %}
    {% set wm = data.get('weather_mid') %}
    {% set we = data.get('weather_end') %}
    | | START | MID | END |
    |:--|:--:|:--:|:--:|
    | **Wind** | {{ ws.wind_speed if ws else '-' }} | ... |
  card_mod:
    style: |
      ha-card { border-radius: 12px; padding: 8px; font-size: 12px; }
      table { width: 100%; font-size: 11px; }
```

### Weather Fields to Capture
- Wind speed (km/h)
- Wind gust (km/h)
- Wind direction
- Delta T (°C)
- Humidity (%)
- Rain chance (%)

### Sensor Fallback Pattern
Always use local sensors first, BOM as fallback:
```yaml
state: >
  {% set local = states('sensor.weather_api_station_1_wind_speed') %}
  {% set bom = states('sensor.bom_wind_speed_kilometre') %}
  {% if local not in ['unknown', 'unavailable', ''] %}
    {{ local | float(0) | round(1) }}
  {% else %}
    {{ bom | float(0) | round(1) }}
  {% endif %}
```

---

## Module Row Template Pattern

**IMPORTANT:** For complex list-style UI with dynamic state (installed/available/locked), use `custom:button-card` templates with JavaScript logic. **Do not use raw HTML cards** — they don't work reliably inside Home Assistant.

### Template: `pds_module_row`

This pattern displays modules with:
- Icon with accent color border-left
- Title and status label (version/available/locked)
- Dynamic action button (Install/Remove/Locked)

```yaml
pds_module_row:
  entity: sensor.paddisense_version
  triggers_update:
    - sensor.paddisense_version
  show_state: false
  show_icon: true
  show_name: true
  show_label: true
  icon: |
    [[[
      return variables.icon || 'mdi:puzzle';
    ]]]
  name: |
    [[[
      return variables.title || variables.module_id;
    ]]]
  label: |
    [[[
      const modId = variables.module_id;
      const attrs = entity?.attributes || {};
      const installedList = attrs.installed_modules || [];
      const installedData = installedList.find(m => m.id === modId);
      const version = installedData?.version || '';

      const licensed = (attrs.licensed_modules || attrs.license_modules || []).includes(modId);
      const available = (attrs.available_modules || []).some(m => m.id === modId);
      const installed = !!installedData;

      const base = variables.desc || '';

      if (installed) return `${base}${version ? ` • v${version}` : ''}`;
      if (!licensed) return `${base} • Not licensed`;
      if (available) return `${base} • Available`;
      return `${base} • Unavailable`;
    ]]]
  tap_action:
    action: call-service
    service: |
      [[[
        const modId = variables.module_id;
        const attrs = entity?.attributes || {};
        const installed = (attrs.installed_modules || []).some(m => m.id === modId);
        const licensed = (attrs.licensed_modules || attrs.license_modules || []).includes(modId);
        const available = (attrs.available_modules || []).some(m => m.id === modId);

        if (installed) return 'paddisense.remove_module';
        if (licensed && available) return 'paddisense.install_module';
        return 'script.turn_on';  // No-op fallback
      ]]]
    service_data: |
      [[[
        return { module_id: variables.module_id };
      ]]]
  confirmation:
    text: |
      [[[
        const modId = variables.module_id;
        const attrs = entity?.attributes || {};
        const installed = (attrs.installed_modules || []).some(m => m.id === modId);
        return installed
          ? `Remove module: ${variables.title || modId}?`
          : `Install module: ${variables.title || modId}?`;
      ]]]
  custom_fields:
    action: |
      [[[
        const modId = variables.module_id;
        const attrs = entity?.attributes || {};
        const installedList = attrs.installed_modules || [];
        const installedData = installedList.find(m => m.id === modId);

        const installed = !!installedData;
        const licensed = (attrs.licensed_modules || attrs.license_modules || []).includes(modId);
        const available = (attrs.available_modules || []).some(m => m.id === modId);

        let text = '';
        let bg = '';
        let fg = '';
        let ico = '';
        let opacity = '1';

        if (installed) {
          text = 'Remove'; bg = '#dc3545'; fg = 'white'; ico = 'mdi:trash-can-outline';
        } else if (licensed && available) {
          text = 'Install'; bg = '#28a745'; fg = 'white'; ico = 'mdi:download';
        } else if (!licensed) {
          text = 'Locked'; bg = 'transparent'; fg = 'var(--secondary-text-color)';
          ico = 'mdi:lock-outline'; opacity = '0.8';
        } else {
          text = 'N/A'; bg = 'transparent'; fg = 'var(--secondary-text-color)';
          ico = 'mdi:minus-circle-outline'; opacity = '0.8';
        }

        return `
          <div style="
            display:flex;align-items:center;gap:8px;
            padding:8px 12px;border-radius:10px;
            background:${bg};color:${fg};
            font-size:13px;font-weight:700;
            opacity:${opacity};
          ">
            <ha-icon icon="${ico}" style="--mdc-icon-size:18px;"></ha-icon>
            <span>${text}</span>
          </div>
        `;
      ]]]
  styles:
    card:
      - border-radius: 12px
      - padding: 12px 14px
      - background: var(--card-background-color)
      - box-shadow: 0 1px 3px rgba(0,0,0,0.08)
      - border-left: |
          [[[
            return `4px solid ${variables.color || '#0066cc'}`;
          ]]]
      - opacity: |
          [[[
            const modId = variables.module_id;
            const attrs = entity?.attributes || {};
            const installed = (attrs.installed_modules || []).some(m => m.id === modId);
            const licensed = (attrs.licensed_modules || attrs.license_modules || []).includes(modId);
            const available = (attrs.available_modules || []).some(m => m.id === modId);
            return (installed || (licensed && available)) ? '1' : '0.75';
          ]]]
    grid:
      - grid-template-areas: '"i n action" "i l action"'
      - grid-template-columns: 48px 1fr auto
      - grid-template-rows: min-content min-content
      - column-gap: 12px
    icon:
      - width: 26px
      - color: |
          [[[
            return variables.color || '#0066cc';
          ]]]
    name:
      - font-size: 15px
      - font-weight: 700
      - align-self: end
    label:
      - font-size: 12px
      - color: var(--secondary-text-color)
      - align-self: start
    custom_fields:
      action:
        - align-self: center
        - justify-self: end
```

### Usage Example

```yaml
- type: custom:button-card
  template: pds_module_row
  variables:
    module_id: ipm
    title: Inventory Manager
    desc: Chemicals, fertilizers & consumables
    icon: mdi:warehouse
    color: '#4caf50'
```

### Why Button-Card Templates (Not Raw HTML)

1. **Reactive updates** — `triggers_update` ensures UI refreshes when entity changes
2. **HA integration** — Works with `tap_action`, `confirmation`, and service calls
3. **Theme compatibility** — Uses CSS variables like `var(--card-background-color)`
4. **Consistent styling** — Follows the same template pattern as other cards
5. **Maintainability** — All logic in YAML, not scattered JS files
