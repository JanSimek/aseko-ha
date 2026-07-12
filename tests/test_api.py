"""Tests for the Aseko API client."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.aseko.api import (
    AsekoApiClient,
    AsekoApiError,
    AsekoAuthError,
    AsekoNotFoundError,
    AsekoTermsNotAcceptedError,
)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    return MagicMock()


@pytest.fixture
def api_client(mock_session):
    """Create an API client with mock session."""
    return AsekoApiClient(mock_session, "test-api-key")


def client_for_response(status, body):
    """Create an API client whose session returns a single canned response.

    Args:
        status: HTTP status code to return
        body: Parsed JSON body, or an exception to raise when parsing it
    """
    response = MagicMock()
    response.status = status
    if isinstance(body, Exception):
        response.json = AsyncMock(side_effect=body)
    else:
        response.json = AsyncMock(return_value=body)

    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.request = MagicMock(return_value=context)

    return AsekoApiClient(session, "test-api-key")


class TestErrorResponses:
    """Tests for how HTTP error responses map to exceptions."""

    async def test_tos_not_accepted_raises_terms_error(self):
        """Test that a 403 TOS_NOT_ACCEPTED is not reported as a bad API key."""
        client = client_for_response(
            403,
            {
                "error": "Terms of services are not accepted.",
                "errorType": "TOS_NOT_ACCEPTED",
                "statusCode": 403,
            },
        )

        with pytest.raises(AsekoTermsNotAcceptedError):
            await client.validate_api_key()

    async def test_terms_error_is_not_an_auth_error(self):
        """Test that the terms error does not trigger auth handling (reauth)."""
        assert not issubclass(AsekoTermsNotAcceptedError, AsekoAuthError)
        assert issubclass(AsekoTermsNotAcceptedError, AsekoApiError)

    async def test_other_403_still_raises_auth_error(self):
        """Test that a 403 for any other reason is still an auth error."""
        client = client_for_response(
            403, {"error": "Forbidden", "errorType": "FORBIDDEN", "statusCode": 403}
        )

        with pytest.raises(AsekoAuthError):
            await client.validate_api_key()

    async def test_401_raises_auth_error(self):
        """Test that a missing or invalid key is still an auth error."""
        client = client_for_response(
            401, {"error": "The API key is missing.", "errorType": "API_KEY_MISSING"}
        )

        with pytest.raises(AsekoAuthError):
            await client.validate_api_key()

    async def test_unparsable_error_body_falls_back_to_auth_error(self):
        """Test that a non-JSON error body does not crash the client."""
        client = client_for_response(403, ValueError("not json"))

        with pytest.raises(AsekoAuthError):
            await client.validate_api_key()


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

    async def test_terms_error_bubbles_up(self, api_client):
        """Test that AsekoTermsNotAcceptedError is fatal and is not swallowed."""
        with patch.object(api_client, "get_unit_serials") as mock_serials:
            mock_serials.return_value = ["UNIT1", "UNIT2"]

            with patch.object(api_client, "get_unit") as mock_get_unit:
                mock_get_unit.side_effect = [
                    MagicMock(serial_number="UNIT1"),
                    AsekoTermsNotAcceptedError("Terms not accepted"),
                ]

                with pytest.raises(
                    AsekoTermsNotAcceptedError, match="Terms not accepted"
                ):
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
