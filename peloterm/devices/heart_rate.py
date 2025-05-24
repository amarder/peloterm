"""Heart rate monitor device."""

import asyncio
from bleak import BleakClient, BleakScanner
from rich.console import Console
from typing import Optional, Callable, List, Dict, Any
from .base import Device

# BLE Service UUIDs
HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"

console = Console()

class HeartRateDevice(Device):
    """Heart rate monitor device."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None):
        """Initialize the heart rate device.
        
        Args:
            device_name: Specific device name to connect to (optional)
            data_callback: Callback function when data is received (optional)
                          Called with metric_name, value, timestamp
        """
        super().__init__(device_name, data_callback)
        self.current_values = {"heart_rate": None}
    
    def get_service_uuid(self) -> str:
        """Return the service UUID for heart rate devices."""
        return HEART_RATE_SERVICE
    
    async def setup_notifications(self):
        """Set up notifications for heart rate measurement."""
        await self.client.start_notify(
            HEART_RATE_MEASUREMENT,
            self.handle_data
        )
        
        # Initialize with a zero value to ensure the metric is available
        if self.data_callback:
            self.data_callback("heart_rate", 0, asyncio.get_event_loop().time())
        
        # Add heart rate to available metrics
        if "heart_rate" not in self.available_metrics:
            self.available_metrics.append("heart_rate")
    
    def handle_data(self, _, data: bytearray):
        """Handle incoming heart rate data."""
        flags = data[0]
        if flags & 0x1:  # If first bit is set, value is uint16
            heart_rate = int.from_bytes(data[1:3], byteorder='little')
        else:  # Value is uint8
            heart_rate = data[1]
        
        self.current_values["heart_rate"] = heart_rate
        timestamp = asyncio.get_event_loop().time()
        
        # Call the callback if provided
        if self.data_callback:
            self.data_callback("heart_rate", heart_rate, timestamp)
        
        if self.debug_mode:
            self.add_debug_message(f"Received heart rate: {heart_rate} BPM")
    
    def get_available_metrics(self) -> List[str]:
        """Return list of available metrics from this device."""
        return ["heart_rate"]  # Heart rate monitor always has heart rate metric
    
    def get_current_values(self) -> Dict[str, Any]:
        """Return dictionary of current values."""
        return self.current_values 