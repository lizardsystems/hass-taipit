"""Tests for the Taipit coordinator."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

from aiotaipit.exceptions import TaipitAuthError, TaipitError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taipit.const import CONF_TOKEN, DOMAIN

from .const import (
    MOCK_METER_ID,
    MOCK_METER_INFO_RESPONSE,
    MOCK_METER_READINGS_RESPONSE,
    MOCK_METERS_RESPONSE,
    MOCK_PASSWORD,
    MOCK_TOKEN_DATA,
    MOCK_USERNAME,
)


async def test_first_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator first refresh populates data."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator is not None
    assert len(coordinator.data) == 1
    assert MOCK_METER_ID in coordinator.data

    meter_data = coordinator.data[MOCK_METER_ID]
    assert meter_data["info"]["serialNumber"] == "SN001"
    assert meter_data["extended"]["meterTypeId"] == 16
    assert meter_data["economizer"]["lastReading"]["energy_a"] == "1234.5"

    # All three API calls should have been made
    mock_api.async_get_meters.assert_awaited_once()
    mock_api.async_get_meter_info.assert_awaited_once_with(MOCK_METER_ID)
    mock_api.async_get_meter_readings.assert_awaited_once_with(MOCK_METER_ID)


async def test_subsequent_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that subsequent refresh only fetches readings (not meters/info)."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    # Reset call counts after initial setup
    mock_api.async_get_meters.reset_mock()
    mock_api.async_get_meter_info.reset_mock()
    mock_api.async_get_meter_readings.reset_mock()

    # Trigger another refresh
    await coordinator.async_refresh()

    # Meters and info should NOT be fetched again
    mock_api.async_get_meters.assert_not_awaited()
    mock_api.async_get_meter_info.assert_not_awaited()

    # Readings should be fetched
    mock_api.async_get_meter_readings.assert_awaited_once_with(MOCK_METER_ID)


async def test_force_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that force refresh re-fetches meters, info, and readings."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    # Reset call counts
    mock_api.async_get_meters.reset_mock()
    mock_api.async_get_meter_info.reset_mock()
    mock_api.async_get_meter_readings.reset_mock()

    # Force refresh
    await coordinator.async_force_refresh()

    # All should be fetched again
    mock_api.async_get_meters.assert_awaited_once()
    mock_api.async_get_meter_info.assert_awaited_once_with(MOCK_METER_ID)
    mock_api.async_get_meter_readings.assert_awaited_once_with(MOCK_METER_ID)


async def test_auth_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that TaipitAuthError immediately raises (no retry)."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    mock_api.async_get_meter_readings.reset_mock()
    mock_api.async_get_meter_readings.side_effect = TaipitAuthError("Token expired")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    # Auth error should not be retried
    mock_api.async_get_meter_readings.assert_awaited_once()


async def test_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that TaipitError results in UpdateFailed."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    mock_api.async_get_meter_readings.side_effect = TaipitError("API error")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_no_meters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that empty meters list results in UpdateFailed."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    # Force refresh with empty meters
    mock_api.async_get_meters.return_value = []
    await coordinator.async_force_refresh()

    assert coordinator.last_update_success is False


async def test_token_update_callback(
    hass: HomeAssistant,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test token update callback persists tokens to config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_TOKEN: MOCK_TOKEN_DATA,
        },
        unique_id=MOCK_USERNAME,
        version=1,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data

    new_token = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 7200,
        "expires_at": 1700007200,
    }
    coordinator._on_token_update(new_token)

    assert entry.data[CONF_TOKEN] == new_token
    # Original data should be preserved
    assert entry.data[CONF_USERNAME] == MOCK_USERNAME
    assert entry.data[CONF_PASSWORD] == MOCK_PASSWORD


async def test_update_interval_set(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that update_interval is set after refresh."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.update_interval is not None
    assert coordinator.update_interval.total_seconds() > 0


async def test_last_update_time_set(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that last_update_time is set from readings timestamp."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    meter_data = coordinator.data[MOCK_METER_ID]

    assert "last_update_time" in meter_data
    assert isinstance(meter_data["last_update_time"], datetime)


async def test_force_refresh_flag_reset_on_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test force_next_update flag is reset even when refresh fails."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    # Make the next refresh fail
    mock_api.async_get_meters.return_value = []

    await coordinator.async_force_refresh()

    # Flag should be reset despite the error
    assert coordinator.force_next_update is False
    assert coordinator.last_update_success is False


async def test_meter_info_failure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that meter info API failure fails the entire refresh."""
    mock_api.async_get_meter_info.side_effect = TaipitError("info fetch failed")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Entry should not load because first refresh fails
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
