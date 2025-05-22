"""Tests for the scanner module."""

import pytest
from unittest.mock import Mock, patch
from peloterm.scanner import (
    discover_devices,
    display_devices,
    HEART_RATE_SERVICE,
    CYCLING_POWER_SERVICE,
    CYCLING_SPEED_CADENCE,
)

@pytest.fixture
def mock_device():
    """Create a mock BLE device."""
    device = Mock()
    device.name = "Test Device"
    device.address = "00:11:22:33:44:55"
    return device

@pytest.fixture
def mock_adv_data():
    """Create mock advertisement data."""
    adv_data = Mock()
    adv_data.rssi = -65
    adv_data.service_uuids = [HEART_RATE_SERVICE.lower()]
    return adv_data

@pytest.mark.asyncio
async def test_discover_devices_with_heart_rate(mock_device, mock_adv_data):
    """Test discovering a device with heart rate service."""
    with patch('peloterm.scanner.BleakScanner.discover') as mock_discover:
        mock_discover.return_value = {mock_device.address: (mock_device, mock_adv_data)}
        
        devices = await discover_devices(timeout=1)
        assert len(devices) == 1
        device = devices[0]
        
        assert device["name"] == "Test Device"
        assert device["address"] == "00:11:22:33:44:55"
        assert device["rssi"] == -65
        assert "Heart Rate" in device["services"]

@pytest.mark.asyncio
async def test_discover_devices_with_power(mock_device, mock_adv_data):
    """Test discovering a device with power service."""
    mock_adv_data.service_uuids = [CYCLING_POWER_SERVICE.lower()]
    
    with patch('peloterm.scanner.BleakScanner.discover') as mock_discover:
        mock_discover.return_value = {mock_device.address: (mock_device, mock_adv_data)}
        
        devices = await discover_devices(timeout=1)
        assert len(devices) == 1
        device = devices[0]
        
        assert "Power" in device["services"]

@pytest.mark.asyncio
async def test_discover_devices_with_speed_cadence(mock_device, mock_adv_data):
    """Test discovering a device with speed/cadence service."""
    mock_adv_data.service_uuids = [CYCLING_SPEED_CADENCE.lower()]
    
    with patch('peloterm.scanner.BleakScanner.discover') as mock_discover:
        mock_discover.return_value = {mock_device.address: (mock_device, mock_adv_data)}
        
        devices = await discover_devices(timeout=1)
        assert len(devices) == 1
        device = devices[0]
        
        assert "Speed/Cadence" in device["services"]

@pytest.mark.asyncio
async def test_discover_devices_unknown_name(mock_device, mock_adv_data):
    """Test discovering a device with no name."""
    mock_device.name = None
    
    with patch('peloterm.scanner.BleakScanner.discover') as mock_discover:
        mock_discover.return_value = {mock_device.address: (mock_device, mock_adv_data)}
        
        devices = await discover_devices(timeout=1)
        assert len(devices) == 1
        device = devices[0]
        
        assert device["name"] == "Unknown"

def test_display_devices(capsys):
    """Test the display_devices function output."""
    test_devices = [{
        "name": "Test Device",
        "address": "00:11:22:33:44:55",
        "rssi": -65,
        "services": ["Heart Rate", "Power"]
    }]
    
    display_devices(test_devices)
    captured = capsys.readouterr()
    
    # Check that key information is present in the output
    assert "Test Device" in captured.out
    assert "00:11:22:33:44:55" in captured.out
    assert "-65dBm" in captured.out
    assert "Heart Rate, Power" in captured.out 