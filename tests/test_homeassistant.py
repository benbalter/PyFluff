"""
Tests for Home Assistant MQTT integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pyfluff.homeassistant import HomeAssistantMQTT
from pyfluff.models import HomeAssistantConfig


class TestHomeAssistantConfig:
    """Test Home Assistant configuration model."""

    def test_default_config(self):
        """Test default HA configuration."""
        config = HomeAssistantConfig()
        assert config.enabled is False
        assert config.broker == "localhost"
        assert config.port == 1883
        assert config.username is None
        assert config.password is None
        assert config.device_id == "furby_connect"
        assert config.device_name == "Furby Connect"

    def test_custom_config(self):
        """Test custom HA configuration."""
        config = HomeAssistantConfig(
            enabled=True,
            broker="192.168.1.100",
            port=1884,
            username="user",
            password="pass",
            device_id="my_furby",
            device_name="My Furby",
        )
        assert config.enabled is True
        assert config.broker == "192.168.1.100"
        assert config.port == 1884
        assert config.username == "user"
        assert config.password == "pass"
        assert config.device_id == "my_furby"
        assert config.device_name == "My Furby"

    def test_port_validation(self):
        """Test port validation."""
        # Valid ports
        HomeAssistantConfig(port=1)
        HomeAssistantConfig(port=8883)
        HomeAssistantConfig(port=65535)

        # Invalid ports
        with pytest.raises(Exception):
            HomeAssistantConfig(port=0)
        with pytest.raises(Exception):
            HomeAssistantConfig(port=65536)


class TestHomeAssistantMQTT:
    """Test Home Assistant MQTT client."""

    def test_initialization(self):
        """Test MQTT client initialization."""
        mqtt = HomeAssistantMQTT(
            broker="localhost",
            port=1883,
            username="user",
            password="pass",
            device_id="furby_test",
            device_name="Test Furby",
        )

        assert mqtt.broker == "localhost"
        assert mqtt.port == 1883
        assert mqtt.username == "user"
        assert mqtt.password == "pass"
        assert mqtt.device_id == "furby_test"
        assert mqtt.device_name == "Test Furby"
        assert mqtt.running is False

    def test_device_info(self):
        """Test device info generation."""
        mqtt = HomeAssistantMQTT(device_id="furby_test", device_name="Test Furby")
        
        # Without MAC address
        device_info = mqtt._get_device_info()
        assert device_info["identifiers"] == ["furby_test"]
        assert device_info["name"] == "Test Furby"
        assert device_info["manufacturer"] == "Hasbro"
        assert device_info["model"] == "Furby Connect"
        assert "connections" not in device_info

        # With MAC address
        device_info = mqtt._get_device_info(mac_address="AA:BB:CC:DD:EE:FF")
        assert device_info["connections"] == [["mac", "AA:BB:CC:DD:EE:FF"]]

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test MQTT connect and disconnect."""
        mqtt = HomeAssistantMQTT()

        # Mock the MQTT client
        with patch("pyfluff.homeassistant.aiomqtt.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Test connect
            await mqtt.connect()
            assert mqtt.running is True
            mock_client.__aenter__.assert_called_once()

            # Test disconnect
            await mqtt.disconnect()
            assert mqtt.running is False
            mock_client.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_discovery(self):
        """Test publishing HA discovery messages."""
        mqtt = HomeAssistantMQTT(device_id="test_furby")
        
        with patch("pyfluff.homeassistant.aiomqtt.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mqtt.client = mock_client

            await mqtt.publish_discovery(mac_address="AA:BB:CC:DD:EE:FF")

            # Verify publish was called for each entity type
            assert mock_client.publish.call_count >= 5  # light, sensor, 3+ moods
            
            # Check some specific topics
            topics_published = [call[0][0] for call in mock_client.publish.call_args_list]
            assert any("light" in topic for topic in topics_published)
            assert any("binary_sensor" in topic for topic in topics_published)
            assert any("number" in topic for topic in topics_published)

    @pytest.mark.asyncio
    async def test_publish_antenna_state(self):
        """Test publishing antenna state."""
        mqtt = HomeAssistantMQTT(device_id="test_furby")
        
        with patch("pyfluff.homeassistant.aiomqtt.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mqtt.client = mock_client

            await mqtt.publish_antenna_state(255, 128, 0, on=True)

            # Verify two publishes: state and RGB
            assert mock_client.publish.call_count == 2
            
            # Check topics and payloads
            calls = mock_client.publish.call_args_list
            topics = [call[0][0] for call in calls]
            payloads = [call[0][1] for call in calls]
            
            assert "pyfluff/test_furby/antenna/state" in topics
            assert "pyfluff/test_furby/antenna/rgb/state" in topics
            assert "ON" in payloads
            assert "255,128,0" in payloads

    @pytest.mark.asyncio
    async def test_publish_connection_state(self):
        """Test publishing connection state."""
        mqtt = HomeAssistantMQTT(device_id="test_furby")
        
        with patch("pyfluff.homeassistant.aiomqtt.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mqtt.client = mock_client

            # Test connected
            await mqtt.publish_connection_state(True)
            mock_client.publish.assert_called_with(
                "pyfluff/test_furby/connection/state", "ON"
            )

            # Test disconnected
            await mqtt.publish_connection_state(False)
            mock_client.publish.assert_called_with(
                "pyfluff/test_furby/connection/state", "OFF"
            )

    @pytest.mark.asyncio
    async def test_publish_mood_state(self):
        """Test publishing mood state."""
        mqtt = HomeAssistantMQTT(device_id="test_furby")
        
        with patch("pyfluff.homeassistant.aiomqtt.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mqtt.client = mock_client

            await mqtt.publish_mood_state("excitedness", 75)
            
            mock_client.publish.assert_called_with(
                "pyfluff/test_furby/mood/excitedness/state", "75"
            )

    @pytest.mark.asyncio
    async def test_subscribe_to_commands(self):
        """Test subscribing to command topics."""
        mqtt = HomeAssistantMQTT(device_id="test_furby")
        
        with patch("pyfluff.homeassistant.aiomqtt.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mqtt.client = mock_client

            callback = AsyncMock()
            await mqtt.subscribe_to_commands(callback)

            # Verify subscriptions
            assert mock_client.subscribe.call_count >= 4
            topics = [call[0][0] for call in mock_client.subscribe.call_args_list]
            assert "pyfluff/test_furby/antenna/set" in topics
            assert "pyfluff/test_furby/antenna/rgb/set" in topics
            assert "pyfluff/test_furby/mood/+/set" in topics
            assert "pyfluff/test_furby/button/+/press" in topics

    @pytest.mark.asyncio
    async def test_handle_messages_not_connected(self):
        """Test handling messages when not connected."""
        mqtt = HomeAssistantMQTT()
        
        # Should return early if not connected
        await mqtt._handle_messages()
        assert mqtt.client is None

    def test_topic_structure(self):
        """Test MQTT topic structure."""
        mqtt = HomeAssistantMQTT(device_id="my_furby")
        
        assert mqtt.base_topic == "pyfluff/my_furby"
        assert mqtt.discovery_prefix == "homeassistant"
