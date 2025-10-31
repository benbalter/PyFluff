#!/usr/bin/env python3
"""
Example: Home Assistant Integration

Demonstrates how to use PyFluff with Home Assistant MQTT Discovery.
This script shows how to:
1. Configure Home Assistant MQTT settings
2. Start the server with HA integration enabled
3. Connect to Furby and publish discovery messages

Prerequisites:
- MQTT broker running (e.g., Mosquitto)
- Home Assistant with MQTT integration configured
- Furby Connect in range

Usage:
    python examples/homeassistant_demo.py

Or with custom MQTT settings:
    HA_MQTT_BROKER=192.168.1.100 HA_MQTT_PORT=1883 \
    HA_MQTT_USERNAME=user HA_MQTT_PASSWORD=pass \
    python examples/homeassistant_demo.py
"""

import asyncio
import logging
import os

from pyfluff.furby import FurbyConnect
from pyfluff.homeassistant import HomeAssistantMQTT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main demo function."""
    # Load MQTT settings from environment or use defaults
    mqtt_broker = os.getenv("HA_MQTT_BROKER", "localhost")
    mqtt_port = int(os.getenv("HA_MQTT_PORT", "1883"))
    mqtt_username = os.getenv("HA_MQTT_USERNAME")
    mqtt_password = os.getenv("HA_MQTT_PASSWORD")

    logger.info("Home Assistant Integration Demo")
    logger.info("=" * 50)
    logger.info(f"MQTT Broker: {mqtt_broker}:{mqtt_port}")
    logger.info("")

    # Initialize Home Assistant MQTT client
    ha_mqtt = HomeAssistantMQTT(
        broker=mqtt_broker,
        port=mqtt_port,
        username=mqtt_username,
        password=mqtt_password,
        device_id="furby_demo",
        device_name="Demo Furby",
    )

    try:
        # Connect to MQTT broker
        logger.info("Connecting to MQTT broker...")
        await ha_mqtt.connect()
        logger.info("✓ Connected to MQTT broker")

        # Initialize Furby connection
        logger.info("")
        logger.info("Connecting to Furby...")
        furby = FurbyConnect()
        await furby.connect()  # Auto-discover and connect
        logger.info(f"✓ Connected to Furby at {furby.device.address if furby.device else 'unknown'}")

        # Publish Home Assistant discovery messages
        logger.info("")
        logger.info("Publishing Home Assistant discovery...")
        mac_address = furby.device.address if furby.device else None
        await ha_mqtt.publish_discovery(mac_address)
        logger.info("✓ Discovery messages published")

        # Publish initial states
        logger.info("")
        logger.info("Publishing initial states...")
        await ha_mqtt.publish_connection_state(True)
        await ha_mqtt.publish_antenna_state(0, 0, 0, False)
        for mood in ["excitedness", "displeasedness", "tiredness", "fullness", "wellness"]:
            await ha_mqtt.publish_mood_state(mood, 50)
        logger.info("✓ Initial states published")

        # Subscribe to commands from Home Assistant
        logger.info("")
        logger.info("Subscribing to Home Assistant commands...")

        async def handle_command(topic: str, payload: str) -> None:
            """Handle commands from Home Assistant."""
            logger.info(f"Received command: {topic} = {payload}")

            try:
                if "antenna/rgb/set" in topic:
                    r, g, b = map(int, payload.split(","))
                    await furby.set_antenna_color(r, g, b)
                    await ha_mqtt.publish_antenna_state(r, g, b, True)
                    logger.info(f"  → Set antenna to RGB({r}, {g}, {b})")

                elif "antenna/set" in topic:
                    if payload.upper() == "ON":
                        await furby.set_antenna_color(255, 255, 255)
                        await ha_mqtt.publish_antenna_state(255, 255, 255, True)
                        logger.info("  → Turned antenna on (white)")
                    else:
                        await furby.set_antenna_color(0, 0, 0)
                        await ha_mqtt.publish_antenna_state(0, 0, 0, False)
                        logger.info("  → Turned antenna off")

                elif "button/giggle/press" in topic:
                    await furby.trigger_action(55, 2, 14, 0)
                    logger.info("  → Triggered giggle action")

            except Exception as e:
                logger.error(f"Error handling command: {e}")

        await ha_mqtt.subscribe_to_commands(handle_command)
        logger.info("✓ Subscribed to command topics")

        # Demo: Set antenna to different colors
        logger.info("")
        logger.info("Demo: Cycling antenna colors...")
        colors = [
            (255, 0, 0, "red"),
            (0, 255, 0, "green"),
            (0, 0, 255, "blue"),
            (255, 255, 0, "yellow"),
            (255, 0, 255, "magenta"),
            (0, 255, 255, "cyan"),
        ]

        for r, g, b, name in colors:
            logger.info(f"  Setting antenna to {name}...")
            await furby.set_antenna_color(r, g, b)
            await ha_mqtt.publish_antenna_state(r, g, b, True)
            await asyncio.sleep(1)

        # Turn off antenna
        logger.info("  Turning antenna off...")
        await furby.set_antenna_color(0, 0, 0)
        await ha_mqtt.publish_antenna_state(0, 0, 0, False)

        # Keep running to receive commands from Home Assistant
        logger.info("")
        logger.info("=" * 50)
        logger.info("Demo running! Check Home Assistant:")
        logger.info("  Settings → Devices & Services → MQTT")
        logger.info("  You should see 'Demo Furby' listed")
        logger.info("")
        logger.info("Try controlling the Furby from Home Assistant!")
        logger.info("Press Ctrl+C to exit")
        logger.info("=" * 50)

        # Run until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        # Cleanup
        if furby and furby.connected:
            await ha_mqtt.publish_connection_state(False)
            await furby.disconnect()
        await ha_mqtt.disconnect()
        logger.info("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
