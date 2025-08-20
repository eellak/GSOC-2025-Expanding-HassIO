# GSOC-2025-Expanding-HassIO
Expanding HassIO Smart Home Capabilities via Low-Code Automation Development with SmAuto

# SmAuto–Home Assistant Integration

## Overview

This project provides a bridge between the [SmAuto](https://github.com/robotics-4-all/smauto) Domain-Specific Language (DSL) for smart automation and the Home Assistant platform.  
It enables users to write complex automation logic in the SmAuto DSL and seamlessly execute that logic to control Home Assistant devices, leveraging MQTT as the communication bus.

## Requirements & External Dependencies

- **SmAuto REST API server:**  
  You must have a running SmAuto REST API server.  
  See the [official SmAuto repo](https://github.com/robotics-4-all/smauto) for setup and installation instructions.

- **Mosquitto MQTT broker:**  
  A running Mosquitto MQTT broker is required as the message bus between Home Assistant and SmAuto.  
  You can use the official [Eclipse Mosquitto Docker image](https://hub.docker.com/_/eclipse-mosquitto) or any compatible MQTT broker.

- **Home Assistant Core:**  
  This integration is designed to be used with Home Assistant Core (dev environment recommended).

> **Note:** This repository only contains the Home Assistant custom integration.  
> You must set up and run the required SmAuto REST API server and MQTT broker separately.

## Architecture

The system consists of the following main components:

- **SmAuto REST API Server:**  
  A FastAPI server (Docker) that receives SmAuto DSL models, generates Python automation scripts, and returns the code via a REST API.

- **Mosquitto MQTT Broker:**  
  Standard MQTT broker (Docker) acting as the central message bus between Home Assistant and the SmAuto automations.

- **Home Assistant Core:**  
  The Home Assistant development environment (running on the host) with the custom SmAuto integration installed.

- **SmAuto Custom Integration:**  
  Home Assistant custom component (`custom_components/smauto/`) responsible for:
    - User interaction and configuration (API URL, key)
    - Sending model files to the SmAuto server
    - Launching the generated Python code as a background process
    - Bridging MQTT messages to and from Home Assistant

## Workflow

### 1. Model Authoring

- Users write automation logic in SmAuto DSL (`*.auto` files) and place them in Home Assistant’s `/config` directory.

### 2. Model Execution

- From Home Assistant UI or service call, the user runs `smauto.run_model`, specifying a `.auto` file.
- The integration reads the model, sends it to the SmAuto REST API, receives generated Python code, and patches it to keep running.
- The script is saved to a temp file and launched as a background process.

### 3. Event Bridge (Home Assistant → SmAuto Script)

- A Home Assistant automation (YAML) publishes sensor/device changes to MQTT (e.g., `porch/weather_station`).

### 4. SmAuto Script Logic

- The running Python script subscribes to the MQTT sensor topics, evaluates the DSL logic, and publishes actuator commands to MQTT (e.g., `office/light`).

### 5. Event Bridge (SmAuto Script → Home Assistant)

- A second Home Assistant automation (YAML) is triggered by MQTT messages on actuator topics and calls the corresponding Home Assistant service (e.g., `light.turn_on`).

## Example: Temperature to Light Automation

1. **SmAuto model**: Turns on a light when temperature exceeds a threshold.
2. **HA automation #1**: Publishes sensor changes to MQTT.
3. **SmAuto script**: Receives sensor updates, triggers when threshold is exceeded, publishes light command to MQTT.
4. **HA automation #2**: Listens to MQTT, turns on the light in Home Assistant.

## Installation

### Prerequisites

- Docker (for SmAuto REST API server and Mosquitto broker)
- Python 3.9+ and Home Assistant Core (development mode recommended)
- MQTT integration enabled in Home Assistant

### Steps

1. **Clone the SmAuto integration and REST API server repositories.**
2. **Build and run Mosquitto broker (example):**
    ```sh
    docker run -it --rm --name mosquitto -p 1883:1883 eclipse-mosquitto
    ```
3. **Build and run the SmAuto REST API server (example):**
    ```sh
    docker build -t smauto .
    docker run -it --rm --name mysmauto -p 8080:8080 smauto
    ```
4. **Copy the SmAuto custom integration into your Home Assistant config directory:**
    ```
    <HA config>/custom_components/smauto/
    ```
5. **Restart Home Assistant.**

### Integration Setup

1. In Home Assistant UI, go to **Settings → Devices & Services → Integrations → Add Integration**.
2. Search for "SmAuto" and add it.
3. Enter the SmAuto API URL (e.g., `http://localhost:8080/generate/autos`) and your API key.

### Home Assistant Automations

Add YAML automations to bridge sensor and actuator events between Home Assistant and MQTT.  
Example for publishing a sensor value to MQTT:

```yaml
# In automations.yaml
- alias: Bridge HA Temperature to SmAuto
  trigger:
    - platform: state
      entity_id: input_number.dummy_temperature_sensor
  action:
    - service: mqtt.publish
      data:
        topic: "porch/weather_station"
        payload_template: >
          {"temperature": {{ states('input_number.dummy_temperature_sensor') | float }}, "humidity": 50}
```

Example for listening to actuator commands from MQTT:

```yaml
- alias: Bridge SmAuto Light Command to HA
  trigger:
    - platform: mqtt
      topic: "office/light"
  action:
    - service: light.turn_on
      target:
        entity_id: light.dummy_office_light
```

*(Update topics and entity IDs to match your devices and model.)*

## Current Status

- [x] SmAuto–HA communication and code generation working.
- [x] Automation logic executes as expected and triggers `change_state`.
- [ ] Finalizing MQTT actuator publish: Debug print appears, but actual message may not be in correct format/type.  
  **Currently fixing: Message type for actuator publish (ensure correct MQTT payload structure and type as required by SmAuto messaging API).**

## Troubleshooting

- **No message seen on MQTT topic?**
  - Check Home Assistant logs for debug/ERROR lines.
  - Subscribe to all topics: `mosquitto_sub -h localhost -t "#" -v`
  - Make sure automations are correctly bridged and topics match.
  - Verify that the MQTT payload sent by SmAuto is in the expected format and message type.
- **Code changes in template not reflected?**
  - Patch `/app/smauto/templates/smauto.py.jinja` inside your SmAuto REST API Docker container, then restart the container and rerun your test.
- **Still issues?**
  - Check for Python errors in Home Assistant logs.

## Roadmap

- [ ] Finalize actuator message publishing to MQTT (fix message type).
- [ ] End-to-end demo with real and dummy devices.
- [ ] Prepare documentation and HACS submission (meet Home Assistant custom integration standards).

## License

MIT License.

## Credits

- [SmAuto](https://github.com/robotics-4-all/smauto) by Konstantinos Panayiotou and Robotics-4-All team.
- Home Assistant Community.