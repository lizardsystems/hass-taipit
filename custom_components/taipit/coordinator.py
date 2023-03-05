"""Taipit Cloud Coordinator."""
from __future__ import annotations

from typing import Any
from datetime import datetime, timezone, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_ID
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady


from aiotaipit import TaipitApi, SimpleTaipitAuth
from aiotaipit.exceptions import (
    TaipitAuthInvalidGrant,
    TaipitError,
    TaipitAuthInvalidClient,
)

from .const import DOMAIN, UPDATE_INTERVAL, LOGGER, MIN_TIME_BETWEEN_UPDATES
from .helpers import from_timestamp_tz


class TaipitCoordinator(DataUpdateCoordinator):
    """Coordinator is responsible for querying the device at a specified route."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialise a custom coordinator."""

        session = async_get_clientsession(hass)
        auth = SimpleTaipitAuth(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], session
        )
        self._api = TaipitApi(auth)

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[int, Any]:
        """Fetch data from Taipit."""
        try:
            LOGGER.debug("Start updating Taipit data")
            _data: dict[int, dict] = self.data
            first_update: bool = False
            if _data is None:
                LOGGER.debug("Retrieving meters for account")
                # fetch list of meters in account
                all_meters: list[dict[str, Any]] = await self._api.async_get_meters()
                _data = {int(meter[CONF_ID]): {"info": meter} for meter in all_meters}
                if _data:
                    LOGGER.debug("%d meters retrieved for account", len(all_meters))
                else:
                    LOGGER.warning("No meters retrieved for account")
                    return
                # fetch extended meter info including model name
                for meter_id in _data:
                    meter_info = await self._api.async_get_meter_info(meter_id)
                    _data[meter_id].update({"extended": meter_info})

                # it is first update
                first_update = True

            # fetch the latest readings
            for meter_id in _data:
                # Check when the latest data was received
                if not first_update:
                    last_update_time = _data[meter_id].get("last_update_time")
                    if last_update_time:
                        delta_time = timedelta(
                            minutes=(
                                datetime.now(timezone.utc) - last_update_time
                            ).total_seconds()
                            / 60
                        )
                        # skip update if time between update is less than 30 min
                        if delta_time < MIN_TIME_BETWEEN_UPDATES:
                            LOGGER.debug(
                                "Skipped updating information for meter SERIAL=%s. Time: %s",
                                _data[meter_id]["meter"]["serialNumber"],
                                delta_time,
                            )
                            continue

                readings = await self._api.async_get_meter_readings(meter_id)
                _data[meter_id].update(readings)

                if not first_update:
                    last_update_time = from_timestamp_tz(
                        readings["economizer"]["lastReading"]["ts_tz"],
                        readings["economizer"]["timezone"],
                    )
                    _data[meter_id]["last_update_time"] = last_update_time

                LOGGER.debug(
                    "Updated information for meter SERIAL=%s",
                    _data[meter_id]["meter"]["serialNumber"],
                )

            return _data

        except TaipitAuthInvalidGrant as exc:
            raise ConfigEntryAuthFailed("Incorrect Login or Password") from exc
        except TaipitAuthInvalidClient as exc:
            raise ConfigEntryAuthFailed("Incorrect client_id or client_secret") from exc
        except TaipitError as exc:
            raise ConfigEntryNotReady("Can not connect to host") from exc
