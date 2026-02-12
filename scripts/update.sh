#!/bin/bash
#
# PaddiSense Updater
# Usage: ./scripts/update.sh
# Or: curl -sSL https://raw.githubusercontent.com/PaddiSense/PaddiSense/main/scripts/update.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           PaddiSense Updater                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Find PaddiSense directory
PADDISENSE_DIR=""
if [ -d "/config/PaddiSense" ]; then
    PADDISENSE_DIR="/config/PaddiSense"
elif [ -d "/config" ] && [ -f "/config/.paddisense" ]; then
    PADDISENSE_DIR="/config"
else
    echo -e "${RED}Error: PaddiSense installation not found.${NC}"
    echo "Run the installer first: curl -sSL https://raw.githubusercontent.com/PaddiSense/PaddiSense/main/scripts/install.sh | bash"
    exit 1
fi

cd "$PADDISENSE_DIR"

# Check for git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not available.${NC}"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
echo "Current version: $CURRENT_VERSION"

# Check for local changes
echo ""
echo -e "${GREEN}[1/4]${NC} Checking for local changes..."
if ! git diff --quiet 2>/dev/null; then
    echo -e "${YELLOW}Warning: Local changes detected.${NC}"
    echo "These files have been modified:"
    git diff --name-only
    echo ""
    read -p "Stash changes and continue? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash push -m "Pre-update stash $(date -Iseconds)"
        echo "Changes stashed."
    else
        echo "Update cancelled."
        exit 0
    fi
fi

# Fetch updates
echo ""
echo -e "${GREEN}[2/4]${NC} Fetching updates..."
git fetch origin main

# Check if update available
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}Already up to date!${NC}"
    exit 0
fi

# Show changes
echo ""
echo -e "${GREEN}[3/4]${NC} Changes available:"
git log --oneline HEAD..origin/main | head -10

COMMIT_COUNT=$(git rev-list --count HEAD..origin/main)
if [ "$COMMIT_COUNT" -gt 10 ]; then
    echo "  ... and $((COMMIT_COUNT - 10)) more commits"
fi

# Apply update
echo ""
echo -e "${GREEN}[4/4]${NC} Applying update..."
git pull origin main

# Get new version
NEW_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

# Update symlinks if needed
if [ -d "/config/packages" ] && [ -d "$PADDISENSE_DIR/packages" ]; then
    echo "Updating package symlinks..."
    for pkg in $PADDISENSE_DIR/packages/*.yaml; do
        if [ -f "$pkg" ]; then
            pkgname=$(basename "$pkg")
            if [ ! -L "/config/packages/$pkgname" ]; then
                ln -sf "$pkg" "/config/packages/$pkgname"
                echo "  Linked new package: $pkgname"
            fi
        fi
    done
fi

# Record update
echo "$(date -Iseconds) updated from $CURRENT_VERSION to $NEW_VERSION" >> "$PADDISENSE_DIR/.update_log"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Update complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Updated: $CURRENT_VERSION → $NEW_VERSION"
echo ""
echo -e "${YELLOW}Please restart Home Assistant to apply changes:${NC}"
echo "  ha core restart"
echo ""

# Check for migration notes
if [ -f "$PADDISENSE_DIR/MIGRATION.md" ]; then
    if grep -q "^## $NEW_VERSION" "$PADDISENSE_DIR/MIGRATION.md"; then
        echo -e "${YELLOW}Migration notes for $NEW_VERSION:${NC}"
        sed -n "/^## $NEW_VERSION/,/^## /p" "$PADDISENSE_DIR/MIGRATION.md" | head -20
        echo ""
    fi
fi
