#!/bin/bash
#
# Promote a module from dev to release repository
#
# Usage:
#   ./scripts/promote-module.sh <module> <version>
#   ./scripts/promote-module.sh ipm 1.2.0
#   ./scripts/promote-module.sh --all 1.0.0-rc.8
#
# This script is for local use. For CI/CD, use the GitHub Action.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PARENT_DIR="$(dirname "$REPO_ROOT")"
RELEASE_REPO="$PARENT_DIR/paddisense-release"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Module list (add new modules here)
ALL_MODULES=(
    "registry"
    "ipm"
    "weather"
    "hfm"
    "wss"
    "str"
    "rtr"
)

usage() {
    echo "Usage: $0 <module|--all> <version>"
    echo ""
    echo "Modules: ${ALL_MODULES[*]}"
    echo ""
    echo "Examples:"
    echo "  $0 ipm 1.2.0"
    echo "  $0 --all 1.0.0-rc.8"
    exit 1
}

# Validate args
if [[ $# -lt 2 ]]; then
    usage
fi

MODULE="$1"
VERSION="$2"

# Check release repo exists
if [[ ! -d "$RELEASE_REPO/.git" ]]; then
    echo -e "${RED}Error:${NC} Release repo not found at $RELEASE_REPO"
    echo "Run: ./scripts/dev-setup.sh --clone"
    exit 1
fi

# Ensure release repo is clean and up to date
echo "Updating release repository..."
cd "$RELEASE_REPO"
git fetch origin
git checkout main
git pull origin main

cd "$REPO_ROOT"

# Determine modules to promote
if [[ "$MODULE" == "--all" ]]; then
    MODULES=("${ALL_MODULES[@]}")
    echo "Promoting all modules: ${MODULES[*]}"
else
    if [[ ! " ${ALL_MODULES[*]} " =~ " ${MODULE} " ]]; then
        echo -e "${RED}Error:${NC} Unknown module: $MODULE"
        echo "Valid modules: ${ALL_MODULES[*]}"
        exit 1
    fi
    MODULES=("$MODULE")
fi

# Copy module files
echo ""
echo "Copying modules..."

for mod in "${MODULES[@]}"; do
    PACKAGE_FILE="PaddiSense/packages/${mod}.yaml"
    DASHBOARD_DIR="PaddiSense/dashboards/${mod}"

    # Copy package file
    if [[ -f "$REPO_ROOT/$PACKAGE_FILE" ]]; then
        echo -e "${GREEN}✓${NC} Copying $PACKAGE_FILE"
        cp "$REPO_ROOT/$PACKAGE_FILE" "$RELEASE_REPO/$PACKAGE_FILE"
    else
        echo -e "${YELLOW}!${NC} Package not found: $PACKAGE_FILE (skipping)"
    fi

    # Copy dashboard directory if exists
    if [[ -d "$REPO_ROOT/$DASHBOARD_DIR" ]]; then
        echo -e "${GREEN}✓${NC} Copying $DASHBOARD_DIR/"
        mkdir -p "$RELEASE_REPO/$DASHBOARD_DIR"
        cp -r "$REPO_ROOT/$DASHBOARD_DIR/"* "$RELEASE_REPO/$DASHBOARD_DIR/"
    fi
done

# Update modules.json manifest
MODULES_JSON="$RELEASE_REPO/PaddiSense/modules.json"
if [[ -f "$MODULES_JSON" ]]; then
    echo ""
    echo "Note: Update $MODULES_JSON manually if module list changed"
fi

# Commit and push
echo ""
echo "Committing to release repository..."
cd "$RELEASE_REPO"

git add -A

if git diff --staged --quiet; then
    echo -e "${YELLOW}!${NC} No changes to commit"
else
    if [[ "$MODULE" == "--all" ]]; then
        COMMIT_MSG="Release v${VERSION}: All modules"
    else
        COMMIT_MSG="Release ${MODULE} v${VERSION}"
    fi

    git commit -m "$COMMIT_MSG"

    echo ""
    echo -e "${GREEN}Committed:${NC} $COMMIT_MSG"
    echo ""
    read -p "Push to origin? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main
        echo -e "${GREEN}✓${NC} Pushed to release repository"
    else
        echo "Skipped push. Run 'git push origin main' in $RELEASE_REPO when ready."
    fi
fi

echo ""
echo "Done!"
