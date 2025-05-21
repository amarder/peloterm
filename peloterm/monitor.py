"""Real-time heart rate monitor and visualizer."""

import asyncio
import plotext as plt
from bleak import BleakClient, BleakScanner
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
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
        # Use lists instead of deques with maxlen to store all data
        self.timestamps = []
        self.heart_rate = []
        self.current_hr = 0
        self.live = None
        self.initial_capacity = window_size
        
        # Configure plotext settings with dark theme
        plt.theme('dark')
    
    def update_plot(self):
        """Update the plot with current heart rate data."""
        if len(self.heart_rate) <= 1:
            return Panel("Collecting data...", title="Heart Rate Monitor", border_style="bright_red")
            
        # Convert timestamps to seconds ago
        now = datetime.now()
        times = [(now - ts).total_seconds() for ts in self.timestamps]
        
        # Clear previous plot
        plt.clf()
        
        # Get terminal dimensions and use full width minus small margin
        width, height = console.size
        # Adjust width based on terminal size to ensure good proportions
        plot_width = width - 6  # Leave minimal margin for panel borders
        plot_height = min(height - 8, 15)
        
        # Set plot size
        plt.plotsize(plot_width, plot_height)
        
        # Apply dark theme for this plot
        plt.theme('dark')
        
        # Plot the data with high-contrast color
        plt.plot(times, self.heart_rate, marker="dot", color="red")
        
        # Set plot attributes with colors that work well in dark mode
        duration_minutes = max(times) // 60
        if duration_minutes >= 1:
            plt.title(f"Heart Rate - {int(duration_minutes)}m {int(max(times) % 60)}s of data")
        else:
            plt.title(f"Heart Rate - {int(max(times))}s of data")
            
        plt.xlabel("Seconds ago")
        plt.ylabel("BPM")
        plt.grid(False)  # Enable grid with default color
        
        # Better x-axis ticks that spread across the full width
        # Adjust number of ticks based on width for better appearance
        num_ticks = min(10, max(6, plot_width // 15))
        max_time = max(times)
        tick_points = [max_time * i / (num_ticks - 1) for i in range(num_ticks)]
        plt.xticks(tick_points)
        
        # Set axis limits with some padding
        plt.xlim(max_time, 0)  # Reverse x-axis to show newest data on right
        
        if len(self.heart_rate) > 0:
            min_hr = min(self.heart_rate)
            max_hr = max(self.heart_rate)
            # Add padding to y-axis and make sure there's a reasonable range
            y_padding = max(5, (max_hr - min_hr) * 0.1)
            plt.ylim(min_hr - y_padding, max_hr + y_padding)
        else:
            plt.ylim(60, 180)  # Default range if no data
        
        # Get the plot as a string and create a Rich Text object
        plot_str = plt.build()
        plot_text = Text.from_ansi(plot_str)
        
        # Create panel with the plot using colors that complement dark mode
        return Panel(
            plot_text,
            title=f"[bold bright_red]Heart Rate Monitor[/bold bright_red] - Current: [bold bright_yellow]{self.current_hr}[/bold bright_yellow] BPM",
            border_style="bright_red",
            padding=(0, 1)
        )
    
    def update_heart_rate(self, value: int):
        """Update heart rate value and plot."""
        self.current_hr = value
        self.heart_rate.append(value)
        self.timestamps.append(datetime.now())
        
        # If using Live display, update it
        if self.live:
            self.live.update(self.update_plot())
    
    def start_display(self):
        """Start the live display."""
        self.live = Live(self.update_plot(), refresh_per_second=4, console=console)
        self.live.start()
    
    def stop_display(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()

def handle_heart_rate(monitor: HeartRateMonitor, data: bytearray):
    """Handle incoming heart rate data."""
    flags = data[0]
    if flags & 0x1:  # If first bit is set, value is uint16
        heart_rate = int.from_bytes(data[1:3], byteorder='little')
    else:  # Value is uint8
        heart_rate = data[1]
    monitor.update_heart_rate(heart_rate)

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

async def run_monitor(device_name: Optional[str], refresh_rate: int):
    """Run the heart rate monitoring loop."""
    device = await find_heart_rate_monitor(device_name)
    if not device:
        return
    
    console.print(f"[green]Connecting to {device.name}...[/green]")
    monitor = HeartRateMonitor()
    
    try:
        async with BleakClient(device) as client:
            # Start the rich live display
            monitor.start_display()
            
            await client.start_notify(
                HEART_RATE_MEASUREMENT,
                lambda _, data: handle_heart_rate(monitor, data)
            )
            
            console.print("[green]Successfully connected! Monitoring heart rate...[/green]")
            while True:
                await asyncio.sleep(refresh_rate)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_display()

def start_monitoring(refresh_rate: int = 1, device_name: Optional[str] = None):
    """Start the heart rate monitoring process."""
    try:
        asyncio.run(run_monitor(device_name, refresh_rate))
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during monitoring: {e}[/red]") 