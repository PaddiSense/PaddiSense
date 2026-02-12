#!/bin/bash
#
# PaddiSense Setup Script
# Run after manual git clone to complete installation
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}PaddiSense Setup${NC}"
echo ""

# Determine if we're in the PaddiSense directory or /config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../VERSION" ]; then
    PADDISENSE_DIR="$(dirname "$SCRIPT_DIR")"
elif [ -f "/config/PaddiSense/VERSION" ]; then
    PADDISENSE_DIR="/config/PaddiSense"
elif [ -f "/config/VERSION" ]; then
    PADDISENSE_DIR="/config"
else
    echo -e "${RED}Error: Cannot determine PaddiSense location.${NC}"
    exit 1
fi

echo "PaddiSense directory: $PADDISENSE_DIR"
echo ""

# Create local data directories
echo "Creating local data directories..."
mkdir -p /config/local_data/weather
mkdir -p /config/local_data/ipm
mkdir -p /config/local_data/rtr
mkdir -p /config/local_data/asm
mkdir -p /config/local_data/pwm
mkdir -p /config/local_data/wss
mkdir -p /config/local_data/farm_registry
echo "  Done."

# Create server.yaml if missing
if [ ! -f "/config/server.yaml" ]; then
    echo "Creating server.yaml..."
    cat > /config/server.yaml << 'EOF'
# PaddiSense Server Configuration
paddisense:
  farm_id: ""
  modules:
    weather: { enabled: true }
    ipm: { enabled: true }
    rtr: { enabled: true }
    hey_farmer: { enabled: true }
    asm: { enabled: true }
    stock_tracker: { enabled: true }
    pwm: { enabled: false }
    wss: { enabled: false }
  updates:
    auto_check: true
    notify: true
EOF
    echo "  Created."
else
    echo "server.yaml already exists."
fi

# Setup package symlinks
echo "Setting up package symlinks..."
mkdir -p /config/packages
if [ -d "$PADDISENSE_DIR/packages" ]; then
    for pkg in $PADDISENSE_DIR/packages/*.yaml; do
        if [ -f "$pkg" ]; then
            pkgname=$(basename "$pkg")
            ln -sf "$pkg" "/config/packages/$pkgname" 2>/dev/null || true
            echo "  $pkgname"
        fi
    done
fi

# Mark as installed
echo "$(date -Iseconds)" > "$PADDISENSE_DIR/.installed"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Register at: https://github.com/PaddiSense/registrations/issues/new?template=basic-registration.yml"
echo "2. Restart Home Assistant: ha core restart"
echo ""
