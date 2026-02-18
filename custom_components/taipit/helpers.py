"""Taipit helper function."""
from __future__ import annotations

from bisect import bisect
from collections.abc import Sequence
from datetime import datetime, timedelta
from random import randrange
from typing import Any

from homeassistant.helpers.typing import StateType
from homeassistant.util import dt

from .const import (
    CLOCK_DRIFT_MINUTES,
    MIN_TIME_BETWEEN_UPDATES,
    STATE_BAD,
    STATE_GOOD,
    STATE_OFFLINE,
    STATE_VERY_GOOD,
)


def utc_from_timestamp_tz(timestamp: int, hours: int) -> datetime:
    """Convert seconds from 1970 with timezone info."""
    return dt.utc_from_timestamp(timestamp) - timedelta(hours=hours)


def get_interval_to(
    seconds: list[int], minutes: list[int], hours: list[int]
) -> timedelta:
    """Return interval to next time expression match (cron-like)."""
    now = dt.now()
    next_time = dt.find_next_time_expression_time(
        now, seconds=seconds, minutes=minutes, hours=hours
    )
    return next_time - now


def get_update_interval() -> timedelta:
    """Return grid-aligned fallback update interval with jitter.

    Aligns to the meter reporting grid (e.g. :00, :30 for 30-minute interval)
    with 2-3 minutes of jitter.
    """
    _now = dt.now()
    total_minutes = (
        _now - datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=_now.tzinfo)
    ).total_seconds() // 60
    minutes_to_next_time = MIN_TIME_BETWEEN_UPDATES - (
        total_minutes % MIN_TIME_BETWEEN_UPDATES
    )
    interval = timedelta(
        minutes=minutes_to_next_time + randrange(2, 3), seconds=randrange(0, 60)
    )
    return interval


def get_next_meter_report_time(last_reading: datetime) -> datetime:
    """Calculate when the meter is next expected to send data.

    Meters send readings at clock-aligned intervals from midnight.
    With MIN_TIME_BETWEEN_UPDATES=30, readings are sent at :00 and :30.
    """
    midnight = last_reading.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes_since_midnight = (last_reading - midnight).total_seconds() / 60
    current_slot = int(minutes_since_midnight // MIN_TIME_BETWEEN_UPDATES)
    next_slot_minutes = (current_slot + 1) * MIN_TIME_BETWEEN_UPDATES

    if next_slot_minutes >= 1440:
        # Wraps to next day
        midnight += timedelta(days=1)
        next_slot_minutes -= 1440

    return midnight + timedelta(minutes=next_slot_minutes)


def get_next_update_time(readings: dict[str, Any]) -> datetime:
    """Get the next expected cloud data update time for a meter.

    Takes the last reading timestamp, finds the next clock-aligned
    report slot, and adds a clock drift buffer.
    """
    last_reading = dt.as_local(
        utc_from_timestamp_tz(
            readings["economizer"]["lastReading"]["ts_tz"],
            readings["economizer"]["timezone"],
        )
    )
    next_report = get_next_meter_report_time(last_reading)
    return next_report + timedelta(minutes=CLOCK_DRIFT_MINUTES)


def get_smart_update_interval(data: dict[int, dict[str, Any]]) -> timedelta:
    """Calculate the next update interval using cloud-aware scheduling.

    Meters send readings at clock-aligned times (e.g. :00 and :30 for
    a 30-minute interval). Meter clocks may drift by 2-3 minutes.

    Algorithm:
    1. For each meter, compute when the next reading is expected
       (next clock slot + clock drift buffer).
    2. Take the earliest expected time across all meters.
    3. If that time is in the future — wait until then + small jitter.
    4. Otherwise the data is overdue — use grid-aligned fallback interval.
    """
    now = dt.now()

    # Find the earliest expected reading across all meters
    earliest_next: datetime | None = None
    for meter_data in data.values():
        try:
            next_time = get_next_update_time(meter_data)
            if earliest_next is None or next_time < earliest_next:
                earliest_next = next_time
        except (KeyError, TypeError):
            continue

    if earliest_next is not None and earliest_next > now:
        # Meter hasn't reported yet — wait until expected time + jitter
        wait = earliest_next - now
        jitter = timedelta(seconds=randrange(30, 90))
        return wait + jitter

    # Data is overdue or no valid readings — use grid-aligned interval
    return get_update_interval()


def format_mac(value: str) -> str:
    """Format MAC Address."""
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
