"""Support for Taipit button."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ENTITY_ID_FORMAT,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TaipitConfigEntry
from .coordinator import TaipitCoordinator
from .entity import TaipitBaseCoordinatorEntity


@dataclass(frozen=True, kw_only=True)
class TaipitButtonEntityDescription(ButtonEntityDescription):
    """Class describing Taipit button entities."""

    async_press: Callable[[TaipitCoordinator], Awaitable]


BUTTON_DESCRIPTIONS: tuple[TaipitButtonEntityDescription, ...] = (
    TaipitButtonEntityDescription(
        key="refresh",
        translation_key="refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
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
        meter_id: int,
    ) -> None:
        """Initialize Taipit button."""
        super().__init__(coordinator, entity_description, meter_id)

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=coordinator.hass
        )

    async def async_press(self) -> None:
        """Press the button."""
        await self.entity_description.async_press(self.coordinator)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TaipitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""
    coordinator: TaipitCoordinator = entry.runtime_data

    entities: list[TaipitButtonEntity] = [
        TaipitButtonEntity(coordinator, entity_description, meter_id)
        for entity_description in BUTTON_DESCRIPTIONS
        for meter_id in coordinator.data
    ]

    async_add_entities(entities, True)
