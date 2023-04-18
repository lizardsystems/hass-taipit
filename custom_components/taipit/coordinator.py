"""Taipit Cloud Coordinator."""
from __future__ import annotations

from logging import getLogger
from typing import Any

from aiotaipit import TaipitApi, SimpleTaipitAuth
from aiotaipit.exceptions import (
    TaipitAuthInvalidGrant,
    TaipitError,
    TaipitAuthInvalidClient,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import annotations

from .const import DOMAIN, CONF_INFO, CONF_SERIAL_NUMBER
from .decorators import api_request_handler
from .helpers import get_interval_to


class TaipitCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Coordinator is responsible for querying the device at a specified route."""

    _api: TaipitApi
    force_next_update: bool
    username: str
    password: str

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialise a custom coordinator."""
        self.force_next_update = False
        session = async_get_clientsession(hass)
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        auth = SimpleTaipitAuth(self.username, self.password, session)
        self._api = TaipitApi(auth)

        super().__init__(hass, getLogger(__name__), name=DOMAIN)

    async def async_force_refresh(self):
        """Force refresh data."""
        self.force_next_update = True
        await self.async_refresh()

    async def _async_update_data(self) -> dict[int, Any] | None:
        """Fetch data from Taipit."""
        try:
            self.logger.debug("Start updating Taipit data")
            _data: dict[int, dict] = self.data

            if _data is None or self.force_next_update:
                # fetch list of meters in account
                self.logger.debug("Retrieving meters for user %s", self.username)
                _data = await self._async_get_meters()
                if _data:
                    self.logger.debug(
                        "%d meters retrieved for user %s", len(_data), self.username
                    )
                else:
                    self.logger.warning(
                        "No meters retrieved for user %s", self.username
                    )
                    return None

                # fetch extended meter info including model name
                for meter_id in _data:
                    meter_info = await self._async_get_meter_info(meter_id)
                    _data[meter_id]["extended"] = meter_info
                    self.logger.debug(
                        "Retrieved information for meter %s",
                        _data[meter_id][CONF_INFO][CONF_SERIAL_NUMBER],
                    )

            # fetch the latest readings
            for meter_id in _data:
                serial_number = _data[meter_id][CONF_INFO][CONF_SERIAL_NUMBER]
                self.logger.debug("Retrieving readings for meter %s...", serial_number)
                readings = await self._async_get_meter_readings(meter_id)
                _data[meter_id].update(readings)
                self.logger.debug("Retrieved readings for meter %s.", serial_number)

            return _data

        except TaipitAuthInvalidGrant as exc:
            raise ConfigEntryAuthFailed("Incorrect Login or Password") from exc
        except TaipitAuthInvalidClient as exc:
            raise ConfigEntryAuthFailed("Incorrect client_id or client_secret") from exc
        except TaipitError as exc:
            raise ConfigEntryNotReady("Can not connect to host") from exc
        finally:
            self.force_next_update = False
            self.update_interval = get_interval_to([0], [1, 31], list(range(24)))
            self.logger.debug(
                "Update interval: %s seconds", self.update_interval.total_seconds()
            )

    @api_request_handler
    async def _async_get_meters(self) -> dict[int, dict[str, Any]]:
        """Get all meters and short info from API."""
        all_meters: list[dict[str, Any]] = await self._api.async_get_meters()
        return {int(meter[CONF_ID]): {CONF_INFO: meter} for meter in all_meters}

    @api_request_handler
    async def _async_get_meter_info(self, meter_id: int) -> dict[str, Any]:
        """Get meter info from API."""
        return await self._api.async_get_meter_info(meter_id)

    @api_request_handler
    async def _async_get_meter_readings(self, meter_id: int) -> dict[str, Any]:
        """Get meter readings from API."""
        return await self._api.async_get_meter_readings(meter_id)
