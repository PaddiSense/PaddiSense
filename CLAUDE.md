# CLAUDE.md — PaddiSense Core Rules (Minimal)

PaddiSense is a modular farm-management platform for **Home Assistant OS (HAOS)** built as **packages + dashboards** with **local JSON data**.

## Non-negotiables
- **HAOS only**
- **Offline-first:** core workflows must run without internet.
- **Local-only by default:** secrets and operational data stay on the server unless explicitly exported.
- **Updates must not overwrite local state:** never touch `secrets.yaml`, `server.yaml`, `local_data/`, or `.storage` unless a deliberate migration exists.
- **Mobile-first UI:** large touch targets, high contrast, dark-mode compatible; avoid hardcoded colors where feasible.

## Repository boundaries
- Repo contains: packages (YAML), dashboards, scripts/tools, default schemas/templates.
- Per-server local files (protected): `server.yaml`, `secrets.yaml`, `local_data/**`, `.storage/**`.

## Module design standard
Each module is **self-contained**:
- One module folder (e.g. `ipm/`, `asm/`, `weather/`, `pwm/`)
- Prefer **single `package.yaml`** per module (avoid duplicate root YAML keys).
- Runtime data stored under `/config/local_data/<module>/` (not tracked in git).
- Each module has a `VERSION` file and exposes a **version sensor** in HA.

## Shared Core: Farm Registry
- Farm Registry is **standalone** and consumed by all modules.
- IDs are **generated only** (no manual ID entry); UI shows names, not IDs.
- Support export/import for backups and migration between servers.

## PWM / ESPHome control contract
- HA/PWM controls **valves/actuators only** (never raw relays).
- Devices may have 1–2 actuators; if 2, they are logically paired (same role).
- Watchdog/faults: raise alert + mark unavailable; **do not force stop**.

## Git hygiene
- No secrets in git.
- Preserve entity IDs unless MAJOR bump + migration notes.
- Keep `main` always releasable; use feature/fix branches and PRs.

## Where detailed docs live
This file stays minimal. Put implementation details in repo docs, e.g.:
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/IPM.md`, `docs/ASM.md`, `docs/WEATHER.md`, `docs/PWM.md`, `docs/WSS.md`
- `reference/` for schemas and command docs
- `reference/UI_STYLE_GUIDE.md` for dashboard styling standards

## UI/UX Development Standards (Learned Best Practices)

### Mobile-First Design
- **70px minimum button height** - "fat thumbs and bad eyes" for outdoor field use
- **Dull orange headers** (`#c77f00`) - visual segregation on mobile screens
- **Hold-to-clear pattern** - tap to action, hold to clear (reduces button clutter)
- **Auto-expanding grids** - support unlimited items via CSS `display: none` conditional

### Button-Card Patterns
- **Never use onclick in custom_fields HTML** - use native `tap_action` with `call-service`
- **Always use try-catch in JavaScript templates** - prevents dashboard crashes
- **triggers_update** - ensures reactive updates when entity changes
- **Template inheritance** - define module templates (e.g., `hfm_title`, `hfm_action`)

### Weather/Sensor Integration
- **Local station first, BOM fallback** - always check local sensors before external APIs
- **Capture all fields**: wind speed, gust, direction, delta T, humidity, rain chance
- **Markdown tables for data display** - compact, readable, mobile-friendly

### Multi-Select Patterns
- **Draft system for multi-user** - device-based drafts allow concurrent recording
- **Paddock selection**: Farm selector → filtered paddock grid → All/Clear/Season buttons
- **Toggle pattern**: tap paddock button to add/remove from selection array

### Dashboard Structure
- **Conditional cards** - show/hide based on wizard step or event type
- **Horizontal-stack for button rows** - consistent spacing
- **Vertical-stack for card groups** - logical grouping

### Color Standards
| Purpose | Hex |
|---------|-----|
| Headers/Titles | `#c77f00` (dull orange) |
| Primary Action | `#0066cc` (blue) |
| Success/Confirm | `#28a745` (green) |
| Danger/Clear | `#dc3545` (red) |
| Warning/Season | `#e6a700` (yellow) |
| Secondary | `#555555` (gray) |
