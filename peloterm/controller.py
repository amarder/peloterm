"""Controller for managing multiple devices and their displays."""

import asyncio
from datetime import datetime
from rich.console import Console
from typing import List, Optional, Dict, Any, Callable
from .display import MetricMonitor, MultiMetricDisplay
from .devices.heart_rate import HeartRateDevice
from .devices.trainer import TrainerDevice
from .devices.speed_cadence import SpeedCadenceDevice
from .scanner import discover_devices
from .config import PelotermConfig, METRIC_DISPLAY_NAMES
from rich.panel import Panel
from rich.status import Status

console = Console()

class DeviceController:
    """Controller for managing multiple devices and their displays."""
    
    def __init__(self, config: PelotermConfig, show_display: bool = True):
        """Initialize the device controller.
        
        Args:
            config: Configuration specifying devices and metrics
            show_display: Whether to show the live graphs display
        """
        self.config = config
        self.heart_rate_device = None
        self.trainer_device = None
        self.speed_cadence_device = None
        self.multi_display = None
        self.metric_monitors = {}  # Dictionary of metric name to monitor
        self.connected_devices = []
        self.available_metrics = []
        self.running = False
        self.debug_mode = False
        self.show_display = show_display
        
        # Create metric monitors from configuration
        for metric_config in config.display:
            self.metric_monitors[metric_config.metric] = MetricMonitor(
                name=metric_config.name,
                color=metric_config.color,
                unit=metric_config.unit
            )
    
    def handle_metric_data(self, metric_name: str, value: Any, timestamp: float):
        """Handle incoming metric data from any device.
        
        Args:
            metric_name: Name of the metric (e.g. "heart_rate", "power", etc.)
            value: The current value of the metric
            timestamp: The timestamp when the value was recorded
        """
        if self.debug_mode:
            console.print(f"[dim]Received metric: {metric_name} = {value}[/dim]")
        
        # Update the monitor if it exists for this metric
        if metric_name in self.metric_monitors:
            monitor = self.metric_monitors[metric_name]
            monitor.update_value(value)
            
            # Update display if running
            if self.multi_display and self.multi_display.live:
                self.multi_display.live.update(self.multi_display.update_display())
    
    async def connect_configured_devices(self, debug: bool = False) -> bool:
        """Connect to devices specified in the configuration."""
        connected = False
        self.debug_mode = debug
        
        # Create a status spinner for connection process
        with console.status("[bold yellow]Connecting to devices...[/bold yellow]", spinner="dots") as status:
            # Try to connect to each configured device
            for device_config in self.config.devices:
                # Connect based on service type
                if "Heart Rate" in device_config.services:
                    if not self.heart_rate_device:
                        console.log(f"[dim]Connecting to heart rate monitor: {device_config.name}...[/dim]")
                        self.heart_rate_device = HeartRateDevice(
                            device_name=device_config.name,
                            data_callback=self.handle_metric_data
                        )
                        if await self.heart_rate_device.connect(address=device_config.address, debug=debug):
                            self.connected_devices.append(self.heart_rate_device)
                            connected = True
                            console.log(f"[green]✓ Connected to {device_config.name}[/green]")
                        else:
                            console.log(f"[red]✗ Failed to connect to {device_config.name}[/red]")
                
                elif "Power" in device_config.services:
                    if not self.trainer_device:
                        console.log(f"[dim]Connecting to trainer: {device_config.name}...[/dim]")
                        # Find all metrics that should come from this trainer
                        trainer_metrics = set()  # Use a set to avoid duplicates
                        for metric in self.config.display:
                            if metric.device == device_config.name:
                                trainer_metrics.add(metric.metric)  # Use the internal metric name
                        
                        trainer_metrics = list(trainer_metrics)  # Convert back to list
                        if debug:
                            console.log(f"[dim]Configured metrics for trainer: {trainer_metrics}[/dim]")
                        
                        self.trainer_device = TrainerDevice(
                            device_name=device_config.name,
                            data_callback=self.handle_metric_data,
                            metrics=trainer_metrics  # Pass the list of metrics to monitor
                        )
                        if await self.trainer_device.connect(address=device_config.address, debug=debug):
                            self.connected_devices.append(self.trainer_device)
                            connected = True
                            console.log(f"[green]✓ Connected to {device_config.name}[/green]")
                        else:
                            console.log(f"[red]✗ Failed to connect to {device_config.name}[/red]")
                
                elif any(s in ["Speed/Cadence", "Speed", "Cadence"] for s in device_config.services):
                    if not self.speed_cadence_device:
                        console.log(f"[dim]Connecting to speed/cadence sensor: {device_config.name}...[/dim]")
                        self.speed_cadence_device = SpeedCadenceDevice(
                            device_name=device_config.name,
                            data_callback=self.handle_metric_data
                        )
                        if await self.speed_cadence_device.connect(address=device_config.address, debug=debug):
                            self.connected_devices.append(self.speed_cadence_device)
                            connected = True
                            console.log(f"[green]✓ Connected to {device_config.name}[/green]")
                        else:
                            console.log(f"[red]✗ Failed to connect to {device_config.name}[/red]")
            
            if connected:
                console.log("[green]✓ Device connections established[/green]")
            else:
                console.log("[red]✗ No devices were successfully connected[/red]")
        
        return connected
    
    async def run(self, refresh_rate: int = 1):
        """Run the controller, updating displays at the specified rate."""
        if not self.connected_devices:
            console.print("[yellow]No devices connected. Nothing to monitor.[/yellow]")
            return
        
        self.running = True
        
        try:
            # Initialize display if needed
            if self.show_display:
                monitors = list(self.metric_monitors.values())
                self.multi_display = MultiMetricDisplay(monitors)
                self.multi_display.start_display()
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(refresh_rate)
                
        except asyncio.CancelledError:
            self.running = False
        finally:
            await self.disconnect_devices()
    
    async def disconnect_devices(self):
        """Disconnect from all connected devices."""
        self.running = False
        
        if self.multi_display:
            self.multi_display.stop_display()
        
        for device in self.connected_devices:
            await device.disconnect()
        
        self.connected_devices = []

def start_monitoring_with_config(
    config: PelotermConfig,
    refresh_rate: int = 1,
    debug: bool = False
):
    """Start monitoring using the provided configuration."""
    try:
        controller = DeviceController(config, show_display=True)
        
        # Run everything in an async event loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(controller.connect_configured_devices(debug=debug))
        loop.run_until_complete(controller.run(refresh_rate=refresh_rate))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise 