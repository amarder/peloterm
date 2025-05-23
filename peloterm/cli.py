"""Command-line interface for Peloterm."""

import asyncio
import typer
from pathlib import Path
from typing import Optional
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
    mock: bool = typer.Option(False, "--mock", "-m", help="Use mock device for testing")
):
    """Start Peloterm with the specified configuration."""
    try:
        if config_path is None:
            config_path = get_default_config_path()
        
        # In mock mode, we don't need an existing config file
        if mock:
            config = Config(mock_mode=True)
            config.display = [
                MetricConfig(
                    metric=metric,
                    display_name=display_name,
                    device="Mock Device",
                    color="white"
                )
                for metric, display_name in METRIC_DISPLAY_NAMES.items()
            ]
            # Save the mock config for future use
            config.save(config_path)
        else:
            # For non-mock mode, we need a valid config file
            if not config_path.exists():
                console.print(
                    "[red]Configuration file not found. "
                    "Run [bold]peloterm scan[/bold] first to create a configuration.[/red]"
                )
                raise typer.Exit(1)
            config = load_config(config_path)
        
        # Display configured devices
        if not mock:  # Skip device table in mock mode
            display_device_table(config)
        
        # Start monitoring with configuration
        start_monitoring_with_config(
            config=config,
            refresh_rate=refresh_rate,
            debug=debug
        )
        
    except Exception as e:
        console.print(f"[red]Error starting Peloterm: {e}[/red]")
        raise typer.Exit(1)

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