#!/bin/bash
#
# PaddiSense Installer
# Usage: curl -sSL https://raw.githubusercontent.com/PaddiSense/PaddiSense/main/scripts/install.sh | bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           PaddiSense Installer                            ║"
echo "║           Farm Management for Home Assistant              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on HAOS
if [ ! -d "/config" ]; then
    echo -e "${RED}Error: /config directory not found.${NC}"
    echo "This installer is designed for Home Assistant OS."
    exit 1
fi

cd /config

# Check for existing installation
if [ -d "/config/PaddiSense" ]; then
    echo -e "${YELLOW}Existing PaddiSense installation found.${NC}"
    echo "To update, run: ./PaddiSense/scripts/update.sh"
    echo "To reinstall, remove /config/PaddiSense first."
    exit 1
fi

# Check for git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not installed.${NC}"
    echo "Please install the Git add-on or use SSH with git."
    exit 1
fi

echo -e "${GREEN}[1/5]${NC} Cloning PaddiSense repository..."
git clone https://github.com/PaddiSense/PaddiSense.git /config/PaddiSense

echo -e "${GREEN}[2/5]${NC} Creating local data directories..."
mkdir -p /config/local_data/weather
mkdir -p /config/local_data/ipm
mkdir -p /config/local_data/rtr
mkdir -p /config/local_data/asm
mkdir -p /config/local_data/pwm
mkdir -p /config/local_data/wss
mkdir -p /config/local_data/farm_registry

echo -e "${GREEN}[3/5]${NC} Setting up server configuration..."
if [ ! -f "/config/server.yaml" ]; then
    cat > /config/server.yaml << 'EOF'
# PaddiSense Server Configuration
# This file is specific to your installation and won't be overwritten by updates.

paddisense:
  # Your farm identifier (set during registration)
  farm_id: ""

  # Modules configuration
  modules:
    # Basic modules (no license required)
    weather:
      enabled: true
    ipm:
      enabled: true
    rtr:
      enabled: true
    hey_farmer:
      enabled: true
    asm:
      enabled: true
    stock_tracker:
      enabled: true

    # Licensed modules
    pwm:
      enabled: false  # Set to true after adding license key
    wss:
      enabled: false  # Set to true after adding license key

  # Update preferences
  updates:
    auto_check: true
    notify: true
EOF
    echo "  Created /config/server.yaml"
else
    echo "  server.yaml already exists, skipping"
fi

echo -e "${GREEN}[4/5]${NC} Checking secrets.yaml..."
if [ ! -f "/config/secrets.yaml" ]; then
    cat > /config/secrets.yaml << 'EOF'
# PaddiSense Secrets
# Store sensitive data here - this file is never committed to git

# License keys (add when received)
# pwm_license_key: "YOUR_PWM_LICENSE_KEY"
# wss_license_key: "YOUR_WSS_LICENSE_KEY"
EOF
    echo "  Created /config/secrets.yaml"
else
    # Check if license key placeholders exist
    if ! grep -q "pwm_license_key" /config/secrets.yaml; then
        echo "" >> /config/secrets.yaml
        echo "# PaddiSense License Keys" >> /config/secrets.yaml
        echo "# pwm_license_key: \"YOUR_PWM_LICENSE_KEY\"" >> /config/secrets.yaml
        echo "# wss_license_key: \"YOUR_WSS_LICENSE_KEY\"" >> /config/secrets.yaml
        echo "  Added license key placeholders to secrets.yaml"
    else
        echo "  secrets.yaml already configured"
    fi
fi

echo -e "${GREEN}[5/5]${NC} Creating package symlinks..."
# Create packages directory if it doesn't exist
mkdir -p /config/packages

# Symlink PaddiSense packages
if [ -d "/config/PaddiSense/packages" ]; then
    for pkg in /config/PaddiSense/packages/*.yaml; do
        if [ -f "$pkg" ]; then
            pkgname=$(basename "$pkg")
            if [ ! -L "/config/packages/$pkgname" ]; then
                ln -sf "$pkg" "/config/packages/$pkgname"
                echo "  Linked: $pkgname"
            fi
        fi
    done
fi

# Record installation
echo "$(date -Iseconds)" > /config/PaddiSense/.installed

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Register for PaddiSense Basic (free):"
echo -e "   ${BLUE}https://github.com/PaddiSense/registrations/issues/new?template=basic-registration.yml${NC}"
echo ""
echo "2. Restart Home Assistant:"
echo "   ha core restart"
echo ""
echo "3. For PWM/WSS modules, request a license at:"
echo -e "   ${BLUE}https://github.com/PaddiSense/registrations${NC}"
echo ""
echo "Documentation: https://github.com/PaddiSense/PaddiSense/docs"
echo ""
