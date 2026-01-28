# UI Style Guide

## Reference Implementation
The **IPM dashboard** (`ipm/dashboards/inventory.yaml`) is the canonical reference for card styling across all PaddiSense modules.

## Button Card Templates

All modules should define templates following this pattern (replace `ipm_` prefix with module prefix, e.g., `pwm_`, `asm_`, `registry_`):

### Title Bar
```yaml
<module>_title:
  color_type: card
  color: "#1e1e1e"
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
      - height: 60px
      - border-radius: 12px
    name:
      - font-size: 14px
      - font-weight: 600
      - color: white
    icon:
      - color: white
      - width: 24px
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
| Dark/Title | `#1e1e1e` | Section headers, title bars |
| Slate/Info | `#546e7a` | Display blocks, read-only info |
| Success/Add | `#28a745` | Plus buttons, positive actions |
| Danger/Remove | `#dc3545` | Minus/delete, destructive actions |
| Primary/Action | `#0066cc` | Primary CTA buttons |
| Secondary/Muted | `#555555` | Secondary actions, less emphasis |
| Chip/Stat | `#424242` | Small stat indicators |

## Sizing Standards

| Element | Height | Font Size | Border Radius |
|---------|--------|-----------|---------------|
| Title | 50px | 18px bold | 12px |
| Info Block | 80px | 32px state, 14px name | 12px |
| Action Button | 70px | 16-20px bold | 12px |
| Secondary Button | 60px | 14px | 12px |
| Stat Chip | 50px | 12px name, 16px state | 25px (pill) |

## Mobile-First Requirements

- Minimum touch target: 60px height
- Primary actions: 70px+ height
- High contrast text (white on dark)
- Readable at arm's length (16px+ for important text)
- No hover-only interactions
