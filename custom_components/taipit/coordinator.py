"""Taipit Cloud Coordinator."""
from __future__ import annotations

import logging
from typing import Any

from aiotaipit import SimpleTaipitAuth, TaipitApi

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_INFO,
    CONF_SERIAL_NUMBER,
    CONF_TOKEN,
    DOMAIN,
    REQUEST_REFRESH_DEFAULT_COOLDOWN,
)
from .decorators import async_api_request_handler
from .helpers import get_smart_update_interval, get_update_interval, utc_from_timestamp_tz

_LOGGER = logging.getLogger(__name__)


class TaipitCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Coordinator is responsible for querying the device at a specified route."""

    config_entry: ConfigEntry
    _api: TaipitApi
    force_next_update: bool
    username: str

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialise a custom coordinator."""
        self.force_next_update = False
        session = async_get_clientsession(hass)
        self.username = config_entry.data[CONF_USERNAME]
        auth = SimpleTaipitAuth(
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
            session,
            token=config_entry.data.get(CONF_TOKEN),
            token_update_callback=self._on_token_update,
        )
        self._api = TaipitApi(auth)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=get_update_interval(),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
                immediate=False,
            ),
        )

    def _on_token_update(self, token_data: dict[str, Any]) -> None:
        """Persist updated tokens to config entry."""
        _LOGGER.debug("Tokens updated, persisting to config entry")
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_TOKEN: token_data},
        )

    async def async_force_refresh(self) -> None:
        """Force refresh data."""
        self.force_next_update = True
        await self.async_refresh()

    async def _async_update_data(self) -> dict[int, Any]:
        """Fetch data from Taipit."""
        _data: dict[int, dict[str, Any]] | None = self.data
        try:
            _LOGGER.debug("Start updating Taipit data")
            if _data is None or self.force_next_update:
                # fetch list of meters in account
                _LOGGER.debug("Retrieving meters for user %s", self.username)
                _data = await self._async_get_meters()
                if not _data:
                    raise UpdateFailed(
                        f"No meters retrieved for user {self.username}"
                    )

                _LOGGER.debug(
                    "%d meters retrieved for user %s", len(_data), self.username
                )

                # fetch extended meter info including model name
                for meter_id in _data:
                    meter_info = await self._async_get_meter_info(meter_id)
                    _data[meter_id]["extended"] = meter_info
                    _LOGGER.debug(
                        "Retrieved information for meter %s",
                        _data[meter_id][CONF_INFO][CONF_SERIAL_NUMBER],
                    )

            # fetch the latest readings
            for meter_id in _data:
                serial_number = _data[meter_id][CONF_INFO][CONF_SERIAL_NUMBER]
                _LOGGER.debug("Retrieving readings for meter %s...", serial_number)
                readings = await self._async_get_meter_readings(meter_id)
                _data[meter_id].update(readings)
                _LOGGER.debug("Retrieved readings for meter %s.", serial_number)
                _data[meter_id]["last_update_time"] = utc_from_timestamp_tz(
                    readings["economizer"]["lastReading"]["ts_tz"],
                    readings["economizer"]["timezone"],
                )
            return _data

        finally:
            self.force_next_update = False
            if _data:
                self.update_interval = get_smart_update_interval(_data)
            else:
                self.update_interval = get_update_interval()
            _LOGGER.debug(
                "Next update in %s seconds", self.update_interval.total_seconds()
            )

    @async_api_request_handler
    async def _async_get_meters(self) -> dict[int, dict[str, Any]]:
        """Get all meters and short info from API."""
        all_meters: list[dict[str, Any]] = await self._api.async_get_meters()
        return {int(meter[CONF_ID]): {CONF_INFO: meter} for meter in all_meters}

    @async_api_request_handler
    async def _async_get_meter_info(self, meter_id: int) -> dict[str, Any]:
        """Get meter info from API."""
        return await self._api.async_get_meter_info(meter_id)

    @async_api_request_handler
    async def _async_get_meter_readings(self, meter_id: int) -> dict[str, Any]:
        """Get meter readings from API."""
        return await self._api.async_get_meter_readings(meter_id)
