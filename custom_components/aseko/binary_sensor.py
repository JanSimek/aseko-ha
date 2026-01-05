"""Binary sensor platform for Aseko integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AsekoUnit
from .const import DOMAIN, STATUS_MESSAGE_TRANSLATIONS
from .coordinator import AsekoDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class AsekoBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an Aseko binary sensor entity."""

    value_fn: Callable[[AsekoUnit], bool | None]
    available_fn: Callable[[AsekoUnit], bool] = lambda _: True


def _parse_bool_status(unit: AsekoUnit, key: str) -> bool | None:
    """Parse a boolean status value."""
    value = unit.status_values.get(key)
    if value is None or value == "---":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.upper() in ("YES", "ON", "TRUE", "1")
    return bool(value)


BINARY_SENSOR_DESCRIPTIONS: tuple[AsekoBinarySensorEntityDescription, ...] = (
    AsekoBinarySensorEntityDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda unit: unit.online,
    ),
    AsekoBinarySensorEntityDescription(
        key="has_warning",
        translation_key="has_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda unit: unit.has_warning,
    ),
    AsekoBinarySensorEntityDescription(
        key="water_flow_to_probes",
        translation_key="water_flow_to_probes",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda unit: _parse_bool_status(unit, "waterFlowToProbes"),
        available_fn=lambda unit: "waterFlowToProbes" in unit.status_values,
    ),
    AsekoBinarySensorEntityDescription(
        key="heating",
        translation_key="heating",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda unit: _parse_bool_status(unit, "heatingRunning"),
        available_fn=lambda unit: "heatingRunning" in unit.status_values,
    ),
    AsekoBinarySensorEntityDescription(
        key="electrolyzer_running",
        translation_key="electrolyzer_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda unit: _parse_bool_status(unit, "electrolyzerRunning"),
        available_fn=lambda unit: "electrolyzerRunning" in unit.status_values,
    ),
    AsekoBinarySensorEntityDescription(
        key="solar_running",
        translation_key="solar_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda unit: _parse_bool_status(unit, "solarRunning"),
        available_fn=lambda unit: "solarRunning" in unit.status_values,
    ),
    AsekoBinarySensorEntityDescription(
        key="filtration_running",
        translation_key="filtration_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda unit: _parse_bool_status(unit, "filtrationRunning"),
        available_fn=lambda unit: "filtrationRunning" in unit.status_values,
    ),
    AsekoBinarySensorEntityDescription(
        key="water_filling_running",
        translation_key="water_filling_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda unit: _parse_bool_status(unit, "waterFillingRunning"),
        available_fn=lambda unit: "waterFillingRunning" in unit.status_values,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aseko binary sensors based on a config entry."""
    coordinator: AsekoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which units we've already created entities for
    known_units: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Add entities for newly discovered units."""
        new_entities: list[AsekoBinarySensorEntity] = []

        for serial_number, unit in coordinator.data.items():
            if serial_number in known_units:
                continue

            for description in BINARY_SENSOR_DESCRIPTIONS:
                if description.available_fn(unit):
                    new_entities.append(
                        AsekoBinarySensorEntity(coordinator, unit, description)
                    )

            known_units.add(serial_number)

        if new_entities:
            async_add_entities(new_entities)

    # Add entities for initial data
    _async_add_new_entities()

    # Register listener for future updates to discover new units
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_entities)
    )


class AsekoBinarySensorEntity(
    CoordinatorEntity[AsekoDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of an Aseko binary sensor."""

    entity_description: AsekoBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AsekoDataUpdateCoordinator,
        unit: AsekoUnit,
        description: AsekoBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._serial_number = unit.serial_number
        self._attr_unique_id = f"{unit.serial_number}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unit.serial_number)},
            name=unit.name or f"Aseko {unit.serial_number}",
            manufacturer="Aseko",
            model=unit.brand_name,
        )

    @property
    def _unit(self) -> AsekoUnit | None:
        """Return the unit data."""
        return self.coordinator.data.get(self._serial_number)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self._unit:
            return None
        return self.entity_description.value_fn(self._unit)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available or self._unit is None:
            return False
        return self.entity_description.available_fn(self._unit)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes for the warning sensor."""
        if self.entity_description.key != "has_warning":
            return None
        if not self._unit or not self._unit.status_messages:
            return None

        error_msgs = [
            m for m in self._unit.status_messages
            if m.get("severity") in ("ERROR", "WARNING")
        ]

        if not error_msgs:
            return None

        return {
            "error_types": ",".join(m.get("type", "") for m in error_msgs),
            "errors": [
                {
                    "type": m.get("type"),
                    "severity": m.get("severity"),
                    "message": STATUS_MESSAGE_TRANSLATIONS.get(
                        m.get("type", ""), m.get("message")
                    ),
                    "detail": m.get("detail"),
                }
                for m in error_msgs
            ],
        }
