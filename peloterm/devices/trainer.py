"""Smart trainer device."""

import asyncio
from bleak import BleakClient, BleakScanner
from rich.console import Console
from typing import Optional, Callable, Dict, Any, List

# InsideRide E-Motion Service UUIDs
UART_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write to trainer
UART_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Receive from trainer

# Fitness Machine Service
FITNESS_MACHINE_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_FEATURE = "00002acc-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_STATUS = "00002ada-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_INDOOR_BIKE_DATA = "00002ad2-0000-1000-8000-00805f9b34fb"

# Known trainer names
KNOWN_TRAINERS = ["insideride", "e-motion", "7578h"]

console = Console()

class TrainerDevice:
    """Smart trainer device."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None):
        """Initialize the trainer device.
        
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
            "power": None,
            "speed": None,
            "cadence": None
        }
        
        # Track available metrics
        self.available_metrics = []
    
    async def find_device(self):
        """Find a smart trainer device."""
        console.print("[blue]Searching for smart trainers...[/blue]")
        
        discovered = await BleakScanner.discover(return_adv=True)
        
        for device, adv_data in discovered.values():
            if self.device_name:
                if device.name and self.device_name.lower() in device.name.lower():
                    console.print(f"[green]✓ Matched requested trainer: {device.name}[/green]")
                    return device
                continue
            
            # Check device name for known trainers
            if device.name and any(name in device.name.lower() for name in KNOWN_TRAINERS):
                console.print(f"[green]✓ Found InsideRide trainer: {device.name}[/green]")
                return device
            
            # Check for UART or Fitness Machine service
            if adv_data.service_uuids:
                uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                if UART_SERVICE.lower() in uuids or FITNESS_MACHINE_SERVICE.lower() in uuids:
                    console.print(f"[green]✓ Found trainer: {device.name or 'Unknown'}[/green]")
                    return device
        
        console.print("[yellow]No smart trainer found. Make sure your device is awake and nearby.[/yellow]")
        return None
    
    def handle_indoor_bike_data(self, _, data: bytearray):
        """Handle incoming indoor bike data."""
        try:
            if self.debug_mode:
                hex_data = " ".join([f"{b:02x}" for b in data])
                self.add_debug_message(f"Received bike data: {hex_data}")
            
            # Parse according to FTMS Indoor Bike Data characteristic format
            flags = int.from_bytes(data[0:2], byteorder='little')
            timestamp = asyncio.get_event_loop().time()
            
            # Initialize values
            power = None
            speed = None
            cadence = None
            
            # Parse data based on flags
            offset = 2  # Start after flags
            
            # Check flags for available data
            if flags & 0x0002:  # Speed present
                raw_speed = int.from_bytes(data[offset:offset+2], byteorder='little')
                speed = raw_speed / 100  # Convert from 0.01 km/h to km/h
                offset += 2
                self.current_values["speed"] = speed
                if self.data_callback:
                    self.data_callback("speed", speed, timestamp)
                if "speed" not in self.available_metrics:
                    self.available_metrics.append("speed")
                    if self.debug_mode:
                        self.add_debug_message(f"Added speed metric: {speed} km/h")
            
            if flags & 0x0004:  # Average speed present
                offset += 2
            
            if flags & 0x0010:  # Instantaneous power present
                power = int.from_bytes(data[offset:offset+2], byteorder='little')
                offset += 2
                self.current_values["power"] = power
                if self.data_callback:
                    self.data_callback("power", power, timestamp)
                if "power" not in self.available_metrics:
                    self.available_metrics.append("power")
                    if self.debug_mode:
                        self.add_debug_message(f"Added power metric: {power} W")
            
            if flags & 0x0020:  # Average power present
                offset += 2
            
            if flags & 0x0040:  # Expended energy present
                offset += 3
            
            if flags & 0x0080:  # Heart rate present
                offset += 1
            
            if flags & 0x0100:  # Metabolic equivalent present
                offset += 1
            
            if flags & 0x0200:  # Elapsed time present
                offset += 2
            
            if flags & 0x0400:  # Remaining time present
                offset += 2
            
            if flags & 0x0800:  # Instantaneous cadence present
                raw_cadence = int.from_bytes(data[offset:offset+2], byteorder='little') 
                cadence = raw_cadence // 2  # Convert from 1/2 RPM to RPM
                self.current_values["cadence"] = cadence
                if self.data_callback:
                    self.data_callback("cadence", cadence, timestamp)
                if "cadence" not in self.available_metrics:
                    self.available_metrics.append("cadence")
                    if self.debug_mode:
                        self.add_debug_message(f"Added cadence metric: {cadence} RPM")
                
        except Exception as e:
            if self.debug_mode:
                self.add_debug_message(f"Error parsing bike data: {e}")
    
    def add_debug_message(self, message: str):
        """Add a debug message to the log."""
        self.debug_messages.append(message)
        # Keep only last 100 messages
        if len(self.debug_messages) > 100:
            self.debug_messages.pop(0)
        
        # Print debug message immediately if in debug mode
        if self.debug_mode:
            console.print(f"[dim]Trainer: {message}[/dim]")
    
    def get_available_metrics(self) -> List[str]:
        """Return list of available metrics from this device."""
        if self.debug_mode:
            self.add_debug_message(f"Available metrics: {self.available_metrics}")
        return self.available_metrics
    
    def get_current_values(self) -> Dict[str, Any]:
        """Return dictionary of current values."""
        return self.current_values
    
    async def connect(self, debug: bool = False):
        """Connect to the trainer device."""
        self.debug_mode = debug
        self.device = await self.find_device()
        if not self.device:
            return False
        
        console.print(f"[green]Connecting to trainer {self.device.name}...[/green]")
        
        try:
            self.client = BleakClient(self.device)
            await self.client.connect()
            
            if debug:
                services = await self.client.get_services()
                console.print("\n[yellow]Available Services:[/yellow]")
                for service in services:
                    console.print(f"[dim]Service:[/dim] {service.uuid}")
                    for char in service.characteristics:
                        console.print(f"  [dim]Characteristic:[/dim] {char.uuid}")
                        self.add_debug_message(f"Found characteristic: {char.uuid}")
            
            # Try to enable notifications for Indoor Bike Data
            indoor_bike_data_success = False
            try:
                await self.client.start_notify(
                    FITNESS_MACHINE_INDOOR_BIKE_DATA,
                    self.handle_indoor_bike_data
                )
                indoor_bike_data_success = True
                if debug:
                    self.add_debug_message("Enabled Indoor Bike Data notifications")
            except Exception as e:
                if debug:
                    self.add_debug_message(f"Error enabling Indoor Bike Data notifications: {e}")
            
            # Try UART as a fallback
            uart_success = False
            if not indoor_bike_data_success:
                try:
                    await self.client.start_notify(UART_RX, self.handle_indoor_bike_data)
                    uart_success = True
                    if debug:
                        self.add_debug_message("Enabled UART notifications")
                except Exception as e:
                    if debug:
                        self.add_debug_message(f"Error enabling UART notifications: {e}")
            
            # Check if either notification method was successful
            if not indoor_bike_data_success and not uart_success:
                if debug:
                    self.add_debug_message("Failed to enable any notifications")
                return False
            
            # Try to send control point commands aggressively to request data
            try:
                # Standard FTMS command to request control
                control_command = bytearray([0x00])  # Request Control
                await self.client.write_gatt_char(FITNESS_MACHINE_CONTROL_POINT, control_command)
                if debug:
                    self.add_debug_message("Sent Request Control command")
                
                # Wait a bit before sending additional commands
                await asyncio.sleep(0.5)
                
                # Send command to start the trainer
                start_command = bytearray([0x07, 0x01])  # Start or Resume
                try:
                    await self.client.write_gatt_char(FITNESS_MACHINE_CONTROL_POINT, start_command)
                    if debug:
                        self.add_debug_message("Sent Start command")
                except Exception as e:
                    if debug:
                        self.add_debug_message(f"Error sending Start command: {e}")
                
                # Also send Reset command
                await asyncio.sleep(0.5)
                reset_command = bytearray([0x01])  # Reset
                try:
                    await self.client.write_gatt_char(FITNESS_MACHINE_CONTROL_POINT, reset_command)
                    if debug:
                        self.add_debug_message("Sent Reset command")
                except Exception as e:
                    if debug:
                        self.add_debug_message(f"Error sending Reset command: {e}")
                
            except Exception as e:
                if debug:
                    self.add_debug_message(f"Could not send control commands: {e}")
            
            # Additionally, try to read the Indoor Bike Data characteristic directly
            try:
                data = await self.client.read_gatt_char(FITNESS_MACHINE_INDOOR_BIKE_DATA)
                self.handle_indoor_bike_data(None, data)
                if debug:
                    self.add_debug_message("Successfully read Indoor Bike Data")
            except Exception as e:
                if debug:
                    self.add_debug_message(f"Error reading Indoor Bike Data: {e}")
            
            console.print("[green]Successfully connected to trainer![/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error connecting to trainer: {e}[/red]")
            return False
    
    async def disconnect(self):
        """Disconnect from the trainer device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            console.print("[yellow]Disconnected from trainer[/yellow]") 