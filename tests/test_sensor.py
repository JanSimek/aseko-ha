"""Tests for the Aseko sensor platform."""

from unittest.mock import MagicMock

from custom_components.aseko.api import AsekoUnit
from custom_components.aseko.sensor import AsekoFiltrationPeriodSensorEntity


def _make_unit(status_values: dict) -> AsekoUnit:
    """Create a minimal AsekoUnit with the given status values."""
    return AsekoUnit(
        serial_number="TEST001",
        name="Test Pool",
        note=None,
        online=True,
        has_warning=False,
        brand_name="ASIN AQUA Net",
        status_values=status_values,
        status_messages=[],
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
