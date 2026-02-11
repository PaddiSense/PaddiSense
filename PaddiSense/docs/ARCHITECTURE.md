# PaddiSense Architecture

## Purpose
High-level system architecture for PaddiSense (Home Assistant OS) with offline-first operation.

## Core Principles
- HAOS only
- Offline-first (no internet required for core workflows)
- Local-only by default (explicit export/import for sharing)
- Updates must not overwrite local state (`server.yaml`, `secrets.yaml`, `local_data/`, `.storage/`)

## Separation of Concerns
### Repo-distributed (Git/HACS)
- Module packages (`package.yaml`)
- Dashboards/views/templates
- Tooling scripts (shell/python) if used
- Default schema/templates (seed JSON)

### Per-server protected
- `server.yaml`
- `secrets.yaml`
- `local_data/**`
- `.storage/**` (unless a deliberate migration exists)

## Module Topology
- Farm Registry (shared core, standalone)
- IPM (inventory)
- ASM (assets/parts/service events)
- Weather (local gateway + API stations)
- PWM (water management)
- others to be addded in time (mob Trackers & Safe Wrker System)

## Data Strategy
- Local JSON is the primary backing store for operational data.
- HA entities are views over JSON state (sensors/helpers/templates).
- All write operations must validate input and be resilient offline.

## Versioning
- SemVer per module (VERSION file).
- Each module exposes a version sensor in HA.

## Security Model
- No secrets in git.
- No remote control surfaces without explicit configuration.
- Principle of least privilege for integrations.

## UI/UX Design Standards

### Card Style Reference
All module dashboards should follow the **IPM card style** (`ipm/dashboards/inventory.yaml`) for consistency:

| Template | Purpose | Color | Height |
|----------|---------|-------|--------|
| `*_title` | Section headers | `#1e1e1e` (dark) | 50px |
| `*_info_block` | Display blocks | `#546e7a` (slate) | 80px |
| `*_minus` | Decrement/remove | `#dc3545` (red) | 70px |
| `*_plus` | Increment/add | `#28a745` (green) | 70px |
| `*_action` | Primary actions | `#0066cc` (blue) | 70px |
| `*_secondary` | Secondary actions | `#555555` (gray) | 60px |
| `*_danger` | Destructive actions | `#dc3545` (red) | 70px |

### Design Principles
- **Mobile-first**: Large touch targets (60-80px minimum height)
- **High contrast**: White text on dark backgrounds
- **Semantic colors**: Green=add, Red=remove/danger, Blue=primary, Gray=secondary
- **Consistent radius**: 12px border-radius (25px for pill/chip elements)
- **Dark mode compatible**: No hardcoded light colors

See `reference/UI_STYLE_GUIDE.md` for detailed template definitions.

## UI Implementation Approach

### Button-Card Templates (Required)

**All dynamic UI in PaddiSense must use `custom:button-card` templates.** Do not use:
- Raw HTML cards
- Custom elements with inline HTML
- Lit-based web components loaded via www/

**Rationale:** HTML-based approaches don't work reliably inside Home Assistant. Button-card provides:
- Reactive updates via `triggers_update`
- Native service calls, confirmations, and tap actions
- CSS variable support for theme compatibility
- Template inheritance for consistency

See `reference/UI_STYLE_GUIDE.md` for the canonical templates including the `pds_module_row` pattern for list-style management UI.

## Open Decisions
Track unresolved architectural questions here:
- ~~Registry storage location and migration approach~~ (resolved: `local_data/registry/`)
- Multi-user record locking strategy
- Update/installer UX (thin integration wizard scope)
