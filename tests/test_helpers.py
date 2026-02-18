"""Tests for Taipit helper functions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from custom_components.taipit.helpers import (
    format_mac,
    get_next_meter_report_time,
    get_next_update_time,
    get_smart_update_interval,
    get_update_interval,
    signal_text,
    utc_from_timestamp_tz,
)


def test_utc_from_timestamp_tz() -> None:
    """Test UTC conversion from timestamp with timezone offset."""
    # timestamp 1700000000 = 2023-11-14 22:13:20 UTC
    # With tz offset 3 hours, result should be 2023-11-14 19:13:20 UTC
    result = utc_from_timestamp_tz(1700000000, 3)
    assert result.year == 2023
    assert result.month == 11
    assert result.day == 14
    assert result.hour == 19
    assert result.minute == 13


def test_format_mac_normal() -> None:
    """Test formatting a normal 12-character MAC address."""
    assert format_mac("aabbccddeeff") == "aa:bb:cc:dd:ee:ff"


def test_format_mac_uppercase() -> None:
    """Test formatting an uppercase MAC address."""
    assert format_mac("AABBCCDDEEFF") == "aa:bb:cc:dd:ee:ff"


def test_format_mac_short() -> None:
    """Test formatting a short MAC address (zero-padded)."""
    assert format_mac("aabb") == "00:00:00:00:aa:bb"


def test_signal_text_offline() -> None:
    """Test signal text for value 0."""
    assert signal_text((1, 12, 17), 0) == "offline"


def test_signal_text_bad() -> None:
    """Test signal text for low signal value."""
    assert signal_text((1, 12, 17), 5) == "bad"


def test_signal_text_good() -> None:
    """Test signal text for medium signal value."""
    assert signal_text((1, 12, 17), 15) == "good"


def test_signal_text_very_good() -> None:
    """Test signal text for high signal value."""
    assert signal_text((1, 12, 17), 20) == "very_good"


def test_signal_text_none() -> None:
    """Test signal text for None value."""
    assert signal_text((1, 12, 17), None) == "offline"


def test_signal_text_boundary_values() -> None:
    """Test signal text at exact boundary thresholds."""
    # Exactly at limits: bisect uses strict less-than
    assert signal_text((1, 12, 17), 1) == "bad"  # == limit → next bucket
    assert signal_text((1, 12, 17), 12) == "good"
    assert signal_text((1, 12, 17), 17) == "very_good"


def test_get_next_meter_report_time() -> None:
    """Test correct clock-aligned slot calculation."""
    # Reading at 14:15 → next slot at 14:30 (30-min interval)
    last_reading = datetime(2023, 11, 14, 14, 15, 0)
    result = get_next_meter_report_time(last_reading)
    assert result == datetime(2023, 11, 14, 14, 30, 0)


def test_get_next_meter_report_time_on_boundary() -> None:
    """Test slot calculation when reading is exactly on a boundary."""
    # Reading at exactly 14:00 → next slot at 14:30
    last_reading = datetime(2023, 11, 14, 14, 0, 0)
    result = get_next_meter_report_time(last_reading)
    assert result == datetime(2023, 11, 14, 14, 30, 0)


def test_get_next_meter_report_time_end_of_day() -> None:
    """Test slot calculation wrapping to next day."""
    # Reading at 23:45 → next slot at 00:00 next day
    last_reading = datetime(2023, 11, 14, 23, 45, 0)
    result = get_next_meter_report_time(last_reading)
    assert result == datetime(2023, 11, 15, 0, 0, 0)


def test_get_next_meter_report_time_just_after_slot() -> None:
    """Test slot calculation just after a boundary."""
    # Reading at 14:31 → next slot at 15:00
    last_reading = datetime(2023, 11, 14, 14, 31, 0)
    result = get_next_meter_report_time(last_reading)
    assert result == datetime(2023, 11, 14, 15, 0, 0)


def test_get_update_interval() -> None:
    """Test that get_update_interval returns a positive timedelta."""
    interval = get_update_interval()
    assert isinstance(interval, timedelta)
    assert interval.total_seconds() > 0


def test_get_next_update_time() -> None:
    """Test get_next_update_time adds clock drift to next report time."""
    readings = {
        "economizer": {
            "lastReading": {"ts_tz": 1700000000},
            "timezone": 3,
        },
    }
    result = get_next_update_time(readings)
    assert isinstance(result, datetime)

    # Last reading: utc_from_timestamp_tz(1700000000, 3) → 2023-11-14 19:13:20 UTC
    # as_local converts to local time, then next slot + 3 min drift
    # The result should be after the last reading
    last_reading_utc = utc_from_timestamp_tz(1700000000, 3)
    assert result > last_reading_utc


def test_get_smart_update_interval_invalid_data() -> None:
    """Test get_smart_update_interval falls back when readings have missing keys."""
    # Data with missing economizer key — should hit KeyError and fall back
    data = {
        12345: {"info": {"serialNumber": "SN001"}, "extended": {}},
    }
    interval = get_smart_update_interval(data)
    assert isinstance(interval, timedelta)
    assert interval.total_seconds() > 0


def test_get_smart_update_interval_empty_data() -> None:
    """Test get_smart_update_interval with empty data dict."""
    interval = get_smart_update_interval({})
    assert isinstance(interval, timedelta)
    assert interval.total_seconds() > 0


def test_get_smart_update_interval_overdue() -> None:
    """Test get_smart_update_interval falls back when data is overdue."""
    # Use a very old timestamp — reading from 2020
    data = {
        12345: {
            "economizer": {
                "lastReading": {"ts_tz": 1577836800},  # 2020-01-01 00:00:00 UTC
                "timezone": 3,
            },
        },
    }
    interval = get_smart_update_interval(data)
    assert isinstance(interval, timedelta)
    assert interval.total_seconds() > 0
