"""Base entity for Taipit integration."""
from aiotaipit.helpers import get_model_name
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN, ATTRIBUTION, CONFIGURATION_URL, CONF_NAME
from .coordinator import TaipitCoordinator


class TaipitBaseCoordinatorEntity(CoordinatorEntity[TaipitCoordinator]):
    """Taipit Base Entity."""
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    meter_id: int

    def __init__(
            self,
            coordinator: TaipitCoordinator,
            entity_description: EntityDescription,
            meter_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description
        self.meter_id = meter_id

        meter_name = self.coordinator.data[self.meter_id]["meter"].get(CONF_NAME)
        meter_manufacturer, meter_model = get_model_name(
            self.coordinator.data[self.meter_id]["extended"]["meterTypeId"]
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self.meter_id))},
            manufacturer=meter_manufacturer,
            model=meter_model,
            name=meter_name,
            configuration_url=CONFIGURATION_URL.format(meter_id=self.meter_id),
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
