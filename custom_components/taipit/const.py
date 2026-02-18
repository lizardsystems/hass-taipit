"""Constants for the taipit integration."""
from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "taipit"

ATTRIBUTION: Final = "Data provided by Taipit Cloud"
CONF_NAME: Final = "name"
CONF_INFO: Final = "info"
CONF_SERIAL_NUMBER: Final = "serialNumber"

PLATFORMS: Final[list[Platform]] = [Platform.SENSOR, Platform.BUTTON]

CONFIGURATION_URL: Final = "https://cloud.meters.taipit.ru/?meter={meter_id}"

STATE_OFFLINE: Final = "offline"
STATE_BAD: Final = "bad"
STATE_GOOD: Final = "good"
STATE_VERY_GOOD: Final = "very_good"

API_TIMEOUT: Final = 30
API_MAX_TRIES: Final = 3
API_RETRY_DELAY: Final = 10

REQUEST_REFRESH_DEFAULT_COOLDOWN: Final = 5
MIN_TIME_BETWEEN_UPDATES: Final = 30  # minutes, meter reporting interval (:00 and :30)
CLOCK_DRIFT_MINUTES: Final = 3  # meter clock may be off by 2-3 minutes

CONF_TOKEN: Final = "token"
