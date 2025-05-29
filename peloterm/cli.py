"""Command-line interface for Peloterm."""

import asyncio
import typer
from pathlib import Path
from typing import Optional, Dict
import threading
import webbrowser
import time
import signal
import traceback
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
from .web.server import start_server, broadcast_metrics, stop_server, web_server
from .web.mock_data import start_mock_data_stream
from .strava_integration import StravaUploader
from .data_recorder import RideRecorder
from .logo import display_logo, get_version_banner

app = typer.Typer(
    help="Peloterm - A terminal-based cycling metrics visualization tool",
    add_completion=False,
)
console = Console()

# Create a sub-app for Strava commands
strava_app = typer.Typer(help="Strava integration commands")
app.add_typer(strava_app, name="strava")

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
    """Print version information with logo."""
    if value:
        console.print(get_version_banner(__version__))
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

@app.command()
def logo(
    style: str = typer.Option("banner", "--style", "-s", help="Logo style: banner, compact, logo, or bike")
):
    """Display the Peloterm logo."""
    display_logo(console, style)

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
    timeout: int = typer.Option(90, "--timeout", "-t", help="Maximum time to wait for all devices in seconds (increased default: 90)"),
    no_recording: bool = typer.Option(False, "--no-recording", help="Disable ride recording (recording enabled by default)")
):
    """Start Peloterm with the specified configuration."""
    
    # Load configuration
    if config_path is None:
        config_path = get_default_config_path()
    config = load_config(config_path)
    config.mock_mode = mock
    
    # Recording is enabled by default unless explicitly disabled
    enable_recording = not no_recording
    
    # Create an event to signal shutdown
    shutdown_event = threading.Event()
    controller = None
    
    def signal_handler(signum, frame):
        console.print("\n[yellow]Gracefully shutting down Peloterm...[/yellow]")
        shutdown_event.set()
        # Also stop the web server if it's running (needed for mock mode)
        if web_server:
            web_server.stop()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Show listening mode interface
    display_logo(console, "compact")
    console.print("[bold blue]🎧 Starting Peloterm[/bold blue]")
    if enable_recording:
        console.print("[green]📹 Ride recording enabled[/green]")
    console.print("\nI'll listen for your configured devices. Turn them on when you're ready!")
    console.print("Press Ctrl+C to stop.\n")
    
    # Display expected devices
    if config.devices and not config.mock_mode:
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
            
            # Initialize controller earlier, it handles mock mode internally
            controller = DeviceController(config=config, show_display=False, enable_recording=enable_recording)
            controller.debug_mode = debug # Pass debug setting to controller

            # Set up web UI callbacks in the controller
            # The controller will now handle broadcasting for both mock and real devices
            controller.set_web_ui_callbacks(broadcast_metrics)

            if config.mock_mode: # Changed from 'if mock:'
                console.print("[yellow]Mock mode: Peloterm will use internal mock data.[/yellow]")
                # For mock mode, connection is simulated, and data flow starts via callbacks
                # The DeviceController's connect_configured_devices will handle MockDevice connection

            # Unified device monitoring logic for web mode
            async def monitor_web_devices():
                nonlocal controller # Ensure controller is from the outer scope
                
                # Start device connection in the background without blocking
                console.print("[blue]🔍 Starting device connection in background...[/blue]")
                
                # Create a task for device connection that runs in parallel
                async def connect_devices_background():
                    connected = await listen_for_devices_connection(controller, config, timeout, debug, shutdown_event)
                    
                    if connected:
                        console.print("[green]✅ Device connection complete![/green]")
                        console.print("[blue]🌐 Devices now streaming to web UI...[/blue]")
                        
                        if enable_recording and controller.ride_recorder and not controller.ride_recorder.is_recording:
                            controller.start_recording()
                            console.print("[green]🎬 Recording started![/green]")
                    else:
                        console.print("[yellow]⚠️  No devices connected, but web UI remains available.[/yellow]")
                
                # Start device connection as a background task
                connection_task = asyncio.create_task(connect_devices_background())
                
                try:
                    # Main monitoring loop - runs immediately while devices connect in background
                    console.print("[blue]🌐 Web UI is ready! Devices will appear as they connect...[/blue]")
                    
                    while not shutdown_event.is_set():
                        await asyncio.sleep(refresh_rate) # Main loop to keep things running
                        if debug:
                            console.print("[dim]Web monitoring active...[/dim]")
                            
                finally:
                    # Clean up connection task if still running
                    if not connection_task.done():
                        connection_task.cancel()
                        try:
                            await connection_task
                        except asyncio.CancelledError:
                            pass
                    
                    if controller.ride_recorder and controller.ride_recorder.is_recording:
                         console.print("[dim]Stopping recording due to shutdown...[/dim]")
                    # Disconnection should happen on the same loop if parts of it are async
                    # or be robust to being called from a different context.
                    if controller and controller.connected_devices: # Check if there are devices to disconnect
                        await controller.disconnect_devices() 
            
            try:
                # Use asyncio.run() for the main async logic for this part of the application.
                # This manages the event loop creation and closing.
                asyncio.run(monitor_web_devices())
            except KeyboardInterrupt:
                console.print("\n[yellow]Web monitoring interrupted by user (KeyboardInterrupt).[/yellow]")
                shutdown_event.set() # Ensure shutdown is signaled
            except SystemExit:
                console.print("\n[yellow]SystemExit caught, initiating shutdown.[/yellow]")
                shutdown_event.set() # Ensure shutdown is signaled
            except Exception as e:
                if debug:
                    console.print(f"[red]Error during web monitoring: {e}[/red]")
                shutdown_event.set() # Ensure shutdown on other errors too
            finally:
                # This finally block is for the try/except around asyncio.run()
                console.print("[dim]Ensuring shutdown signal is set before main web finally block.[/dim]")
                shutdown_event.set() # Ensure it's set so main finally block acts correctly
                pass

        finally:
            # This is the outermost finally for the `if web:` block
            console.print(f"[dim]Outermost finally for 'if web:' reached. Shutdown event set: {shutdown_event.is_set()}[/dim]")
            
            # Stop the web server
            stop_server()
            if web_thread:
                web_thread.join(timeout=1.0)
            
            console.print("[green]Shutdown complete[/green]")
    else:
        # Terminal mode
        controller = DeviceController(config, show_display=True, enable_recording=enable_recording)
        controller.debug_mode = debug # Pass debug setting
        
        if not config.mock_mode: # Changed from 'not mock'
            console.print("\n[green]🚴 Starting terminal mode...[/green]")
            display_device_table(config)
        else:
            console.print("[yellow]Mock mode: Peloterm will use internal mock data for terminal.[/yellow]")
        
        # Event loop for terminal mode
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # `connect_configured_devices` in controller handles mock device connection internally
            connected = loop.run_until_complete(
                listen_for_devices_connection(controller, config, timeout, debug, shutdown_event)
            )
            
            if connected and not shutdown_event.is_set():
                console.print("\n[green]✅ Device connection complete![/green]")
                console.print("[green]🚴 Starting terminal monitoring...[/green]")
                
                if enable_recording and not controller.ride_recorder.is_recording:
                    controller.start_recording()
                    console.print("[green]🎬 Recording started![/green]")
                
                # The controller.run method handles its own display loop for terminal
                loop.run_until_complete(controller.run(refresh_rate=refresh_rate))
            else:
                console.print("\n[yellow]❌ Device listening cancelled or no devices connected for terminal.[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            if debug:
                raise
        finally:
            if not config.mock_mode:
                try:
                    # Ensure devices are disconnected first
                    if controller.connected_devices:
                        if debug:
                            console.print("[yellow]Disconnecting devices...[/yellow]")
                        loop.run_until_complete(controller.disconnect_devices())
                        # Give BLE stack more time to clean up
                        time.sleep(1.0)
                    
                    # Clean up the loop
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    
                    # Wait for all tasks to complete with timeout
                    if pending:
                        try:
                            loop.run_until_complete(asyncio.wait_for(
                                asyncio.gather(*pending, return_exceptions=True),
                                timeout=2.0
                            ))
                        except asyncio.TimeoutError:
                            if debug:
                                console.print("[dim]Some tasks didn't complete in time, forcing cleanup[/dim]")
                    
                    loop.close()
                except Exception as e:
                    if debug:
                        console.print(f"[red]Error during cleanup: {e}[/red]")
                    # Force close the loop even if there are errors
                    try:
                        if not loop.is_closed():
                            loop.close()
                    except:
                        pass


async def listen_for_devices_connection(controller, config, timeout, debug, shutdown_event):
    """Handle listening for device connections with enhanced user guidance."""
    
    if config.mock_mode:
        # In mock mode, we only care about connecting the single MockDevice.
        # The controller.connect_configured_devices method is already updated to handle this.
        console.print("[yellow][CLI] 🔍 Mock mode: Attempting to connect mock device...[/yellow]")
        mock_connected_status = await controller.connect_configured_devices(debug=debug, suppress_failures_during_listening=False)
        console.print(f"[yellow][CLI] Mock controller.connect_configured_devices returned: {mock_connected_status}[/yellow]") # Debug print
        if mock_connected_status:
            console.print("[green][CLI] 🎉 Mock device connected! [/green]")
            return True
        else:
            console.print("[red][CLI] ✗ Failed to connect mock device.[/red]")
            return False

    # --- Enhanced logic for non-mock mode below ---
    connected_count = 0
    total_devices = len(config.devices)
    
    if total_devices == 0:
        console.print("[yellow]No devices configured to connect to in non-mock mode.[/yellow]")
        return False # No devices to connect

    # Print device list with helpful guidance
    console.print(f"\n[bold blue]🔍 Looking for {total_devices} configured devices:[/bold blue]")
    device_table = Table(title="Target Devices", show_header=True, header_style="bold magenta")
    device_table.add_column("Device Name", style="cyan")
    device_table.add_column("Type", style="yellow")
    device_table.add_column("Status", style="white")
    
    for device_config in config.devices:
        device_type = "/".join(device_config.services)
        device_table.add_row(device_config.name, device_type, "🔍 Searching...")
    
    console.print(device_table)
    console.print(f"\n[blue]💡 Quick tips for device connection:[/blue]")
    console.print(f"   • Make sure devices are turned ON and nearby (within 3 feet)")
    console.print(f"   • Press any button on devices to wake them up")  
    console.print(f"   • If a device doesn't connect, try turning it off/on")
    console.print(f"   • Connection timeout: {timeout} seconds\n")

    start_time = asyncio.get_event_loop().time()
    last_progress_update = 0
    connection_attempts = {}
    
    console.print(f"[yellow]🔍 Listening for devices... (0/{total_devices} connected)[/yellow]")
    
    while connected_count < total_devices and not shutdown_event.is_set():
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - start_time
        
        if elapsed > timeout:
            console.print(f"\n[yellow]⏰ Connection timeout reached ({timeout}s).[/yellow]")
            break
        
        # Show progress every 10 seconds
        if elapsed - last_progress_update >= 10:
            remaining_time = max(0, timeout - elapsed)
            console.print(f"[dim]⏳ Still searching... ({connected_count}/{total_devices} connected, {remaining_time:.0f}s remaining)[/dim]")
            last_progress_update = elapsed
        
        # Try to connect to any missing devices (suppress failure messages during listening)
        old_connected_count = connected_count
        if await controller.connect_configured_devices(debug=debug, suppress_failures_during_listening=True):
            connected_count = len(controller.connected_devices)
            if connected_count > old_connected_count:
                newly_connected = connected_count - old_connected_count
                if connected_count >= total_devices:
                    console.print(f"\n[green]🎉 All {total_devices} devices connected successfully![/green]")
                    break
                else:
                    console.print(f"\n[cyan]📱 Progress: {connected_count}/{total_devices} devices connected (+{newly_connected})[/cyan]")
                    remaining_time = max(0, timeout - elapsed)
                    console.print(f"[yellow]🔍 Still searching for {total_devices - connected_count} more device(s)... ({remaining_time:.0f}s remaining)[/yellow]")
        
        # Wait a bit before trying again (reduced for more responsive feedback)
        await asyncio.sleep(1.5)
    
    # Final status report
    if connected_count == total_devices:
        console.print(f"[green]✅ Perfect! All {total_devices} devices are connected and ready.[/green]")
    elif connected_count > 0:
        console.print(f"[cyan]✅ Partial success: {connected_count}/{total_devices} devices connected.[/cyan]")
        console.print(f"[yellow]⚠️  Missing {total_devices - connected_count} device(s), but you can still start riding![/yellow]")
        
        # Show which devices are missing
        connected_names = {device.device_name for device in controller.connected_devices if device.device_name}
        missing_devices = []
        for device_config in config.devices:
            if device_config.name not in connected_names:
                missing_devices.append(f"{device_config.name} ({'/'.join(device_config.services)})")
        
        if missing_devices:
            console.print(f"[dim]Missing devices: {', '.join(missing_devices)}[/dim]")
            console.print(f"[blue]💡 To connect missing devices later:[/blue]")
            console.print(f"   • Turn them on and they should auto-reconnect")
            console.print(f"   • Or restart peloterm with: peloterm start --timeout {timeout + 30}")
    else:
        console.print(f"[red]❌ No devices connected after {timeout} seconds.[/red]")
        console.print(f"[blue]💡 Troubleshooting suggestions:[/blue]")
        console.print(f"   1. Check that devices are turned on and in pairing mode")
        console.print(f"   2. Try moving closer to your computer (within 3 feet)")
        console.print(f"   3. Run device scan: peloterm scan --timeout 15")
        console.print(f"   4. Try with longer timeout: peloterm start --timeout {timeout + 60}")
        console.print(f"   5. Check device batteries and restart devices if needed")
    
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

@strava_app.command("setup")
def strava_setup():
    """Set up Strava integration by configuring API credentials."""
    uploader = StravaUploader()
    
    if uploader.setup():
        console.print("\n[green]✓ Strava setup complete![/green]")
        console.print("You can now upload rides using: [bold]peloterm strava upload[/bold]")
    else:
        console.print("\n[red]✗ Strava setup failed[/red]")
        raise typer.Exit(1)

@strava_app.command("test")
def strava_test():
    """Test the Strava API connection."""
    uploader = StravaUploader()
    
    if uploader.test_connection():
        console.print("\n[green]✓ Strava connection successful![/green]")
    else:
        console.print("\n[red]✗ Strava connection failed[/red]")
        console.print("Try running: [bold]peloterm strava setup[/bold]")
        raise typer.Exit(1)

@strava_app.command("upload")
def strava_upload(
    fit_file: Optional[Path] = typer.Argument(None, help="Path to FIT file to upload"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Activity name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Activity description"),
    activity_type: str = typer.Option("Ride", "--type", "-t", help="Activity type (default: Ride)")
):
    """Upload a FIT file to Strava."""
    uploader = StravaUploader()
    
    # If no file specified, look for recent rides
    if not fit_file:
        rides_dir = Path.home() / ".peloterm" / "rides"
        if not rides_dir.exists():
            console.print("[red]No rides directory found. Record a ride first or specify a FIT file.[/red]")
            raise typer.Exit(1)
        
        # Find the most recent FIT file
        fit_files = list(rides_dir.glob("*.fit"))
        if not fit_files:
            console.print("[red]No FIT files found in rides directory.[/red]")
            raise typer.Exit(1)
        
        # Sort by modification time and get the most recent
        fit_file = max(fit_files, key=lambda f: f.stat().st_mtime)
        console.print(f"[blue]Using most recent ride: {fit_file.name}[/blue]")
    
    if not fit_file.exists():
        console.print(f"[red]File not found: {fit_file}[/red]")
        raise typer.Exit(1)
    
    success = uploader.upload_ride(
        str(fit_file),
        name=name,
        description=description,
        activity_type=activity_type
    )
    
    if success:
        console.print("\n[green]🎉 Successfully uploaded to Strava![/green]")
    else:
        console.print("\n[red]✗ Upload failed[/red]")
        raise typer.Exit(1)

@strava_app.command("list")
def list_rides():
    """List recorded rides available for upload."""
    rides_dir = Path.home() / ".peloterm" / "rides"
    
    if not rides_dir.exists():
        console.print("[yellow]No rides directory found.[/yellow]")
        return
    
    fit_files = list(rides_dir.glob("*.fit"))
    
    if not fit_files:
        console.print("[yellow]No recorded rides found.[/yellow]")
        console.print("Record a ride using: [bold]peloterm start --record[/bold]")
        return
    
    # Sort by modification time (newest first)
    fit_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    table = Table(title="Recorded Rides", show_header=True, header_style="bold blue")
    table.add_column("File", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Size", style="magenta")
    
    for fit_file in fit_files:
        mtime = fit_file.stat().st_mtime
        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        size_kb = fit_file.stat().st_size / 1024
        
        table.add_row(
            fit_file.name,
            date_str,
            f"{size_kb:.1f} KB"
        )
    
    console.print(table)
    console.print(f"\nUse [bold]peloterm strava upload [FILE][/bold] to upload a specific ride")
    console.print(f"Or [bold]peloterm strava upload[/bold] to upload the most recent ride")

@app.command()
def devices(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to the configuration file. Uses default location if not specified."
    ),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Discovery timeout in seconds"),
    reconnect: bool = typer.Option(False, "--reconnect", help="Attempt to reconnect to configured devices"),
    status: bool = typer.Option(False, "--status", help="Show current device connection status")
):
    """Manage and test device connections interactively."""
    
    # Load configuration
    if config_path is None:
        config_path = get_default_config_path()
    config = load_config(config_path)
    
    if status:
        # Show current configuration and device status
        console.print("\n[bold blue]Current Device Configuration:[/bold blue]")
        display_device_table(config)
        
        console.print(f"\n[blue]💡 Quick actions:[/blue]")
        console.print(f"   • Test connections: [cyan]peloterm devices --reconnect[/cyan]")
        console.print(f"   • Scan for devices: [cyan]peloterm scan --timeout {timeout}[/cyan]")
        console.print(f"   • Start monitoring: [cyan]peloterm start --timeout {timeout + 30}[/cyan]")
        return
    
    if reconnect:
        # Test connection to configured devices
        console.print("[bold blue]🔗 Testing connections to configured devices...[/bold blue]")
        
        async def test_connections():
            from .device_manager import SmartDeviceManager
            
            device_manager = SmartDeviceManager(config)
            target_names = [device.name for device in config.devices]
            
            if not target_names:
                console.print("[yellow]No devices configured. Run 'peloterm scan' first.[/yellow]")
                return
            
            found_devices = await device_manager.smart_device_discovery(target_names, timeout)
            
            # Report results
            console.print(f"\n[bold]Connection Test Results:[/bold]")
            success_count = 0
            
            for device_config in config.devices:
                device_name = device_config.name
                if device_name in found_devices and found_devices[device_name]:
                    device_info = found_devices[device_name]
                    rssi = device_info['rssi']
                    signal_strength = "Strong" if rssi > -50 else "Medium" if rssi > -70 else "Weak"
                    console.print(f"[green]✅ {device_name}[/green] - Signal: {signal_strength} ({rssi}dBm)")
                    success_count += 1
                else:
                    console.print(f"[red]❌ {device_name}[/red] - Not found")
            
            if success_count == len(target_names):
                console.print(f"\n[green]🎉 Perfect! All {success_count} devices are discoverable.[/green]")
                console.print(f"[blue]Ready to start: [cyan]peloterm start[/cyan][/blue]")
            elif success_count > 0:
                console.print(f"\n[yellow]⚠️ Partial success: {success_count}/{len(target_names)} devices found.[/yellow]")
                console.print(f"[blue]You can still start with: [cyan]peloterm start[/cyan][/blue]")
            else:
                console.print(f"\n[red]❌ No devices found. Check troubleshooting tips above.[/red]")
        
        try:
            asyncio.run(test_connections())
        except Exception as e:
            console.print(f"[red]Error during connection test: {e}[/red]")
        return
    
    # Interactive device management
    console.print("[bold blue]🛠️ Interactive Device Management[/bold blue]")
    console.print("\nChoose an action:")
    console.print("1. [cyan]Scan for new devices[/cyan]")
    console.print("2. [cyan]Test configured device connections[/cyan]") 
    console.print("3. [cyan]View current configuration[/cyan]")
    console.print("4. [cyan]Exit[/cyan]")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                console.print(f"[blue]Scanning for devices (timeout: {timeout}s)...[/blue]")
                scan_sensors(timeout)
                break
            elif choice == "2":
                # Recursive call with reconnect flag
                devices(config_path, timeout, reconnect=True, status=False)
                break
            elif choice == "3":
                devices(config_path, timeout, reconnect=False, status=True)
                break
            elif choice == "4":
                console.print("[blue]Goodbye![/blue]")
                break
            else:
                console.print("[yellow]Invalid choice. Please enter 1-4.[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            break
        except EOFError:
            break

if __name__ == "__main__":
    app()