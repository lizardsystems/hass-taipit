"""Constants for the taipit integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "taipit"
UPDATE_INTERVAL: Final[timedelta] = timedelta(minutes=5)

ATTRIBUTION: Final = "Data provided by Taipit Cloud"
CONF_METERS: Final = "meters"
CONF_NAME: Final = "name"

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIGURATION_URL: Final = "https://cloud.meters.taipit.ru/?meter={meter_id}"

STATE_OFFLINE = "offline"
STATE_BAD = "bad"
STATE_GOOD = "good"
STATE_VERY_GOOD = "very_good"

SIGNAL_ICONS = {
    STATE_OFFLINE: "mdi:signal-cellular-outline",
    STATE_BAD: "mdi:signal-cellular-1",
    STATE_GOOD: "mdi:signal-cellular-2",
    STATE_VERY_GOOD: "mdi:signal-cellular-3",
}

DEFAULT_API_TIMEOUT: Final = 20
