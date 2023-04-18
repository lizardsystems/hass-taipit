"""Constants for the taipit integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "taipit"
UPDATE_INTERVAL: Final[timedelta] = timedelta(minutes=5)


ATTRIBUTION: Final = "Data provided by Taipit Cloud"
CONF_METERS: Final = "meters"
CONF_NAME: Final = "name"
CONF_INFO: Final = "info"
CONF_SERIAL_NUMBER: Final = "serialNumber"

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

CONFIGURATION_URL: Final = "https://cloud.meters.taipit.ru/?meter={meter_id}"

STATE_OFFLINE: Final = "offline"
STATE_BAD: Final = "bad"
STATE_GOOD: Final = "good"
STATE_VERY_GOOD: Final = "very_good"

SIGNAL_ICONS = {
    STATE_OFFLINE: "mdi:signal-cellular-outline",
    STATE_BAD: "mdi:signal-cellular-1",
    STATE_GOOD: "mdi:signal-cellular-2",
    STATE_VERY_GOOD: "mdi:signal-cellular-3",
}

API_TIMEOUT: Final = 30
API_MAX_TRIES: Final = 3
API_RETRY_DELAY: Final = 10

REQUEST_REFRESH_DEFAULT_COOLDOWN = 5
