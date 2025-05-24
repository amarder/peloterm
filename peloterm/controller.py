"""Controller for managing multiple devices and their displays."""

import asyncio
from datetime import datetime
from rich.console import Console
from typing import List, Optional, Dict, Any, Callable
from .display import MetricMonitor, MultiMetricDisplay
from .devices.heart_rate import HeartRateDevice
from .devices.trainer import TrainerDevice
from .devices.speed_cadence import SpeedCadenceDevice
from .devices.mock import MockDevice
from .scanner import discover_devices
from .config import Config, METRIC_DISPLAY_NAMES, DEFAULT_UNITS
from rich.panel import Panel
from rich.status import Status
from .devices.base import Device
from .data_recorder import RideRecorder

console = Console()

class DeviceController:
    """Controller for managing multiple devices and their displays."""
    
    def __init__(self, config: Config, show_display: bool = True, enable_recording: bool = False):
        """Initialize the device controller.
        
        Args:
            config: Configuration specifying devices and metrics
            show_display: Whether to show the live graphs display
            enable_recording: Whether to enable ride data recording
        """
        self.config = config
        self.heart_rate_device = None
        self.trainer_device = None
        self.speed_cadence_device = None
        self.mock_device = None
        self.multi_display = None
        self.metric_monitors = {}  # Dictionary of metric name to monitor
        self.connected_devices = []
        self.available_metrics = []
        self.running = False
        self.debug_mode = False
        self.show_display = show_display
        self.enable_recording = enable_recording
        self.ride_recorder = RideRecorder() if enable_recording else None
        
        # Web UI related attributes
        self.web_ui_active = False
        self._web_broadcast_callback: Optional[Callable] = None
        
        # Create metric monitors from configuration
        for metric_config in config.display:
            self.metric_monitors[metric_config.metric] = MetricMonitor(
                name=metric_config.display_name,
                color=metric_config.color,
                unit=DEFAULT_UNITS.get(metric_config.metric, '')
            )
    
    def set_web_ui_callbacks(self, broadcast_callback: Callable):
        """Set the callback for broadcasting metrics to the web UI."""
        self.web_ui_active = True
        self._web_broadcast_callback = broadcast_callback
    
    def handle_metric_data(self, metric_name: str, value: Any, timestamp: float):
        """Handle incoming metric data from any device.
        
        Args:
            metric_name: Name of the metric (e.g. "heart_rate", "power", etc.)
            value: The current value of the metric
            timestamp: The timestamp when the value was recorded
        """
        if self.debug_mode:
            console.print(f"[dim]Received metric: {metric_name} = {value}[/dim]")
        
        # Record data if recording is enabled
        if self.ride_recorder and self.ride_recorder.is_recording:
            self.ride_recorder.add_data_point(timestamp, {metric_name: value})
        
        # Update the monitor if it exists for this metric
        if metric_name in self.metric_monitors:
            monitor = self.metric_monitors[metric_name]
            monitor.update_value(value)
            
            # Update display if running
            if self.show_display and self.multi_display and self.multi_display.live:
                self.multi_display.live.update(self.multi_display.update_display())
        
        # Broadcast to web UI if active
        if self.web_ui_active and self._web_broadcast_callback:
            metric_update = {metric_name: value}
            try:
                self._web_broadcast_callback(metric_update)
            except Exception as e:
                if self.debug_mode:
                    console.log(f"[yellow]Error calling web broadcast callback: {e}[/yellow]")
    
    async def handle_device_disconnect(self, device: Device):
        """Handle device disconnection."""
        if device in self.connected_devices:
            console.log(f"[yellow]Device {device.device_name or 'Unknown'} disconnected[/yellow]")
            if self.debug_mode:
                device.add_debug_message("Device disconnected")

    async def handle_device_reconnect(self, device: Device):
        """Handle device reconnection."""
        if device not in self.connected_devices:
            self.connected_devices.append(device)
            console.log(f"[green]Device {device.device_name or 'Unknown'} reconnected[/green]")
            if self.debug_mode:
                device.add_debug_message("Device reconnected")

    async def connect_configured_devices(self, debug: bool = False, suppress_failures_during_listening: bool = False) -> bool:
        """Connect to devices specified in the configuration."""
        connected = False
        self.debug_mode = debug
        
        # Check if mock mode is enabled
        if self.config.mock_mode:
            console.log("[dim][Controller] connect_configured_devices: In mock mode.[/dim]") # Debug print
            # Ensure data_callback is set for the mock device instance
            if not self.mock_device:
                self.mock_device = MockDevice(data_callback=self.handle_metric_data)
                console.log("[dim][Controller] Instantiated MockDevice.[/dim]") # Debug print
            else:
                self.mock_device.data_callback = self.handle_metric_data
                console.log("[dim][Controller] Reused existing MockDevice, updated callback.[/dim]") # Debug print
            
            mock_connect_success = await self.mock_device.connect(debug=debug)
            console.log(f"[dim][Controller] MockDevice.connect returned: {mock_connect_success}[/dim]") # Debug print

            if mock_connect_success:
                if self.mock_device not in self.connected_devices:
                    self.connected_devices.append(self.mock_device)
                console.log("[green][Controller] ✓ Connected to mock device[/green]")
                return True
            else:
                console.log("[red][Controller] ✗ Failed to connect to mock device[/red]")
                return False
        
        # Prepare connection tasks for concurrent execution (only if not in mock_mode)
        connection_tasks = []
        
        for device_config in self.config.devices:
            # Create connection tasks based on service type, only if not already connected
            if "Heart Rate" in device_config.services:
                if not self.heart_rate_device or not (self.heart_rate_device.client and self.heart_rate_device.client.is_connected):
                    task = self._create_heart_rate_connection_task(device_config, debug, suppress_failures_during_listening)
                    connection_tasks.append(("heart_rate", task))
                elif self.heart_rate_device in self.connected_devices:
                    connected = True  # Already connected
            
            elif "Power" in device_config.services:
                if not self.trainer_device or not (self.trainer_device.client and self.trainer_device.client.is_connected):
                    task = self._create_trainer_connection_task(device_config, debug, suppress_failures_during_listening)
                    connection_tasks.append(("trainer", task))
                elif self.trainer_device in self.connected_devices:
                    connected = True  # Already connected
            
            elif any(s in ["Speed/Cadence", "Speed", "Cadence"] for s in device_config.services):
                if not self.speed_cadence_device or not (self.speed_cadence_device.client and self.speed_cadence_device.client.is_connected):
                    task = self._create_speed_cadence_connection_task(device_config, debug, suppress_failures_during_listening)
                    connection_tasks.append(("speed_cadence", task))
                elif self.speed_cadence_device in self.connected_devices:
                    connected = True  # Already connected
        
        if not connection_tasks:
            if connected:
                # All devices already connected
                return True
            else:
                if not suppress_failures_during_listening:
                    console.log("[yellow]No devices configured to connect to[/yellow]")
                return False
        
        if debug:
            console.log(f"[dim]Attempting to connect to {len(connection_tasks)} device(s) concurrently...[/dim]")
        
        # Execute all connection tasks concurrently
        tasks = [task for _, task in connection_tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, (device_type, _) in enumerate(connection_tasks):
            result = results[i]
            if isinstance(result, Exception):
                if debug:
                    console.log(f"[red]✗ Error connecting to {device_type}: {result}[/red]")
            elif result:
                connected = True
        
        if connected:
            if debug:
                console.log("[green]✓ Device connections established[/green]")
        else:
            if debug:
                console.log("[red]✗ No devices were successfully connected[/red]")
        
        return connected
    
    async def _create_heart_rate_connection_task(self, device_config, debug, suppress_failures_during_listening):
        """Create a task for connecting to a heart rate device."""
        if debug:
            console.log(f"[dim]Connecting to heart rate monitor: {device_config.name}...[/dim]")
        
        # Reuse existing device object if it exists
        if not self.heart_rate_device:
            self.heart_rate_device = HeartRateDevice(
                device_name=device_config.name,
                data_callback=self.handle_metric_data
            )
            await self.heart_rate_device.set_callbacks(
                disconnect_callback=self.handle_device_disconnect,
                reconnect_callback=self.handle_device_reconnect
            )
        
        if await self.heart_rate_device.connect(address=device_config.address, debug=debug):
            if self.heart_rate_device not in self.connected_devices:
                self.connected_devices.append(self.heart_rate_device)
            console.log(f"[green]✓ Connected to {device_config.name}[/green]")
            return True
        else:
            if not suppress_failures_during_listening:
                console.log(f"[red]✗ Failed to connect to {device_config.name}[/red]")
            return False
    
    async def _create_trainer_connection_task(self, device_config, debug, suppress_failures_during_listening):
        """Create a task for connecting to a trainer device."""
        if debug:
            console.log(f"[dim]Connecting to trainer: {device_config.name}...[/dim]")
        
        # Reuse existing device object if it exists
        if not self.trainer_device:
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
            await self.trainer_device.set_callbacks(
                disconnect_callback=self.handle_device_disconnect,
                reconnect_callback=self.handle_device_reconnect
            )
        
        if await self.trainer_device.connect(address=device_config.address, debug=debug):
            if self.trainer_device not in self.connected_devices:
                self.connected_devices.append(self.trainer_device)
            console.log(f"[green]✓ Connected to {device_config.name}[/green]")
            return True
        else:
            if not suppress_failures_during_listening:
                console.log(f"[red]✗ Failed to connect to {device_config.name}[/red]")
            return False
    
    async def _create_speed_cadence_connection_task(self, device_config, debug, suppress_failures_during_listening):
        """Create a task for connecting to a speed/cadence device."""
        if debug:
            console.log(f"[dim]Connecting to speed/cadence sensor: {device_config.name}...[/dim]")
        
        # Reuse existing device object if it exists
        if not self.speed_cadence_device:
            self.speed_cadence_device = SpeedCadenceDevice(
                device_name=device_config.name,
                data_callback=self.handle_metric_data
            )
            await self.speed_cadence_device.set_callbacks(
                disconnect_callback=self.handle_device_disconnect,
                reconnect_callback=self.handle_device_reconnect
            )
        
        if await self.speed_cadence_device.connect(address=device_config.address, debug=debug):
            if self.speed_cadence_device not in self.connected_devices:
                self.connected_devices.append(self.speed_cadence_device)
            console.log(f"[green]✓ Connected to {device_config.name}[/green]")
            return True
        else:
            if not suppress_failures_during_listening:
                console.log(f"[red]✗ Failed to connect to {device_config.name}[/red]")
            return False
    
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
            try:
                self.multi_display.stop_display()
            except Exception as e:
                if self.debug_mode:
                    console.log(f"[yellow]Warning: Error stopping display: {e}[/yellow]")
        
        # Disconnect devices one by one with error handling
        for device in self.connected_devices[:]:  # Copy list to avoid modification during iteration
            try:
                device_name = getattr(device, 'device_name', 'Unknown')
                console.log(f"[dim]Disconnecting {device_name}...[/dim]")
                await device.disconnect()
                console.log(f"[dim]✓ Disconnected {device_name}[/dim]")
            except Exception as e:
                console.log(f"[yellow]Warning: Error disconnecting device: {e}[/yellow]")
        
        self.connected_devices = []
        
        # Give BLE stack a moment to clean up
        try:
            await asyncio.sleep(0.2)
        except:
            pass

    def start_recording(self, ride_name: Optional[str] = None) -> None:
        """Start recording ride data."""
        if not self.ride_recorder:
            console.print("[yellow]Recording not enabled for this session[/yellow]")
            return
        
        if self.ride_recorder.is_recording:
            console.print("[yellow]Already recording[/yellow]")
            return
            
        self.ride_recorder.ride_name = ride_name
        self.ride_recorder.start_recording()
    
    def stop_recording(self) -> Optional[str]:
        """Stop recording and save FIT file.
        
        Returns:
            Path to the generated FIT file, or None if recording was not active
        """
        if not self.ride_recorder or not self.ride_recorder.is_recording:
            console.print("[yellow]Not currently recording[/yellow]")
            return None
        
        return self.ride_recorder.stop_recording()
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Get current recording status and statistics."""
        if not self.ride_recorder:
            return {"recording_enabled": False}
        
        status = {
            "recording_enabled": True,
            "is_recording": self.ride_recorder.is_recording,
            "data_points": len(self.ride_recorder.data_points),
        }
        
        if self.ride_recorder.start_time:
            status["start_time"] = self.ride_recorder.start_time
            if self.ride_recorder.is_recording:
                import time
                status["duration"] = time.time() - self.ride_recorder.start_time
        
        return status

def start_monitoring_with_config(
    config: Config,
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