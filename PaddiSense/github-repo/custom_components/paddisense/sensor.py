"""Sensor platform for PaddiSense integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .registry.sensor import async_setup_entry as registry_async_setup_entry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PaddiSense sensors from a config entry."""
    # Delegate to registry sensor setup
    await registry_async_setup_entry(hass, entry, async_add_entities)
