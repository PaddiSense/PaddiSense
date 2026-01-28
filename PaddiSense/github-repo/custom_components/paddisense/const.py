"""Constants for PaddiSense integration."""
from pathlib import Path

DOMAIN = "paddisense"
VERSION = "2026.1.0"

# Data directories
DATA_DIR = Path("/config/local_data")
REGISTRY_DATA_DIR = DATA_DIR / "registry"
REGISTRY_CONFIG_FILE = REGISTRY_DATA_DIR / "config.json"
REGISTRY_BACKUP_DIR = REGISTRY_DATA_DIR / "backups"

# Server configuration
SERVER_YAML = Path("/config/server.yaml")

# Version file
VERSION_FILE = Path("/config/PaddiSense/registry/VERSION")

# Config keys
CONF_GROWER_NAME = "grower_name"
CONF_FARM_NAME = "farm_name"
CONF_FARM_ID = "farm_id"
CONF_TIMEZONE = "timezone"
CONF_IMPORT_EXISTING = "import_existing"

# Default values
DEFAULT_FARM_ID = "farm_1"
DEFAULT_BAY_PREFIX = "B-"

# Service names
SERVICE_ADD_PADDOCK = "add_paddock"
SERVICE_EDIT_PADDOCK = "edit_paddock"
SERVICE_DELETE_PADDOCK = "delete_paddock"
SERVICE_SET_CURRENT_SEASON = "set_current_season"
SERVICE_ADD_BAY = "add_bay"
SERVICE_EDIT_BAY = "edit_bay"
SERVICE_DELETE_BAY = "delete_bay"
SERVICE_ADD_SEASON = "add_season"
SERVICE_EDIT_SEASON = "edit_season"
SERVICE_DELETE_SEASON = "delete_season"
SERVICE_SET_ACTIVE_SEASON = "set_active_season"
SERVICE_ADD_FARM = "add_farm"
SERVICE_EDIT_FARM = "edit_farm"
SERVICE_DELETE_FARM = "delete_farm"
SERVICE_EXPORT_REGISTRY = "export_registry"
SERVICE_IMPORT_REGISTRY = "import_registry"

# Platforms
PLATFORMS = ["sensor"]

# Sensor attributes
ATTR_PADDOCKS = "paddocks"
ATTR_BAYS = "bays"
ATTR_SEASONS = "seasons"
ATTR_FARMS = "farms"
ATTR_HIERARCHY = "hierarchy"
ATTR_GROWER = "grower"
ATTR_ACTIVE_SEASON = "active_season"
ATTR_ACTIVE_SEASON_NAME = "active_season_name"
ATTR_TOTAL_PADDOCKS = "total_paddocks"
ATTR_TOTAL_BAYS = "total_bays"
ATTR_TOTAL_SEASONS = "total_seasons"
ATTR_TOTAL_FARMS = "total_farms"
