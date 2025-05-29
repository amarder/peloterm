"""Tests for device classes."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from peloterm.devices.base import Device

class TestDevice:
    """Test the base Device class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock BleakClient."""
        client = AsyncMock()
        client.is_connected = True
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.start_notify = AsyncMock()
        return client

    @pytest.fixture
    def mock_device(self):
        """Create a mock BLE device."""
        device = Mock()
        device.name = "Test Device"
        device.address = "00:11:22:33:44:55"
        return device

    @pytest.fixture
    async def test_device(self):
        """Create a test Device instance."""
        class TestDeviceImpl(Device):
            def get_service_uuid(self):
                return "test-service-uuid"
            
            async def setup_notifications(self):
                return True

        device = TestDeviceImpl(device_name="Test Device")
        yield device
        # Cleanup: ensure device is properly disconnected
        await device.disconnect()

    @pytest.mark.asyncio
    async def test_device_reconnection(self, test_device, mock_device, mock_client):
        """Test device reconnection functionality."""
        # Mock the device discovery and client creation
        with patch('peloterm.devices.base.BleakScanner.find_device_by_address', return_value=mock_device), \
             patch('peloterm.devices.base.BleakClient', return_value=mock_client):
            
            # Set up mock callbacks
            disconnect_callback = AsyncMock()
            reconnect_callback = AsyncMock()
            await test_device.set_callbacks(
                disconnect_callback=disconnect_callback,
                reconnect_callback=reconnect_callback
            )

            # Initial connection
            connected = await test_device.connect(address="00:11:22:33:44:55")
            assert connected
            assert test_device._last_known_address == "00:11:22:33:44:55"

            # Simulate disconnection
            await test_device._handle_disconnect()
            
            # Verify disconnect callback was called
            disconnect_callback.assert_awaited_once()
            
            # Wait for reconnection attempts
            await asyncio.sleep(0.1)  # Small delay to allow reconnection task to run
            
            # Verify reconnect callback was called (since our mock connect always succeeds)
            reconnect_callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_reconnection(self, test_device, mock_device, mock_client):
        """Test device reconnection when attempts fail."""
        # Make connect fail after initial success (1 success + 5 failures for reconnection attempts)
        mock_client.connect.side_effect = [None] + [Exception("Connection failed")] * 5

        with patch('peloterm.devices.base.BleakScanner.find_device_by_address', return_value=mock_device), \
             patch('peloterm.devices.base.BleakClient', return_value=mock_client):
            
            # Set up mock callbacks
            disconnect_callback = AsyncMock()
            reconnect_callback = AsyncMock()
            await test_device.set_callbacks(
                disconnect_callback=disconnect_callback,
                reconnect_callback=reconnect_callback
            )

            # Initial connection (uses _connection_backoff for retries, but should succeed on first try)
            connected = await test_device.connect(address="00:11:22:33:44:55")
            assert connected

            # Simulate disconnection
            await test_device._handle_disconnect()
            
            # Verify disconnect callback was called
            disconnect_callback.assert_awaited_once()
            
            # Wait for all reconnection attempts
            await asyncio.sleep(test_device._reconnect_delay * test_device._max_reconnect_attempts)
            
            # Verify reconnect callback was not called (since reconnection failed)
            reconnect_callback.assert_not_awaited()
            
            # Verify the correct number of connection attempts were made
            # Initial connection (1 successful) + _max_reconnect_attempts (5 failed reconnection attempts) = 6 total
            assert mock_client.connect.call_count == 6  # Initial + 5 retry attempts

    @pytest.mark.asyncio
    async def test_reconnection_config(self, test_device, mock_device, mock_client):
        """Test device reconnection configuration."""
        # Customize reconnection settings
        test_device._max_reconnect_attempts = 2
        test_device._reconnect_delay = 0.1

        with patch('peloterm.devices.base.BleakScanner.find_device_by_address', return_value=mock_device), \
             patch('peloterm.devices.base.BleakClient', return_value=mock_client):
            
            # Set up mock callbacks
            disconnect_callback = AsyncMock()
            reconnect_callback = AsyncMock()
            await test_device.set_callbacks(
                disconnect_callback=disconnect_callback,
                reconnect_callback=reconnect_callback
            )
            
            # Initial connection (should succeed on first try)
            mock_client.connect.side_effect = [None]  # Success for initial connection
            connected = await test_device.connect(address="00:11:22:33:44:55")
            assert connected
            assert mock_client.connect.call_count == 1

            # Reset call count to track only reconnection attempts
            mock_client.connect.reset_mock()
            
            # Make subsequent connections fail for reconnection attempts
            mock_client.connect.side_effect = Exception("Connection failed")

            # Simulate disconnection
            await test_device._handle_disconnect()
            
            # Wait for the reconnection task to be created
            await asyncio.sleep(0.01)
            
            # Get reference to the reconnection task
            reconnect_task = test_device._reconnect_task
            assert reconnect_task is not None, "Reconnection task should have been created"
            
            # Wait for the reconnection task to complete
            await reconnect_task
            
            # Verify disconnect callback was called
            disconnect_callback.assert_awaited_once()
            
            # Verify reconnect callback was not called (since reconnection failed)
            reconnect_callback.assert_not_awaited()
            
            # Verify exactly 2 retry attempts were made during reconnection
            assert mock_client.connect.call_count == 6  # 2 reconnection attempts × 3 connection retries each = 6 total 