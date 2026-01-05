# Aseko Pool Integration for Home Assistant

A Home Assistant custom integration for Aseko pool monitoring devices using the new Aseko REST API.

## Features

- Monitor water and air temperature
- Monitor pH and redox (ORP) values
- Monitor chlorine levels (free and bounded)
- Monitor salinity and water level
- Monitor electrolyzer, filtration, solar, and heating status
- Monitor filter pressure and flow speed
- Binary sensors for equipment running states
- Warning sensor with detailed error type attributes for automations

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

### Measurement Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| Water temperature | Pool water temperature | °C |
| Air temperature | Ambient air temperature | °C |
| Solar temperature | Solar system temperature | °C |
| Water temperature required | Target water temperature | °C |
| pH | Water pH level | pH |
| pH required | Target pH level | pH |
| Redox | ORP/Redox potential | mV |
| Redox required | Target redox value | mV |
| Free chlorine | Free chlorine concentration | ppm |
| Free chlorine required | Target free chlorine | ppm |
| Bounded chlorine | Bounded chlorine concentration | ppm |
| Salinity | Water salinity | g/L |
| Water level | Measured water level | cm |
| Electrolyzer | Electrolyzer output percentage | % |
| Dose | Dosing percentage | % |
| Electrode power | Electrode power output | g/h |
| Filter flow speed | Filter flow rate | m³/h |
| Filter pressure | Filter pressure | bar |

### State Sensors

| Sensor | Description | Values |
|--------|-------------|--------|
| Mode | Current operation mode | AUTO, ECO, OFF, ON, PARTY, WINTER |
| Filtration speed | Current filtration speed | BOOST, HIGH, LOW, MEDIUM, OFF |
| Electrolyzer direction | Electrolyzer polarity | LEFT, RIGHT, WAITING |
| Pool flow | Pool water flow type | OVERFLOW, BOTTOM |
| Water level state | Water level status | OK, FILLING, LOW, HIGH |

## Binary Sensors

| Sensor | Description |
|--------|-------------|
| Online | Device connectivity status |
| Warning | Active warnings/errors (see attributes) |
| Water flow to probes | Water flow detection |
| Heating | Heating system running |
| Electrolyzer running | Electrolyzer running |
| Solar running | Solar system running |
| Filtration running | Filtration pump running |
| Water filling running | Water refill in progress |

### Warning Sensor Attributes

When the Warning binary sensor is `on`, it exposes additional attributes for use in automations:

| Attribute | Description |
|-----------|-------------|
| `error_types` | Comma-separated list of error type codes |
| `errors` | List of error objects with `type`, `severity`, `message`, and `detail` |

Example error types: `TOO_MANY_PH_DOSING_ATTEMPTS_WITHOUT_CHANGE`, `WATER_LEVEL_TOO_LOW`, `NO_WATER_FLOW_TO_PROBES`, etc.

## Automation Examples

### Water Level Alerts

Use the `water_level_state` sensor to trigger automations based on water level:

```yaml
automation:
  - alias: "Pool water level low"
    trigger:
      - platform: state
        entity_id: sensor.my_pool_water_level_state
        to: "LOW"
    action:
      - service: notify.mobile_app
        data:
          message: "Pool water level is LOW!"

  - alias: "Pool water level high"
    trigger:
      - platform: state
        entity_id: sensor.my_pool_water_level_state
        to: "HIGH"
    action:
      - service: notify.mobile_app
        data:
          message: "Pool water level is HIGH!"
```

### Error Type Based Alerts

Use the Warning sensor attributes to trigger on specific error types:

```yaml
automation:
  - alias: "Pool pH dosing error"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_pool_warning
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ 'TOO_MANY_PH_DOSING_ATTEMPTS_WITHOUT_CHANGE' in
             state_attr('binary_sensor.my_pool_warning', 'error_types') }}
    action:
      - service: notify.mobile_app
        data:
          message: "Pool: pH dosing failed - check reagent level!"
```

## License

This project is licensed under the GNU Lesser General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.
