# Home Assistant Integration

PyFluff supports automatic integration with Home Assistant via MQTT Discovery. This allows your Furby Connect to appear as a native device in Home Assistant with full control over its features.

## Features

When enabled, PyFluff will expose the following entities in Home Assistant:

### Light Entity
- **Antenna LED**: RGB color control for the antenna LED
  - Turn on/off
  - Set RGB color (0-255 for each channel)
  - Real-time state updates

### Binary Sensor
- **Connection Status**: Shows whether Furby is connected via Bluetooth

### Number Inputs (Mood Meters)
- **Excitedness**: 0-100 slider
- **Displeasedness**: 0-100 slider  
- **Tiredness**: 0-100 slider
- **Fullness**: 0-100 slider
- **Wellness**: 0-100 slider

### Buttons
- **Giggle**: Trigger giggle action
- **Puke**: Trigger puke action
- **LCD On**: Turn LCD backlight on
- **LCD Off**: Turn LCD backlight off

## Prerequisites

1. **MQTT Broker**: You need a running MQTT broker. Common options:
   - [Mosquitto](https://mosquitto.org/) (recommended for Home Assistant)
   - Home Assistant's built-in Mosquitto broker addon

2. **Home Assistant**: Version 2023.1 or later with MQTT integration configured

## Setup

### 1. Install MQTT Broker (if needed)

If you're using Home Assistant OS, install the Mosquitto broker addon:

1. Go to **Settings → Add-ons → Add-on Store**
2. Search for "Mosquitto broker"
3. Install and start the addon

For standalone installations:

```bash
# Debian/Ubuntu
sudo apt-get install mosquitto mosquitto-clients

# Start the service
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 2. Configure Home Assistant MQTT Integration

In Home Assistant:

1. Go to **Settings → Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "MQTT"
4. Configure with your broker details (usually `localhost:1883` for local broker)

### 3. Configure PyFluff

PyFluff reads Home Assistant configuration from environment variables. Create a `.env` file or set these variables:

```bash
# Enable Home Assistant integration
export HA_ENABLED=true

# MQTT broker settings
export HA_MQTT_BROKER=localhost
export HA_MQTT_PORT=1883

# Optional: MQTT authentication
export HA_MQTT_USERNAME=your_username
export HA_MQTT_PASSWORD=your_password

# Optional: Customize device identity
export HA_DEVICE_ID=furby_connect
export HA_DEVICE_NAME="Furby Connect"
```

### 4. Start PyFluff Server

```bash
# With environment variables
HA_ENABLED=true python -m pyfluff.server

# Or source your .env file first
source .env
python -m pyfluff.server
```

### 5. Connect to Furby

Once PyFluff starts:

1. Open the web interface at `http://localhost:8080`
2. Connect to your Furby (via scan or MAC address)
3. PyFluff will automatically publish discovery messages to Home Assistant

### 6. Check Home Assistant

Your Furby should now appear in Home Assistant:

1. Go to **Settings → Devices & Services → MQTT**
2. You should see "Furby Connect" listed under devices
3. Click on it to see all available entities

## Usage Examples

### Automations

Create automations using Furby's entities:

**Example: Flash antenna when doorbell rings**

```yaml
automation:
  - alias: "Furby Doorbell Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_bell
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.furby_connect_antenna_led
        data:
          rgb_color: [255, 0, 0]
      - delay: "00:00:01"
      - service: light.turn_off
        target:
          entity_id: light.furby_connect_antenna_led
```

**Example: Wake up Furby in the morning**

```yaml
automation:
  - alias: "Wake Furby"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.furby_connect_excitedness
        data:
          value: 100
      - service: button.press
        target:
          entity_id: button.furby_connect_giggle
```

### Dashboards

Add Furby controls to your dashboard:

```yaml
type: vertical-stack
cards:
  - type: light
    entity: light.furby_connect_antenna_led
    name: Antenna LED
  
  - type: entities
    entities:
      - entity: number.furby_connect_excitedness
      - entity: number.furby_connect_displeasedness
      - entity: number.furby_connect_tiredness
      - entity: number.furby_connect_fullness
      - entity: number.furby_connect_wellness
    title: Mood Control
  
  - type: horizontal-stack
    cards:
      - type: button
        entity: button.furby_connect_giggle
        name: Giggle
      - type: button
        entity: button.furby_connect_puke
        name: Puke
```

### Scripts

Create reusable scripts:

```yaml
script:
  furby_party_mode:
    alias: "Furby Party Mode"
    sequence:
      - service: number.set_value
        target:
          entity_id: number.furby_connect_excitedness
        data:
          value: 100
      - repeat:
          count: 5
          sequence:
            - service: light.turn_on
              target:
                entity_id: light.furby_connect_antenna_led
              data:
                rgb_color: [255, 0, 0]
            - delay: "00:00:00.5"
            - service: light.turn_on
              target:
                entity_id: light.furby_connect_antenna_led
              data:
                rgb_color: [0, 255, 0]
            - delay: "00:00:00.5"
            - service: light.turn_on
              target:
                entity_id: light.furby_connect_antenna_led
              data:
                rgb_color: [0, 0, 255]
            - delay: "00:00:00.5"
```

## MQTT Topics

PyFluff uses the following MQTT topic structure:

### State Topics (Published by PyFluff)
- `pyfluff/{device_id}/antenna/state` - LED on/off state
- `pyfluff/{device_id}/antenna/rgb/state` - RGB color value (e.g., "255,128,0")
- `pyfluff/{device_id}/connection/state` - Connection status (ON/OFF)
- `pyfluff/{device_id}/mood/{type}/state` - Mood meter values (0-100)

### Command Topics (Subscribed by PyFluff)
- `pyfluff/{device_id}/antenna/set` - Turn LED on/off
- `pyfluff/{device_id}/antenna/rgb/set` - Set RGB color
- `pyfluff/{device_id}/mood/{type}/set` - Set mood value
- `pyfluff/{device_id}/button/{type}/press` - Press button

### Discovery Topics
- `homeassistant/light/{device_id}/antenna/config`
- `homeassistant/binary_sensor/{device_id}/connection/config`
- `homeassistant/number/{device_id}/{mood}/config`
- `homeassistant/button/{device_id}/{button}/config`

## Troubleshooting

### Furby not appearing in Home Assistant

1. **Check MQTT broker is running**:
   ```bash
   mosquitto_sub -h localhost -t '#' -v
   ```

2. **Verify PyFluff is publishing**:
   Look for log messages like "Published Home Assistant discovery messages"

3. **Check Home Assistant MQTT integration**:
   Go to Settings → Devices & Services → MQTT → Configure → Listen to a topic
   Enter `homeassistant/#` to see discovery messages

4. **Restart Home Assistant**:
   Sometimes HA needs a restart to pick up new MQTT devices

### Connection drops frequently

1. Check Bluetooth signal strength
2. Ensure Furby is not going into F2F mode
3. Monitor MQTT broker logs for connection issues

### State not updating

1. Verify PyFluff is connected to Furby (check web interface)
2. Check MQTT broker logs for publish errors
3. Ensure Home Assistant MQTT integration is active

## Advanced Configuration

### Multiple Furbies

To connect multiple Furbies, run separate PyFluff instances with different device IDs:

```bash
# Furby 1
HA_ENABLED=true HA_DEVICE_ID=furby_1 HA_DEVICE_NAME="Living Room Furby" \
  python -m pyfluff.server --port 8080

# Furby 2
HA_ENABLED=true HA_DEVICE_ID=furby_2 HA_DEVICE_NAME="Bedroom Furby" \
  python -m pyfluff.server --port 8081
```

### Custom MQTT Topics

The base topic structure can be modified in the HomeAssistantMQTT class if needed:

```python
ha_mqtt = HomeAssistantMQTT(
    broker="localhost",
    device_id="my_custom_furby",
    device_name="Custom Furby"
)
```

### TLS/SSL MQTT

For secure MQTT connections, modify the connection parameters in `pyfluff/homeassistant.py`:

```python
self.client = aiomqtt.Client(
    hostname=self.broker,
    port=8883,
    username=self.username,
    password=self.password,
    tls_context=ssl.create_default_context()
)
```

## Security Considerations

1. **Network Security**: Keep MQTT traffic on your local network or use TLS/SSL
2. **Authentication**: Use MQTT username/password authentication
3. **Firewall**: Restrict MQTT broker access to trusted devices only
4. **Updates**: Keep Home Assistant and PyFluff updated

## See Also

- [MQTT Discovery Documentation](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
- [Home Assistant Automations](https://www.home-assistant.io/docs/automation/)
- [MQTT Topics Best Practices](https://www.hivemq.com/blog/mqtt-essentials-part-5-mqtt-topics-best-practices/)
