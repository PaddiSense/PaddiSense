#!/bin/bash
# =============================================================================
# HACS Installer for PaddiSense
# Downloads and installs HACS (Home Assistant Community Store)
# =============================================================================

set -e

HACS_DIR="/config/custom_components/hacs"
TEMP_DIR="/config/.hacs_install_temp"

# Check if HACS is already installed
if [ -d "$HACS_DIR" ]; then
    echo "HACS is already installed at $HACS_DIR"
    echo "To reinstall, first remove the existing installation"
    exit 0
fi

echo "Installing HACS..."

# Create temp directory
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Download latest HACS release
echo "Downloading HACS..."
curl -sfSL "https://github.com/hacs/integration/releases/latest/download/hacs.zip" -o hacs.zip

if [ ! -f hacs.zip ]; then
    echo "ERROR: Failed to download HACS"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Create custom_components directory if needed
mkdir -p /config/custom_components

# Extract HACS
echo "Extracting HACS..."
unzip -q hacs.zip -d /config/custom_components/hacs

# Cleanup
cd /config
rm -rf "$TEMP_DIR"

echo "HACS installed successfully!"
echo ""
echo "IMPORTANT: You must restart Home Assistant to complete the installation."
echo "After restart, go to Settings > Devices & Services > Add Integration > HACS"
