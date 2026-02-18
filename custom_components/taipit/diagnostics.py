"""Diagnostics support for Taipit."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TaipitConfigEntry

TO_REDACT_CONFIG = {
    "username",
    "password",
    "token",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TaipitConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    meters_data: dict[str, Any] = {}
    if coordinator.data:
        for meter_id, meter_data in coordinator.data.items():
            meters_data[str(meter_id)] = meter_data

    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT_CONFIG),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "meters": meters_data,
        },
    }
