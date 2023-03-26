"""Taipit Cloud Coordinator."""
from __future__ import annotations

import datetime as dt
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
from homeassistant.util.dt import now, as_local

from .const import DOMAIN, UPDATE_INTERVAL, MIN_TIME_BETWEEN_UPDATES
from .decorators import api_request_handler
from .helpers import utc_from_timestamp_tz


class TaipitCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Coordinator is responsible for querying the device at a specified route."""

    _api: TaipitApi
    force_next_update: bool

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialise a custom coordinator."""
        self.force_next_update = False
        session = async_get_clientsession(hass)
        auth = SimpleTaipitAuth(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], session
        )
        self._api = TaipitApi(auth)

        super().__init__(
            hass,
            getLogger(__name__),
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[int, Any] | None:
        """Fetch data from Taipit."""
        try:
            self.logger.debug("Start updating Taipit data")
            _data: dict[int, dict] = self.data

            if _data is None or self.force_next_update:
                self.logger.debug("Retrieving meters for account")
                # fetch list of meters in account
                _data = await self._async_get_meters()
                if _data:
                    self.logger.debug("%d meters retrieved for account", len(_data))
                else:
                    self.logger.warning("No meters retrieved for account")
                    return None
                # fetch extended meter info including model name
                for meter_id in _data:
                    meter_info = await self._async_get_meter_info(meter_id)
                    _data[meter_id].update({"extended": meter_info})
                    self.logger.debug(
                        "Retrieved information for meter ID %s", str(meter_id)
                    )

            # fetch the latest readings
            for meter_id in _data:
                # Check when the latest data was received
                # skip update if time between update is less than 30 min
                if not self.force_next_update:
                    _update_time = _data[meter_id].get("next_update_time")
                    if _update_time:
                        delta_time = (_update_time - now()).total_seconds() / 60
                        if delta_time > 0:
                            self.logger.debug(
                                "Skipped updating information for meter SERIAL=%s. Time: %s ",
                                _data[meter_id]["meter"]["serialNumber"],
                                delta_time,
                            )
                            continue

                readings = await self._async_get_meter_readings(meter_id)
                _data[meter_id].update(readings)
                _data[meter_id]["next_update_time"] = self.get_next_update_time(
                    readings
                )

                self.logger.debug(
                    "Updated information for meter SERIAL=%s. Next update time: %s",
                    _data[meter_id]["meter"]["serialNumber"],
                    _data[meter_id]["next_update_time"],
                )
            return _data

        except TaipitAuthInvalidGrant as exc:
            raise ConfigEntryAuthFailed("Incorrect Login or Password") from exc
        except TaipitAuthInvalidClient as exc:
            raise ConfigEntryAuthFailed("Incorrect client_id or client_secret") from exc
        except TaipitError as exc:
            raise ConfigEntryNotReady("Can not connect to host") from exc
        finally:
            self.force_next_update = False

    @staticmethod
    def get_next_update_time(readings: dict[str, Any]) -> dt.datetime:
        """Get next update time for meter."""
        _update_time = as_local(
            utc_from_timestamp_tz(
                readings["economizer"]["lastReading"]["ts_tz"],
                readings["economizer"]["timezone"],
            )
        )
        _next_update_time = _update_time + MIN_TIME_BETWEEN_UPDATES

        return _next_update_time

    @api_request_handler
    async def _async_get_meters(self) -> dict[int, dict[str, Any]]:
        all_meters: list[dict[str, Any]] = await self._api.async_get_meters()
        return {int(meter[CONF_ID]): {"info": meter} for meter in all_meters}

    @api_request_handler
    async def _async_get_meter_info(self, meter_id: int) -> dict[str, Any]:
        return await self._api.async_get_meter_info(meter_id)

    @api_request_handler
    async def _async_get_meter_readings(self, meter_id: int) -> dict[str, Any]:
        return await self._api.async_get_meter_readings(meter_id)
