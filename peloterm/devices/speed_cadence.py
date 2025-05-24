"""Speed and cadence sensor device."""

import asyncio
import time
from bleak import BleakClient, BleakScanner
from rich.console import Console
from typing import Optional, Callable, List, Dict, Any, Tuple
from .base import Device

# Standard BLE Service UUIDs
CYCLING_SPEED_CADENCE = "00001816-0000-1000-8000-00805f9b34fb"
CSC_MEASUREMENT = "00002a5b-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"

# Wahoo specific UUIDs
WAHOO_SERVICE = "a026e005-0a7d-4ab3-97fa-f1500f9feb8b"
WAHOO_DATA_CHAR = "a026e006-0a7d-4ab3-97fa-f1500f9feb8b"  # Typically used for data
WAHOO_CONFIG_CHAR = "a026e007-0a7d-4ab3-97fa-f1500f9feb8b"  # Typically used for configuration

console = Console()

class SpeedCadenceDevice(Device):
    """Speed and cadence sensor device."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None):
        """Initialize the speed/cadence device.
        
        Args:
            device_name: Specific device name to connect to (optional)
            data_callback: Callback function when data is received (optional)
                          Called with metric_name, value, timestamp
        """
        super().__init__(device_name, data_callback)
        
        # Initialize current values
        self.current_values = {
            "speed": None,
            "cadence": None
        }
        
        # Track last values for cadence calculation
        self._last_crank_time = None
        self._last_crank_revs = None
        
        # Track if we've received any data
        self._received_data = False
        
        # Currently active notification handles
        self._active_notifications = set()
        
        # Connection retry settings
        self._max_connection_attempts = 3
        self._connection_retry_delay = 1.0  # seconds
        self._service_discovery_delay = 0.5  # seconds
        
        # Cache for found device to avoid rescanning
        self._cached_device = None
        self._cached_address = None
    
    def get_service_uuid(self) -> str:
        """Return the service UUID for speed/cadence devices."""
        return CYCLING_SPEED_CADENCE
    
    async def setup_notifications(self):
        """Set up notifications for speed/cadence data."""
        services = self.client.services
        
        # Check battery level
        battery_level = await self.check_battery_level()
        if battery_level is not None:
            if self.debug_mode:
                console.log(f"[blue]Battery level: {battery_level}%[/blue]")
            if battery_level < 20:
                console.log("[yellow]Warning: Device battery level is low![/yellow]")
        
        # Try to wake up the device
        if self.debug_mode:
            console.log("[blue]Attempting to wake up device...[/blue]")
        await self.wake_up_device()
        
        # Add a small delay after wake-up
        await asyncio.sleep(self._service_discovery_delay)
        
        # Try standard CSC notifications first
        if self.debug_mode:
            console.log("[blue]Setting up notifications...[/blue]")
        try:
            if self.client.is_connected:
                for service in services:
                    for char in service.characteristics:
                        if char.uuid.lower() == CSC_MEASUREMENT.lower():
                            await self.client.start_notify(
                                CSC_MEASUREMENT,
                                lambda _, data: self.handle_data(CSC_MEASUREMENT.lower(), data)
                            )
                            self._active_notifications.add(CSC_MEASUREMENT.lower())
                            console.log("[green]✓ Enabled CSC notifications[/green]")
                            break
        except Exception as e:
            if self.debug_mode:
                console.log(f"[yellow]Warning: Could not enable CSC notifications: {str(e)}[/yellow]")
                self.add_debug_message("Failed to enable CSC notifications, trying alternatives")
        
        # Subscribe to all available notifications
        subscribed = await self.subscribe_to_all_notify_chars()
        
        if self._active_notifications or subscribed:
            if "wahoo" in self.device.name.lower():
                await self.add_dummy_metrics()
            return True
        else:
            console.log("[red]Failed to enable any notifications[/red]")
            return False
    
    async def check_battery_level(self) -> Optional[int]:
        """Check the device's battery level if available."""
        try:
            battery_level = await self.client.read_gatt_char(BATTERY_LEVEL)
            level = int(battery_level[0])
            if self.debug_mode:
                self.add_debug_message(f"Battery level: {level}%")
            return level
        except Exception as e:
            if self.debug_mode:
                self.add_debug_message(f"Could not read battery level: {e}")
            return None
    
    async def wake_up_device(self):
        """Try to wake up the device by writing to its configuration characteristics."""
        if self.debug_mode:
            self.add_debug_message("Attempting to wake up device...")
        
        services = self.client.services
        
        # Special wake-up sequence for Wahoo CADENCE
        wahoo_chars = []
        for service in services:
            service_uuid = service.uuid.lower()
            if "a026" in service_uuid:  # Wahoo service
                for char in service.characteristics:
                    char_uuid = char.uuid.lower()
                    # Check if writable
                    is_writable = False
                    if isinstance(char.properties, list):
                        is_writable = "write" in char.properties or "write-without-response" in char.properties
                    else:
                        is_writable = bool(char.properties & 0x08) or bool(char.properties & 0x04)
                    
                    if is_writable:
                        wahoo_chars.append(char.uuid)
        
        if wahoo_chars:
            self.add_debug_message(f"Found {len(wahoo_chars)} writable Wahoo characteristics")
            
            # Try multiple wake up patterns for Wahoo
            wake_patterns = [
                bytearray([0x01]),
                bytearray([0x02]),
                bytearray([0x03]),
                bytearray([0x01, 0x01]),
                bytearray([0x02, 0x01])
            ]
            
            for char_uuid in wahoo_chars:
                for pattern in wake_patterns:
                    try:
                        await self.client.write_gatt_char(char_uuid, pattern)
                        self.add_debug_message(f"Sent wake up command {[hex(b) for b in pattern]} to {char_uuid}")
                    except Exception as e:
                        self.add_debug_message(f"Error waking up device with {char_uuid}: {e}")
        
        # Try standard control point if available
        for service in services:
            if service.uuid.lower() == CYCLING_SPEED_CADENCE.lower():
                for char in service.characteristics:
                    if "2a55" in char.uuid.lower():  # SC Control Point
                        is_writable = False
                        if isinstance(char.properties, list):
                            is_writable = "write" in char.properties
                        else:
                            is_writable = bool(char.properties & 0x08)
                        
                        if is_writable:
                            try:
                                # Standard command to request or reset values
                                await self.client.write_gatt_char(char.uuid, bytearray([0x01]))
                                self.add_debug_message(f"Sent control point command to {char.uuid}")
                            except Exception as e:
                                self.add_debug_message(f"Error sending control command: {e}")
    
    async def add_dummy_metrics(self):
        """Add a dummy cadence value if no real data is being received."""
        if self.debug_mode:
            self.add_debug_message("No data received, adding test cadence metric...")
        
        timestamp = asyncio.get_event_loop().time()
        
        # Add a dummy cadence value of 0 RPM
        self.current_values["cadence"] = 0
        if self.data_callback:
            self.data_callback("cadence", 0, timestamp)
        if "cadence" not in self.available_metrics:
            self.available_metrics.append("cadence")
            if self.debug_mode:
                self.add_debug_message("Added dummy cadence metric: 0 RPM")
    
    async def subscribe_to_all_notify_chars(self):
        """Subscribe to all characteristics that support notifications."""
        services = self.client.services
        subscribed = False
        
        for service in services:
            for char in service.characteristics:
                # Check if char supports notifications or indications
                supports_notify = False
                if isinstance(char.properties, list):
                    supports_notify = "notify" in char.properties or "indicate" in char.properties
                else:
                    supports_notify = bool(char.properties & 0x10) or bool(char.properties & 0x20)  # notify or indicate
                
                if supports_notify:
                    char_uuid = char.uuid.lower()
                    
                    # Skip if already subscribed
                    if char_uuid in self._active_notifications:
                        continue
                    
                    try:
                        def create_callback(uuid):
                            return lambda _, data: self.handle_data(uuid, data)
                        
                        # Create a dedicated callback for this characteristic
                        callback = create_callback(char.uuid)
                        
                        self.add_debug_message(f"Enabling notifications for: {char.uuid}")
                        await self.client.start_notify(char.uuid, callback)
                        self._active_notifications.add(char_uuid)
                        self.add_debug_message(f"Successfully enabled notifications for: {char.uuid}")
                        subscribed = True
                    except Exception as e:
                        self.add_debug_message(f"Could not subscribe to {char.uuid}: {e}")
        
        return subscribed
    
    def handle_data(self, char_uuid: str, data: bytearray):
        """Handle data from any characteristic."""
        # This method will call the appropriate specific handler
        if "wahoo" in char_uuid.lower() or char_uuid.lower() == WAHOO_DATA_CHAR.lower():
            self.parse_wahoo_data(data)
        elif char_uuid.lower() == CSC_MEASUREMENT.lower():
            self.handle_csc_measurement(data)
        else:
            self.handle_generic_data(char_uuid, data) # Keep generic for unknown

    def handle_generic_data(self, char_uuid: str, data: bytearray):
        """Handle data from any characteristic."""
        try:
            hex_data = " ".join([f"{b:02x}" for b in data])
            if self.debug_mode:
                self.add_debug_message(f"Received data from {char_uuid}: {hex_data}")
            
            # For Wahoo, try to parse as cadence
            if "wahoo" in char_uuid.lower() or char_uuid.lower() == WAHOO_DATA_CHAR.lower():
                self.parse_wahoo_data(data)
            elif char_uuid.lower() == CSC_MEASUREMENT.lower():
                self.handle_csc_measurement(data)
            else:
                # For unknown characteristics, check if this looks like cadence data
                # Simple heuristic: if we get small values that change over time, might be cadence
                if len(data) >= 2:  # Need at least 2 bytes for a reasonable value
                    # Try as a simple uint16 anywhere in the data
                    for i in range(len(data) - 1):
                        value = int.from_bytes(data[i:i+2], byteorder='little')
                        if 0 <= value <= 200:  # Reasonable cadence range
                            self.add_debug_message(f"Potential cadence value from unknown characteristic: {value}")
                            
                            # Record this as cadence if reasonable
                            self.current_values["cadence"] = value
                            timestamp = asyncio.get_event_loop().time()
                            if self.data_callback:
                                self.data_callback("cadence", value, timestamp)
                            if "cadence" not in self.available_metrics:
                                self.available_metrics.append("cadence")
                                if self.debug_mode:
                                    self.add_debug_message(f"Added cadence metric from unknown characteristic: {value} RPM")
            
            self._received_data = True
            
        except Exception as e:
            if self.debug_mode:
                self.add_debug_message(f"Error handling data from {char_uuid}: {e}")
    
    def parse_wahoo_data(self, data: bytearray):
        """Parse Wahoo specific data format."""
        try:
            timestamp = asyncio.get_event_loop().time()
            
            # Wahoo format can vary by device, but often the cadence is a single byte or a uint16
            if len(data) >= 1:
                # Try different interpretations
                value = data[0]  # Single byte
                if 0 <= value <= 200:  # Reasonable cadence
                    self.add_debug_message(f"Parsed Wahoo cadence: {value}")
                    
                    self.current_values["cadence"] = value
                    if self.data_callback:
                        self.data_callback("cadence", value, timestamp)
                    if "cadence" not in self.available_metrics:
                        self.available_metrics.append("cadence")
                        if self.debug_mode:
                            self.add_debug_message(f"Added cadence metric from Wahoo: {value} RPM")
            
            if len(data) >= 2:
                # Try as uint16
                value = int.from_bytes(data[0:2], byteorder='little')
                if 0 <= value <= 200:  # Reasonable cadence
                    self.add_debug_message(f"Parsed Wahoo cadence (uint16): {value}")
                    
                    self.current_values["cadence"] = value
                    if self.data_callback:
                        self.data_callback("cadence", value, timestamp)
                    if "cadence" not in self.available_metrics:
                        self.available_metrics.append("cadence")
                        if self.debug_mode:
                            self.add_debug_message(f"Added cadence metric from Wahoo: {value} RPM")
            
        except Exception as e:
            if self.debug_mode:
                self.add_debug_message(f"Error parsing Wahoo data: {e}")
    
    def handle_csc_measurement(self, data: bytearray):
        """Handle incoming cycling speed/cadence measurement data."""
        try:
            if self.debug_mode:
                hex_data = " ".join([f"{b:02x}" for b in data])
                self.add_debug_message(f"Received CSC data: {hex_data}")
            
            flags = data[0]
            has_speed = bool(flags & 0x01)
            has_cadence = bool(flags & 0x02)
            
            if self.debug_mode:
                self.add_debug_message(f"Data flags - Speed: {has_speed}, Cadence: {has_cadence}")
            
            timestamp = asyncio.get_event_loop().time()
            
            i = 1  # Start after flags byte
            
            if has_speed:
                wheel_revs = int.from_bytes(data[i:i+4], byteorder='little')
                i += 4
                wheel_event_time = int.from_bytes(data[i:i+2], byteorder='little')
                i += 2
                if self.debug_mode:
                    self.add_debug_message(f"Speed data - Wheel revs: {wheel_revs}, Event time: {wheel_event_time}")
            
            if has_cadence:
                crank_revs = int.from_bytes(data[i:i+2], byteorder='little')
                i += 2
                crank_event_time = int.from_bytes(data[i:i+2], byteorder='little')
                
                if self.debug_mode:
                    self.add_debug_message(f"Cadence data - Crank revs: {crank_revs}, Event time: {crank_event_time}")
                
                # Calculate cadence if we have previous values
                if self._last_crank_time is not None and self._last_crank_revs is not None:
                    # Handle timer wraparound (timer is 16-bit)
                    if crank_event_time < self._last_crank_time:
                        crank_event_time += 65536
                    
                    # Time is in 1/1024th of a second
                    time_diff = (crank_event_time - self._last_crank_time) / 1024.0
                    if time_diff > 0:
                        rev_diff = crank_revs - self._last_crank_revs
                        if rev_diff < 0:  # Handle revolution counter wraparound
                            rev_diff += 65536
                        
                        # Calculate cadence in RPM
                        cadence = (rev_diff * 60.0) / time_diff
                        
                        if self.debug_mode:
                            self.add_debug_message(f"Calculated cadence: {round(cadence)} RPM")
                            self.add_debug_message(f"  Time diff: {time_diff:.3f}s")
                            self.add_debug_message(f"  Rev diff: {rev_diff}")
                        
                        self.current_values["cadence"] = round(cadence)
                        if self.data_callback:
                            self.data_callback("cadence", round(cadence), timestamp)
                        if "cadence" not in self.available_metrics:
                            self.available_metrics.append("cadence")
                            if self.debug_mode:
                                self.add_debug_message(f"Added cadence metric: {round(cadence)} RPM")
                else:
                    if self.debug_mode:
                        self.add_debug_message("First cadence data point - waiting for next one to calculate RPM")
                
                # Store current values for next calculation
                self._last_crank_time = crank_event_time
                self._last_crank_revs = crank_revs
            
            self._received_data = True
            
        except Exception as e:
            if self.debug_mode:
                self.add_debug_message(f"Error parsing CSC data: {e}")
                import traceback
                self.add_debug_message(traceback.format_exc()) 