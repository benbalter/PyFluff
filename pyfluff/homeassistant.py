"""
Home Assistant MQTT Discovery integration for PyFluff.

This module implements Home Assistant MQTT Discovery protocol to automatically
expose Furby Connect as a device in Home Assistant with various entities:
- Light (antenna RGB LED)
- Sensors (connection status, firmware version)
- Number inputs (mood meters)
- Buttons (actions, LCD controls)
"""

import asyncio
import json
import logging
from typing import Any

import aiomqtt

logger = logging.getLogger(__name__)


class HomeAssistantMQTT:
    """
    Home Assistant MQTT Discovery client for PyFluff.

    Publishes device and entity discovery messages to Home Assistant,
    handles state updates, and subscribes to command topics.
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        device_id: str = "furby_connect",
        device_name: str = "Furby Connect",
    ) -> None:
        """
        Initialize Home Assistant MQTT client.

        Args:
            broker: MQTT broker hostname/IP
            port: MQTT broker port
            username: Optional MQTT username
            password: Optional MQTT password
            device_id: Unique device identifier for Home Assistant
            device_name: Human-readable device name
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.device_id = device_id
        self.device_name = device_name

        self.client: aiomqtt.Client | None = None
        self._running = False
        self._subscribe_task: asyncio.Task[None] | None = None

        # Discovery prefix for Home Assistant
        self.discovery_prefix = "homeassistant"
        self.base_topic = f"pyfluff/{self.device_id}"

        # Callback for handling commands from Home Assistant
        self.command_callback: Any = None

    @property
    def running(self) -> bool:
        """Check if MQTT client is running."""
        return self._running

    def _get_device_info(self, mac_address: str | None = None) -> dict[str, Any]:
        """
        Get device information for Home Assistant discovery.

        Args:
            mac_address: Optional MAC address of connected Furby

        Returns:
            Device info dict for HA discovery messages
        """
        device_info: dict[str, Any] = {
            "identifiers": [self.device_id],
            "name": self.device_name,
            "manufacturer": "Hasbro",
            "model": "Furby Connect",
            "sw_version": "1.0.0",
        }

        if mac_address:
            device_info["connections"] = [["mac", mac_address]]

        return device_info

    async def connect(self) -> None:
        """Connect to MQTT broker."""
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")

            # Build client kwargs
            client_kwargs: dict[str, Any] = {
                "hostname": self.broker,
                "port": self.port,
            }

            if self.username and self.password:
                client_kwargs["username"] = self.username
                client_kwargs["password"] = self.password

            self.client = aiomqtt.Client(**client_kwargs)
            await self.client.__aenter__()

            self._running = True
            logger.info("Connected to MQTT broker")

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self._running = False

        if self._subscribe_task:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass

        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT: {e}")
            finally:
                self.client = None

    async def publish_discovery(self, mac_address: str | None = None) -> None:
        """
        Publish Home Assistant MQTT discovery messages for all entities.

        Args:
            mac_address: Optional MAC address of connected Furby
        """
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")

        device_info = self._get_device_info(mac_address)

        # Antenna RGB Light
        await self._publish_light_discovery(device_info)

        # Connection status sensor
        await self._publish_connection_sensor_discovery(device_info)

        # Mood number inputs
        await self._publish_mood_discovery(device_info)

        # Action buttons
        await self._publish_action_buttons_discovery(device_info)

        logger.info("Published Home Assistant discovery messages")

    async def _publish_light_discovery(self, device_info: dict[str, Any]) -> None:
        """Publish RGB light discovery for antenna LED."""
        if not self.client:
            return

        config = {
            "name": "Antenna LED",
            "unique_id": f"{self.device_id}_antenna_led",
            "device": device_info,
            "command_topic": f"{self.base_topic}/antenna/set",
            "state_topic": f"{self.base_topic}/antenna/state",
            "rgb_command_topic": f"{self.base_topic}/antenna/rgb/set",
            "rgb_state_topic": f"{self.base_topic}/antenna/rgb/state",
            "rgb_command_template": "{{ red }},{{ green }},{{ blue }}",
            "rgb_value_template": "{{ value }}",
            "optimistic": False,
            "qos": 1,
        }

        topic = f"{self.discovery_prefix}/light/{self.device_id}/antenna/config"
        await self.client.publish(topic, json.dumps(config), retain=True)
        logger.debug(f"Published light discovery to {topic}")

    async def _publish_connection_sensor_discovery(self, device_info: dict[str, Any]) -> None:
        """Publish connection status sensor discovery."""
        if not self.client:
            return

        config = {
            "name": "Connection",
            "unique_id": f"{self.device_id}_connection",
            "device": device_info,
            "state_topic": f"{self.base_topic}/connection/state",
            "icon": "mdi:bluetooth",
            "qos": 1,
        }

        topic = f"{self.discovery_prefix}/binary_sensor/{self.device_id}/connection/config"
        await self.client.publish(topic, json.dumps(config), retain=True)
        logger.debug(f"Published connection sensor discovery to {topic}")

    async def _publish_mood_discovery(self, device_info: dict[str, Any]) -> None:
        """Publish mood meter number input discoveries."""
        if not self.client:
            return

        moods = [
            ("excitedness", "Excitedness", "mdi:emoticon-happy"),
            ("displeasedness", "Displeasedness", "mdi:emoticon-sad"),
            ("tiredness", "Tiredness", "mdi:sleep"),
            ("fullness", "Fullness", "mdi:food"),
            ("wellness", "Wellness", "mdi:heart-pulse"),
        ]

        for mood_key, mood_name, icon in moods:
            config = {
                "name": mood_name,
                "unique_id": f"{self.device_id}_{mood_key}",
                "device": device_info,
                "command_topic": f"{self.base_topic}/mood/{mood_key}/set",
                "state_topic": f"{self.base_topic}/mood/{mood_key}/state",
                "min": 0,
                "max": 100,
                "step": 1,
                "mode": "slider",
                "icon": icon,
                "qos": 1,
            }

            topic = f"{self.discovery_prefix}/number/{self.device_id}/{mood_key}/config"
            await self.client.publish(topic, json.dumps(config), retain=True)
            logger.debug(f"Published {mood_name} mood discovery to {topic}")

    async def _publish_action_buttons_discovery(self, device_info: dict[str, Any]) -> None:
        """Publish action button discoveries."""
        if not self.client:
            return

        buttons = [
            ("giggle", "Giggle", "mdi:emoticon-lol"),
            ("puke", "Puke", "mdi:emoticon-sick"),
            ("lcd_on", "LCD On", "mdi:eye"),
            ("lcd_off", "LCD Off", "mdi:eye-off"),
        ]

        for button_key, button_name, icon in buttons:
            config = {
                "name": button_name,
                "unique_id": f"{self.device_id}_{button_key}",
                "device": device_info,
                "command_topic": f"{self.base_topic}/button/{button_key}/press",
                "icon": icon,
                "qos": 1,
                "payload_press": "PRESS",
            }

            topic = f"{self.discovery_prefix}/button/{self.device_id}/{button_key}/config"
            await self.client.publish(topic, json.dumps(config), retain=True)
            logger.debug(f"Published {button_name} button discovery to {topic}")

    async def publish_antenna_state(self, red: int, green: int, blue: int, on: bool = True) -> None:
        """
        Publish antenna LED state to MQTT.

        Args:
            red: Red channel (0-255)
            green: Green channel (0-255)
            blue: Blue channel (0-255)
            on: Whether LED is on or off
        """
        if not self.client:
            return

        state = "ON" if on else "OFF"
        rgb_value = f"{red},{green},{blue}"

        await self.client.publish(f"{self.base_topic}/antenna/state", state)
        await self.client.publish(f"{self.base_topic}/antenna/rgb/state", rgb_value)
        logger.debug(f"Published antenna state: {state} RGB({rgb_value})")

    async def publish_connection_state(self, connected: bool) -> None:
        """
        Publish connection state to MQTT.

        Args:
            connected: Whether Furby is connected
        """
        if not self.client:
            return

        state = "ON" if connected else "OFF"
        await self.client.publish(f"{self.base_topic}/connection/state", state)
        logger.debug(f"Published connection state: {state}")

    async def publish_mood_state(self, mood_type: str, value: int) -> None:
        """
        Publish mood meter state to MQTT.

        Args:
            mood_type: Type of mood (excitedness, displeasedness, etc.)
            value: Mood value (0-100)
        """
        if not self.client:
            return

        await self.client.publish(f"{self.base_topic}/mood/{mood_type}/state", str(value))
        logger.debug(f"Published {mood_type} mood state: {value}")

    async def subscribe_to_commands(self, callback: Any) -> None:
        """
        Subscribe to command topics from Home Assistant.

        Args:
            callback: Async callback function to handle commands
                     Signature: async def callback(topic: str, payload: str) -> None
        """
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")

        self.command_callback = callback

        # Subscribe to all command topics
        topics = [
            f"{self.base_topic}/antenna/set",
            f"{self.base_topic}/antenna/rgb/set",
            f"{self.base_topic}/mood/+/set",
            f"{self.base_topic}/button/+/press",
        ]

        for topic in topics:
            await self.client.subscribe(topic)
            logger.debug(f"Subscribed to {topic}")

        # Start message handler task
        self._subscribe_task = asyncio.create_task(self._handle_messages())
        logger.info("Subscribed to Home Assistant command topics")

    async def _handle_messages(self) -> None:
        """Handle incoming MQTT messages."""
        if not self.client:
            return

        try:
            async for message in self.client.messages:
                topic = str(message.topic)
                payload = message.payload.decode() if message.payload else ""

                logger.debug(f"Received MQTT message: {topic} = {payload}")

                if self.command_callback:
                    try:
                        await self.command_callback(topic, payload)
                    except Exception as e:
                        logger.error(f"Error in command callback: {e}")

        except asyncio.CancelledError:
            logger.debug("MQTT message handler cancelled")
        except Exception as e:
            logger.error(f"Error handling MQTT messages: {e}")
