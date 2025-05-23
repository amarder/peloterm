"""Smart trainer monitor and controller."""

import asyncio
from bleak import BleakClient, BleakScanner
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from datetime import datetime
from typing import Optional, List

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

class TrainerMonitor:
    def __init__(self, window_size: int = 60, debug: bool = False):
        """Initialize the trainer monitor."""
        self.timestamps = []
        self.power = []
        self.cadence = []
        self.current_power = 0
        self.current_cadence = 0
        self.live = None
        self.initial_capacity = window_size
        self.debug = debug
        self.debug_messages = []
        
    def update_display_content(self):
        """Update the display content for the trainer monitor."""
        power_text = f"Power: {self.current_power}W"
        cadence_text = f"Cadence: {self.current_cadence} RPM" if self.current_cadence else "Cadence: N/A"
        
        content = f"{power_text}\\n{cadence_text}"
        
        if self.debug:
            content += "\\n\\n[bold yellow]Debug Output:[/bold yellow]\\n" + "\\n".join(self.debug_messages[-10:])
            
        return Panel(
            content,
            title="Trainer Monitor",
            border_style="bright_blue"
        )

    def add_debug_message(self, message: str):
        """Add a debug message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.debug_messages.append(f"[dim]{timestamp}[/dim] {message}")
        # Keep only last 100 messages
        if len(self.debug_messages) > 100:
            self.debug_messages.pop(0)
        # Also print to console for immediate feedback
        console.print(f"[dim]{timestamp}[/dim] {message}")
    
    def update_metrics(self, power: Optional[int] = None, cadence: Optional[int] = None, raw_data: Optional[bytearray] = None):
        """Update trainer metrics."""
        timestamp = datetime.now()
        
        if power is not None:
            self.current_power = power
            self.power.append(power)
            self.timestamps.append(timestamp)
        
        if cadence is not None:
            self.current_cadence = cadence
            # Ensure cadence list is aligned with power list if power is also updated
            if power is None and self.power: # if only cadence is updated
                 # This assumes cadence updates arrive with power updates or independently.
                 # If cadence updates are independent and less frequent, this might need adjustment.
                 pass # Cadence list will grow, may not align with timestamps if only cadence is given
            self.cadence.append(cadence)
        
        if self.debug and raw_data is not None:
            hex_data = " ".join([f"{b:02x}" for b in raw_data])
            self.add_debug_message(f"Raw: {hex_data} | Power: {power}W" + (f" | Cadence: {cadence} RPM" if cadence else ""))
        
        if self.live:
            self.live.update(self.update_display_content())
    
    def start_display(self):
        """Start the live display."""
        self.live = Live(self.update_display_content(), refresh_per_second=4, console=console)
        self.live.start()
    
    def stop_display(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()

def handle_indoor_bike_data(monitor: TrainerMonitor, data: bytearray):
    """Handle incoming indoor bike data."""
    try:
        if monitor.debug:
            hex_data = " ".join([f"{b:02x}" for b in data])
            monitor.add_debug_message(f"Received bike data: {hex_data}")
        
        # Parse according to FTMS Indoor Bike Data characteristic format
        flags = int.from_bytes(data[0:2], byteorder='little')
        
        # Initialize values
        power = None
        cadence = None
        
        # Parse data based on flags
        offset = 2  # Start after flags
        
        # Check flags for available data
        if flags & 0x0002:  # Speed present
            offset += 2
        if flags & 0x0004:  # Average speed present
            offset += 2
        if flags & 0x0010:  # Instantaneous power present
            power = int.from_bytes(data[offset:offset+2], byteorder='little')
            offset += 2
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
            cadence = int.from_bytes(data[offset:offset+2], byteorder='little') // 2  # Convert from 1/2 RPM to RPM
        
        monitor.update_metrics(power=power, cadence=cadence, raw_data=data)
            
    except Exception as e:
        if monitor.debug:
            monitor.add_debug_message(f"[red]Error parsing bike data: {e}[/red]")

async def find_trainer(device_name: Optional[str] = None) -> Optional[BleakClient]:
    """Find a smart trainer device."""
    console.print("[blue]Searching for smart trainers...[/blue]")
    
    discovered = await BleakScanner.discover(return_adv=True)
    
    for device, adv_data in discovered.values():
        if device_name:
            if device.name and device_name.lower() in device.name.lower():
                console.print(f"[green]✓ Matched requested device: {device.name}[/green]")
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

async def run_trainer_monitor(device_name: Optional[str], refresh_rate: int, debug: bool = False):
    """Run the trainer monitoring loop."""
    device = await find_trainer(device_name)
    if not device:
        return
    
    console.print(f"[green]Connecting to {device.name}...[/green]")
    monitor = TrainerMonitor(debug=debug)
    
    try:
        async with BleakClient(device) as client:
            if debug:
                services = await client.get_services()
                console.print("\n[yellow]Available Services:[/yellow]")
                for service in services:
                    console.print(f"[dim]Service:[/dim] {service.uuid}")
                    for char in service.characteristics:
                        console.print(f"  [dim]Characteristic:[/dim] {char.uuid}")
                        for desc in char.descriptors:
                            console.print(f"    [dim]Descriptor:[/dim] {desc.uuid}")
                
                monitor.add_debug_message("Connected to device")
                monitor.add_debug_message(f"Device name: {device.name}")
                monitor.add_debug_message(f"Device address: {device.address}")
            
            # Start the rich live display
            monitor.start_display()
            
            # Try to read the Fitness Machine Feature characteristic
            try:
                feature_data = await client.read_gatt_char(FITNESS_MACHINE_FEATURE)
                if debug:
                    hex_data = " ".join([f"{b:02x}" for b in feature_data])
                    monitor.add_debug_message(f"Fitness Machine Features: {hex_data}")
            except Exception as e:
                if debug:
                    monitor.add_debug_message(f"[yellow]Could not read features: {e}[/yellow]")
            
            # Try to enable notifications for Indoor Bike Data
            try:
                await client.start_notify(
                    FITNESS_MACHINE_INDOOR_BIKE_DATA,
                    lambda _, data: handle_indoor_bike_data(monitor, data)
                )
                if debug:
                    monitor.add_debug_message("Enabled Indoor Bike Data notifications")
            except Exception as e:
                if debug:
                    monitor.add_debug_message(f"[red]Error enabling Indoor Bike Data notifications: {e}[/red]")
                    monitor.add_debug_message("Trying UART notifications instead...")
                
                # Fall back to UART if Indoor Bike Data fails
                try:
                    await client.start_notify(UART_RX, lambda _, data: handle_indoor_bike_data(monitor, data))
                    if debug:
                        monitor.add_debug_message("Enabled UART notifications")
                except Exception as e:
                    if debug:
                        monitor.add_debug_message(f"[red]Error enabling UART notifications: {e}[/red]")
                    return
            
            # Try to enable control point notifications
            try:
                await client.start_notify(
                    FITNESS_MACHINE_CONTROL_POINT,
                    lambda _, data: monitor.add_debug_message(f"Control point notification: {' '.join([f'{b:02x}' for b in data])}")
                )
                if debug:
                    monitor.add_debug_message("Enabled Control Point notifications")
            except Exception as e:
                if debug:
                    monitor.add_debug_message(f"[yellow]Could not enable control point notifications: {e}[/yellow]")
            
            # Send control point command to request data
            try:
                # Standard FTMS command to start control
                control_command = bytearray([0x00])  # Request Control
                await client.write_gatt_char(FITNESS_MACHINE_CONTROL_POINT, control_command)
                if debug:
                    monitor.add_debug_message("Sent control point command")
            except Exception as e:
                if debug:
                    monitor.add_debug_message(f"[yellow]Could not send control command: {e}[/yellow]")
            
            console.print("[green]Successfully connected! Monitoring trainer metrics...[/green]")
            
            # Main loop
            while True:
                await asyncio.sleep(refresh_rate)
                if debug:
                    # Try to read current values directly
                    try:
                        data = await client.read_gatt_char(FITNESS_MACHINE_INDOOR_BIKE_DATA)
                        handle_indoor_bike_data(monitor, data)
                    except Exception as e:
                        monitor.add_debug_message("Waiting for data...")
    except Exception as e:
        if debug:
            monitor.add_debug_message(f"[red]Connection error: {e}[/red]")
    finally:
        monitor.stop_display()

def start_trainer_monitoring(refresh_rate: int = 1, device_name: Optional[str] = None, debug: bool = False):
    """Start the trainer monitoring process."""
    try:
        asyncio.run(run_trainer_monitor(device_name, refresh_rate, debug))
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during monitoring: {e}[/red]") 