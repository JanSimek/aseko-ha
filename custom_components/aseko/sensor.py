"""Sensor platform for Aseko integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AsekoUnit
from .const import DOMAIN
from .coordinator import AsekoDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class AsekoSensorEntityDescription(SensorEntityDescription):
    """Describes an Aseko sensor entity."""

    status_key: str
    value_fn: Callable[[str], Any] | None = None


def _parse_float(value: str) -> float | None:
    """Parse a float value, returning None for invalid values."""
    if value in ("---", "", None):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_int(value: str) -> int | None:
    """Parse an int value, returning None for invalid values."""
    if value in ("---", "", None):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


SENSOR_DESCRIPTIONS: tuple[AsekoSensorEntityDescription, ...] = (
    AsekoSensorEntityDescription(
        key="water_temperature",
        translation_key="water_temperature",
        status_key="waterTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="air_temperature",
        translation_key="air_temperature",
        status_key="airTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="ph",
        translation_key="ph",
        status_key="ph",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="redox",
        translation_key="redox",
        status_key="redox",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_int,
    ),
    AsekoSensorEntityDescription(
        key="cl_free",
        translation_key="cl_free",
        status_key="clFree",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="salinity",
        translation_key="salinity",
        status_key="salinity",
        native_unit_of_measurement="g/L",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="electrolyzer",
        translation_key="electrolyzer",
        status_key="electrolyzer",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_int,
    ),
    AsekoSensorEntityDescription(
        key="dose",
        translation_key="dose",
        status_key="dose",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_int,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aseko sensors based on a config entry."""
    coordinator: AsekoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which units we've already created entities for
    known_units: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Add entities for newly discovered units."""
        new_entities: list[AsekoSensorEntity] = []

        for serial_number, unit in coordinator.data.items():
            if serial_number in known_units:
                continue

            for description in SENSOR_DESCRIPTIONS:
                if description.status_key in unit.status_values:
                    new_entities.append(
                        AsekoSensorEntity(coordinator, unit, description)
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


class AsekoSensorEntity(CoordinatorEntity[AsekoDataUpdateCoordinator], SensorEntity):
    """Representation of an Aseko sensor."""

    entity_description: AsekoSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AsekoDataUpdateCoordinator,
        unit: AsekoUnit,
        description: AsekoSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self._unit:
            return None

        raw_value = self._unit.status_values.get(self.entity_description.status_key)
        if raw_value is None:
            return None

        if self.entity_description.value_fn:
            return self.entity_description.value_fn(raw_value)

        return raw_value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._unit is not None
