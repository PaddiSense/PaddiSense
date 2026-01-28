"""Sensor platform for PaddiSense Farm Registry."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import (
    ATTR_ACTIVE_SEASON,
    ATTR_ACTIVE_SEASON_NAME,
    ATTR_BAYS,
    ATTR_FARMS,
    ATTR_GROWER,
    ATTR_HIERARCHY,
    ATTR_PADDOCKS,
    ATTR_SEASONS,
    ATTR_TOTAL_BAYS,
    ATTR_TOTAL_FARMS,
    ATTR_TOTAL_PADDOCKS,
    ATTR_TOTAL_SEASONS,
    DOMAIN,
    VERSION,
)
from ..helpers import (
    extract_farms,
    extract_grower,
    get_active_season,
    get_version,
    load_registry_config,
    load_server_yaml,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PaddiSense sensors from a config entry."""
    entities = [
        PaddiSenseRegistrySensor(hass, entry),
        PaddiSenseVersionSensor(hass, entry),
    ]
    async_add_entities(entities)


class PaddiSenseRegistrySensor(SensorEntity):
    """Sensor exposing farm registry data."""

    _attr_has_entity_name = True
    _attr_name = "Registry"
    _attr_icon = "mdi:barn"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_registry"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PaddiSense",
            "manufacturer": "PaddiSense",
            "model": "Farm Registry",
            "sw_version": VERSION,
        }
        self._data: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Listen for data update events
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_data_updated", self._handle_data_update
            )
        )

        # Initial data load
        await self._async_update_data()

    @callback
    def _handle_data_update(self, event) -> None:
        """Handle data update event."""
        self.hass.async_create_task(self._async_update_data())

    async def _async_update_data(self) -> None:
        """Update sensor data."""
        config = await self.hass.async_add_executor_job(load_registry_config)
        server = await self.hass.async_add_executor_job(load_server_yaml)

        grower = extract_grower(server)
        registry_farms = config.get("farms", {})
        farms = extract_farms(server, registry_farms)
        paddocks = config.get("paddocks", {})
        bays = config.get("bays", {})
        seasons = config.get("seasons", {})

        active_season = get_active_season(seasons)
        active_season_name = (
            seasons.get(active_season, {}).get("name") if active_season else None
        )

        # Build hierarchy for UI
        hierarchy = self._build_hierarchy(farms, paddocks, bays)

        self._data = {
            "status": "ready" if config.get("initialized") else "not_initialized",
            "initialized": config.get("initialized", False),
            ATTR_GROWER: grower,
            ATTR_FARMS: farms,
            ATTR_PADDOCKS: paddocks,
            ATTR_BAYS: bays,
            ATTR_SEASONS: seasons,
            ATTR_HIERARCHY: hierarchy,
            ATTR_ACTIVE_SEASON: active_season,
            ATTR_ACTIVE_SEASON_NAME: active_season_name,
            ATTR_TOTAL_FARMS: len(farms),
            ATTR_TOTAL_PADDOCKS: len(paddocks),
            ATTR_TOTAL_BAYS: len(bays),
            ATTR_TOTAL_SEASONS: len(seasons),
            "farm_names": sorted([f.get("name", fid) for fid, f in farms.items()]),
            "paddock_names": sorted(
                [p.get("name", pid) for pid, p in paddocks.items()]
            ),
            "season_names": sorted([s.get("name", sid) for sid, s in seasons.items()]),
        }

        self.async_write_ha_state()

    def _build_hierarchy(
        self,
        farms: dict[str, Any],
        paddocks: dict[str, Any],
        bays: dict[str, Any],
    ) -> dict[str, Any]:
        """Build hierarchical summary for UI."""
        hierarchy = {}

        for farm_id, farm in farms.items():
            farm_paddocks = {
                pid: p
                for pid, p in paddocks.items()
                if p.get("farm_id") == farm_id
            }

            paddock_data = {}
            for pid, paddock in farm_paddocks.items():
                paddock_bays = [
                    {"id": bid, "name": b.get("name"), "order": b.get("order", 0)}
                    for bid, b in bays.items()
                    if b.get("paddock_id") == pid
                ]
                paddock_bays.sort(key=lambda x: x["order"])

                paddock_data[pid] = {
                    "name": paddock.get("name", pid),
                    "bay_count": len(paddock_bays),
                    "bays": paddock_bays,
                    "current_season": paddock.get("current_season", True),
                }

            hierarchy[farm_id] = {
                "name": farm.get("name", farm_id),
                "paddock_count": len(farm_paddocks),
                "paddocks": paddock_data,
            }

        return hierarchy

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._data.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._data

    async def async_update(self) -> None:
        """Update the sensor."""
        await self._async_update_data()


class PaddiSenseVersionSensor(SensorEntity):
    """Sensor exposing PaddiSense version."""

    _attr_has_entity_name = True
    _attr_name = "Version"
    _attr_icon = "mdi:tag"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_version"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PaddiSense",
            "manufacturer": "PaddiSense",
            "model": "Farm Registry",
            "sw_version": VERSION,
        }

    @property
    def native_value(self) -> str:
        """Return the version."""
        return VERSION

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        module_version = get_version()
        return {
            "integration_version": VERSION,
            "module_version": module_version,
            "domain": DOMAIN,
        }
