# PaddiSense Git Workflow & Repository Structure

## Repository Overview

| Repository | Visibility | Purpose |
|------------|------------|---------|
| **PaddiSense** | Private | Development & testing of all modules |
| **paddisense-release** | Public | Released, tested modules for grower servers |
| **PaddiSense-HACS** | Public | HACS installer component + Module Manager UI |
| **PaddiSense-Registrations** | Private | Grower email tracking & update notifications |

### How It Fits Together

```
Grower Server
├── 1. Installs PaddiSense-HACS via HACS
└── 2. Module Manager UI pulls modules from paddisense-release

paddisense-release (public)
├── Contains only tested, released modules
└── Updated automatically by GitHub Action when dev repo is tagged

PaddiSense (private)
├── All development happens here
├── Multiple developers work on feature branches
└── Tags trigger automatic release promotion
```

## Quick Start for Developers

### First-Time Setup

```bash
# Clone the dev repo
git clone git@github.com:PKmac78/PaddiSense.git
cd PaddiSense

# Run setup script to validate and clone sibling repos
chmod +x scripts/dev-setup.sh
./scripts/dev-setup.sh --clone
```

This creates the correct structure:

```
~/your-folder/
├── PaddiSense/           ← Dev repo
├── paddisense-release/   ← Release repo (sibling, not nested)
└── PaddiSense-HACS/      ← HACS installer (sibling)
```

### Validate Your Setup

```bash
./scripts/dev-setup.sh        # Check for issues
./scripts/dev-setup.sh --fix  # Auto-fix common issues
```

## Branch Strategy

```
PaddiSense (Dev Repo)
│
├── main              ← Stable, mirrors release
├── dev               ← Integration branch
│
├── feature/ipm-v2    ← Developer A
├── feature/weather   ← Developer B
└── fix/registry-bug  ← Bug fixes
```

### Branch Rules

| Branch | Purpose | Merges To |
|--------|---------|-----------|
| `main` | Release-ready code | → triggers release |
| `dev` | Integration testing | → main |
| `feature/*` | New work | → dev |
| `fix/*` | Bug fixes | → dev |

## Developer Workflow

### Starting New Work

```bash
# Get latest dev
git checkout dev
git pull origin dev

# Create feature branch
git checkout -b feature/my-module-work
```

### Working on Your Module

Each module is self-contained:

```
PaddiSense/
├── packages/
│   ├── registry.yaml   ← Core module
│   ├── ipm.yaml        ← Your module
│   └── weather.yaml
└── dashboards/
    ├── registry/
    ├── ipm/
    └── weather/
```

Only modify files in your assigned module unless coordinating with the team.

### Committing

```bash
# Stage your module files
git add PaddiSense/packages/my_module.yaml
git add PaddiSense/dashboards/my_module/

# Commit with clear message
git commit -m "feat(my_module): Add spray tracking

- Added spray event sensor
- Updated dashboard with spray history card
- Bumped version to 1.2.0"

# Push your branch
git push -u origin feature/my-module-work
```

### Pull Requests

1. Create PR from your branch → `dev`
2. Get review (or self-review)
3. Merge after CI passes
4. Test on dev server

## Release Process

### Automatic Release (Recommended)

When you tag a version, GitHub Actions automatically promotes to release:

```bash
# Ensure dev is stable
git checkout dev && git pull

# Merge to main
git checkout main
git pull
git merge dev
git push

# Tag triggers release
git tag -a v1.2.0 -m "Release 1.2.0: IPM spray tracking"
git push origin v1.2.0
```

The GitHub Action will:
1. Copy modules to `paddisense-release`
2. Commit and push
3. Tag the release repo

### Manual Release (Local)

For releasing specific modules without tagging:

```bash
./scripts/promote-module.sh ipm 1.2.0      # Single module
./scripts/promote-module.sh --all 1.0.0    # All modules
```

### GitHub Action Setup

The workflow requires a `RELEASE_REPO_TOKEN` secret with push access to `paddisense-release`.

To set up:
1. Create a Personal Access Token with `repo` scope
2. Add as secret in PaddiSense repo: Settings → Secrets → `RELEASE_REPO_TOKEN`

## Hotfix Process

For critical fixes that can't wait:

```bash
# Branch from main
git checkout main
git checkout -b fix/critical-issue

# Make minimal fix, PR to main
# After merge, tag new release

# Merge fix back to dev
git checkout dev
git merge main
```

## What NOT to Commit

These must never be in git (enforced by `.gitignore`):

| File/Folder | Reason |
|-------------|--------|
| `secrets.yaml` | Contains passwords, API keys |
| `server.yaml` | Per-server configuration |
| `local_data/` | Farm-specific operational data |
| `.storage/` | Home Assistant state |
| `paddisense-release/` | Separate repo |

## Commit Message Format

```
type(scope): Short description

- Detail 1
- Detail 2
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Scope:** Module name (`ipm`, `weather`, `registry`, etc.)

## Troubleshooting

### "I accidentally cloned release inside dev"

```bash
./scripts/dev-setup.sh --fix
```

### "I have merge conflicts"

1. Pull latest dev before starting work
2. Keep PRs small and focused
3. Communicate when working on shared files

### "GitHub Action failed"

Check that `RELEASE_REPO_TOKEN` secret is set and has push access.

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/dev-setup.sh` | Validate/fix dev environment |
| `scripts/dev-setup.sh --clone` | Clone sibling repos |
| `scripts/dev-setup.sh --fix` | Auto-fix common issues |
| `scripts/promote-module.sh` | Manual release promotion |
