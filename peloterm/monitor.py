"""Real-time heart rate monitor and visualizer."""

import asyncio
import plotext as plt
from bleak import BleakClient, BleakScanner
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from datetime import datetime
from typing import Optional
from collections import deque

# BLE Service UUIDs
HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"

console = Console()

class HeartRateMonitor:
    def __init__(self, window_size: int = 60):
        """Initialize the heart rate monitor."""
        self.window_size = window_size
        self.timestamps = deque(maxlen=window_size)
        self.heart_rate = deque(maxlen=window_size)
        self.current_hr = 0
    
    def update_heart_rate(self, value: int):
        """Update heart rate value."""
        self.current_hr = value
        self.heart_rate.append(value)
        self.timestamps.append(datetime.now())
    
    def generate_plot(self) -> str:
        """Generate a plot of heart rate over time."""
        plt.clf()
        plt.theme("dark")
        
        if self.heart_rate:
            # Convert timestamps to seconds ago
            now = datetime.now()
            times = [(now - ts).total_seconds() for ts in self.timestamps]
            
            plt.plot(times, list(self.heart_rate), label="Heart Rate", color="red")
            plt.title("Heart Rate Monitor")
            plt.xlabel("Seconds Ago")
            plt.ylabel("BPM")
            plt.grid(True)
        
        return plt.build()

async def find_heart_rate_monitor(device_name: Optional[str] = None):
    """Find a heart rate monitor device."""
    console.print("[blue]Searching for heart rate monitors...[/blue]")
    
    discovered = await BleakScanner.discover(return_adv=True)
    
    for device, adv_data in discovered.values():
        if device_name:
            if device.name and device_name.lower() in device.name.lower():
                console.print(f"[green]✓ Matched requested device: {device.name}[/green]")
                return device
            continue
        
        if adv_data.service_uuids:
            uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
            if HEART_RATE_SERVICE.lower() in uuids:
                console.print(f"[green]✓ Found heart rate monitor: {device.name or 'Unknown'}[/green]")
                return device
    
    console.print("[yellow]No heart rate monitor found. Make sure your device is awake and nearby.[/yellow]")
    return None

def handle_heart_rate(monitor: HeartRateMonitor, data: bytearray):
    """Handle incoming heart rate data."""
    flags = data[0]
    if flags & 0x1:  # If first bit is set, value is uint16
        heart_rate = int.from_bytes(data[1:3], byteorder='little')
    else:  # Value is uint8
        heart_rate = data[1]
    monitor.update_heart_rate(heart_rate)

def create_layout(monitor: HeartRateMonitor) -> Layout:
    """Create the display layout."""
    layout = Layout()
    layout.split_column(
        Layout(monitor.generate_plot(), name="plot"),
        Layout(f"Current Heart Rate: {monitor.current_hr} BPM", name="stats")
    )
    return layout

async def run_monitor(device_name: Optional[str], refresh_rate: int):
    """Run the heart rate monitoring loop."""
    device = await find_heart_rate_monitor(device_name)
    if not device:
        return
    
    console.print(f"[green]Connecting to {device.name}...[/green]")
    monitor = HeartRateMonitor()
    
    async with BleakClient(device) as client:
        await client.start_notify(
            HEART_RATE_MEASUREMENT,
            lambda _, data: handle_heart_rate(monitor, data)
        )
        
        console.print("[green]Successfully connected! Monitoring heart rate...[/green]")
        with Live(create_layout(monitor), refresh_per_second=1/refresh_rate) as live:
            while True:
                await asyncio.sleep(refresh_rate)
                live.update(create_layout(monitor))

def start_monitoring(refresh_rate: int = 1, device_name: Optional[str] = None):
    """Start the heart rate monitoring process."""
    try:
        asyncio.run(run_monitor(device_name, refresh_rate))
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during monitoring: {e}[/red]") 