"""Config flow for PaddiSense integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_FARM_ID,
    CONF_FARM_NAME,
    CONF_GROWER_NAME,
    CONF_IMPORT_EXISTING,
    DEFAULT_BAY_PREFIX,
    DEFAULT_FARM_ID,
    DOMAIN,
)
from .helpers import (
    existing_data_detected,
    extract_grower,
    get_existing_data_summary,
    load_server_yaml,
)
from .registry.backend import RegistryBackend


class PaddiSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PaddiSense."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict = {}
        self._existing_data: dict = {}

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step - welcome and existing data detection."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        # Check for existing data
        has_existing = await self.hass.async_add_executor_job(existing_data_detected)

        if has_existing:
            self._existing_data = await self.hass.async_add_executor_job(
                get_existing_data_summary
            )
            return await self.async_step_detect_existing()

        return await self.async_step_farm()

    async def async_step_detect_existing(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle existing data detection."""
        if user_input is not None:
            if user_input.get(CONF_IMPORT_EXISTING):
                # Import existing data
                self._data[CONF_IMPORT_EXISTING] = True
                return await self.async_step_import_confirm()
            else:
                # Fresh start - will initialize new config
                return await self.async_step_farm()

        summary = self._existing_data
        description_placeholders = {
            "paddock_count": str(summary.get("paddock_count", 0)),
            "bay_count": str(summary.get("bay_count", 0)),
            "season_count": str(summary.get("season_count", 0)),
        }

        return self.async_show_form(
            step_id="detect_existing",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IMPORT_EXISTING, default=True): bool,
                }
            ),
            description_placeholders=description_placeholders,
        )

    async def async_step_import_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Confirm import of existing data."""
        if user_input is not None:
            # Load server.yaml for grower info
            server_config = await self.hass.async_add_executor_job(load_server_yaml)
            grower = extract_grower(server_config)

            self._data[CONF_GROWER_NAME] = grower.get("name", "PaddiSense Farm")

            # Initialize backend (ensures directories exist)
            backend = RegistryBackend()
            await self.hass.async_add_executor_job(backend.init)

            return self.async_create_entry(
                title=self._data[CONF_GROWER_NAME],
                data=self._data,
            )

        summary = self._existing_data
        description_placeholders = {
            "paddock_count": str(summary.get("paddock_count", 0)),
            "bay_count": str(summary.get("bay_count", 0)),
            "season_count": str(summary.get("season_count", 0)),
        }

        return self.async_show_form(
            step_id="import_confirm",
            description_placeholders=description_placeholders,
        )

    async def async_step_farm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle farm setup step."""
        errors = {}

        if user_input is not None:
            self._data[CONF_GROWER_NAME] = user_input[CONF_GROWER_NAME]
            self._data[CONF_FARM_NAME] = user_input[CONF_FARM_NAME]
            self._data[CONF_FARM_ID] = DEFAULT_FARM_ID

            return await self.async_step_paddock()

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
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GROWER_NAME,
                        default=grower.get("name", "PaddiSense Farm"),
                    ): str,
                    vol.Required(
                        CONF_FARM_NAME,
                        default=default_farm_name,
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_paddock(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle optional first paddock setup."""
        errors = {}

        if user_input is not None:
            # Initialize backend
            backend = RegistryBackend()
            await self.hass.async_add_executor_job(backend.init)

            # Add farm if specified
            farm_name = self._data.get(CONF_FARM_NAME, "Main Farm")
            await self.hass.async_add_executor_job(backend.add_farm, farm_name)

            # Add paddock if specified
            paddock_name = user_input.get("paddock_name", "").strip()
            if paddock_name:
                bay_count = user_input.get("bay_count", 1)
                bay_prefix = user_input.get("bay_prefix", DEFAULT_BAY_PREFIX)

                result = await self.hass.async_add_executor_job(
                    backend.add_paddock,
                    paddock_name,
                    bay_count,
                    DEFAULT_FARM_ID,
                    bay_prefix,
                    True,
                )

                if not result.get("success"):
                    errors["base"] = "paddock_error"
                    return self.async_show_form(
                        step_id="paddock",
                        data_schema=self._get_paddock_schema(),
                        errors=errors,
                    )

            return self.async_create_entry(
                title=self._data[CONF_GROWER_NAME],
                data=self._data,
            )

        return self.async_show_form(
            step_id="paddock",
            data_schema=self._get_paddock_schema(),
            errors=errors,
        )

    def _get_paddock_schema(self) -> vol.Schema:
        """Get the paddock setup schema."""
        return vol.Schema(
            {
                vol.Optional("paddock_name", default=""): str,
                vol.Optional("bay_count", default=5): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=50)
                ),
                vol.Optional("bay_prefix", default=DEFAULT_BAY_PREFIX): str,
            }
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
            menu_options=["paddock_management", "season_management", "export_import"],
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
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        {"add": "Add Paddock", "delete": "Delete Paddock"}
                    ),
                }
            ),
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
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required("bay_count", default=5): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=50)
                    ),
                    vol.Optional("bay_prefix", default=DEFAULT_BAY_PREFIX): str,
                }
            ),
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

        # Get list of paddocks
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
            data_schema=vol.Schema(
                {
                    vol.Required("paddock_id"): vol.In(paddock_options),
                }
            ),
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
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        {"add": "Add Season", "set_active": "Set Active Season"}
                    ),
                }
            ),
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
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required("start_date"): str,
                    vol.Required("end_date"): str,
                    vol.Optional("active", default=False): bool,
                }
            ),
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

        # Get list of seasons
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
            data_schema=vol.Schema(
                {
                    vol.Required("season_id"): vol.In(season_options),
                }
            ),
            errors=errors,
        )

    async def async_step_export_import(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Export/Import options."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "export":
                backend = RegistryBackend()
                result = await self.hass.async_add_executor_job(backend.export_registry)
                if result.get("success"):
                    return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="export_import",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        {"export": "Export Backup"}
                    ),
                }
            ),
        )
