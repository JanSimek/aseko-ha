"""Aseko API client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any

from aiohttp import ClientSession, ClientResponseError

from .const import API_BASE_URL, CLIENT_NAME, CLIENT_VERSION

_LOGGER = logging.getLogger(__name__)


class AsekoApiError(Exception):
    """Base exception for Aseko API errors."""


class AsekoAuthError(AsekoApiError):
    """Exception for authentication errors."""


class AsekoConnectionError(AsekoApiError):
    """Exception for connection errors."""


class AsekoNotFoundError(AsekoApiError):
    """Exception for resource not found (404)."""


@dataclass
class AsekoUnit:
    """Representation of an Aseko unit."""

    serial_number: str
    name: str | None
    note: str | None
    online: bool
    has_warning: bool
    brand_name: str | None
    status_values: dict[str, Any]


class AsekoApiClient:
    """Client for the Aseko REST API."""

    def __init__(self, session: ClientSession, api_key: str) -> None:
        """Initialize the API client.

        Args:
            session: aiohttp ClientSession (from Home Assistant)
            api_key: API key from https://account.aseko.cloud/profile/settings/api-keys
        """
        self._session = session
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        """Return headers required for API requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-Client-Name": CLIENT_NAME,
            "X-Client-Version": CLIENT_VERSION,
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/auth/check")
            **kwargs: Additional arguments passed to session.request

        Returns:
            JSON response as dictionary

        Raises:
            AsekoAuthError: If API key is invalid (401/403)
            AsekoNotFoundError: If resource not found (404)
            AsekoConnectionError: For connection errors
            AsekoApiError: For other API errors
        """
        url = f"{API_BASE_URL}{endpoint}"

        try:
            async with self._session.request(
                method, url, headers=self._headers(), **kwargs
            ) as response:
                if response.status in (401, 403):
                    raise AsekoAuthError("Invalid or expired API key")
                if response.status == 404:
                    raise AsekoNotFoundError(f"Resource not found: {endpoint}")
                response.raise_for_status()
                return await response.json()
        except ClientResponseError as err:
            raise AsekoApiError(f"API request failed: {err.status}") from err
        except AsekoApiError:
            raise
        except Exception as err:
            raise AsekoConnectionError(f"Connection error: {err}") from err

    async def validate_api_key(self) -> bool:
        """Validate the API key.

        Returns:
            True if the API key is valid

        Raises:
            AsekoAuthError: If the API key is invalid
            AsekoApiError: For other API errors
        """
        data = await self._request("GET", "/auth/check")
        return data.get("valid", False)

    async def get_unit_serials(self) -> list[str]:
        """Get all paired unit serial numbers without fetching details.

        This is a lightweight call for validation/setup purposes.
        Returns serial numbers sorted for stable ordering.

        Returns:
            List of serial numbers (sorted)

        Raises:
            AsekoApiError: For API errors
        """
        all_serial_numbers: list[str] = []
        page = 1
        limit = 100

        while True:
            data = await self._request(
                "GET",
                "/paired-units",
                params={"page": page, "limit": limit},
            )

            items = data.get("items", [])
            if not items:
                break

            all_serial_numbers.extend(item["serialNumber"] for item in items)

            total_items = data.get("totalItems", 0)
            if page * limit >= total_items:
                break
            page += 1

        # Sort for stable ordering across API responses
        return sorted(all_serial_numbers)

    async def get_units(self) -> list[AsekoUnit]:
        """Get all paired units with full details.

        Automatically handles pagination and fetches unit details in parallel.

        Returns:
            List of AsekoUnit objects

        Raises:
            AsekoAuthError: If authentication fails (fatal, bubbles up)
            AsekoApiError: For API errors or if fetching units fails
        """
        all_serial_numbers = await self.get_unit_serials()

        if not all_serial_numbers:
            return []

        # Fetch all unit details in parallel
        results = await asyncio.gather(
            *[self.get_unit(sn) for sn in all_serial_numbers],
            return_exceptions=True,
        )

        units: list[AsekoUnit] = []
        errors: list[tuple[str, Exception]] = []
        not_found_count = 0

        for serial_number, result in zip(all_serial_numbers, results):
            if isinstance(result, AsekoAuthError):
                # Auth errors are fatal - bubble up immediately
                raise result
            if isinstance(result, AsekoNotFoundError):
                _LOGGER.debug("Unit %s not found, skipping", serial_number)
                not_found_count += 1
            elif isinstance(result, Exception):
                _LOGGER.warning(
                    "Failed to fetch unit %s: %s", serial_number, result
                )
                errors.append((serial_number, result))
            else:
                units.append(result)

        # If we had serials but got no units at all, something is wrong
        if not units and all_serial_numbers:
            if not_found_count == len(all_serial_numbers):
                raise AsekoApiError(
                    f"All {not_found_count} units returned 404 - data may be stale"
                )
            if errors:
                raise AsekoApiError(
                    f"Failed to fetch any units. Errors: {len(errors)}"
                )

        return units

    async def get_unit(self, serial_number: str) -> AsekoUnit:
        """Get detailed information for a specific unit.

        Args:
            serial_number: The unit's serial number

        Returns:
            AsekoUnit object

        Raises:
            AsekoNotFoundError: If unit not found
            AsekoApiError: For other API errors
        """
        data = await self._request("GET", f"/paired-units/{serial_number}")
        return self._parse_unit(data)

    def _parse_unit(self, data: dict[str, Any]) -> AsekoUnit:
        """Parse unit data from API response.

        Args:
            data: Raw API response for a single unit

        Returns:
            AsekoUnit instance
        """
        brand_name = None
        if brand_data := data.get("brandName"):
            primary = brand_data.get("primary", "")
            secondary = brand_data.get("secondary", "")
            brand_name = f"{primary} {secondary}".strip() or None

        # Derive has_warning from statusMessages (API doesn't have hasWarning field)
        status_messages = data.get("statusMessages", [])
        has_warning = any(
            msg.get("severity") in ("ERROR", "WARNING")
            for msg in status_messages
        )

        return AsekoUnit(
            serial_number=data["serialNumber"],
            name=data.get("name"),
            note=data.get("note"),
            online=data.get("online", False),
            has_warning=has_warning,
            brand_name=brand_name,
            status_values=data.get("statusValues", {}),
        )

