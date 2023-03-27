"""Support for Taipit button."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonEntityDescription,
    ButtonEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
)
from .coordinator import TaipitCoordinator
from .entity import TaipitBaseCoordinatorEntity


@dataclass
class TaipitButtonRequiredKeysMixin:
    """Mixin for required keys."""

    async_press: Callable[[TaipitCoordinator], Awaitable]


@dataclass
class TaipitButtonEntityDescription(
    ButtonEntityDescription, TaipitButtonRequiredKeysMixin
):
    """Class describing Taipit button entities."""


BUTTON_DESCRIPTIONS: tuple[TaipitButtonEntityDescription, ...] = (
    TaipitButtonEntityDescription(
        key="refresh",
        icon="mdi:refresh",
        name="Refresh from cloud",
        entity_category=EntityCategory.CONFIG,
        async_press=lambda coordinator: (coordinator.async_force_refresh()),
    ),
)


class TaipitButtonEntity(TaipitBaseCoordinatorEntity, ButtonEntity):
    """Representation of a Taipit button."""

    entity_description: TaipitButtonEntityDescription

    def __init__(
            self,
            coordinator: TaipitCoordinator,
            entity_description: TaipitButtonEntityDescription,
            meter_id: int
    ) -> None:
        """Initialize Taipit button."""
        super().__init__(coordinator, entity_description, meter_id)

    async def async_press(self) -> None:
        """Press the button."""
        await self.entity_description.async_press(self.coordinator)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""

    coordinator: TaipitCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[TaipitButtonEntity] = [
        TaipitButtonEntity(coordinator, entity_description, meter_id)
        for entity_description in BUTTON_DESCRIPTIONS
        for meter_id in coordinator.data
    ]

    async_add_entities(entities, True)
