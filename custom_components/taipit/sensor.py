"""Taipit Sensor definitions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify

from aiotaipit.helpers import get_model_name

from .const import (
    ATTRIBUTION,
    DOMAIN,
    CONF_NAME,
    CONFIGURATION_URL,
    STATE_OFFLINE,
    STATE_BAD,
    STATE_GOOD,
    STATE_VERY_GOOD,
    SIGNAL_ICONS,
    LOGGER,
)
from .coordinator import TaipitCoordinator
from .helpers import from_timestamp_tz, format_mac, signal_text


@dataclass
class TaipitEntityDescriptionMixin:
    """Mixin for required Taipit base description keys."""

    value_fn: Callable[[dict[str, Any]], StateType]


@dataclass
class TaipitBaseSensorEntityDescription(SensorEntityDescription):
    """Describes Taipit sensor entity default overrides."""

    attr_fn: Callable[[dict[str, Any]], Mapping[str, Any] | None] = lambda data: None
    avabl_fn: Callable[[dict[str, Any]], bool] = lambda data: True
    icon_fn: Callable[[StateType], str] | None = None


@dataclass
class TaipitSensorEntityDescription(
    TaipitBaseSensorEntityDescription, TaipitEntityDescriptionMixin
):
    """Describes Taipit sensor entity."""


SENSOR_TYPES: tuple[TaipitSensorEntityDescription, ...] = (
    TaipitSensorEntityDescription(
        key="energy_a",
        name="Active Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_a"]),
        translation_key="energy_a",
    ),
    TaipitSensorEntityDescription(
        key="energy_t1_a",
        name="Active Energy T1",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_t1_a"]),
        translation_key="energy_t1_a",
    ),
    TaipitSensorEntityDescription(
        key="energy_t2_a",
        name="Active Energy T2",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_t2_a"]),
        translation_key="energy_t2_a",
    ),
    TaipitSensorEntityDescription(
        key="energy_t3_a",
        name="Active Energy T3",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: float(data["economizer"]["lastReading"]["energy_t3_a"]),
        translation_key="energy_t3_a",
    ),
    TaipitSensorEntityDescription(
        key="electric_current",
        name="Electric Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        avabl_fn=lambda data: data["economizer"]["addParams"]["values"]["i"][0],
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["i"][0]),
        translation_key="electric_current",
    ),
    TaipitSensorEntityDescription(
        key="voltage",
        name="Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        avabl_fn=lambda data: data["economizer"]["addParams"]["values"]["u"][0],
        value_fn=lambda data: float(data["economizer"]["addParams"]["values"]["u"][0]),
        translation_key="voltage",
    ),
    TaipitSensorEntityDescription(
        key="current_timestamp",
        name="Last Data Update",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
        value_fn=lambda data: from_timestamp_tz(
            data["economizer"]["lastReading"]["ts_tz"],
            data["economizer"]["timezone"],
        ),
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="current_timestamp",
    ),
    TaipitSensorEntityDescription(
        key="serial_number",
        name="Serial Number",
        icon="mdi:identifier",
        value_fn=lambda data: data["meter"]["serialNumber"],
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="serial_number",
    ),
    TaipitSensorEntityDescription(
        key="mac_address",
        name="MAC address",
        icon="mdi:network",
        value_fn=lambda data: format_mac(data["controller"]["id"]),
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="mac_address",
    ),
    TaipitSensorEntityDescription(
        key="signal",
        name="Signal",
        icon_fn=lambda data: SIGNAL_ICONS[
            signal_text((1, 12, 17), data["controller"]["signal"])
        ],
        options=[STATE_OFFLINE, STATE_BAD, STATE_GOOD, STATE_VERY_GOOD],
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda data: signal_text((1, 12, 17), data["controller"]["signal"]),
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="signal",
    ),
)


class TaipitSensor(CoordinatorEntity[TaipitCoordinator], SensorEntity):
    """Taipit Sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description: TaipitSensorEntityDescription
    meter_id: int | None = None

    def __init__(
        self,
        coordinator: TaipitCoordinator,
        entity_description: TaipitSensorEntityDescription,
        meter_id: int,
    ) -> None:
        """Initialize the Sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.meter_id = meter_id

        meter_name = coordinator.data[meter_id]["meter"].get(CONF_NAME)
        meter_manufacturer, meter_model = get_model_name(
            coordinator.data[meter_id]["extended"]["meterTypeId"]
        )
        meter_serial: str = coordinator.data[meter_id]["meter"]["serialNumber"]

        self._attr_unique_id = slugify(
            "_".join(
                [
                    meter_manufacturer,
                    meter_model,
                    str(meter_serial),
                    self.entity_description.key,
                ]
            )
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(meter_id))},
            manufacturer=meter_manufacturer,
            model=meter_model,
            name=meter_name,
            configuration_url=CONFIGURATION_URL.format(meter_id=self.meter_id),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.get(self.meter_id) is not None
            and self.entity_description.avabl_fn(self.coordinator.data[self.meter_id])
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value_fn(
            self.coordinator.data[self.meter_id]
        )

        self._attr_extra_state_attributes = self.entity_description.attr_fn(
            self.coordinator.data[self.meter_id]
        )

        if self.entity_description.icon_fn is not None:
            self._attr_icon = self.entity_description.icon_fn(
                self.coordinator.data[self.meter_id]
            )

        LOGGER.debug("Entity ID: %s Value: %s", self.unique_id, self.native_value)

        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""

    coordinator: TaipitCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[TaipitSensor] = [
        TaipitSensor(coordinator, entity_description, meter_id)
        for entity_description in SENSOR_TYPES
        for meter_id in coordinator.data
    ]

    async_add_entities(entities, True)
