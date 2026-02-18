"""The taipit integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS
from .coordinator import TaipitCoordinator

_LOGGER = logging.getLogger(__name__)

type TaipitConfigEntry = ConfigEntry[TaipitCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TaipitConfigEntry) -> bool:
    """Set up taipit from a config entry."""
    coordinator = TaipitCoordinator(hass, config_entry=entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    _async_remove_stale_devices(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def _async_remove_stale_devices(
    hass: HomeAssistant,
    entry: TaipitConfigEntry,
    coordinator: TaipitCoordinator,
) -> None:
    """Remove device entries for meters that no longer exist."""
    device_registry = dr.async_get(hass)

    current_identifiers: set[str] = set()
    if coordinator.data:
        for meter_id in coordinator.data:
            current_identifiers.add(str(meter_id))

    for device_entry in dr.async_entries_for_config_entry(
        device_registry, entry.entry_id
    ):
        if not any(
            ident[0] == DOMAIN and ident[1] in current_identifiers
            for ident in device_entry.identifiers
        ):
            _LOGGER.info(
                "Removing stale device %s (%s)",
                device_entry.name,
                device_entry.id,
            )
            device_registry.async_remove_device(device_entry.id)


async def async_unload_entry(hass: HomeAssistant, entry: TaipitConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
