"""Controller for managing multiple devices and their displays."""

import asyncio
from datetime import datetime
from rich.console import Console
from typing import List, Optional, Dict, Any, Callable
from .display import MetricMonitor, MultiMetricDisplay
from .devices.heart_rate import HeartRateDevice
from .devices.trainer import TrainerDevice

console = Console()

# Metric display configuration
METRIC_CONFIG = {
    "heart_rate": {"name": "Heart Rate", "color": "red", "unit": "BPM"},
    "power": {"name": "Power", "color": "yellow", "unit": "W"},
    "speed": {"name": "Speed", "color": "blue", "unit": "km/h"},
    "cadence": {"name": "Cadence", "color": "green", "unit": "RPM"}
}

class DeviceController:
    """Controller for managing multiple devices and their displays."""
    
    def __init__(self):
        """Initialize the device controller."""
        self.heart_rate_device = None
        self.trainer_device = None
        self.multi_display = None
        self.metric_monitors = {}  # Dictionary of metric name to monitor
        self.connected_devices = []
        self.available_metrics = []
        self.running = False
        self.debug_mode = False
    
    def handle_metric_data(self, metric_name: str, value: Any, timestamp: float):
        """Handle incoming metric data from any device.
        
        Args:
            metric_name: Name of the metric (e.g. "heart_rate", "power", etc.)
            value: The current value of the metric
            timestamp: The timestamp when the value was recorded
        """
        if self.debug_mode:
            console.print(f"[dim]Received metric: {metric_name} = {value}[/dim]")
            
        # Create monitor if it doesn't exist
        if metric_name not in self.metric_monitors and metric_name in METRIC_CONFIG:
            config = METRIC_CONFIG[metric_name]
            self.metric_monitors[metric_name] = MetricMonitor(
                name=config["name"], 
                color=config["color"], 
                unit=config["unit"]
            )
            
            # If we already have a display, update its monitors
            if self.multi_display:
                monitors = list(self.metric_monitors.values())
                self.multi_display.monitors = monitors
        
        # Update the monitor with the new value
        if metric_name in self.metric_monitors:
            monitor = self.metric_monitors[metric_name]
            monitor.update_value(value)
            
            # Update display if running
            if self.multi_display and self.multi_display.live:
                self.multi_display.live.update(self.multi_display.update_display())
    
    async def auto_discover_connect(self, debug: bool = False) -> bool:
        """Automatically discover and connect to all available devices."""
        self.debug_mode = debug
        connected = False
        
        # Try to connect to a heart rate monitor
        self.heart_rate_device = HeartRateDevice(
            data_callback=self.handle_metric_data
        )
        if await self.heart_rate_device.connect():
            self.connected_devices.append(self.heart_rate_device)
            connected = True
        else:
            self.heart_rate_device = None
        
        # Try to connect to a trainer
        self.trainer_device = TrainerDevice(
            data_callback=self.handle_metric_data
        )
        if await self.trainer_device.connect(debug=debug):
            self.connected_devices.append(self.trainer_device)
            connected = True
        else:
            self.trainer_device = None
        
        # If no devices connected, return False
        if not connected:
            console.print("[yellow]No devices found or connected.[/yellow]")
            return False
            
        # Wait for devices to start reporting metrics (up to 5 seconds)
        if debug:
            console.print("[blue]Waiting for devices to report metrics...[/blue]")
            
        wait_time = 5  # seconds
        check_interval = 0.5  # seconds
        attempts = int(wait_time / check_interval)
        
        for i in range(attempts):
            # Check all connected devices for metrics
            for device in self.connected_devices:
                device_metrics = device.get_available_metrics()
                if device_metrics:
                    self.available_metrics.extend([m for m in device_metrics if m not in self.available_metrics])
                    
            # If we found metrics, we can break early
            if self.available_metrics:
                if debug:
                    console.print(f"[green]Found metrics: {', '.join(self.available_metrics)}[/green]")
                break
                
            # Otherwise wait and try again
            await asyncio.sleep(check_interval)
            if debug and i % 2 == 0:  # Show progress every second
                console.print(f"[dim]Still waiting for metrics... ({i+1}/{attempts})[/dim]")
        
        # Initialize monitors for all available metrics
        if self.available_metrics:
            for metric in self.available_metrics:
                if metric in METRIC_CONFIG:
                    config = METRIC_CONFIG[metric]
                    self.metric_monitors[metric] = MetricMonitor(
                        name=config["name"],
                        color=config["color"],
                        unit=config["unit"]
                    )
            
            # Set up the display with all metric monitors
            self.multi_display = MultiMetricDisplay(list(self.metric_monitors.values()))
            return True
        else:
            console.print("[yellow]No metrics available from connected devices.[/yellow]")
            if debug:
                # Print device status
                for device in self.connected_devices:
                    device_type = "Heart Rate Monitor" if isinstance(device, HeartRateDevice) else "Trainer"
                    console.print(f"[yellow]Connected {device_type} is not reporting any metrics.[/yellow]")
                    if isinstance(device, TrainerDevice) and hasattr(device, 'debug_messages') and device.debug_messages:
                        console.print("[yellow]Debug messages from trainer:[/yellow]")
                        for msg in device.debug_messages[-5:]:
                            console.print(f"[dim]{msg}[/dim]")
            return False
    
    async def run(self, refresh_rate: int = 1):
        """Run the device monitoring loop."""
        if not self.connected_devices:
            console.print("[yellow]No devices connected. Cannot start monitoring.[/yellow]")
            return
        
        # Start the live display
        self.running = True
        self.multi_display.start_display()
        
        try:
            console.print(f"[green]Monitoring started with {len(self.connected_devices)} device(s) and {len(self.metric_monitors)} metric(s).[/green]")
            
            # Main loop - keep checking if we receive new metrics
            while self.running:
                # Check all connected devices for new metrics
                for device in self.connected_devices:
                    # Add any new metrics that have become available
                    new_metrics = [m for m in device.get_available_metrics() 
                                   if m not in self.available_metrics]
                    
                    if new_metrics:
                        self.available_metrics.extend(new_metrics)
                        for metric in new_metrics:
                            if metric in METRIC_CONFIG:
                                config = METRIC_CONFIG[metric]
                                self.metric_monitors[metric] = MetricMonitor(
                                    name=config["name"],
                                    color=config["color"],
                                    unit=config["unit"]
                                )
                        
                        # Update display with new monitors
                        if self.multi_display:
                            self.multi_display.monitors = list(self.metric_monitors.values())
                
                await asyncio.sleep(refresh_rate)
        finally:
            # Stop display and disconnect devices
            if self.multi_display:
                self.multi_display.stop_display()
            await self.disconnect_devices()
    
    async def disconnect_devices(self):
        """Disconnect from all connected devices."""
        self.running = False
        
        tasks = []
        if self.heart_rate_device:
            tasks.append(self.heart_rate_device.disconnect())
        
        if self.trainer_device:
            tasks.append(self.trainer_device.disconnect())
        
        if tasks:
            await asyncio.gather(*tasks)

def start_auto_monitoring(refresh_rate: int = 1, debug: bool = False):
    """Start automatic device discovery and monitoring process."""
    controller = DeviceController()
    
    try:
        # Setup event loop
        loop = asyncio.get_event_loop()
        
        # Auto-discover and connect to devices
        if not loop.run_until_complete(controller.auto_discover_connect(debug=debug)):
            console.print("[yellow]No viable devices found to monitor.[/yellow]")
            return
        
        # Run the monitoring loop
        loop.run_until_complete(controller.run(refresh_rate=refresh_rate))
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during monitoring: {e}[/red]")
        if debug:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
    finally:
        try:
            # Ensure devices are disconnected
            loop.run_until_complete(controller.disconnect_devices())
        except Exception:
            pass 