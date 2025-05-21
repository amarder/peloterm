"""Speed and cadence sensor device."""

import asyncio
from bleak import BleakClient, BleakScanner
from rich.console import Console
from typing import Optional, Callable, List, Dict, Any

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

class SpeedCadenceDevice:
    """Speed and cadence sensor device."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None):
        """Initialize the speed/cadence device.
        
        Args:
            device_name: Specific device name to connect to (optional)
            data_callback: Callback function when data is received (optional)
                          Called with metric_name, value, timestamp
        """
        self.device_name = device_name
        self.data_callback = data_callback
        self.client = None
        self.device = None
        self.debug_mode = False
        self.debug_messages = []
        
        # Track current values
        self.current_values = {
            "speed": None,
            "cadence": None
        }
        
        # Track available metrics
        self.available_metrics = []
        
        # Track last values for cadence calculation
        self._last_crank_time = None
        self._last_crank_revs = None
        
        # Track if we've received any data
        self._received_data = False
        
        # Currently active notification handles
        self._active_notifications = set()
    
    async def find_device(self):
        """Find a speed/cadence sensor device."""
        console.print("[blue]Searching for speed/cadence sensors...[/blue]")
        
        discovered = await BleakScanner.discover(return_adv=True)
        
        # Debug all discovered devices
        if self.debug_mode:
            self.add_debug_message("Discovered devices:")
            for device, adv_data in discovered.values():
                self.add_debug_message(f"Device: {device.name} ({device.address})")
                if adv_data.service_uuids:
                    self.add_debug_message(f"  Services: {', '.join(str(uuid) for uuid in adv_data.service_uuids)}")
                else:
                    self.add_debug_message("  No service UUIDs advertised")
        
        # First try to find by name (if specified)
        if self.device_name:
            for device, adv_data in discovered.values():
                if device.name and self.device_name.lower() in device.name.lower():
                    console.print(f"[green]✓ Matched requested speed/cadence device: {device.name}[/green]")
                    if self.debug_mode:
                        self.add_debug_message(f"Matched device by name: {device.name}")
                    return device
        
        # Then try to find Wahoo CADENCE devices by name
        if self.device_name and "wahoo" in self.device_name.lower() and "cadence" in self.device_name.lower():
            for device, adv_data in discovered.values():
                if device.name and "wahoo" in device.name.lower() and "cadence" in device.name.lower():
                    console.print(f"[green]✓ Found Wahoo cadence sensor: {device.name}[/green]")
                    if self.debug_mode:
                        self.add_debug_message(f"Matched Wahoo cadence device: {device.name}")
                    return device
        
        # Then try by service UUID
        for device, adv_data in discovered.values():
            if adv_data.service_uuids:
                uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                if CYCLING_SPEED_CADENCE.lower() in uuids:
                    console.print(f"[green]✓ Found speed/cadence sensor by service: {device.name or 'Unknown'}[/green]")
                    if self.debug_mode:
                        self.add_debug_message(f"Matched device by service UUID: {device.name}")
                    return device
        
        # Finally, try known Wahoo UUIDs
        for device, adv_data in discovered.values():
            if adv_data.service_uuids:
                uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                if any("wahoo" in uuid.lower() for uuid in uuids):
                    console.print(f"[green]✓ Found Wahoo device by service: {device.name or 'Unknown'}[/green]")
                    if self.debug_mode:
                        self.add_debug_message(f"Matched device by Wahoo service: {device.name}")
                    return device
        
        # Additional search for common manufacturer data from Wahoo
        for device, adv_data in discovered.values():
            if device.name and "wahoo" in device.name.lower():
                console.print(f"[green]✓ Found Wahoo device by name: {device.name}[/green]")
                if self.debug_mode:
                    self.add_debug_message(f"Matched device by Wahoo name: {device.name}")
                return device
        
        console.print("[yellow]No speed/cadence sensor found. Make sure your device is awake and nearby.[/yellow]")
        return None
    
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
    
    def add_debug_message(self, message: str):
        """Add a debug message to the log."""
        self.debug_messages.append(message)
        if len(self.debug_messages) > 100:
            self.debug_messages.pop(0)
        console.print(f"[dim]{message}[/dim]")
    
    def get_available_metrics(self) -> List[str]:
        """Return list of available metrics from this device."""
        if self.debug_mode:
            self.add_debug_message(f"Available metrics requested: {self.available_metrics}")
            self.add_debug_message(f"Have we received any data? {'Yes' if self._received_data else 'No'}")
        return self.available_metrics
    
    def get_current_values(self) -> Dict[str, Any]:
        """Return dictionary of current values."""
        if self.debug_mode:
            self.add_debug_message(f"Current values requested: {self.current_values}")
        return self.current_values
    
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
                            return lambda _, data: self.handle_generic_data(uuid, data)
                        
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
    
    async def connect(self, debug: bool = False):
        """Connect to the speed/cadence device."""
        self.debug_mode = debug
        self.device = await self.find_device()
        if not self.device:
            return False
        
        console.print(f"[green]Connecting to speed/cadence sensor {self.device.name}...[/green]")
        
        try:
            self.client = BleakClient(self.device)
            await self.client.connect()
            
            if debug:
                services = self.client.services
                console.print("\n[yellow]Available Services:[/yellow]")
                self.add_debug_message("Discovered services:")
                for service in services:
                    console.print(f"[dim]Service:[/dim] {service.uuid}")
                    self.add_debug_message(f"Service: {service.uuid}")
                    for char in service.characteristics:
                        # Handle properties as either list or int
                        props = []
                        if isinstance(char.properties, list):
                            props = char.properties
                        else:
                            if char.properties & 0x02:  # read
                                props.append("read")
                            if char.properties & 0x04:  # write without response
                                props.append("write-without-response")
                            if char.properties & 0x08:  # write
                                props.append("write")
                            if char.properties & 0x10:  # notify
                                props.append("notify")
                            if char.properties & 0x20:  # indicate
                                props.append("indicate")
                        
                        console.print(f"  [dim]Characteristic:[/dim] {char.uuid} ({', '.join(props)})")
                        self.add_debug_message(f"  Characteristic: {char.uuid} ({', '.join(props)})")
                        for desc in char.descriptors:
                            self.add_debug_message(f"    Descriptor: {desc.uuid}")
            
            # Check battery level
            battery_level = await self.check_battery_level()
            if battery_level is not None:
                console.print(f"[blue]Device battery level: {battery_level}%[/blue]")
                if battery_level < 20:
                    console.print("[yellow]Warning: Device battery level is low![/yellow]")
            
            # Try to wake up the device
            await self.wake_up_device()
            
            # Try spinning the wheel notification
            if "wahoo" in self.device.name.lower() and "cadence" in self.device.name.lower():
                console.print("[blue]Wahoo CADENCE sensor detected[/blue]")
                console.print("[blue]NOTE: The sensor may need the crank to be spun to start sending data[/blue]")
                console.print("[blue]Please spin the crank/pedal a few times to activate the sensor[/blue]")
            
            # First try to subscribe to standard CSC characteristic
            try:
                if not self.client.is_connected:
                    if debug:
                        self.add_debug_message("Device disconnected before enabling notifications")
                    return False
                
                services = self.client.services
                csc_char = None
                for service in services:
                    for char in service.characteristics:
                        if char.uuid.lower() == CSC_MEASUREMENT.lower():
                            csc_char = char
                            break
                    if csc_char:
                        break
                
                if csc_char:
                    if debug:
                        self.add_debug_message(f"Found CSC Measurement characteristic: {csc_char.uuid}")
                        self.add_debug_message(f"Properties: {csc_char.properties}")
                        self.add_debug_message("Enabling notifications...")
                    
                    await self.client.start_notify(
                        CSC_MEASUREMENT,
                        lambda _, data: self.handle_csc_measurement(data)
                    )
                    self._active_notifications.add(CSC_MEASUREMENT.lower())
                    
                    if debug:
                        self.add_debug_message("Successfully enabled CSC Measurement notifications")
                else:
                    if debug:
                        self.add_debug_message(f"Standard CSC Measurement characteristic not found")
            except Exception as e:
                if debug:
                    self.add_debug_message(f"Error enabling standard CSC notifications: {e}")
                    import traceback
                    self.add_debug_message(traceback.format_exc())
            
            # Subscribe to all notifiable characteristics
            subscribed = await self.subscribe_to_all_notify_chars()
            
            # If we've successfully set up at least one notification
            if self._active_notifications or subscribed:
                console.print("[green]Successfully connected to speed/cadence sensor![/green]")
                
                # Add dummy metrics if this is a Wahoo device (will be replaced by real data when received)
                if "wahoo" in self.device.name.lower():
                    await self.add_dummy_metrics()
                
                return True
            else:
                if debug:
                    self.add_debug_message("Failed to subscribe to any notifiable characteristics")
                    console.print("[red]Failed to subscribe to any notifiable characteristics[/red]")
                return False
                
        except Exception as e:
            if debug:
                self.add_debug_message(f"Error during connection: {e}")
                import traceback
                self.add_debug_message(traceback.format_exc())
            console.print(f"[red]Error connecting to speed/cadence sensor: {e}[/red]")
            return False
    
    async def disconnect(self):
        """Disconnect from the speed/cadence device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            console.print("[yellow]Disconnected from speed/cadence sensor[/yellow]") 