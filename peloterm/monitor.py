"""Real-time cycling metrics monitor and visualizer."""

import asyncio
import plotext as plt
from bleak import BleakClient, BleakScanner
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from datetime import datetime
from typing import Optional, Dict
from collections import deque

# BLE Service UUIDs
HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"
CYCLING_POWER_SERVICE = "00001818-0000-1000-8000-00805f9b34fb"
CYCLING_POWER_MEASUREMENT = "00002a63-0000-1000-8000-00805f9b34fb"
CYCLING_SPEED_CADENCE = "00001816-0000-1000-8000-00805f9b34fb"
CSC_MEASUREMENT = "00002a5b-0000-1000-8000-00805f9b34fb"

console = Console()

class MetricsMonitor:
    def __init__(self, window_size: int = 60):
        """Initialize the metrics monitor."""
        self.window_size = window_size
        self.timestamps = deque(maxlen=window_size)
        self.heart_rate = deque(maxlen=window_size)
        self.power = deque(maxlen=window_size)
        self.cadence = deque(maxlen=window_size)
        self.speed = deque(maxlen=window_size)
        
        # Current values
        self.current = {
            "heart_rate": 0,
            "power": 0,
            "cadence": 0,
            "speed": 0
        }
    
    def update_metric(self, metric: str, value: float):
        """Update a specific metric."""
        self.current[metric] = value
        getattr(self, metric).append(value)
        if len(self.timestamps) < len(getattr(self, metric)):
            self.timestamps.append(datetime.now())
    
    def generate_plot(self) -> str:
        """Generate a plot of all metrics."""
        plt.clf()
        plt.theme("dark")
        
        # Convert timestamps to seconds ago
        now = datetime.now()
        times = [(now - ts).total_seconds() for ts in self.timestamps]
        
        # Plot each metric
        if self.heart_rate:
            plt.plot(times, list(self.heart_rate), label="Heart Rate", color="red")
        if self.power:
            plt.plot(times, list(self.power), label="Power", color="yellow")
        if self.cadence:
            plt.plot(times, list(self.cadence), label="Cadence", color="cyan")
        if self.speed:
            plt.plot(times, list(self.speed), label="Speed", color="green")
        
        plt.title("Cycling Metrics")
        plt.xlabel("Seconds Ago")
        plt.ylabel("Value")
        plt.grid(True)
        
        return plt.build()

async def find_device(device_name: Optional[str] = None):
    """Find a specific device or any compatible device."""
    devices = await BleakScanner.discover()
    
    for device in devices:
        if device_name and device.name and device_name.lower() in device.name.lower():
            return device
        elif not device_name and device.metadata.get("uuids"):
            uuids = [str(uuid).lower() for uuid in device.metadata["uuids"]]
            if any(service.lower() in uuids for service in 
                  [HEART_RATE_SERVICE, CYCLING_POWER_SERVICE, CYCLING_SPEED_CADENCE]):
                return device
    
    return None

def handle_heart_rate(monitor: MetricsMonitor, data: bytearray):
    """Handle incoming heart rate data."""
    heart_rate = data[1]
    monitor.update_metric("heart_rate", heart_rate)

def handle_power(monitor: MetricsMonitor, data: bytearray):
    """Handle incoming power data."""
    power = int.from_bytes(data[2:4], byteorder="little")
    monitor.update_metric("power", power)

def handle_speed_cadence(monitor: MetricsMonitor, data: bytearray):
    """Handle incoming speed and cadence data."""
    flags = data[0]
    if flags & 0x1:  # Speed data present
        speed = int.from_bytes(data[1:5], byteorder="little") * 0.001  # Convert to km/h
        monitor.update_metric("speed", speed)
    if flags & 0x2:  # Cadence data present
        cadence = int.from_bytes(data[5:7], byteorder="little")
        monitor.update_metric("cadence", cadence)

async def monitor_metrics(client: BleakClient, monitor: MetricsMonitor):
    """Set up notifications for all available services."""
    services = await client.get_services()
    
    for service in services:
        if service.uuid.lower() == HEART_RATE_SERVICE.lower():
            await client.start_notify(
                HEART_RATE_MEASUREMENT,
                lambda _, data: handle_heart_rate(monitor, data)
            )
        elif service.uuid.lower() == CYCLING_POWER_SERVICE.lower():
            await client.start_notify(
                CYCLING_POWER_MEASUREMENT,
                lambda _, data: handle_power(monitor, data)
            )
        elif service.uuid.lower() == CYCLING_SPEED_CADENCE.lower():
            await client.start_notify(
                CSC_MEASUREMENT,
                lambda _, data: handle_speed_cadence(monitor, data)
            )

def create_layout(monitor: MetricsMonitor) -> Layout:
    """Create the display layout."""
    layout = Layout()
    layout.split_column(
        Layout(monitor.generate_plot(), name="plot"),
        Layout(f"""Current Values:
HR: {monitor.current['heart_rate']} bpm
Power: {monitor.current['power']} W
Cadence: {monitor.current['cadence']} rpm
Speed: {monitor.current['speed']:.1f} km/h""", name="stats")
    )
    return layout

async def run_monitor(device_name: Optional[str], refresh_rate: int):
    """Run the monitoring loop."""
    device = await find_device(device_name)
    if not device:
        console.print("[red]No compatible device found[/red]")
        return
    
    console.print(f"[green]Found device: {device.name}[/green]")
    monitor = MetricsMonitor()
    
    async with BleakClient(device) as client:
        await monitor_metrics(client, monitor)
        
        with Live(create_layout(monitor), refresh_per_second=1/refresh_rate) as live:
            while True:
                await asyncio.sleep(refresh_rate)
                live.update(create_layout(monitor))

def start_monitoring(refresh_rate: int = 1, device_name: Optional[str] = None):
    """Start the monitoring process."""
    try:
        asyncio.run(run_monitor(device_name, refresh_rate))
    except Exception as e:
        console.print(f"[red]Error during monitoring: {e}[/red]") 