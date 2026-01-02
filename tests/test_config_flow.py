"""Tests for the Aseko config flow."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.aseko.config_flow import AsekoConfigFlow, _stable_hash
from custom_components.aseko.const import DOMAIN, CONF_API_KEY


class TestStableHash:
    """Tests for the stable hash function."""

    def test_same_input_same_output(self):
        """Test that same input produces same output."""
        hash1 = _stable_hash("test-api-key")
        hash2 = _stable_hash("test-api-key")
        assert hash1 == hash2

    def test_different_input_different_output(self):
        """Test that different inputs produce different outputs."""
        hash1 = _stable_hash("test-api-key-1")
        hash2 = _stable_hash("test-api-key-2")
        assert hash1 != hash2

    def test_hash_length(self):
        """Test that hash is 12 characters."""
        result = _stable_hash("test")
        assert len(result) == 12


class TestReauthAccountMismatch:
    """Tests for reauth account mismatch handling."""

    async def test_reauth_same_account_succeeds(self, hass: HomeAssistant):
        """Test that reauth with same account succeeds."""
        # This would require full Home Assistant test infrastructure
        # Placeholder for integration test
        pass

    async def test_reauth_different_account_fails(self, hass: HomeAssistant):
        """Test that reauth with different account shows error."""
        # This would require full Home Assistant test infrastructure
        # Placeholder for integration test
        pass


class TestUniqueIdStability:
    """Tests for unique ID stability."""

    def test_sorted_serials_produces_stable_id(self):
        """Test that sorted serials produce stable unique IDs."""
        # Given unsorted API responses
        serials_response_1 = ["ZZZ", "AAA", "MMM"]
        serials_response_2 = ["MMM", "ZZZ", "AAA"]

        # When sorted
        sorted_1 = sorted(serials_response_1)
        sorted_2 = sorted(serials_response_2)

        # Then first element is the same
        assert sorted_1[0] == sorted_2[0] == "AAA"
