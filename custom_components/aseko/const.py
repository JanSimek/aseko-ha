"""Constants for the Aseko integration."""

from typing import Final

DOMAIN: Final = "aseko"

API_BASE_URL: Final = "https://api.aseko.cloud/api/v1"
CLIENT_NAME: Final = "HomeAssistant-Aseko"
CLIENT_VERSION: Final = "1.0.0"

CONF_API_KEY: Final = "api_key"

DEFAULT_SCAN_INTERVAL: Final = 60  # seconds

# Translations for status message types from Aseko API
# Used for extra_state_attributes on the warning binary sensor
STATUS_MESSAGE_TRANSLATIONS: Final[dict[str, str]] = {
    "AUTO_MODE_FILTRATION_INTERVALS_WRONG": "Auto mode filtration intervals incorrect",
    "BACKWASH_ERROR": "Backwash error",
    "BACKWASH_RUNNING": "Backwash running",
    "CLOCK_MEMORY_BATTERY_LOW": "Clock memory battery low",
    "COVER_ERROR_CURRENT": "Cover error - current issue",
    "COVER_ERROR_PULSES": "Cover error - pulse issue",
    "ELECTROLYSIS_ON_TOO_MANY_DAYS": "Electrolysis running too many days",
    "HEATER_COOLING_FILTRATION": "Heater cooling filtration active",
    "MAXIMUM_DISINFECTION_DOSE_EXCEEDED": "Maximum disinfection dose exceeded",
    "MAXIMUM_HOURLY_DISINFECTION_DOSE_EXCEEDED": "Maximum hourly disinfection dose exceeded",
    "MCU_COMMUNICATION_ERROR": "MCU communication error",
    "NO_FLOW_FROM_DOSING_UNIT": "No flow from dosing unit",
    "NO_WATER_FLOW_TO_PROBES": "No water flow to probes",
    "PH_TOO_LOW_FOR_ELECTROLYSIS": "pH too low for electrolysis",
    "PH_VALUE_CHANGING_TOO_RAPIDLY": "pH value changing too rapidly",
    "POOL_COVER_IN_MOTION": "Pool cover in motion",
    "PUMP_OVERHEATED": "Pump overheated",
    "SALT_HIGH_TEMPERATURE": "Salt system high temperature",
    "SOLAR_HIGH_TEMPERATURE": "Solar system high temperature",
    "SOLAR_NO_TEMPERATURE": "Solar system no temperature reading",
    "START_BY_EMS": "Started by EMS",
    "START_BY_SOLAR": "Started by solar",
    "STOPPED_BY_TIMER": "Stopped by timer",
    "TEMP_SUPERIOR_TO_FILTRATION": "Temperature superior to filtration",
    "TOO_LITTLE_SALT_PER_HOUR": "Too little salt per hour",
    "TOO_MANY_PH_DOSING_ATTEMPTS_WITHOUT_CHANGE": "pH dosing failed - no change after 20 doses",
    "TOO_MUCH_SALT_PER_HOUR": "Too much salt per hour",
    "UNEXPECTED_COVER_OPERATION_MODE": "Unexpected cover operation mode",
    "UNIT_OFFLINE": "Unit offline",
    "VS_PUMP_TYPE_NOT_SET": "Variable speed pump type not set",
    "WATER_LEVEL_TOO_HIGH": "Water level too high",
    "WATER_LEVEL_TOO_LOW": "Water level too low",
    "WATER_REFILLING_TIME_EXCEEDED": "Water refilling time exceeded",
    "WINTER_MODE_ACTIVATED": "Winter mode activated",
}
