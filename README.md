# Aseko Pool Integration for Home Assistant

A Home Assistant custom integration for Aseko pool monitoring devices using the new Aseko REST API.

## Features

- Monitor water temperature
- Monitor air temperature
- Monitor pH levels
- Monitor redox (ORP) values
- Monitor free chlorine levels
- Monitor salinity
- Monitor electrolyzer status
- Monitor dosing status
- Binary sensors for online status, warnings, water flow, and heating

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Click "Add"
6. Search for "Aseko Pool" and install it
7. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/aseko` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

### Getting an API Key

1. Go to [Aseko Account Settings](https://account.aseko.cloud/profile/settings/api-keys)
2. Create a new API key
3. Copy the key

### Adding the Integration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Aseko Pool"
4. Enter your API key
5. Click "Submit"

## Supported Devices

This integration supports Aseko ASIN AQUA and ASIN Pool devices connected to the Aseko cloud.

## Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| Water temperature | Pool water temperature | °C |
| Air temperature | Ambient air temperature | °C |
| pH | Water pH level | pH |
| Redox | ORP/Redox potential | mV |
| Free chlorine | Free chlorine concentration | ppm |
| Salinity | Water salinity | g/L |
| Electrolyzer | Electrolyzer output percentage | % |
| Dose | Dosing percentage | % |

## Binary Sensors

| Sensor | Description |
|--------|-------------|
| Online | Device connectivity status |
| Warning | Active warnings on the device |
| Water flow to probes | Water flow detection |
| Heating | Heating system status |

## License

This project is licensed under the GNU Lesser General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.
