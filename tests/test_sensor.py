"""Tests for Taipit sensor entities."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taipit.const import DOMAIN

from .const import (
    MOCK_METER_ID,
    MOCK_METER_INFO_RESPONSE,
    MOCK_METER_READINGS_RESPONSE,
    MOCK_METERS_RESPONSE,
    MOCK_THREE_PHASE_READINGS_RESPONSE,
)


def _get_entity_id(
    hass: HomeAssistant, unique_id: str
) -> str:
    """Get entity_id by unique_id from entity registry."""
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None, f"Entity with unique_id '{unique_id}' not found"
    return entity_id


async def test_sensors_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test correct number of sensors created for single-phase meter."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Count sensor entities for our domain
    entities = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    sensor_entities = [e for e in entities if e.domain == "sensor"]

    # Single-phase meter with T1 and T2 (T3 is None):
    # energy_a, energy_t1_a, energy_t2_a (T3 disabled because None)
    # electric_current, voltage, power_factor (single-phase, 1 value each)
    # current_timestamp, serial_number, mac_address, signal
    # Phase sensors not created (single phase: len(i/u/cos) == 1, not > 1)
    assert len(sensor_entities) == 10


async def test_sensor_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test sensor values are correct."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # energy_a unique_id: neva_mt_114_wi_fi_sn001_energy_a
    energy_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_energy_a")
    state = hass.states.get(energy_id)
    assert state is not None
    assert float(state.state) == 1234.5

    # serial_number
    serial_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_serial_number")
    state = hass.states.get(serial_id)
    assert state is not None
    assert state.state == "SN001"


async def test_sensor_signal(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test signal sensor returns correct text for value 15."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    signal_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_signal")
    state = hass.states.get(signal_id)
    assert state is not None
    assert state.state == "good"


async def test_sensor_mac_address(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test MAC sensor formats address correctly."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mac_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_mac_address")
    state = hass.states.get(mac_id)
    assert state is not None
    assert state.state == "aa:bb:cc:dd:ee:ff"


async def test_sensor_timestamp(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test timestamp sensor has a valid value."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ts_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_current_timestamp")
    state = hass.states.get(ts_id)
    assert state is not None
    assert state.state != "unavailable"
    assert state.state != "unknown"


async def test_sensor_unavailable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test sensor unavailable when energy_a is falsy."""
    readings = {
        **MOCK_METER_READINGS_RESPONSE,
        "economizer": {
            **MOCK_METER_READINGS_RESPONSE["economizer"],
            "lastReading": {
                **MOCK_METER_READINGS_RESPONSE["economizer"]["lastReading"],
                "energy_a": None,
            },
        },
    }
    mock_api.async_get_meter_readings.return_value = readings
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    energy_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_energy_a")
    state = hass.states.get(energy_id)
    assert state is not None
    assert state.state == "unavailable"


async def test_three_phase_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test 3-phase addParams create phase sensors."""
    mock_api.async_get_meter_readings.return_value = MOCK_THREE_PHASE_READINGS_RESPONSE
    mock_api.async_get_meter_info.return_value = {
        "meterTypeId": 15,
        "serialNumber": "SN002",
        "name": "Three Phase Meter",
    }
    mock_api.async_get_meters.return_value = [
        {
            "id": MOCK_METER_ID,
            "serialNumber": "SN002",
            "name": "Three Phase Meter",
            "meterTypeId": 15,
        },
    ]
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Phase 1 current should exist (unique_id uses model name from meterTypeId 15)
    phase1_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_315_gsm_sn002_electric_current_phase_1"
    )
    assert phase1_id is not None

    # Single-phase electric_current should NOT exist
    single_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_315_gsm_sn002_electric_current"
    )
    assert single_id is None


async def test_disabled_tariff_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test energy_t3_a is not created when value is None."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # T3 should not exist (value is None in mock data)
    t3_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_energy_t3_a"
    )
    assert t3_id is None

    # T1 and T2 should exist
    t1_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_energy_t1_a"
    )
    assert t1_id is not None

    t2_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_energy_t2_a"
    )
    assert t2_id is not None


async def test_power_factor_dash_disabled(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test power_factor sensor not created when cos value is '-'."""
    readings = {
        **MOCK_METER_READINGS_RESPONSE,
        "economizer": {
            **MOCK_METER_READINGS_RESPONSE["economizer"],
            "addParams": {
                "values": {
                    "i": ["5.0"],
                    "u": ["230.0"],
                    "cos": ["-"],
                }
            },
        },
    }
    mock_api.async_get_meter_readings.return_value = readings
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # power_factor should NOT be created (cos == "-")
    pf_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_power_factor"
    )
    assert pf_id is None

    # electric_current and voltage should still exist
    current_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_electric_current"
    )
    assert current_id is not None

    voltage_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_voltage"
    )
    assert voltage_id is not None


async def test_three_phase_sensor_count(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test correct number of sensors for 3-phase meter with all tariffs."""
    mock_api.async_get_meter_readings.return_value = MOCK_THREE_PHASE_READINGS_RESPONSE
    mock_api.async_get_meter_info.return_value = {
        "meterTypeId": 15,
        "serialNumber": "SN002",
        "name": "Three Phase Meter",
    }
    mock_api.async_get_meters.return_value = [
        {
            "id": MOCK_METER_ID,
            "serialNumber": "SN002",
            "name": "Three Phase Meter",
            "meterTypeId": 15,
        },
    ]
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    sensor_entities = [e for e in entities if e.domain == "sensor"]

    # 3-phase meter with T1, T2, T3 (all non-None):
    # energy_a, energy_t1_a, energy_t2_a, energy_t3_a = 4 energy
    # 3 phases × (current + voltage + power_factor) = 9 phase sensors
    # current_timestamp, serial_number, mac_address, signal = 4 diagnostic
    # Single-phase sensors NOT created (len > 1)
    assert len(sensor_entities) == 17


async def test_single_phase_current(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test single-phase meter has electric_current enabled, phase sensors disabled."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Single-phase current should exist
    current_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_electric_current"
    )
    assert current_id is not None

    state = hass.states.get(current_id)
    assert state is not None
    assert float(state.state) == 5.0

    # Phase-specific sensors should NOT exist
    phase1_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "neva_mt_114_wi_fi_sn001_electric_current_phase_1"
    )
    assert phase1_id is None


async def test_sensor_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator update propagates to sensor values."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    energy_id = _get_entity_id(hass, "neva_mt_114_wi_fi_sn001_energy_a")
    state = hass.states.get(energy_id)
    assert float(state.state) == 1234.5

    # Update readings with new value
    updated_readings = {
        **MOCK_METER_READINGS_RESPONSE,
        "economizer": {
            **MOCK_METER_READINGS_RESPONSE["economizer"],
            "lastReading": {
                **MOCK_METER_READINGS_RESPONSE["economizer"]["lastReading"],
                "energy_a": "5678.9",
            },
        },
    }
    mock_api.async_get_meter_readings.return_value = updated_readings

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(energy_id)
    assert float(state.state) == 5678.9
