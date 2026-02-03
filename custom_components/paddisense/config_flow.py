"""Config flow for PaddiSense integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    AVAILABLE_MODULES,
    CONFIG_DIR,
    CONF_FARM_ID,
    CONF_FARM_NAME,
    CONF_GITHUB_TOKEN,
    CONF_GROWER_NAME,
    CONF_IMPORT_EXISTING,
    CONF_INSTALL_TYPE,
    CONF_LICENSE_EXPIRY,
    CONF_LICENSE_GROWER,
    CONF_LICENSE_KEY,
    CONF_LICENSE_MODULES,
    CONF_LICENSE_SEASON,
    CONF_SELECTED_MODULES,
    DEFAULT_BAY_PREFIX,
    DEFAULT_FARM_ID,
    DOMAIN,
    INSTALL_TYPE_FRESH,
    INSTALL_TYPE_IMPORT,
    INSTALL_TYPE_UPGRADE,
    MODULE_METADATA,
)

# Dev mode bypass - skip license validation if .dev_mode file exists
DEV_MODE_FILE = CONFIG_DIR / ".dev_mode"
from .license import LicenseError, validate_license
from .helpers import (
    existing_data_detected,
    existing_repo_detected,
    extract_grower,
    get_existing_data_summary,
    get_repo_summary,
    load_server_yaml,
)
from .installer import BackupManager, ConfigWriter, GitManager, ModuleManager
from .registry.backend import RegistryBackend

_LOGGER = logging.getLogger(__name__)


class PaddiSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PaddiSense."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict = {}
        self._existing_data: dict = {}
        self._repo_summary: dict = {}
        self._git_available = False
        self._selected_modules: list[str] = []

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step - welcome and detection."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        # Check for existing repo and data
        has_repo = await self.hass.async_add_executor_job(existing_repo_detected)
        has_data = await self.hass.async_add_executor_job(existing_data_detected)

        if has_repo:
            self._repo_summary = await self.hass.async_add_executor_job(get_repo_summary)

        if has_data:
            self._existing_data = await self.hass.async_add_executor_job(get_existing_data_summary)

        # Determine available options
        if has_repo and has_data:
            # Both exist - offer upgrade
            return await self.async_step_welcome_upgrade()
        elif has_data:
            # Data exists but no repo - offer import
            return await self.async_step_welcome_import()
        else:
            # Fresh install
            return await self.async_step_welcome_fresh()

    async def async_step_welcome_fresh(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Welcome screen for fresh installation."""
        if user_input is not None:
            self._data[CONF_INSTALL_TYPE] = INSTALL_TYPE_FRESH
            return await self.async_step_farm()

        return self.async_show_form(
            step_id="welcome_fresh",
            description_placeholders={
                "title": "Welcome to PaddiSense!",
            },
        )

    async def async_step_welcome_upgrade(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Welcome screen when existing installation detected."""
        if user_input is not None:
            install_type = user_input.get("install_type", INSTALL_TYPE_UPGRADE)
            self._data[CONF_INSTALL_TYPE] = install_type
            # Both fresh and upgrade go to farm setup first
            return await self.async_step_farm()

        return self.async_show_form(
            step_id="welcome_upgrade",
            data_schema=vol.Schema({
                vol.Required("install_type", default=INSTALL_TYPE_UPGRADE): vol.In({
                    INSTALL_TYPE_UPGRADE: "Upgrade existing installation",
                    INSTALL_TYPE_FRESH: "Fresh installation (re-download)",
                }),
            }),
            description_placeholders={
                "version": self._repo_summary.get("version", "unknown"),
                "module_count": str(self._repo_summary.get("module_count", 0)),
                "paddock_count": str(self._existing_data.get("paddock_count", 0)),
                "bay_count": str(self._existing_data.get("bay_count", 0)),
            },
        )

    async def async_step_welcome_import(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Welcome screen when only data exists (no repo)."""
        if user_input is not None:
            if user_input.get(CONF_IMPORT_EXISTING):
                self._data[CONF_INSTALL_TYPE] = INSTALL_TYPE_IMPORT
                self._data[CONF_IMPORT_EXISTING] = True
            else:
                self._data[CONF_INSTALL_TYPE] = INSTALL_TYPE_FRESH

            return await self.async_step_farm()

        return self.async_show_form(
            step_id="welcome_import",
            data_schema=vol.Schema({
                vol.Required(CONF_IMPORT_EXISTING, default=True): bool,
            }),
            description_placeholders={
                "paddock_count": str(self._existing_data.get("paddock_count", 0)),
                "bay_count": str(self._existing_data.get("bay_count", 0)),
                "season_count": str(self._existing_data.get("season_count", 0)),
            },
        )

    async def async_step_git_check(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Check if git is available."""
        # Dev mode bypass - skip git operations if repo already exists
        is_dev_mode = await self.hass.async_add_executor_job(DEV_MODE_FILE.exists)
        git_manager = GitManager(token=self._data.get(CONF_GITHUB_TOKEN))
        is_cloned = await self.hass.async_add_executor_job(git_manager.is_repo_cloned)

        if is_dev_mode and is_cloned:
            _LOGGER.info("Dev mode: Skipping git operations, using existing repo")
            return await self.async_step_modules()

        self._git_available = await self.hass.async_add_executor_job(
            git_manager.is_git_available
        )

        if not self._git_available:
            return self.async_abort(reason="git_not_available")

        # Proceed to clone/pull repo
        return await self.async_step_clone_repo()

    async def async_step_clone_repo(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Clone the PaddiSense repository."""
        git_manager = GitManager(token=self._data.get(CONF_GITHUB_TOKEN))

        # Check if already cloned
        is_cloned = await self.hass.async_add_executor_job(git_manager.is_repo_cloned)

        if is_cloned:
            # Pull latest instead
            result = await self.hass.async_add_executor_job(git_manager.pull)
        else:
            # Clone fresh
            result = await self.hass.async_add_executor_job(git_manager.clone)

        if not result.get("success"):
            return self.async_abort(
                reason="clone_failed",
                description_placeholders={"error": result.get("error", "Unknown error")},
            )

        return await self.async_step_modules()

    async def async_step_farm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle farm setup step."""
        errors = {}

        if user_input is not None:
            self._data[CONF_GROWER_NAME] = user_input[CONF_GROWER_NAME]
            self._data[CONF_FARM_NAME] = user_input[CONF_FARM_NAME]
            self._data[CONF_FARM_ID] = DEFAULT_FARM_ID

            return await self.async_step_license()

        # Try to get defaults from server.yaml
        server_config = await self.hass.async_add_executor_job(load_server_yaml)
        grower = extract_grower(server_config)

        pwm_farms = server_config.get("pwm", {}).get("farms", {})
        default_farm_name = "Main Farm"
        if pwm_farms:
            first_farm = list(pwm_farms.values())[0]
            default_farm_name = first_farm.get("name", "Main Farm")

        return self.async_show_form(
            step_id="farm",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_GROWER_NAME,
                    default=grower.get("name", "PaddiSense Farm"),
                ): str,
                vol.Required(
                    CONF_FARM_NAME,
                    default=default_farm_name,
                ): str,
            }),
            errors=errors,
        )

    async def async_step_license(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """License key validation step."""
        errors = {}

        # Dev mode bypass - skip license if .dev_mode file exists
        is_dev_mode = await self.hass.async_add_executor_job(DEV_MODE_FILE.exists)
        if is_dev_mode:
            _LOGGER.info("Dev mode detected - bypassing license validation")
            self._data[CONF_LICENSE_KEY] = "DEV_MODE"
            self._data[CONF_LICENSE_GROWER] = "Developer"
            self._data[CONF_LICENSE_EXPIRY] = "2099-12-31"
            self._data[CONF_LICENSE_MODULES] = AVAILABLE_MODULES
            self._data[CONF_LICENSE_SEASON] = "DEV"
            self._data[CONF_GITHUB_TOKEN] = ""
            return await self.async_step_git_check()

        if user_input is not None:
            key = user_input.get(CONF_LICENSE_KEY, "").strip()

            try:
                license_info = await self.hass.async_add_executor_job(
                    validate_license, key
                )

                # Store license data
                self._data[CONF_LICENSE_KEY] = key
                self._data[CONF_LICENSE_GROWER] = license_info.grower
                self._data[CONF_LICENSE_EXPIRY] = license_info.expiry.isoformat()
                self._data[CONF_LICENSE_MODULES] = license_info.modules
                self._data[CONF_LICENSE_SEASON] = license_info.season
                self._data[CONF_GITHUB_TOKEN] = license_info.github_token

                # Auto-fill grower name if license grower differs
                if license_info.grower and not self._data.get(CONF_GROWER_NAME):
                    self._data[CONF_GROWER_NAME] = license_info.grower

                return await self.async_step_git_check()

            except LicenseError as err:
                errors["base"] = str(err)

        return self.async_show_form(
            step_id="license",
            data_schema=vol.Schema({
                vol.Required(CONF_LICENSE_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "grower_name": self._data.get(CONF_GROWER_NAME, ""),
                "farm_name": self._data.get(CONF_FARM_NAME, ""),
            },
        )

    async def async_step_modules(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle module selection step."""
        errors = {}

        # Get allowed modules from license (default to all if no license)
        allowed_modules = self._data.get(CONF_LICENSE_MODULES, AVAILABLE_MODULES)

        if user_input is not None:
            # Collect selected modules (only from allowed list)
            self._selected_modules = []
            for module_id in AVAILABLE_MODULES:
                if module_id in allowed_modules:
                    if user_input.get(f"module_{module_id}", False):
                        self._selected_modules.append(module_id)

            self._data[CONF_SELECTED_MODULES] = self._selected_modules

            return await self.async_step_install()

        # Build schema with module checkboxes (only show licensed modules)
        schema_dict = {}
        for module_id in AVAILABLE_MODULES:
            if module_id in allowed_modules:
                # Default IPM and ASM to checked if licensed
                default = module_id in ["ipm", "asm"]
                schema_dict[vol.Optional(f"module_{module_id}", default=default)] = bool

        return self.async_show_form(
            step_id="modules",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "ipm_name": MODULE_METADATA["ipm"]["name"],
                "ipm_desc": MODULE_METADATA["ipm"]["description"],
                "asm_name": MODULE_METADATA["asm"]["name"],
                "asm_desc": MODULE_METADATA["asm"]["description"],
                "weather_name": MODULE_METADATA["weather"]["name"],
                "weather_desc": MODULE_METADATA["weather"]["description"],
                "pwm_name": MODULE_METADATA["pwm"]["name"],
                "pwm_desc": MODULE_METADATA["pwm"]["description"],
            },
            errors=errors,
        )

    async def async_step_install(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Perform installation."""
        # Initialize backend
        backend = RegistryBackend()
        await self.hass.async_add_executor_job(backend.init)

        # Add farm if this is a fresh install
        if self._data.get(CONF_INSTALL_TYPE) != INSTALL_TYPE_IMPORT:
            farm_name = self._data.get(CONF_FARM_NAME, "Main Farm")
            await self.hass.async_add_executor_job(backend.add_farm, farm_name)

        # Install selected modules
        if self._selected_modules:
            module_manager = ModuleManager()
            result = await self.hass.async_add_executor_job(
                module_manager.install_multiple,
                self._selected_modules,
            )
            if not result.get("success"):
                _LOGGER.warning("Some modules failed to install: %s", result)

        # Update configuration.yaml
        config_writer = ConfigWriter()

        # Create lovelace_dashboards.yaml if needed
        await self.hass.async_add_executor_job(
            config_writer.create_lovelace_dashboards_file
        )

        # Update configuration.yaml
        config_result = await self.hass.async_add_executor_job(
            config_writer.update_configuration
        )
        if not config_result.get("success"):
            _LOGGER.warning("Could not update configuration.yaml: %s", config_result)

        # Create entry
        return self.async_create_entry(
            title=self._data.get(CONF_GROWER_NAME, "PaddiSense"),
            data=self._data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PaddiSenseOptionsFlow:
        """Get the options flow for this handler."""
        return PaddiSenseOptionsFlow(config_entry)


class PaddiSenseOptionsFlow(config_entries.OptionsFlow):
    """Handle PaddiSense options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "renew_license",
                "module_management",
                "paddock_management",
                "season_management",
                "backup_restore",
            ],
        )

    async def async_step_renew_license(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Renew license key (simple copy-paste)."""
        errors = {}

        if user_input is not None:
            key = user_input.get(CONF_LICENSE_KEY, "").strip()
            try:
                license_info = await self.hass.async_add_executor_job(
                    validate_license, key
                )
                # Update config entry with new license data
                new_data = {**self._config_entry.data}
                new_data[CONF_LICENSE_KEY] = key
                new_data[CONF_LICENSE_GROWER] = license_info.grower
                new_data[CONF_LICENSE_EXPIRY] = license_info.expiry.isoformat()
                new_data[CONF_LICENSE_MODULES] = license_info.modules
                new_data[CONF_LICENSE_SEASON] = license_info.season
                new_data[CONF_GITHUB_TOKEN] = license_info.github_token

                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=new_data
                )
                return self.async_create_entry(title="", data={})
            except LicenseError as err:
                errors["base"] = str(err)

        return self.async_show_form(
            step_id="renew_license",
            data_schema=vol.Schema({
                vol.Required(CONF_LICENSE_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "current_expiry": self._config_entry.data.get(CONF_LICENSE_EXPIRY, "Unknown"),
                "grower": self._config_entry.data.get(CONF_LICENSE_GROWER, "Unknown"),
            },
        )

    async def async_step_module_management(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Manage modules."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "install":
                return await self.async_step_install_module()
            elif action == "remove":
                return await self.async_step_remove_module()

        return self.async_show_form(
            step_id="module_management",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "install": "Install Module",
                    "remove": "Remove Module",
                }),
            }),
        )

    async def async_step_install_module(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Install a module."""
        module_manager = ModuleManager()
        available = await self.hass.async_add_executor_job(
            module_manager.get_available_modules
        )

        if not available:
            return self.async_abort(reason="no_modules_available")

        if user_input is not None:
            result = await self.hass.async_add_executor_job(
                module_manager.install_module,
                user_input["module_id"],
            )
            if result.get("success") and result.get("restart_required"):
                await self.hass.services.async_call("homeassistant", "restart")
            return self.async_create_entry(title="", data={})

        module_options = {m["id"]: f"{m['name']} ({m['version']})" for m in available}

        return self.async_show_form(
            step_id="install_module",
            data_schema=vol.Schema({
                vol.Required("module_id"): vol.In(module_options),
            }),
        )

    async def async_step_remove_module(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Remove a module."""
        module_manager = ModuleManager()
        installed = await self.hass.async_add_executor_job(
            module_manager.get_installed_modules
        )

        if not installed:
            return self.async_abort(reason="no_modules_installed")

        if user_input is not None:
            result = await self.hass.async_add_executor_job(
                module_manager.remove_module,
                user_input["module_id"],
            )
            if result.get("success") and result.get("restart_required"):
                await self.hass.services.async_call("homeassistant", "restart")
            return self.async_create_entry(title="", data={})

        module_options = {m["id"]: f"{m['name']} ({m['version']})" for m in installed}

        return self.async_show_form(
            step_id="remove_module",
            data_schema=vol.Schema({
                vol.Required("module_id"): vol.In(module_options),
            }),
        )

    async def async_step_paddock_management(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Manage paddocks."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add":
                return await self.async_step_add_paddock()
            elif action == "delete":
                return await self.async_step_delete_paddock()

        return self.async_show_form(
            step_id="paddock_management",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "add": "Add Paddock",
                    "delete": "Delete Paddock",
                }),
            }),
        )

    async def async_step_add_paddock(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Add a new paddock."""
        errors = {}

        if user_input is not None:
            backend = RegistryBackend()
            result = await self.hass.async_add_executor_job(
                backend.add_paddock,
                user_input["name"],
                user_input["bay_count"],
                DEFAULT_FARM_ID,
                user_input.get("bay_prefix", DEFAULT_BAY_PREFIX),
                True,
            )

            if result.get("success"):
                return self.async_create_entry(title="", data={})
            else:
                errors["base"] = "paddock_error"

        return self.async_show_form(
            step_id="add_paddock",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("bay_count", default=5): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=50)
                ),
                vol.Optional("bay_prefix", default=DEFAULT_BAY_PREFIX): str,
            }),
            errors=errors,
        )

    async def async_step_delete_paddock(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Delete a paddock."""
        errors = {}

        if user_input is not None:
            backend = RegistryBackend()
            result = await self.hass.async_add_executor_job(
                backend.delete_paddock,
                user_input["paddock_id"],
            )

            if result.get("success"):
                return self.async_create_entry(title="", data={})
            else:
                errors["base"] = "delete_error"

        from .helpers import load_registry_config
        config = await self.hass.async_add_executor_job(load_registry_config)
        paddocks = config.get("paddocks", {})

        if not paddocks:
            return self.async_abort(reason="no_paddocks")

        paddock_options = {
            pid: f"{p.get('name', pid)} ({p.get('bay_count', 0)} bays)"
            for pid, p in paddocks.items()
        }

        return self.async_show_form(
            step_id="delete_paddock",
            data_schema=vol.Schema({
                vol.Required("paddock_id"): vol.In(paddock_options),
            }),
            errors=errors,
        )

    async def async_step_season_management(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Manage seasons."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add":
                return await self.async_step_add_season()
            elif action == "set_active":
                return await self.async_step_set_active_season()

        return self.async_show_form(
            step_id="season_management",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "add": "Add Season",
                    "set_active": "Set Active Season",
                }),
            }),
        )

    async def async_step_add_season(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Add a new season."""
        errors = {}

        if user_input is not None:
            backend = RegistryBackend()
            result = await self.hass.async_add_executor_job(
                backend.add_season,
                user_input["name"],
                user_input["start_date"],
                user_input["end_date"],
                user_input.get("active", False),
            )

            if result.get("success"):
                return self.async_create_entry(title="", data={})
            else:
                errors["base"] = "season_error"

        return self.async_show_form(
            step_id="add_season",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("start_date"): str,
                vol.Required("end_date"): str,
                vol.Optional("active", default=False): bool,
            }),
            errors=errors,
        )

    async def async_step_set_active_season(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Set active season."""
        errors = {}

        if user_input is not None:
            backend = RegistryBackend()
            result = await self.hass.async_add_executor_job(
                backend.set_active_season,
                user_input["season_id"],
            )

            if result.get("success"):
                return self.async_create_entry(title="", data={})
            else:
                errors["base"] = "season_error"

        from .helpers import load_registry_config
        config = await self.hass.async_add_executor_job(load_registry_config)
        seasons = config.get("seasons", {})

        if not seasons:
            return self.async_abort(reason="no_seasons")

        season_options = {
            sid: f"{s.get('name', sid)} ({s.get('start_date', '')} - {s.get('end_date', '')})"
            for sid, s in seasons.items()
        }

        return self.async_show_form(
            step_id="set_active_season",
            data_schema=vol.Schema({
                vol.Required("season_id"): vol.In(season_options),
            }),
            errors=errors,
        )

    async def async_step_backup_restore(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Backup and restore options."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "backup":
                backup_manager = BackupManager()
                result = await self.hass.async_add_executor_job(
                    backup_manager.create_backup, "manual"
                )
                return self.async_create_entry(title="", data={})
            elif action == "restore":
                return await self.async_step_restore_backup()

        return self.async_show_form(
            step_id="backup_restore",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "backup": "Create Backup",
                    "restore": "Restore from Backup",
                }),
            }),
        )

    async def async_step_restore_backup(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Restore from backup."""
        backup_manager = BackupManager()
        backups = await self.hass.async_add_executor_job(backup_manager.list_backups)

        if not backups:
            return self.async_abort(reason="no_backups")

        if user_input is not None:
            result = await self.hass.async_add_executor_job(
                backup_manager.restore_backup,
                user_input["backup_id"],
            )
            if result.get("success") and result.get("restart_required"):
                await self.hass.services.async_call("homeassistant", "restart")
            return self.async_create_entry(title="", data={})

        backup_options = {
            b["backup_id"]: f"{b['backup_id']} ({b.get('tag', '')})"
            for b in backups[:10]  # Show last 10
        }

        return self.async_show_form(
            step_id="restore_backup",
            data_schema=vol.Schema({
                vol.Required("backup_id"): vol.In(backup_options),
            }),
        )
