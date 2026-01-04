"""Config flow for Aseko integration."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AsekoApiClient, AsekoAuthError, AsekoApiError
from .const import DOMAIN, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


def _stable_hash(value: str) -> str:
    """Generate a stable hash from a string value.

    Uses SHA256 for deterministic hashing across Python restarts.
    """
    return hashlib.sha256(value.encode()).hexdigest()[:12]


class AsekoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aseko."""

    VERSION = 1

    async def _validate_api_key(
        self, api_key: str
    ) -> tuple[str | None, dict[str, str]]:
        """Validate API key and return unique_id or errors.

        Uses lightweight list endpoint to get serial numbers for unique_id.
        Serial numbers are sorted for stable ordering.

        Returns:
            Tuple of (unique_id, errors dict)
        """
        errors: dict[str, str] = {}

        try:
            session = async_get_clientsession(self.hass)
            client = AsekoApiClient(session, api_key)
            valid = await client.validate_api_key()

            if not valid:
                errors["base"] = "invalid_auth"
                return None, errors

            # Get unit serial numbers (lightweight, sorted for stability)
            serials = await client.get_unit_serials()
            if serials:
                # Use first sorted serial as unique_id
                unique_id = serials[0]
            else:
                # Fallback: use stable hash of API key (not the key itself)
                unique_id = f"aseko_{_stable_hash(api_key)}"

            return unique_id, errors

        except AsekoAuthError:
            errors["base"] = "invalid_auth"
        except AsekoApiError:
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return None, errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            unique_id, errors = await self._validate_api_key(api_key)

            if unique_id and not errors:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Aseko Pool",
                    data={CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when API key expires."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth with new API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            unique_id, errors = await self._validate_api_key(api_key)

            if unique_id and not errors:
                # Get the existing entry
                reauth_entry = self.hass.config_entries.async_get_entry(
                    self.context.get("entry_id")
                )
                if not reauth_entry:
                    errors["base"] = "unknown"
                elif reauth_entry.unique_id != unique_id:
                    # New API key belongs to a different account
                    errors["base"] = "account_mismatch"
                else:
                    # Same account, update the entry
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        data={CONF_API_KEY: api_key},
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={},
        )
