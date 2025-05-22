"""Heart rate monitor device."""

import asyncio
from bleak import BleakClient, BleakScanner
from rich.console import Console
from typing import Optional, Callable, List, Dict, Any

# BLE Service UUIDs
HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"

console = Console()

class HeartRateDevice:
    """Heart rate monitor device."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None):
        """Initialize the heart rate device.
        
        Args:
            device_name: Specific device name to connect to (optional)
            data_callback: Callback function when data is received (optional)
                          Called with metric_name, value, timestamp
        """
        self.device_name = device_name
        self.data_callback = data_callback
        self.client = None
        self.device = None
        self.current_value = None
        self.available_metrics = []
    
    async def find_device(self):
        """Find a heart rate monitor device."""
        console.print("[blue]Searching for heart rate monitors...[/blue]")
        
        discovered = await BleakScanner.discover(return_adv=True)
        
        for device, adv_data in discovered.values():
            if self.device_name:
                if device.name and self.device_name.lower() in device.name.lower():
                    console.print(f"[green]✓ Matched requested heart rate device: {device.name}[/green]")
                    return device
                continue
            
            if adv_data.service_uuids:
                uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                if HEART_RATE_SERVICE.lower() in uuids:
                    console.print(f"[green]✓ Found heart rate monitor: {device.name or 'Unknown'}[/green]")
                    return device
        
        console.print("[yellow]No heart rate monitor found. Make sure your device is awake and nearby.[/yellow]")
        return None
    
    def handle_heart_rate(self, _, data: bytearray):
        """Handle incoming heart rate data."""
        flags = data[0]
        if flags & 0x1:  # If first bit is set, value is uint16
            heart_rate = int.from_bytes(data[1:3], byteorder='little')
        else:  # Value is uint8
            heart_rate = data[1]
        
        self.current_value = heart_rate
        timestamp = asyncio.get_event_loop().time()
        
        # Call the callback if provided
        if self.data_callback:
            self.data_callback("heart_rate", heart_rate, timestamp)
    
    def get_available_metrics(self) -> List[str]:
        """Return list of available metrics from this device."""
        return ["heart_rate"]  # Heart rate monitor always has heart rate metric
    
    def get_current_values(self) -> Dict[str, Any]:
        """Return dictionary of current values."""
        return {"heart_rate": self.current_value}
    
    async def connect(self) -> bool:
        """Connect to the heart rate device."""
        self.device = await self.find_device()
        if not self.device:
            return False
        
        try:
            self.client = BleakClient(self.device)
            await self.client.connect()
            
            await self.client.start_notify(
                HEART_RATE_MEASUREMENT,
                self.handle_heart_rate
            )
            
            # Initialize with a zero value to ensure the metric is available
            if self.data_callback:
                self.data_callback("heart_rate", 0, asyncio.get_event_loop().time())
            
            return True
        except Exception as e:
            console.print(f"[red]Error connecting to heart rate monitor: {e}[/red]")
            return False
    
    async def disconnect(self):
        """Disconnect from the heart rate device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            console.print("[yellow]Disconnected from heart rate monitor[/yellow]") 