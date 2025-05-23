"""Command-line interface for Peloterm."""

import asyncio
import typer
from pathlib import Path
from typing import Optional
import threading
import webbrowser
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
from .controller import start_monitoring_with_config
from .config import (
    Config,
    MetricConfig,
    METRIC_DISPLAY_NAMES,
    create_default_config_from_scan,
    save_config,
    load_config,
    get_default_config_path
)
from .web.server import start_server, broadcast_metrics
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
    duration: int = typer.Option(30, "--duration", help="Target ride duration in minutes (default: 30)")
):
    """Start Peloterm with the specified configuration."""
    
    if web:
        # Start web server in a separate thread
        def run_web_server():
            start_server(port=port, ride_duration_minutes=duration)
        
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()
        
        # Give the server a moment to start
        import time
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
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping PeloTerm...[/yellow]")
            finally:
                loop.close()
        else:
            # TODO: Integrate real device monitoring with web server
            console.print("[yellow]Web mode: Connect your devices and metrics will appear in browser[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            
            # Keep the main thread alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping PeloTerm...[/yellow]")
    else:
        # Display configured devices in terminal mode
        if not mock:
            display_device_table(config)
        
        start_monitoring_with_config(
            config=config,
            refresh_rate=refresh_rate,
            debug=debug
        )

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