"""Data update coordinator for Aseko integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    AsekoApiClient,
    AsekoUnit,
    AsekoApiError,
    AsekoAuthError,
    AsekoTermsNotAcceptedError,
)
from .const import ACCOUNT_PORTAL_URL, DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AsekoDataUpdateCoordinator(DataUpdateCoordinator[dict[str, AsekoUnit]]):
    """Class to manage fetching Aseko data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: AsekoApiClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            client: Aseko API client
            entry: Config entry
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, AsekoUnit]:
        """Fetch data from Aseko API.

        Returns:
            Dictionary mapping serial numbers to AsekoUnit objects

        Raises:
            ConfigEntryError: If the account has not accepted the terms of service
            ConfigEntryAuthFailed: If authentication fails (triggers reauth)
            UpdateFailed: If data fetch fails
        """
        try:
            units = await self.client.get_units()
            return {unit.serial_number: unit for unit in units}
        except AsekoTermsNotAcceptedError as err:
            # Not ConfigEntryAuthFailed: reauth would ask for another API key, and
            # every key is rejected until the terms are accepted in the portal.
            raise ConfigEntryError(
                "Aseko's terms of service have not been accepted. Accept them at "
                f"{ACCOUNT_PORTAL_URL} and then reload this integration."
            ) from err
        except AsekoAuthError as err:
            # Trigger reauth flow
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except AsekoApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
