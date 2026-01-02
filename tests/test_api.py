"""Tests for the Aseko API client."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.aseko.api import (
    AsekoApiClient,
    AsekoApiError,
    AsekoAuthError,
    AsekoNotFoundError,
)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    return MagicMock()


@pytest.fixture
def api_client(mock_session):
    """Create an API client with mock session."""
    return AsekoApiClient(mock_session, "test-api-key")


class TestGetUnitSerials:
    """Tests for get_unit_serials method."""

    async def test_returns_sorted_serials(self, api_client):
        """Test that serial numbers are returned sorted."""
        with patch.object(api_client, "_request") as mock_request:
            mock_request.return_value = {
                "items": [
                    {"serialNumber": "ZZZ123"},
                    {"serialNumber": "AAA456"},
                    {"serialNumber": "MMM789"},
                ],
                "totalItems": 3,
            }

            serials = await api_client.get_unit_serials()

            assert serials == ["AAA456", "MMM789", "ZZZ123"]


class TestGetUnits:
    """Tests for get_units method."""

    async def test_auth_error_bubbles_up(self, api_client):
        """Test that AsekoAuthError from parallel fetches is raised."""
        with patch.object(api_client, "get_unit_serials") as mock_serials:
            mock_serials.return_value = ["UNIT1", "UNIT2"]

            with patch.object(api_client, "get_unit") as mock_get_unit:
                # First unit succeeds, second returns auth error
                mock_get_unit.side_effect = [
                    MagicMock(serial_number="UNIT1"),
                    AsekoAuthError("Token expired"),
                ]

                with pytest.raises(AsekoAuthError, match="Token expired"):
                    await api_client.get_units()

    async def test_all_404_raises_error(self, api_client):
        """Test that all units returning 404 raises an error."""
        with patch.object(api_client, "get_unit_serials") as mock_serials:
            mock_serials.return_value = ["UNIT1", "UNIT2", "UNIT3"]

            with patch.object(api_client, "get_unit") as mock_get_unit:
                mock_get_unit.side_effect = AsekoNotFoundError("Not found")

                with pytest.raises(AsekoApiError, match="All 3 units returned 404"):
                    await api_client.get_units()

    async def test_partial_success_returns_available_units(self, api_client):
        """Test that partial failures still return successful units."""
        with patch.object(api_client, "get_unit_serials") as mock_serials:
            mock_serials.return_value = ["UNIT1", "UNIT2", "UNIT3"]

            unit1 = MagicMock(serial_number="UNIT1")
            unit3 = MagicMock(serial_number="UNIT3")

            with patch.object(api_client, "get_unit") as mock_get_unit:
                mock_get_unit.side_effect = [
                    unit1,
                    AsekoNotFoundError("Not found"),
                    unit3,
                ]

                units = await api_client.get_units()

                assert len(units) == 2
                assert units[0].serial_number == "UNIT1"
                assert units[1].serial_number == "UNIT3"

    async def test_empty_serials_returns_empty_list(self, api_client):
        """Test that no serials returns empty list without error."""
        with patch.object(api_client, "get_unit_serials") as mock_serials:
            mock_serials.return_value = []

            units = await api_client.get_units()

            assert units == []
