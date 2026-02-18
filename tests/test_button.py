"""Tests for Taipit button entities."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taipit.const import DOMAIN


def _get_entity_id(
    hass: HomeAssistant, unique_id: str
) -> str:
    """Get entity_id by unique_id from entity registry."""
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("button", DOMAIN, unique_id)
    assert entity_id is not None, f"Button with unique_id '{unique_id}' not found"
    return entity_id


async def test_button_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test refresh button exists for each meter."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    button_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_refresh")
    state = hass.states.get(button_id)
    assert state is not None


async def test_button_press(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test pressing button calls coordinator.async_force_refresh()."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    button_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_refresh")

    with patch.object(coordinator, "async_force_refresh", new_callable=AsyncMock) as mock_refresh:
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": button_id},
            blocking=True,
        )

        mock_refresh.assert_awaited_once()


async def test_button_entity_category(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test button entity category is diagnostic."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    button_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_refresh")
    entry = entity_registry.async_get(button_id)
    assert entry is not None
    assert entry.entity_category is EntityCategory.DIAGNOSTIC
