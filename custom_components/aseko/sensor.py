"""Sensor platform for Aseko integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
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
    UnitOfLength,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AsekoUnit
from .const import (
    DOMAIN,
    ELECTROLYZER_DIRECTION_OPTIONS,
    FILTRATION_SPEED_OPTIONS,
    MODE_OPTIONS,
    POOL_FLOW_OPTIONS,
    STATUS_MESSAGE_TRANSLATIONS,
    WARNING_REASON_NONE,
    WARNING_REASON_OTHER,
    WATER_LEVEL_STATE_OPTIONS,
)
from .coordinator import AsekoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Unknown enum values already logged, so each is reported only once.
_LOGGED_UNKNOWN_ENUM_VALUES: set[tuple[str, str]] = set()

# States of the warning reason sensor: no warning, every known message type
# (lowercased so it can be translated), or a message type we don't know yet.
WARNING_REASON_OPTIONS: list[str] = [
    WARNING_REASON_NONE,
    *(message_type.lower() for message_type in STATUS_MESSAGE_TRANSLATIONS),
    WARNING_REASON_OTHER,
]


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


def _enum_parser(status_key: str, options: list[str]) -> Callable[[str], str | None]:
    """Return a parser mapping an upper-case API value to a lowercase option.

    A value outside ``options`` maps to None (unknown state) instead of
    raising, and is logged once so the option list can be extended.
    """

    def parse(value: str) -> str | None:
        if not isinstance(value, str) or value in ("---", ""):
            return None
        option = value.lower()
        if option in options:
            return option
        if (status_key, value) not in _LOGGED_UNKNOWN_ENUM_VALUES:
            _LOGGED_UNKNOWN_ENUM_VALUES.add((status_key, value))
            _LOGGER.warning(
                "Unknown value %r for Aseko status %s; please report it",
                value,
                status_key,
            )
        return None

    return parse


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
    # Additional numeric sensors
    AsekoSensorEntityDescription(
        key="cl_free_required",
        translation_key="cl_free_required",
        status_key="clFreeRequired",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="cl_bounded",
        translation_key="cl_bounded",
        status_key="clBounded",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="electrode_power",
        translation_key="electrode_power",
        status_key="electrodePower",
        native_unit_of_measurement="g/h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="filter_flow_speed",
        translation_key="filter_flow_speed",
        status_key="filterFlowSpeed",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="filter_pressure",
        translation_key="filter_pressure",
        status_key="filterPressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="ph_required",
        translation_key="ph_required",
        status_key="phRequired",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="redox_required",
        translation_key="redox_required",
        status_key="redoxRequired",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_int,
    ),
    AsekoSensorEntityDescription(
        key="solar_temperature",
        translation_key="solar_temperature",
        status_key="solarTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="water_level",
        translation_key="water_level",
        status_key="waterLevel",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    AsekoSensorEntityDescription(
        key="water_temperature_required",
        translation_key="water_temperature_required",
        status_key="waterTemperatureRequired",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_float,
    ),
    # Enum/state sensors (no unit, string values)
    AsekoSensorEntityDescription(
        key="electrolyzer_direction",
        translation_key="electrolyzer_direction",
        status_key="electrolyzerDirection",
        device_class=SensorDeviceClass.ENUM,
        options=ELECTROLYZER_DIRECTION_OPTIONS,
        value_fn=_enum_parser("electrolyzerDirection", ELECTROLYZER_DIRECTION_OPTIONS),
    ),
    AsekoSensorEntityDescription(
        key="mode",
        translation_key="mode",
        status_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=MODE_OPTIONS,
        value_fn=_enum_parser("mode", MODE_OPTIONS),
    ),
    AsekoSensorEntityDescription(
        key="filtration_speed",
        translation_key="filtration_speed",
        status_key="filtrationSpeed",
        device_class=SensorDeviceClass.ENUM,
        options=FILTRATION_SPEED_OPTIONS,
        value_fn=_enum_parser("filtrationSpeed", FILTRATION_SPEED_OPTIONS),
    ),
    AsekoSensorEntityDescription(
        key="pool_flow",
        translation_key="pool_flow",
        status_key="poolFlow",
        device_class=SensorDeviceClass.ENUM,
        options=POOL_FLOW_OPTIONS,
        value_fn=_enum_parser("poolFlow", POOL_FLOW_OPTIONS),
    ),
    AsekoSensorEntityDescription(
        key="water_level_state",
        translation_key="water_level_state",
        status_key="waterLevelState",
        device_class=SensorDeviceClass.ENUM,
        options=WATER_LEVEL_STATE_OPTIONS,
        value_fn=_enum_parser("waterLevelState", WATER_LEVEL_STATE_OPTIONS),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aseko sensors based on a config entry."""
    coordinator: AsekoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track the unique IDs we've already created entities for, keyed per
    # status value rather than per unit — a status key that only shows up in a
    # later update still gets its sensor created.
    known_entities: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Add entities for newly discovered units and status values."""
        new_entities: list[SensorEntity] = []

        for serial_number, unit in coordinator.data.items():
            for description in SENSOR_DESCRIPTIONS:
                unique_id = f"{serial_number}_{description.key}"
                if (
                    description.status_key in unit.status_values
                    and unique_id not in known_entities
                ):
                    known_entities.add(unique_id)
                    new_entities.append(
                        AsekoSensorEntity(coordinator, unit, description)
                    )

            unique_id = f"{serial_number}_warning_reason"
            if unique_id not in known_entities:
                known_entities.add(unique_id)
                new_entities.append(AsekoWarningReasonSensorEntity(coordinator, unit))

            unique_id = f"{serial_number}_upcoming_filtration_period"
            if (
                "upcomingFiltrationPeriod" in unit.status_values
                and unique_id not in known_entities
            ):
                known_entities.add(unique_id)
                new_entities.append(
                    AsekoFiltrationPeriodSensorEntity(coordinator, unit)
                )

        if new_entities:
            async_add_entities(new_entities)

    # Add entities for initial data
    _async_add_new_entities()

    # Register listener for future updates to discover new units
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_entities)
    )


class _AsekoUnitEntity(CoordinatorEntity[AsekoDataUpdateCoordinator], SensorEntity):
    """Base for entities bound to a single Aseko unit.

    Holds the shared device info, unit lookup and availability logic so the
    concrete sensors only add their own value handling.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AsekoDataUpdateCoordinator,
        unit: AsekoUnit,
    ) -> None:
        """Initialize the entity and its device info."""
        super().__init__(coordinator)
        self._serial_number = unit.serial_number
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unit.serial_number)},
            name=unit.name or f"Aseko {unit.serial_number}",
            manufacturer="Aseko",
            model=unit.brand_name,
        )

    @property
    def _unit(self) -> AsekoUnit | None:
        """Return the current data for this unit."""
        return self.coordinator.data.get(self._serial_number)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._unit is not None


class AsekoSensorEntity(_AsekoUnitEntity):
    """Representation of an Aseko sensor."""

    entity_description: AsekoSensorEntityDescription

    def __init__(
        self,
        coordinator: AsekoDataUpdateCoordinator,
        unit: AsekoUnit,
        description: AsekoSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, unit)
        self.entity_description = description
        self._attr_unique_id = f"{unit.serial_number}_{description.key}"

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


class AsekoFiltrationPeriodSensorEntity(_AsekoUnitEntity):
    """Sensor representing the upcoming filtration period.

    The state is the kind of period ("nonstop", "next" or "running"); the
    concrete start/end times are exposed as attributes so the state stays a
    stable, translatable enum instead of a formatted string.
    """

    _attr_translation_key = "upcoming_filtration_period"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["nonstop", "next", "running"]

    def __init__(
        self,
        coordinator: AsekoDataUpdateCoordinator,
        unit: AsekoUnit,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, unit)
        self._attr_unique_id = f"{unit.serial_number}_upcoming_filtration_period"

    def _period(self) -> dict[str, Any] | None:
        """Return the upcoming filtration period dict, if present and non-empty."""
        if not self._unit:
            return None
        period = self._unit.status_values.get("upcomingFiltrationPeriod")
        return period if isinstance(period, dict) and period else None

    @property
    def native_value(self) -> str | None:
        """Return the kind of the upcoming filtration period.

        One of "nonstop", "next" (a future period is scheduled) or "running"
        (a period is currently active), or None when unknown.
        """
        period = self._period()
        if period is None:
            return None
        if period.get("isNonstop"):
            return "nonstop"
        if period.get("start") and period.get("end"):
            return "next" if period.get("isNext") else "running"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return detailed filtration period attributes."""
        period = self._period()
        if period is None:
            return None
        return {
            "is_nonstop": period.get("isNonstop"),
            "is_next": period.get("isNext"),
            "start": period.get("start"),
            "end": period.get("end"),
        }


class AsekoWarningReasonSensorEntity(_AsekoUnitEntity):
    """Sensor naming the reason of the current warning.

    The Warning binary sensor only says that something is wrong. This sensor's
    state is the message type of the most severe active warning, lowercased so
    the frontend and logbook show it translated ("Water level too low"). It is
    "none" when there is no warning and "other" for a type not known yet.
    """

    _attr_translation_key = "warning_reason"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = WARNING_REASON_OPTIONS

    def __init__(
        self,
        coordinator: AsekoDataUpdateCoordinator,
        unit: AsekoUnit,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, unit)
        self._attr_unique_id = f"{unit.serial_number}_warning_reason"

    def _primary_warning(self) -> dict[str, Any] | None:
        """Return the most severe active warning (errors before warnings)."""
        if not self._unit:
            return None
        warnings = self._unit.active_warnings
        if not warnings:
            return None
        errors = [msg for msg in warnings if msg.get("severity") == "ERROR"]
        return (errors or warnings)[0]

    @property
    def native_value(self) -> str | None:
        """Return the reason of the most severe active warning."""
        if not self._unit:
            return None
        warning = self._primary_warning()
        if warning is None:
            return WARNING_REASON_NONE
        reason = str(warning.get("type", "")).lower()
        return reason if reason in self._attr_options else WARNING_REASON_OTHER

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return details of the warning shown in the state."""
        warning = self._primary_warning()
        if warning is None:
            return None
        return {
            "type": warning.get("type"),
            "severity": warning.get("severity"),
            "message": warning.get("message"),
            "detail": warning.get("detail"),
            "active_warnings": len(self._unit.active_warnings),
        }
