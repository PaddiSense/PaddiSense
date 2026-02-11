#!/bin/bash
#
# PaddiSense Development Environment Setup
#
# This script validates and configures the development environment.
# Run from the PaddiSense (dev) repository root.
#
# Usage:
#   ./scripts/dev-setup.sh           # Validate current setup
#   ./scripts/dev-setup.sh --fix     # Fix common issues
#   ./scripts/dev-setup.sh --clone   # Clone sibling repos (first-time setup)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PARENT_DIR="$(dirname "$REPO_ROOT")"

# Expected repository structure (siblings, not nested)
RELEASE_REPO_URL="git@github.com:PKmac78/paddisense-release.git"
HACS_REPO_URL="git@github.com:PKmac78/PaddiSense-HACS.git"

echo "========================================"
echo "PaddiSense Development Setup"
echo "========================================"
echo ""

errors=0
warnings=0

# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    errors=$((errors + 1))
}

check_warn() {
    echo -e "${YELLOW}!${NC} $1"
    warnings=$((warnings + 1))
}

# ------------------------------------------------------------------------------
# Validation checks
# ------------------------------------------------------------------------------

echo "Checking repository structure..."
echo ""

# Check we're in the dev repo
if [[ -d "$REPO_ROOT/.git" ]]; then
    REMOTE_URL=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || echo "")
    if [[ "$REMOTE_URL" == *"PaddiSense.git"* ]] || [[ "$REMOTE_URL" == *"PaddiSense"* ]]; then
        check_pass "In PaddiSense dev repository"
    else
        check_warn "Repository origin doesn't match expected PaddiSense URL"
        echo "       Found: $REMOTE_URL"
    fi
else
    check_fail "Not in a git repository"
fi

# Check for nested repos (BAD)
echo ""
echo "Checking for nested repositories (should not exist)..."

NESTED_REPOS=("paddisense-release" "paddisense-hacs" "PaddiSense-HACS")
for nested in "${NESTED_REPOS[@]}"; do
    if [[ -d "$REPO_ROOT/$nested/.git" ]]; then
        check_fail "Found nested repository: $nested/"
        echo "       This should be a sibling, not nested inside dev repo"

        if [[ "$1" == "--fix" ]]; then
            echo "       Removing nested repo..."
            rm -rf "$REPO_ROOT/$nested"
            check_pass "Removed $nested/"
        fi
    else
        check_pass "No nested $nested/ repository"
    fi
done

# Check .gitignore includes nested repo paths
echo ""
echo "Checking .gitignore..."

GITIGNORE="$REPO_ROOT/.gitignore"
if [[ -f "$GITIGNORE" ]]; then
    if grep -q "paddisense-release/" "$GITIGNORE"; then
        check_pass "paddisense-release/ in .gitignore"
    else
        check_warn "paddisense-release/ not in .gitignore"
        if [[ "$1" == "--fix" ]]; then
            echo "paddisense-release/" >> "$GITIGNORE"
            check_pass "Added paddisense-release/ to .gitignore"
        fi
    fi
else
    check_warn ".gitignore not found"
fi

# Check for extra remotes (should only have origin)
echo ""
echo "Checking git remotes..."

REMOTE_COUNT=$(git -C "$REPO_ROOT" remote | wc -l)
if [[ "$REMOTE_COUNT" -eq 1 ]]; then
    check_pass "Single remote (origin) configured"
else
    check_warn "Multiple remotes configured ($REMOTE_COUNT found)"
    git -C "$REPO_ROOT" remote -v | sed 's/^/       /'

    if [[ "$1" == "--fix" ]]; then
        # Remove non-origin remotes
        for remote in $(git -C "$REPO_ROOT" remote | grep -v origin); do
            echo "       Removing remote: $remote"
            git -C "$REPO_ROOT" remote remove "$remote"
        done
        check_pass "Cleaned up extra remotes"
    fi
fi

# Check branch structure
echo ""
echo "Checking branch structure..."

if git -C "$REPO_ROOT" show-ref --verify --quiet refs/heads/main 2>/dev/null; then
    check_pass "main branch exists"
else
    check_warn "main branch not found locally"
fi

if git -C "$REPO_ROOT" show-ref --verify --quiet refs/heads/dev 2>/dev/null; then
    check_pass "dev branch exists"
else
    check_warn "dev branch not found locally"
fi

CURRENT_BRANCH=$(git -C "$REPO_ROOT" branch --show-current)
echo "       Current branch: $CURRENT_BRANCH"

# Check protected files exist and are ignored
echo ""
echo "Checking protected local files..."

if [[ -f "$REPO_ROOT/secrets.yaml" ]]; then
    check_pass "secrets.yaml exists (local)"
else
    check_warn "secrets.yaml not found (needed for local HA)"
fi

if [[ -f "$REPO_ROOT/server.yaml" ]]; then
    check_pass "server.yaml exists (local)"
else
    check_warn "server.yaml not found (needed for local HA)"
fi

# ------------------------------------------------------------------------------
# Clone sibling repos (optional)
# ------------------------------------------------------------------------------

if [[ "$1" == "--clone" ]]; then
    echo ""
    echo "========================================"
    echo "Cloning sibling repositories..."
    echo "========================================"
    echo ""

    # Clone paddisense-release as sibling
    RELEASE_PATH="$PARENT_DIR/paddisense-release"
    if [[ -d "$RELEASE_PATH" ]]; then
        check_pass "paddisense-release already exists at $RELEASE_PATH"
    else
        echo "Cloning paddisense-release..."
        git clone "$RELEASE_REPO_URL" "$RELEASE_PATH"
        check_pass "Cloned paddisense-release to $RELEASE_PATH"
    fi

    # Clone PaddiSense-HACS as sibling
    HACS_PATH="$PARENT_DIR/PaddiSense-HACS"
    if [[ -d "$HACS_PATH" ]]; then
        check_pass "PaddiSense-HACS already exists at $HACS_PATH"
    else
        echo "Cloning PaddiSense-HACS..."
        git clone "$HACS_REPO_URL" "$HACS_PATH"
        check_pass "Cloned PaddiSense-HACS to $HACS_PATH"
    fi
fi

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------

echo ""
echo "========================================"
echo "Summary"
echo "========================================"
echo ""

if [[ $errors -gt 0 ]]; then
    echo -e "${RED}Errors: $errors${NC}"
    echo "Run with --fix to attempt automatic fixes"
fi

if [[ $warnings -gt 0 ]]; then
    echo -e "${YELLOW}Warnings: $warnings${NC}"
fi

if [[ $errors -eq 0 ]] && [[ $warnings -eq 0 ]]; then
    echo -e "${GREEN}All checks passed!${NC}"
fi

echo ""
echo "Repository structure should be:"
echo "  $PARENT_DIR/"
echo "  ├── PaddiSense/           ← Dev repo (you are here)"
echo "  ├── paddisense-release/   ← Release repo (sibling)"
echo "  └── PaddiSense-HACS/      ← HACS installer (sibling)"
echo ""

if [[ "$1" != "--clone" ]]; then
    echo "Run with --clone to clone sibling repos for local development"
fi

exit $errors
