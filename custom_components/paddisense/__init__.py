"""PaddiSense Farm Management Integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_BAY,
    SERVICE_ADD_FARM,
    SERVICE_ADD_PADDOCK,
    SERVICE_ADD_SEASON,
    SERVICE_DELETE_BAY,
    SERVICE_DELETE_FARM,
    SERVICE_DELETE_PADDOCK,
    SERVICE_DELETE_SEASON,
    SERVICE_EDIT_BAY,
    SERVICE_EDIT_FARM,
    SERVICE_EDIT_PADDOCK,
    SERVICE_EDIT_SEASON,
    SERVICE_EXPORT_REGISTRY,
    SERVICE_IMPORT_REGISTRY,
    SERVICE_SET_ACTIVE_SEASON,
    SERVICE_SET_CURRENT_SEASON,
)
from .registry.backend import RegistryBackend

_LOGGER = logging.getLogger(__name__)

# Service schemas
ADD_PADDOCK_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Required("bay_count"): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Optional("farm_id", default="farm_1"): cv.string,
        vol.Optional("bay_prefix", default="B-"): cv.string,
        vol.Optional("current_season", default=True): cv.boolean,
    }
)

EDIT_PADDOCK_SCHEMA = vol.Schema(
    {
        vol.Required("paddock_id"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("farm_id"): cv.string,
        vol.Optional("current_season"): cv.boolean,
    }
)

DELETE_PADDOCK_SCHEMA = vol.Schema(
    {
        vol.Required("paddock_id"): cv.string,
    }
)

SET_CURRENT_SEASON_SCHEMA = vol.Schema(
    {
        vol.Required("paddock_id"): cv.string,
        vol.Optional("value"): cv.boolean,
    }
)

ADD_BAY_SCHEMA = vol.Schema(
    {
        vol.Required("paddock_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Optional("order"): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("is_last", default=False): cv.boolean,
    }
)

EDIT_BAY_SCHEMA = vol.Schema(
    {
        vol.Required("bay_id"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("order"): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("is_last"): cv.boolean,
    }
)

DELETE_BAY_SCHEMA = vol.Schema(
    {
        vol.Required("bay_id"): cv.string,
    }
)

ADD_SEASON_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Required("start_date"): cv.string,
        vol.Required("end_date"): cv.string,
        vol.Optional("active", default=False): cv.boolean,
    }
)

EDIT_SEASON_SCHEMA = vol.Schema(
    {
        vol.Required("season_id"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("start_date"): cv.string,
        vol.Optional("end_date"): cv.string,
    }
)

DELETE_SEASON_SCHEMA = vol.Schema(
    {
        vol.Required("season_id"): cv.string,
    }
)

SET_ACTIVE_SEASON_SCHEMA = vol.Schema(
    {
        vol.Required("season_id"): cv.string,
    }
)

ADD_FARM_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
    }
)

EDIT_FARM_SCHEMA = vol.Schema(
    {
        vol.Required("farm_id"): cv.string,
        vol.Optional("name"): cv.string,
    }
)

DELETE_FARM_SCHEMA = vol.Schema(
    {
        vol.Required("farm_id"): cv.string,
    }
)

IMPORT_REGISTRY_SCHEMA = vol.Schema(
    {
        vol.Required("filename"): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up PaddiSense from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PaddiSense from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize backend
    backend = RegistryBackend()
    await hass.async_add_executor_job(backend.init)

    # Store backend reference
    hass.data[DOMAIN]["backend"] = backend
    hass.data[DOMAIN]["entry_id"] = entry.entry_id

    # Register services
    await _async_register_services(hass, backend)

    # Register frontend resources
    await _async_register_frontend(hass)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove services
        for service in [
            SERVICE_ADD_PADDOCK,
            SERVICE_EDIT_PADDOCK,
            SERVICE_DELETE_PADDOCK,
            SERVICE_SET_CURRENT_SEASON,
            SERVICE_ADD_BAY,
            SERVICE_EDIT_BAY,
            SERVICE_DELETE_BAY,
            SERVICE_ADD_SEASON,
            SERVICE_EDIT_SEASON,
            SERVICE_DELETE_SEASON,
            SERVICE_SET_ACTIVE_SEASON,
            SERVICE_ADD_FARM,
            SERVICE_EDIT_FARM,
            SERVICE_DELETE_FARM,
            SERVICE_EXPORT_REGISTRY,
            SERVICE_IMPORT_REGISTRY,
        ]:
            hass.services.async_remove(DOMAIN, service)

        hass.data[DOMAIN].pop("backend", None)
        hass.data[DOMAIN].pop("entry_id", None)

    return unload_ok


async def _async_register_services(hass: HomeAssistant, backend: RegistryBackend) -> None:
    """Register PaddiSense services."""

    async def handle_add_paddock(call: ServiceCall) -> None:
        """Handle add_paddock service call."""
        result = await hass.async_add_executor_job(
            backend.add_paddock,
            call.data["name"],
            call.data["bay_count"],
            call.data.get("farm_id", "farm_1"),
            call.data.get("bay_prefix", "B-"),
            call.data.get("current_season", True),
        )
        _log_service_result("add_paddock", result)
        await _async_update_sensors(hass)

    async def handle_edit_paddock(call: ServiceCall) -> None:
        """Handle edit_paddock service call."""
        result = await hass.async_add_executor_job(
            backend.edit_paddock,
            call.data["paddock_id"],
            call.data.get("name"),
            call.data.get("farm_id"),
            call.data.get("current_season"),
        )
        _log_service_result("edit_paddock", result)
        await _async_update_sensors(hass)

    async def handle_delete_paddock(call: ServiceCall) -> None:
        """Handle delete_paddock service call."""
        result = await hass.async_add_executor_job(
            backend.delete_paddock,
            call.data["paddock_id"],
        )
        _log_service_result("delete_paddock", result)
        await _async_update_sensors(hass)

    async def handle_set_current_season(call: ServiceCall) -> None:
        """Handle set_current_season service call."""
        result = await hass.async_add_executor_job(
            backend.set_current_season,
            call.data["paddock_id"],
            call.data.get("value"),
        )
        _log_service_result("set_current_season", result)
        await _async_update_sensors(hass)

    async def handle_add_bay(call: ServiceCall) -> None:
        """Handle add_bay service call."""
        result = await hass.async_add_executor_job(
            backend.add_bay,
            call.data["paddock_id"],
            call.data["name"],
            call.data.get("order"),
            call.data.get("is_last", False),
        )
        _log_service_result("add_bay", result)
        await _async_update_sensors(hass)

    async def handle_edit_bay(call: ServiceCall) -> None:
        """Handle edit_bay service call."""
        result = await hass.async_add_executor_job(
            backend.edit_bay,
            call.data["bay_id"],
            call.data.get("name"),
            call.data.get("order"),
            call.data.get("is_last"),
        )
        _log_service_result("edit_bay", result)
        await _async_update_sensors(hass)

    async def handle_delete_bay(call: ServiceCall) -> None:
        """Handle delete_bay service call."""
        result = await hass.async_add_executor_job(
            backend.delete_bay,
            call.data["bay_id"],
        )
        _log_service_result("delete_bay", result)
        await _async_update_sensors(hass)

    async def handle_add_season(call: ServiceCall) -> None:
        """Handle add_season service call."""
        result = await hass.async_add_executor_job(
            backend.add_season,
            call.data["name"],
            call.data["start_date"],
            call.data["end_date"],
            call.data.get("active", False),
        )
        _log_service_result("add_season", result)
        await _async_update_sensors(hass)

    async def handle_edit_season(call: ServiceCall) -> None:
        """Handle edit_season service call."""
        result = await hass.async_add_executor_job(
            backend.edit_season,
            call.data["season_id"],
            call.data.get("name"),
            call.data.get("start_date"),
            call.data.get("end_date"),
        )
        _log_service_result("edit_season", result)
        await _async_update_sensors(hass)

    async def handle_delete_season(call: ServiceCall) -> None:
        """Handle delete_season service call."""
        result = await hass.async_add_executor_job(
            backend.delete_season,
            call.data["season_id"],
        )
        _log_service_result("delete_season", result)
        await _async_update_sensors(hass)

    async def handle_set_active_season(call: ServiceCall) -> None:
        """Handle set_active_season service call."""
        result = await hass.async_add_executor_job(
            backend.set_active_season,
            call.data["season_id"],
        )
        _log_service_result("set_active_season", result)
        await _async_update_sensors(hass)

    async def handle_add_farm(call: ServiceCall) -> None:
        """Handle add_farm service call."""
        result = await hass.async_add_executor_job(
            backend.add_farm,
            call.data["name"],
        )
        _log_service_result("add_farm", result)
        await _async_update_sensors(hass)

    async def handle_edit_farm(call: ServiceCall) -> None:
        """Handle edit_farm service call."""
        result = await hass.async_add_executor_job(
            backend.edit_farm,
            call.data["farm_id"],
            call.data.get("name"),
        )
        _log_service_result("edit_farm", result)
        await _async_update_sensors(hass)

    async def handle_delete_farm(call: ServiceCall) -> None:
        """Handle delete_farm service call."""
        result = await hass.async_add_executor_job(
            backend.delete_farm,
            call.data["farm_id"],
        )
        _log_service_result("delete_farm", result)
        await _async_update_sensors(hass)

    async def handle_export_registry(call: ServiceCall) -> None:
        """Handle export_registry service call."""
        result = await hass.async_add_executor_job(backend.export_registry)
        _log_service_result("export_registry", result)

    async def handle_import_registry(call: ServiceCall) -> None:
        """Handle import_registry service call."""
        result = await hass.async_add_executor_job(
            backend.import_registry,
            call.data["filename"],
        )
        _log_service_result("import_registry", result)
        await _async_update_sensors(hass)

    # Register all services
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_PADDOCK, handle_add_paddock, schema=ADD_PADDOCK_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_PADDOCK, handle_edit_paddock, schema=EDIT_PADDOCK_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_PADDOCK, handle_delete_paddock, schema=DELETE_PADDOCK_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_CURRENT_SEASON, handle_set_current_season, schema=SET_CURRENT_SEASON_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_BAY, handle_add_bay, schema=ADD_BAY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_BAY, handle_edit_bay, schema=EDIT_BAY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_BAY, handle_delete_bay, schema=DELETE_BAY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_SEASON, handle_add_season, schema=ADD_SEASON_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_SEASON, handle_edit_season, schema=EDIT_SEASON_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_SEASON, handle_delete_season, schema=DELETE_SEASON_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_ACTIVE_SEASON, handle_set_active_season, schema=SET_ACTIVE_SEASON_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_FARM, handle_add_farm, schema=ADD_FARM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_FARM, handle_edit_farm, schema=EDIT_FARM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_FARM, handle_delete_farm, schema=DELETE_FARM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EXPORT_REGISTRY, handle_export_registry
    )
    hass.services.async_register(
        DOMAIN, SERVICE_IMPORT_REGISTRY, handle_import_registry, schema=IMPORT_REGISTRY_SCHEMA
    )


def _log_service_result(service: str, result: dict[str, Any]) -> None:
    """Log service result."""
    if result.get("success"):
        _LOGGER.info("PaddiSense %s: %s", service, result.get("message", "Success"))
    else:
        _LOGGER.error("PaddiSense %s failed: %s", service, result.get("error", "Unknown error"))


async def _async_update_sensors(hass: HomeAssistant) -> None:
    """Trigger sensor update after data change."""
    # Fire event to trigger sensor update
    hass.bus.async_fire(f"{DOMAIN}_data_updated")


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register frontend resources."""
    # Register custom card JS as a static path
    hass.http.register_static_path(
        "/paddisense/paddisense-registry-card.js",
        hass.config.path("custom_components/paddisense/www/paddisense-registry-card.js"),
        cache_headers=False,
    )

    _LOGGER.info(
        "PaddiSense frontend registered. Add to Lovelace resources: "
        "/paddisense/paddisense-registry-card.js"
    )
