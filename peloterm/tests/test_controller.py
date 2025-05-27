"""Tests for the controller module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from peloterm.controller import DeviceController
from peloterm.config import Config, DeviceConfig, MetricConfig, METRIC_DISPLAY_NAMES
from peloterm.devices.base import Device

@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Config(
        devices=[
            DeviceConfig(
                name="Test HR Monitor",
                address="00:11:22:33:44:55",
                services=["Heart Rate"]
            ),
            DeviceConfig(
                name="Test Trainer",
                address="66:77:88:99:AA:BB",
                services=["Power"]
            )
        ],
        display=[
            MetricConfig(
                metric="heart_rate",
                display_name=METRIC_DISPLAY_NAMES["heart_rate"],
                device="Test HR Monitor",
                color="red"
            ),
            MetricConfig(
                metric="power",
                display_name=METRIC_DISPLAY_NAMES["power"],
                device="Test Trainer",
                color="yellow"
            ),
            MetricConfig(
                metric="speed",
                display_name=METRIC_DISPLAY_NAMES["speed"],
                device="Test Trainer",
                color="blue"
            )
        ]
    )

@pytest.fixture
def mock_discovered_devices():
    """Create mock discovered devices."""
    return [
        {
            "name": "Test HR Monitor",
            "address": "00:11:22:33:44:55",
            "services": ["Heart Rate"],
            "rssi": -65
        },
        {
            "name": "Test Trainer",
            "address": "66:77:88:99:AA:BB",
            "services": ["Power"],
            "rssi": -70
        }
    ]

@pytest.fixture
def mock_heart_rate_device():
    """Create a mock heart rate device."""
    device = AsyncMock()
    device.device_name = "Test HR Monitor"
    device.connect = AsyncMock(return_value=True)
    device.disconnect = AsyncMock()
    return device

@pytest.fixture
def mock_trainer_device():
    """Create a mock trainer device."""
    device = AsyncMock()
    device.device_name = "Test Trainer"
    device.connect = AsyncMock(return_value=True)
    device.disconnect = AsyncMock()
    return device

@pytest.mark.asyncio
async def test_controller_initialization(sample_config):
    """Test controller initialization with configuration."""
    controller = DeviceController(config=sample_config)
    
    # Check that metric monitors were created from config
    assert len(controller.metric_monitors) == 3  # heart_rate, power, speed
    assert "heart_rate" in controller.metric_monitors
    assert "power" in controller.metric_monitors
    assert "speed" in controller.metric_monitors
    
    # Check monitor configuration
    hr_monitor = controller.metric_monitors["heart_rate"]
    assert hr_monitor.color == "red"
    assert hr_monitor.unit == "BPM"
    
    power_monitor = controller.metric_monitors["power"]
    assert power_monitor.color == "yellow"
    assert power_monitor.unit == "W"

@pytest.mark.asyncio
async def test_connect_configured_devices(
    sample_config,
    mock_discovered_devices,
    mock_heart_rate_device,
    mock_trainer_device
):
    """Test connecting to configured devices."""
    with patch('peloterm.controller.discover_devices', return_value=mock_discovered_devices), \
         patch('peloterm.controller.HeartRateDevice', return_value=mock_heart_rate_device), \
         patch('peloterm.controller.TrainerDevice', return_value=mock_trainer_device):
        
        controller = DeviceController(config=sample_config)
        success = await controller.connect_configured_devices()
        
        assert success
        assert len(controller.connected_devices) == 2
        assert controller.heart_rate_device == mock_heart_rate_device
        assert controller.trainer_device == mock_trainer_device
        
        # Verify devices were connected
        mock_heart_rate_device.connect.assert_called_once()
        mock_trainer_device.connect.assert_called_once()

@pytest.mark.asyncio
async def test_handle_metric_data(sample_config):
    """Test handling metric data updates."""
    controller = DeviceController(config=sample_config)
    
    # Update heart rate
    controller.handle_metric_data("heart_rate", 150, 0)
    assert controller.metric_monitors["heart_rate"].current_value == 150
    
    # Update power
    controller.handle_metric_data("power", 200, 0)
    assert controller.metric_monitors["power"].current_value == 200

    # Update speed
    controller.handle_metric_data("speed", 30, 0)
    assert controller.metric_monitors["speed"].current_value == 30

@pytest.mark.asyncio
async def test_disconnect_devices(
    sample_config,
    mock_heart_rate_device,
    mock_trainer_device
):
    """Test disconnecting devices."""
    controller = DeviceController(config=sample_config)
    
    # Add mock devices to controller
    controller.heart_rate_device = mock_heart_rate_device
    controller.trainer_device = mock_trainer_device
    controller.connected_devices = [mock_heart_rate_device, mock_trainer_device]
    
    # Disconnect devices
    await controller.disconnect_devices()
    
    assert len(controller.connected_devices) == 0
    mock_heart_rate_device.disconnect.assert_called_once()
    mock_trainer_device.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_device_disconnect_handling(
    sample_config,
    mock_heart_rate_device,
    mock_trainer_device
):
    """Test handling of device disconnection."""
    with patch('peloterm.controller.HeartRateDevice', return_value=mock_heart_rate_device), \
         patch('peloterm.controller.TrainerDevice', return_value=mock_trainer_device):
        
        controller = DeviceController(config=sample_config)
        await controller.connect_configured_devices()
        
        # Verify initial state
        assert len(controller.connected_devices) == 2
        assert mock_heart_rate_device in controller.connected_devices
        
        # Simulate heart rate device disconnection
        await controller.handle_device_disconnect(mock_heart_rate_device)
        
        # Device should still be in connected_devices as reconnection will be attempted
        assert mock_heart_rate_device in controller.connected_devices

@pytest.mark.asyncio
async def test_device_reconnect_handling(
    sample_config,
    mock_heart_rate_device,
    mock_trainer_device
):
    """Test handling of device reconnection."""
    with patch('peloterm.controller.HeartRateDevice', return_value=mock_heart_rate_device), \
         patch('peloterm.controller.TrainerDevice', return_value=mock_trainer_device):
        
        controller = DeviceController(config=sample_config)
        await controller.connect_configured_devices()
        
        # Remove device to simulate disconnected state
        controller.connected_devices.remove(mock_heart_rate_device)
        assert mock_heart_rate_device not in controller.connected_devices
        
        # Simulate successful reconnection
        await controller.handle_device_reconnect(mock_heart_rate_device)
        
        # Verify device was added back to connected_devices
        assert mock_heart_rate_device in controller.connected_devices

@pytest.mark.asyncio
async def test_device_callbacks_registration(
    sample_config,
    mock_heart_rate_device,
    mock_trainer_device
):
    """Test that device callbacks are properly registered."""
    with patch('peloterm.controller.HeartRateDevice', return_value=mock_heart_rate_device), \
         patch('peloterm.controller.TrainerDevice', return_value=mock_trainer_device):
        
        controller = DeviceController(config=sample_config)
        await controller.connect_configured_devices()
        
        # Verify callbacks were set
        mock_heart_rate_device.set_callbacks.assert_awaited_once_with(
            disconnect_callback=controller.handle_device_disconnect,
            reconnect_callback=controller.handle_device_reconnect
        )
        
        mock_trainer_device.set_callbacks.assert_awaited_once_with(
            disconnect_callback=controller.handle_device_disconnect,
            reconnect_callback=controller.handle_device_reconnect
        ) 