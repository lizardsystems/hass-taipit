"""Tests for the Taipit integration setup."""
from __future__ import annotations

from unittest.mock import AsyncMock

from aiotaipit.exceptions import TaipitAuthError, TaipitError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taipit.const import DOMAIN

from .const import (
    MOCK_METER_ID,
    MOCK_METER_INFO_RESPONSE,
    MOCK_METER_READINGS_RESPONSE,
    MOCK_METERS_RESPONSE,
)


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test successful setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None


async def test_setup_entry_auth_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test setup when authentication fails."""
    mock_api.async_get_meters.side_effect = TaipitAuthError("Invalid credentials")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_entry_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test setup when API call fails."""
    mock_api.async_get_meters.side_effect = TaipitError("API error")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_no_meters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test setup when no meters are returned."""
    mock_api.async_get_meters.return_value = []
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test successful unload of a config entry."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_stale_device_removed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that stale devices are removed after setup."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Create a stale device (meter that no longer exists)
    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "99999")},
    )

    # Verify stale device exists
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "99999")}
    )
    assert stale_device is not None

    # Reload the entry - stale device cleanup happens on setup
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Stale device should be removed
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "99999")}
    )
    assert stale_device is None

    # Valid device should still exist
    valid_device = device_registry.async_get_device(
        identifiers={(DOMAIN, str(MOCK_METER_ID))}
    )
    assert valid_device is not None


async def test_no_stale_devices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that no devices are removed when all meters are present."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # All devices should be present
    valid_device = device_registry.async_get_device(
        identifiers={(DOMAIN, str(MOCK_METER_ID))}
    )
    assert valid_device is not None

    # Reload
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Device should still exist
    valid_device = device_registry.async_get_device(
        identifiers={(DOMAIN, str(MOCK_METER_ID))}
    )
    assert valid_device is not None


async def test_stale_device_two_meters_one_removed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test stale device removal when one of two meters is removed."""
    second_meter_id = 67890
    two_meters = [
        *MOCK_METERS_RESPONSE,
        {
            "id": second_meter_id,
            "serialNumber": "SN002",
            "name": "Second Meter",
            "meterTypeId": 16,
        },
    ]
    mock_api.async_get_meters.return_value = two_meters

    # Return different info/readings per meter so unique_ids don't collide
    def _meter_info(meter_id):
        if meter_id == second_meter_id:
            return {"meterTypeId": 16, "serialNumber": "SN002", "name": "Second Meter"}
        return MOCK_METER_INFO_RESPONSE

    def _meter_readings(meter_id):
        if meter_id == second_meter_id:
            return {
                **MOCK_METER_READINGS_RESPONSE,
                "meter": {"serialNumber": "SN002", "name": "Second Meter"},
            }
        return MOCK_METER_READINGS_RESPONSE

    mock_api.async_get_meter_info.side_effect = _meter_info
    mock_api.async_get_meter_readings.side_effect = _meter_readings
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    assert device_registry.async_get_device(
        identifiers={(DOMAIN, str(MOCK_METER_ID))}
    ) is not None
    assert device_registry.async_get_device(
        identifiers={(DOMAIN, str(second_meter_id))}
    ) is not None

    # Now only return the first meter
    mock_api.async_get_meters.return_value = MOCK_METERS_RESPONSE
    mock_api.async_get_meter_info.side_effect = None
    mock_api.async_get_meter_info.return_value = MOCK_METER_INFO_RESPONSE
    mock_api.async_get_meter_readings.side_effect = None
    mock_api.async_get_meter_readings.return_value = MOCK_METER_READINGS_RESPONSE

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # First meter should still exist
    assert device_registry.async_get_device(
        identifiers={(DOMAIN, str(MOCK_METER_ID))}
    ) is not None

    # Second meter should be removed
    assert device_registry.async_get_device(
        identifiers={(DOMAIN, str(second_meter_id))}
    ) is None
