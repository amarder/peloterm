"""Command-line interface for Peloterm."""

import asyncio
import typer
from pathlib import Path
from typing import Optional
import threading
import webbrowser
import time
import signal
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich import print as rprint
from enum import Enum
from . import __version__
from .monitor import start_monitoring as start_hr_monitoring
from .trainer import start_trainer_monitoring
from .scanner import scan_sensors, discover_devices, display_devices
from .controller import DeviceController, start_monitoring_with_config
from .config import (
    Config,
    MetricConfig,
    METRIC_DISPLAY_NAMES,
    create_default_config_from_scan,
    save_config,
    load_config,
    get_default_config_path
)
from .web.server import start_server, broadcast_metrics, stop_server
from .web.mock_data import start_mock_data_stream

app = typer.Typer(
    help="Peloterm - A terminal-based cycling metrics visualization tool",
    add_completion=False,
)
console = Console()

class DeviceType(str, Enum):
    """Available device types."""
    HEART_RATE = "heart_rate"
    TRAINER = "trainer"
    SPEED_CADENCE = "speed_cadence"

class MetricType(str, Enum):
    """Available metric types."""
    HEART_RATE = "heart_rate"
    POWER = "power"
    SPEED = "speed"
    CADENCE = "cadence"

def version_callback(value: bool):
    """Print version information."""
    if value:
        console.print(f"[bold]Peloterm[/bold] version: {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version information.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Peloterm - Monitor your cycling metrics in real-time."""
    pass

def display_device_table(config: Config):
    """Display a table of configured devices and their metrics."""
    table = Table(title="Configured Devices", show_header=True, header_style="bold blue")
    table.add_column("Device Name", style="cyan")
    table.add_column("Services", style="magenta")
    table.add_column("Metrics", style="green")

    for device in config.devices:
        # Get metrics for this device
        device_metrics = [
            metric.display_name for metric in config.display 
            if metric.device == device.name
        ]
        table.add_row(
            device.name,
            ", ".join(device.services),
            ", ".join(device_metrics)
        )
    
    console.print(table)

@app.command()
def start(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to the configuration file. Uses default location if not specified."
    ),
    refresh_rate: int = typer.Option(1, "--refresh-rate", "-r", help="Display refresh rate in seconds"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    mock: bool = typer.Option(False, "--mock", "-m", help="Use mock device for testing"),
    web: bool = typer.Option(True, "--web/--no-web", help="Start with web UI (default: True)"),
    port: int = typer.Option(8000, "--port", "-p", help="Web server port"),
    duration: int = typer.Option(30, "--duration", help="Target ride duration in minutes (default: 30)"),
    timeout: int = typer.Option(60, "--timeout", "-t", help="Maximum time to wait for all devices in seconds")
):
    """Start Peloterm with the specified configuration."""
    
    # Load configuration
    if config_path is None:
        config_path = get_default_config_path()
    config = load_config(config_path)
    
    # Create an event to signal shutdown
    shutdown_event = threading.Event()
    
    def signal_handler(signum, frame):
        console.print("\n[yellow]Gracefully shutting down PeloTerm...[/yellow]")
        console.print("[dim]Please wait while devices disconnect...[/dim]")
        shutdown_event.set()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Show listening mode interface
    console.print("[bold blue]🎧 Starting Peloterm[/bold blue]")
    console.print("\nI'll listen for your configured devices. Turn them on when you're ready!")
    console.print("Press Ctrl+C to cancel.\n")
    
    # Display expected devices
    if config.devices and not mock:
        table = Table(title="Waiting for these devices", show_header=True, header_style="bold cyan")
        table.add_column("Device Name", style="cyan")
        table.add_column("Type", style="magenta")
        
        for device in config.devices:
            device_type = "Unknown"
            if "Heart Rate" in device.services:
                device_type = "Heart Rate Monitor"
            elif "Power" in device.services:
                device_type = "Trainer/Power Meter"
            elif any(s in ["Speed/Cadence", "Speed", "Cadence"] for s in device.services):
                device_type = "Speed/Cadence Sensor"
            
            table.add_row(device.name, device_type)
        
        console.print(table)
        console.print()
    
    if web:
        # Start web server in a separate thread
        web_thread = None
        try:
            def run_web_server():
                start_server(port=port, ride_duration_minutes=duration)
            
            web_thread = threading.Thread(target=run_web_server, daemon=True)
            web_thread.start()
            
            # Give the server a moment to start
            time.sleep(1)
            
            # Open web browser
            url = f"http://localhost:{port}"
            console.print(f"[green]Web UI available at: {url}[/green]")
            console.print(f"[blue]Target ride duration: {duration} minutes[/blue]")
            webbrowser.open(url)
            
            if mock:
                # Start mock data streaming
                console.print("[yellow]Mock mode: streaming fake cycling data[/yellow]")
                
                # Create a new event loop for the mock data stream
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(start_mock_data_stream(broadcast_metrics, interval=refresh_rate))
                finally:
                    loop.close()
            else:
                # Initialize device controller for web mode
                controller = DeviceController(config=config, show_display=False)
                
                # Create a new event loop for device monitoring
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def monitor_devices():
                    # Connect to devices using listening mode
                    connected = await listen_for_devices_connection(controller, config, timeout, debug, shutdown_event)
                    
                    if connected:
                        console.print("[green]✅ Device connection complete![/green]")
                        console.print("[blue]🌐 Starting monitoring...[/blue]")
                        
                        # Create a queue for metric updates
                        metric_queue = asyncio.Queue()
                        
                        # Start a background task to process the queue
                        async def process_metric_queue():
                            try:
                                while not shutdown_event.is_set():
                                    try:
                                        metric_data = await asyncio.wait_for(metric_queue.get(), timeout=0.5)
                                        await broadcast_metrics(metric_data)
                                        metric_queue.task_done()
                                    except asyncio.TimeoutError:
                                        continue  # Check shutdown_event every 0.5 seconds
                            except asyncio.CancelledError:
                                pass
                        
                        # Start the queue processor
                        queue_task = asyncio.create_task(process_metric_queue())
                        
                        # Override the controller's data callback to broadcast to web
                        def web_data_callback(metric: str, value: float, timestamp: float):
                            if not shutdown_event.is_set():
                                try:
                                    asyncio.run_coroutine_threadsafe(
                                        metric_queue.put({metric: value}),
                                        loop
                                    )
                                except RuntimeError:
                                    # Loop might be closed during shutdown
                                    pass
                        
                        # Set the callback for each device
                        for device in controller.connected_devices:
                            device.data_callback = web_data_callback
                        
                        try:
                            # Run the controller until shutdown is requested
                            while not shutdown_event.is_set():
                                await asyncio.sleep(refresh_rate)
                                if debug:
                                    console.print("[dim]Monitoring devices...[/dim]")
                        finally:
                            # Clean up
                            if not queue_task.done():
                                queue_task.cancel()
                                try:
                                    await queue_task
                                except asyncio.CancelledError:
                                    pass
                            
                            # Disconnect devices
                            await controller.disconnect_devices()
                    else:
                        console.print("[red]Failed to connect to any devices[/red]")
                
                try:
                    loop.run_until_complete(monitor_devices())
                except Exception as e:
                    if debug:
                        console.print(f"[red]Error during monitoring: {e}[/red]")
                finally:
                    try:
                        # Ensure devices are disconnected first
                        if 'controller' in locals() and controller.connected_devices:
                            console.print("[yellow]Disconnecting devices...[/yellow]")
                            loop.run_until_complete(controller.disconnect_devices())
                            # Give BLE stack time to clean up
                            time.sleep(0.5)
                        
                        # Cancel all running tasks
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        
                        # Wait for all tasks to complete
                        if pending:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        
                        # Close the loop
                        loop.close()
                    except Exception as e:
                        if debug:
                            console.print(f"[red]Error during cleanup: {e}[/red]")
                        # Force close the loop even if there are errors
                        try:
                            loop.close()
                        except:
                            pass
        finally:
            # Stop the web server
            stop_server()
            if web_thread:
                web_thread.join(timeout=1.0)
            
            console.print("[green]Shutdown complete[/green]")
    else:
        # Terminal mode
        controller = DeviceController(config, show_display=True)
        
        if not mock:
            console.print("\n[green]🚴 Starting terminal mode...[/green]")
            display_device_table(config)
        
        # Create event loop for listening
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if mock:
                # Use the old sequential mode for mock in terminal
                start_monitoring_with_config(
                    config=config,
                    refresh_rate=refresh_rate,
                    debug=debug
                )
            else:
                connected = loop.run_until_complete(
                    listen_for_devices_connection(controller, config, timeout, debug, shutdown_event)
                )
                
                if connected and not shutdown_event.is_set():
                    console.print("\n[green]✅ Device connection complete![/green]")
                    console.print("[green]🚴 Starting terminal monitoring...[/green]")
                    loop.run_until_complete(controller.run(refresh_rate=refresh_rate))
                else:
                    console.print("\n[yellow]❌ Device listening cancelled or no devices connected.[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            if debug:
                raise
        finally:
            if not mock:
                try:
                    # Ensure devices are disconnected first
                    if controller.connected_devices:
                        console.print("[yellow]Disconnecting devices...[/yellow]")
                        loop.run_until_complete(controller.disconnect_devices())
                        # Give BLE stack time to clean up
                        time.sleep(0.5)
                    
                    # Clean up the loop
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    
                    loop.close()
                except Exception as e:
                    if debug:
                        console.print(f"[red]Error during cleanup: {e}[/red]")
                    # Force close the loop even if there are errors
                    try:
                        loop.close()
                    except:
                        pass

async def listen_for_devices_connection(controller, config, timeout, debug, shutdown_event):
    """Handle listening for device connections."""
    connected_count = 0
    total_devices = len(config.devices)
    
    with console.status("[bold yellow]🔍 Listening for devices...[/bold yellow]", spinner="dots") as status:
        start_time = asyncio.get_event_loop().time()
        
        while connected_count < total_devices and not shutdown_event.is_set():
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            
            if elapsed > timeout:
                console.print(f"\n[yellow]⏰ Timeout reached ({timeout}s). Connected to {connected_count}/{total_devices} devices.[/yellow]")
                break
            
            # Update status
            remaining_time = max(0, timeout - elapsed)
            status.update(f"[bold yellow]🔍 Listening for devices... ({connected_count}/{total_devices} connected, {remaining_time:.0f}s remaining)[/bold yellow]")
            
            # Try to connect to any missing devices
            if await controller.connect_configured_devices(debug=debug):
                connected_count = len(controller.connected_devices)
                if connected_count >= total_devices:
                    console.print(f"\n[green]🎉 All devices connected! ({connected_count}/{total_devices})[/green]")
                    break
                else:
                    console.print(f"\n[cyan]📱 Connected to {connected_count}/{total_devices} devices. Still waiting for more...[/cyan]")
            
            # Wait a bit before trying again
            await asyncio.sleep(2)
    
    return connected_count > 0

@app.command()
def scan(
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Path to save the configuration file. Uses default location if not specified."
    ),
    timeout: int = typer.Option(10, "--timeout", "-t", help="Scan timeout in seconds"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode")
):
    """Scan for BLE devices and create a configuration file."""
    try:
        # First display the scan results
        console.print(Panel.fit("Scanning for Devices", style="bold blue"))
        devices = asyncio.run(discover_devices(timeout=timeout))
        
        if not devices:
            console.print("[yellow]No compatible devices found.[/yellow]")
            return
        
        # Display the device table
        display_devices(devices)
        
        # Create and save configuration
        config = create_default_config_from_scan(devices)
        save_config(config, output)
        
        console.print(f"\n[green]Configuration saved to: {output or get_default_config_path()}[/green]")
        console.print("\nYou can now edit this file to customize your setup.")
        console.print("Then use [bold]peloterm start[/bold] to run with your configuration.")
        
    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()