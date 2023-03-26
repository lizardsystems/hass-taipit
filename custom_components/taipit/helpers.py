"""Taipit helper function."""

from __future__ import annotations

from bisect import bisect
from collections.abc import Sequence
from datetime import datetime, timedelta

from homeassistant.helpers.typing import StateType
from homeassistant.util.dt import utc_from_timestamp, as_local

from .const import STATE_OFFLINE, STATE_BAD, STATE_GOOD, STATE_VERY_GOOD


def utc_from_timestamp_tz(timestamp: int, hours: int) -> datetime:
    """Convert  seconds from 1970 with timezone info"""
    return utc_from_timestamp(timestamp) - timedelta(hours=hours)


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
