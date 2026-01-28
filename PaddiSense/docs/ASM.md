# ASM — Asset Service Manager

> **UI Note:** Dashboard cards should follow the **IPM card style** for consistency. See `docs/ARCHITECTURE.md` and `reference/UI_STYLE_GUIDE.md`.

## Scope
- Assets, parts, service/inspection events.
- pre-start check major focus
- Offline-first; local JSON backing store.

## Data
- Primary data: `local_data/asm/`
  - `data.json`
  - `config.json`
  - `backups/`

## User Flows
- Add/edit assets
- Add/edit parts, adjust stock
- Record service events (with optional parts consumption)
- record pre-start check for an asset
- View history, reports
- Export/backup/restore/reset

## Multi-user Considerations
- Concurrent event logging
- Protect master category/service-type edits if editable

## Versioning
- Module VERSION
- Version sensor exposed

## Entities & Services
Document key HA entities and scripts here.

## Backend / Tooling
Document any CLI/shell/python entrypoints here.
