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
from rich.panel import Panel

console = Console()

# Metric display configuration
METRIC_CONFIG = {
    "heart_rate": {"name": "Heart Rate", "color": "red", "unit": "BPM"},
    "power": {"name": "Power", "color": "red", "unit": "W"},
    "speed": {"name": "Speed", "color": "red", "unit": "km/h"},
    "cadence": {"name": "Cadence", "color": "red", "unit": "RPM"}
}

class DeviceController:
    """Controller for managing multiple devices and their displays."""
    
    def __init__(self, show_display: bool = True):
        """Initialize the device controller.
        
        Args:
            show_display: Whether to show the live graphs display
        """
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
    
    async def auto_discover_connect(
        self,
        debug: bool = False,
        device_types: Optional[List[str]] = None,
        metric_types: Optional[List[str]] = None,
        device_names: Optional[List[str]] = None
    ) -> bool:
        """Automatically discover and connect to devices based on filters."""
        console.print(Panel.fit("Starting Auto-Discovery and Monitoring", style="bold blue"))
        
        connected = False
        self.debug_mode = debug
        
        # If specific device names were requested, output for clarity
        if device_names:
            names_str = ", ".join(device_names)
            console.print(f"Will look for devices named: {names_str}")
        
        # First scan once to find devices
        console.print("Scanning for available devices...")
        devices = await discover_devices(timeout=5)  # Use a 5 second scan timeout
        
        if not devices:
            console.print("No compatible devices found in scan.")
            return False
            
        console.print(f"Found {len(devices)} device(s) in scan.")
        
        # Look for heart rate monitor in scan results
        if not device_types or "heart_rate" in device_types:
            heart_rate_device = next(
                (
                    device for device in devices 
                    if "Heart Rate" in device["services"] and
                    (not device_names or any(name.lower() in device["name"].lower() for name in device_names))
                ),
                None
            )
            if heart_rate_device:
                console.print(f"[blue]Found heart rate monitor: {heart_rate_device['name']}[/blue]")
                console.print(f"[blue]Attempting to connect to {heart_rate_device['name']}...[/blue]")
                
                self.heart_rate_device = HeartRateDevice(
                    device_name=heart_rate_device["name"],
                    data_callback=self.handle_metric_data
                )
                if await self.heart_rate_device.connect():
                    self.connected_devices.append(self.heart_rate_device)
                    connected = True
                    console.print(f"[green]✓ Connected to {heart_rate_device['name']}[/green]")
            elif debug:
                console.print("[dim]No heart rate monitor found in scan[/dim]")
        
        # Look for trainer in scan results
        if not device_types or "trainer" in device_types:
            trainer_device = next(
                (
                    device for device in devices 
                    if "Power" in device["services"] and
                    (not device_names or any(name.lower() in device["name"].lower() for name in device_names))
                ),
                None
            )
            if trainer_device:
                console.print(f"[blue]Found trainer: {trainer_device['name']}[/blue]")
                console.print(f"[blue]Attempting to connect to {trainer_device['name']}...[/blue]")
                
                self.trainer_device = TrainerDevice(
                    device_name=trainer_device["name"],
                    data_callback=self.handle_metric_data
                )
                if await self.trainer_device.connect():
                    self.connected_devices.append(self.trainer_device)
                    connected = True
                    console.print(f"[green]✓ Connected to {trainer_device['name']}[/green]")
            elif debug:
                console.print("[dim]No trainer found in scan[/dim]")
        
        # Look for speed/cadence sensor in scan results
        if not device_types or "speed_cadence" in device_types:
            speed_cadence_device = None
            
            # Debug device information
            if debug:
                console.print("[dim]Looking for speed/cadence devices...[/dim]")
                for device in devices:
                    console.print(f"[dim]Device: {device['name']} - Services: {device['services']}[/dim]")
                if device_names:
                    console.print(f"[dim]Looking for device names: {device_names}[/dim]")
            
            # First, try to find by exact name match if names were specified
            if device_names:
                for device in devices:
                    if any(name.lower() in device["name"].lower() for name in device_names):
                        speed_cadence_device = device
                        if debug:
                            console.print(f"[dim]Matched device by name: {device['name']}[/dim]")
                        break
            
            # If no match by name or no names specified, try service-based matching
            if not speed_cadence_device:
                for device in devices:
                    services = device["services"]
                    # Check for Wahoo CADENCE in the name as a special case
                    if "CADENCE" in device["name"] and "Wahoo" in device["name"]:
                        speed_cadence_device = device
                        if debug:
                            console.print(f"[dim]Matched Wahoo Cadence device: {device['name']}[/dim]")
                        break
                    # Standard service check
                    elif any(s in ["Speed/Cadence", "Speed", "Cadence"] for s in services):
                        speed_cadence_device = device
                        if debug:
                            console.print(f"[dim]Matched device by service: {device['name']} - {services}[/dim]")
                        break
            
            if speed_cadence_device:
                console.print(f"[blue]Found speed/cadence sensor: {speed_cadence_device['name']}[/blue]")
                console.print(f"[blue]Attempting to connect to {speed_cadence_device['name']}...[/blue]")
                
                # Create device with cached info - it won't scan again
                self.speed_cadence_device = SpeedCadenceDevice(
                    device_name=speed_cadence_device["name"],
                    data_callback=self.handle_metric_data
                )
                
                # Set cached information so it doesn't need to scan again
                self.speed_cadence_device._cached_device = None  # Force new connection with address
                self.speed_cadence_device._cached_address = speed_cadence_device.get("address", None)
                
                if self.speed_cadence_device._cached_address is None and hasattr(speed_cadence_device, "address"):
                    self.speed_cadence_device._cached_address = speed_cadence_device.address
                    
                # Attempt connection with debug mode if requested
                success = await self.speed_cadence_device.connect(debug=debug)
                
                if success:
                    self.connected_devices.append(self.speed_cadence_device)
                    connected = True
                    console.print(f"[green]✓ Connected to {speed_cadence_device['name']}[/green]")
                else:
                    console.print(f"[red]Failed to connect to {speed_cadence_device['name']}[/red]")
            elif debug:
                console.print("[dim]No speed/cadence sensor found in scan[/dim]")
            
        # Initialize metrics from connected devices
        for device in self.connected_devices:
            device_metrics = device.get_available_metrics()
            if device_metrics:
                # Only add metrics that are requested (if any specified)
                filtered_metrics = [
                    m for m in device_metrics 
                    if not metric_types or m in metric_types
                ]
                self.available_metrics.extend([
                    m for m in filtered_metrics 
                    if m not in self.available_metrics
                ])
        
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
            console.print(f"[green]Ready to monitor {len(self.available_metrics)} metrics: {', '.join(self.available_metrics)}[/green]")
            return True
        else:
            # Check if we have any Wahoo CADENCE devices connected
            # These devices only send metrics when the crank is spinning
            has_wahoo_cadence = any(
                hasattr(device, 'device') and device.device and device.device.name and 
                "wahoo" in device.device.name.lower() and "cadence" in device.device.name.lower()
                for device in self.connected_devices
            )
            
            if has_wahoo_cadence:
                console.print("[yellow]Wahoo CADENCE sensor detected.[/yellow]")
                console.print("[yellow]NOTE: The sensor only sends data when the crank is spinning.[/yellow]")
                console.print("[yellow]Please spin the pedals a few times to activate the sensor.[/yellow]")
                
                # Add a dummy cadence monitor anyway
                if "cadence" in METRIC_CONFIG:
                    config = METRIC_CONFIG["cadence"]
                    self.metric_monitors["cadence"] = MetricMonitor(
                        name=config["name"],
                        color=config["color"],
                        unit=config["unit"]
                    )
                    self.available_metrics.append("cadence")
                
                # Set up the display with all metric monitors
                self.multi_display = MultiMetricDisplay(list(self.metric_monitors.values()))
                console.print("[green]Ready to monitor cadence when the sensor activates[/green]")
                return True
            else:
                console.print("[yellow]No metrics available from connected devices.[/yellow]")
                if debug:
                    # Print device status
                    for device in self.connected_devices:
                        device_type = (
                            "Heart Rate Monitor" if isinstance(device, HeartRateDevice)
                            else "Trainer" if isinstance(device, TrainerDevice)
                            else "Speed/Cadence Sensor"
                        )
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
        
        # Start the live display only if show_display is True
        self.running = True
        if self.show_display and self.multi_display:
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
                        
                        # Update display with new monitors if enabled
                        if self.show_display and self.multi_display:
                            self.multi_display.monitors = list(self.metric_monitors.values())
                
                await asyncio.sleep(refresh_rate)
        finally:
            # Stop display if it was started
            if self.show_display and self.multi_display:
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
        
        if self.speed_cadence_device:
            tasks.append(self.speed_cadence_device.disconnect())
        
        if tasks:
            await asyncio.gather(*tasks)

def start_auto_monitoring(
    refresh_rate: int = 1,
    debug: bool = False,
    device_types: Optional[List[str]] = None,
    metric_types: Optional[List[str]] = None,
    device_names: Optional[List[str]] = None
):
    """Start automatic device discovery and monitoring process.
    
    Args:
        refresh_rate: How often to refresh the display in seconds
        debug: Whether to show debug information
        device_types: List of device types to connect to (e.g. ["heart_rate", "trainer"])
        metric_types: List of metrics to monitor (e.g. ["heart_rate", "power"])
        device_names: List of specific device names to connect to
    """
    # When in debug mode, don't show the display to make logs more visible
    controller = DeviceController(show_display=not debug)
    
    try:
        # Setup event loop
        loop = asyncio.get_event_loop()
        
        # Auto-discover and connect to devices
        if not loop.run_until_complete(controller.auto_discover_connect(
            debug=debug,
            device_types=device_types,
            metric_types=metric_types,
            device_names=device_names
        )):
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