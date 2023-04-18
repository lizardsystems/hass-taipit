"""Taipit helper function."""
from __future__ import annotations

from bisect import bisect
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from homeassistant.helpers.typing import StateType
from homeassistant.util import dt
from homeassistant.util.dt import utc_from_timestamp, as_local

from .const import (
    STATE_OFFLINE,
    STATE_BAD,
    STATE_GOOD,
    STATE_VERY_GOOD,
    MIN_TIME_BETWEEN_UPDATES,
)


def utc_from_timestamp_tz(timestamp: int, hours: int) -> datetime:
    """Convert  seconds from 1970 with timezone info"""
    return utc_from_timestamp(timestamp) - timedelta(hours=hours)


def get_interval_to(
    seconds: list[int], minutes: list[int], hours: list[int]
) -> timedelta:
    """Return data update interval."""
    now = dt.utcnow()
    next_time = dt.find_next_time_expression_time(
        now, seconds=seconds, minutes=minutes, hours=hours
    )
    minutes_to_next_time = (next_time - now).total_seconds() / 60
    interval = timedelta(minutes=minutes_to_next_time)

    return interval


def get_next_update_time(readings: dict[str, Any]) -> datetime:
    """Get next update time for meter."""
    _update_time = as_local(
        utc_from_timestamp_tz(
            readings["economizer"]["lastReading"]["ts_tz"],
            readings["economizer"]["timezone"],
        )
    )
    _next_update_time = _update_time + MIN_TIME_BETWEEN_UPDATES

    return _next_update_time


def format_mac(value: str) -> str:
    """Format MAC Address"""
    mac = value.rjust(12, "0")
    return ":".join(mac.lower()[i : i + 2] for i in range(0, 12, 2))


def signal_text(limits: Sequence[int], value: StateType) -> str:
    """Get signal text."""
    return (
        STATE_OFFLINE,  # =0
        STATE_BAD,  # >1
        STATE_GOOD,  # >12
        STATE_VERY_GOOD,  # >17
    )[bisect(limits, value if value is not None else -1000)]
