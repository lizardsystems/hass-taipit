"""Taipit Sensor definitions."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util.dt import as_local

from . import TaipitConfigEntry
from .const import (
    STATE_BAD,
    STATE_GOOD,
    STATE_OFFLINE,
    STATE_VERY_GOOD,
)
from .coordinator import TaipitCoordinator
from .entity import TaipitBaseCoordinatorEntity
from .helpers import format_mac, signal_text, utc_from_timestamp_tz


@dataclass(frozen=True, kw_only=True)
class TaipitSensorEntityDescription(SensorEntityDescription):
    """Describes Taipit sensor entity."""

    value_fn: Callable[[dict[str, Any]], StateType | date | datetime]
    available_fn: Callable[[dict[str, Any]], bool] = lambda _: True
    enabled: Callable[[dict[str, Any]], bool] = lambda _: True


SENSOR_TYPES: tuple[TaipitSensorEntityDescription, ...] = (
    TaipitSensorEntityDescription(
        key="energy_a",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        available_fn=lambda data: data["economizer"]["lastReading"]["energy_a"],
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_a"]),
        translation_key="energy_a",
    ),
    TaipitSensorEntityDescription(
        key="energy_t1_a",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        available_fn=lambda data: data["economizer"]["lastReading"]["energy_t1_a"],
        enabled=lambda data: data["economizer"]["lastReading"]["energy_t1_a"],
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_t1_a"]),
        translation_key="energy_t1_a",
    ),
    TaipitSensorEntityDescription(
        key="energy_t2_a",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        available_fn=lambda data: data["economizer"]["lastReading"]["energy_t2_a"],
        enabled=lambda data: data["economizer"]["lastReading"]["energy_t2_a"],
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_t2_a"]),
        translation_key="energy_t2_a",
    ),
    TaipitSensorEntityDescription(
        key="energy_t3_a",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        available_fn=lambda data: data["economizer"]["lastReading"]["energy_t3_a"],
        enabled=lambda data: data["economizer"]["lastReading"]["energy_t3_a"],
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_t3_a"]),
        translation_key="energy_t3_a",
    ),
    TaipitSensorEntityDescription(
        key="electric_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) == 1,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) == 1,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["i"][0]),
        translation_key="electric_current",
    ),
    TaipitSensorEntityDescription(
        key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) == 1,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) == 1,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["u"][0]),
        translation_key="voltage",
    ),
    TaipitSensorEntityDescription(
        key="power_factor",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) == 1
        and data["economizer"]["addParams"]["values"]["cos"][0] != "-",
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) == 1
        and data["economizer"]["addParams"]["values"]["cos"][0] != "-",
        value_fn=lambda data: float(
            data["economizer"]["addParams"]["values"]["cos"][0]
        ),
        translation_key="power_factor",
    ),
    TaipitSensorEntityDescription(
        key="electric_current_phase_1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) > 1,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) > 1,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["i"][0]),
        translation_key="electric_current_phase_1",
    ),
    TaipitSensorEntityDescription(
        key="voltage_phase_1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) > 1,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) > 1,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["u"][0]),
        translation_key="voltage_phase_1",
    ),
    TaipitSensorEntityDescription(
        key="power_factor_phase_1",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) > 1
        and data["economizer"]["addParams"]["values"]["cos"][0] != "-",
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) > 1
        and data["economizer"]["addParams"]["values"]["cos"][0] != "-",
        value_fn=lambda data: float(
            data["economizer"]["addParams"]["values"]["cos"][0]
        ),
        translation_key="power_factor_1",
    ),
    TaipitSensorEntityDescription(
        key="electric_current_phase_2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) > 1,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) > 1,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["i"][1]),
        translation_key="electric_current_phase_2",
    ),
    TaipitSensorEntityDescription(
        key="voltage_phase_2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) > 1,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) > 1,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["u"][1]),
        translation_key="voltage_phase_2",
    ),
    TaipitSensorEntityDescription(
        key="power_factor_phase_2",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) > 1
        and data["economizer"]["addParams"]["values"]["cos"][1] != "-",
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) > 1
        and data["economizer"]["addParams"]["values"]["cos"][1] != "-",
        value_fn=lambda data: float(
            data["economizer"]["addParams"]["values"]["cos"][1]
        ),
        translation_key="power_factor_2",
    ),
    TaipitSensorEntityDescription(
        key="electric_current_phase_3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) > 2,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["i"]) > 2,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["i"][2]),
        translation_key="electric_current_phase_3",
    ),
    TaipitSensorEntityDescription(
        key="voltage_phase_3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) > 2,
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["u"]) > 2,
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["u"][2]),
        translation_key="voltage_phase_3",
    ),
    TaipitSensorEntityDescription(
        key="power_factor_phase_3",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        available_fn=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) > 2
        and data["economizer"]["addParams"]["values"]["cos"][2] != "-",
        enabled=lambda data: len(data["economizer"]["addParams"]["values"]["cos"]) > 2
        and data["economizer"]["addParams"]["values"]["cos"][2] != "-",
        value_fn=lambda data: float(
            data["economizer"]["addParams"]["values"]["cos"][2]
        ),
        translation_key="power_factor_3",
    ),
    TaipitSensorEntityDescription(
        key="current_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: as_local(
            utc_from_timestamp_tz(
                data["economizer"]["lastReading"]["ts_tz"],
                data["economizer"]["timezone"],
            )
        ),
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="current_timestamp",
    ),
    TaipitSensorEntityDescription(
        key="serial_number",
        value_fn=lambda data: data["meter"]["serialNumber"],
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="serial_number",
    ),
    TaipitSensorEntityDescription(
        key="mac_address",
        value_fn=lambda data: format_mac(data["controller"]["id"]),
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="mac_address",
    ),
    TaipitSensorEntityDescription(
        key="signal",
        options=[STATE_OFFLINE, STATE_BAD, STATE_GOOD, STATE_VERY_GOOD],
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda data: signal_text((1, 12, 17), data["controller"]["signal"]),
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="signal",
    ),
)


class TaipitSensor(TaipitBaseCoordinatorEntity, SensorEntity):
    """Taipit Sensor."""

    entity_description: TaipitSensorEntityDescription

    def __init__(
        self,
        coordinator: TaipitCoordinator,
        entity_description: TaipitSensorEntityDescription,
        meter_id: int,
    ) -> None:
        """Initialize the Sensor."""
        super().__init__(coordinator, entity_description, meter_id)
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=coordinator.hass
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.get(self.meter_id) is not None
            and self.entity_description.available_fn(
                self.coordinator.data[self.meter_id]
            )
        )

    @property
    def native_value(self) -> StateType | date | datetime:
        """Return the state of the sensor."""
        data = self.coordinator.data
        if (
            data is None
            or data.get(self.meter_id) is None
            or not self.entity_description.available_fn(data[self.meter_id])
        ):
            return None
        return self.entity_description.value_fn(data[self.meter_id])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TaipitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""
    coordinator: TaipitCoordinator = entry.runtime_data

    entities: list[TaipitSensor] = [
        TaipitSensor(coordinator, entity_description, meter_id)
        for entity_description in SENSOR_TYPES
        for meter_id in coordinator.data
        if entity_description.enabled(coordinator.data[meter_id])
    ]

    async_add_entities(entities, True)
