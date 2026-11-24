"""Tests for the Aseko sensor platform."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.aseko.api import AsekoUnit
from custom_components.aseko.const import (
    ACTIVE_WARNING_SEVERITIES,
    STATUS_MESSAGE_TRANSLATIONS,
    STATUS_MESSAGE_TRANSLATIONS_CS,
)
from custom_components.aseko.sensor import (
    SENSOR_DESCRIPTIONS,
    AsekoFiltrationPeriodSensorEntity,
    AsekoSensorEntity,
    AsekoWarningReasonSensorEntity,
)

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "aseko"
ENUM_DESCRIPTIONS = [d for d in SENSOR_DESCRIPTIONS if d.options]


def _make_unit(
    status_values: dict, status_messages: list | None = None
) -> AsekoUnit:
    """Create a minimal AsekoUnit with the given status values and messages."""
    return AsekoUnit(
        serial_number="TEST001",
        name="Test Pool",
        note=None,
        online=True,
        has_warning=False,
        brand_name="ASIN AQUA Net",
        status_values=status_values,
        status_messages=status_messages or [],
    )


def _make_entity(unit: AsekoUnit) -> AsekoFiltrationPeriodSensorEntity:
    """Create an AsekoFiltrationPeriodSensorEntity with a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {unit.serial_number: unit}
    entity = AsekoFiltrationPeriodSensorEntity(coordinator, unit)
    return entity


class TestAsekoFiltrationPeriodSensorEntity:
    """Tests for AsekoFiltrationPeriodSensorEntity."""

    def test_nonstop_filtration_returns_nonstop(self):
        """When isNonstop is True, native_value should be 'nonstop'."""
        unit = _make_unit(
            {
                "upcomingFiltrationPeriod": {
                    "isNonstop": True,
                    "isNext": False,
                    "start": None,
                    "end": None,
                }
            }
        )
        entity = _make_entity(unit)
        assert entity.native_value == "nonstop"

    def test_upcoming_period_returns_next(self):
        """When isNext is True, native_value should be 'next'."""
        unit = _make_unit(
            {
                "upcomingFiltrationPeriod": {
                    "isNonstop": False,
                    "isNext": True,
                    "start": "10:00",
                    "end": "12:00",
                }
            }
        )
        entity = _make_entity(unit)
        assert entity.native_value == "next"

    def test_running_period_returns_running(self):
        """When isNext is False (currently running), native_value should be 'running'."""
        unit = _make_unit(
            {
                "upcomingFiltrationPeriod": {
                    "isNonstop": False,
                    "isNext": False,
                    "start": "08:00",
                    "end": "10:00",
                }
            }
        )
        entity = _make_entity(unit)
        assert entity.native_value == "running"

    def test_period_without_times_returns_none(self):
        """A period dict lacking start/end (and not nonstop) yields None."""
        unit = _make_unit(
            {"upcomingFiltrationPeriod": {"isNonstop": False, "isNext": True}}
        )
        entity = _make_entity(unit)
        assert entity.native_value is None

    def test_native_value_is_within_declared_options(self):
        """Any non-None state must be one of the declared ENUM options."""
        unit = _make_unit(
            {
                "upcomingFiltrationPeriod": {
                    "isNonstop": False,
                    "isNext": True,
                    "start": "10:00",
                    "end": "12:00",
                }
            }
        )
        entity = _make_entity(unit)
        assert entity.native_value in entity.options

    def test_missing_period_returns_none(self):
        """When upcomingFiltrationPeriod is absent, native_value should be None."""
        unit = _make_unit({"waterTemperature": 25.0})
        entity = _make_entity(unit)
        assert entity.native_value is None

    def test_null_period_returns_none(self):
        """When upcomingFiltrationPeriod is None, native_value should be None."""
        unit = _make_unit({"upcomingFiltrationPeriod": None})
        entity = _make_entity(unit)
        assert entity.native_value is None

    def test_extra_state_attributes_full_data(self):
        """Extra attributes should expose raw period fields."""
        period = {
            "isNonstop": False,
            "isNext": True,
            "start": "10:00",
            "end": "12:00",
        }
        unit = _make_unit({"upcomingFiltrationPeriod": period})
        entity = _make_entity(unit)
        attrs = entity.extra_state_attributes
        assert attrs == {
            "is_nonstop": False,
            "is_next": True,
            "start": "10:00",
            "end": "12:00",
        }

    def test_extra_state_attributes_missing_period_returns_none(self):
        """Extra attributes should be None when no period data."""
        unit = _make_unit({})
        entity = _make_entity(unit)
        assert entity.extra_state_attributes is None

    def test_unique_id_uses_serial_number(self):
        """Unique ID should include the serial number."""
        unit = _make_unit({"upcomingFiltrationPeriod": {}})
        entity = _make_entity(unit)
        assert entity.unique_id == "TEST001_upcoming_filtration_period"

    def test_translation_key(self):
        """Translation key should be correct."""
        unit = _make_unit({"upcomingFiltrationPeriod": {}})
        entity = _make_entity(unit)
        assert entity.translation_key == "upcoming_filtration_period"


def _description(key: str):
    """Return the sensor description with the given key."""
    return next(d for d in SENSOR_DESCRIPTIONS if d.key == key)


class TestEnumSensors:
    """Tests for the enum status sensors."""

    def test_enum_sensors_declare_options(self):
        """Every enum sensor should declare its options."""
        keys = {d.key for d in ENUM_DESCRIPTIONS}
        assert keys == {
            "electrolyzer_direction",
            "mode",
            "filtration_speed",
            "pool_flow",
            "water_level_state",
        }

    def test_upper_case_value_is_lowercased(self):
        """API values are upper case; the state should be the lowercase option."""
        unit = _make_unit({"waterLevelState": "LOW"})
        entity = AsekoSensorEntity(
            MagicMock(data={unit.serial_number: unit}),
            unit,
            _description("water_level_state"),
        )
        assert entity.native_value == "low"

    @pytest.mark.parametrize("value", ["SIDEWAYS", "---", "", None])
    def test_unknown_or_empty_value_returns_none(self, value):
        """A value outside the options must not raise; it becomes unknown."""
        unit = _make_unit({"mode": value})
        entity = AsekoSensorEntity(
            MagicMock(data={unit.serial_number: unit}), unit, _description("mode")
        )
        assert entity.native_value is None


def _make_reason_entity(messages: list) -> AsekoWarningReasonSensorEntity:
    """Create a warning reason sensor for a unit with the given messages."""
    unit = _make_unit({}, messages)
    coordinator = MagicMock()
    coordinator.data = {unit.serial_number: unit}
    return AsekoWarningReasonSensorEntity(coordinator, unit)


class TestAsekoWarningReasonSensorEntity:
    """Tests for AsekoWarningReasonSensorEntity."""

    def test_no_warning_returns_none_state(self):
        """Without active warnings the state is 'none' with no attributes."""
        entity = _make_reason_entity(
            [{"type": "START_BY_SOLAR", "severity": "INFO"}]
        )
        assert entity.native_value == "none"
        assert entity.extra_state_attributes is None

    def test_known_warning_is_lowercased_type(self):
        """A known message type becomes the lowercased state."""
        entity = _make_reason_entity(
            [
                {
                    "type": "WATER_LEVEL_TOO_LOW",
                    "severity": "ERROR",
                    "message": "Water level too low",
                    "detail": "Pump OFF",
                }
            ]
        )
        assert entity.native_value == "water_level_too_low"
        assert entity.extra_state_attributes == {
            "type": "WATER_LEVEL_TOO_LOW",
            "severity": "ERROR",
            "message": "Water level too low",
            "detail": "Pump OFF",
            "active_warnings": 1,
        }

    def test_error_takes_precedence_over_warning(self):
        """An ERROR is shown before an earlier WARNING."""
        entity = _make_reason_entity(
            [
                {"type": "CLOCK_MEMORY_BATTERY_LOW", "severity": "WARNING"},
                {"type": "PUMP_OVERHEATED", "severity": "ERROR"},
            ]
        )
        assert entity.native_value == "pump_overheated"
        assert entity.extra_state_attributes["active_warnings"] == 2

    def test_unknown_type_returns_other(self):
        """A message type not known yet maps to 'other', raw type in attributes."""
        entity = _make_reason_entity(
            [{"type": "SOMETHING_NEW", "severity": "WARNING", "message": "New"}]
        )
        assert entity.native_value == "other"
        assert entity.extra_state_attributes["type"] == "SOMETHING_NEW"

    def test_state_is_always_within_options(self):
        """Every possible state must be a declared option."""
        for messages in (
            [],
            [{"type": "WATER_LEVEL_TOO_LOW", "severity": "ERROR"}],
            [{"type": "SOMETHING_NEW", "severity": "ERROR"}],
            [{"severity": "ERROR"}],
        ):
            entity = _make_reason_entity(messages)
            assert entity.native_value in entity.options

    def test_unique_id_and_translation_key(self):
        """Unique ID and translation key should be stable."""
        entity = _make_reason_entity([])
        assert entity.unique_id == "TEST001_warning_reason"
        assert entity.translation_key == "warning_reason"


@pytest.mark.parametrize(
    "translation_file", ["strings.json", "translations/en.json", "translations/cs.json"]
)
def test_every_enum_state_is_translated(translation_file):
    """Each option of each enum sensor needs a translation in every language."""
    sensors = json.loads(
        (COMPONENT_DIR / translation_file).read_text(encoding="utf-8")
    )["entity"]["sensor"]
    expected = {d.translation_key: d.options for d in ENUM_DESCRIPTIONS}
    expected["warning_reason"] = _make_reason_entity([]).options
    for translation_key, options in expected.items():
        states = sensors[translation_key]["state"]
        assert set(states) == set(options), translation_key


class TestMatchesApiSpec:
    """Check the hard-coded value lists against the Aseko OpenAPI spec.

    tests/fixtures/openapi_enums.json is an extract of the enums in the
    official spec (https://api.aseko.cloud/api/v1/docs). When Aseko adds a
    value, refresh the fixture and these tests point at what to extend.
    """

    SPEC = json.loads(
        (Path(__file__).parent / "fixtures" / "openapi_enums.json").read_text(
            encoding="utf-8"
        )
    )

    def test_enum_sensor_options_match_spec(self):
        """Each enum sensor's options are exactly the spec's values, lowercased."""
        spec_values = self.SPEC["StatusValues"]
        assert {d.status_key for d in ENUM_DESCRIPTIONS} == set(spec_values)
        for description in ENUM_DESCRIPTIONS:
            expected = [v.lower() for v in spec_values[description.status_key]]
            assert sorted(description.options) == sorted(expected), description.key

    def test_every_message_type_is_translated(self):
        """Every message type in the spec has an English and Czech text."""
        spec_types = set(self.SPEC["StatusMessage"]["type"])
        assert set(STATUS_MESSAGE_TRANSLATIONS) == spec_types
        assert set(STATUS_MESSAGE_TRANSLATIONS_CS) == spec_types

    def test_active_severities_exist_in_spec(self):
        """The severities treated as warnings are real severities."""
        assert set(ACTIVE_WARNING_SEVERITIES) <= set(
            self.SPEC["StatusMessage"]["severity"]
        )
