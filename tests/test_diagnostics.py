"""Tests for Taipit diagnostics."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taipit.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .const import MOCK_METER_ID


async def test_diagnostics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test diagnostics output."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Config entry data should be present
    assert "config_entry" in result
    assert "coordinator" in result

    # Coordinator info
    assert result["coordinator"]["last_update_success"] is True
    assert "update_interval" in result["coordinator"]

    # Meters should be present
    meters = result["coordinator"]["meters"]
    assert str(MOCK_METER_ID) in meters


async def test_diagnostics_redacts(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test diagnostics redacts sensitive data."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Sensitive fields should be redacted
    assert result["config_entry"]["username"] == "**REDACTED**"
    assert result["config_entry"]["password"] == "**REDACTED**"
    assert result["config_entry"]["token"] == "**REDACTED**"
