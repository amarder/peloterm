"""Command-line interface for Peloterm."""

import asyncio
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint
from enum import Enum
from . import __version__
from .monitor import start_monitoring as start_hr_monitoring
from .trainer import start_trainer_monitoring
from .scanner import scan_sensors, discover_devices, display_devices
from .controller import start_monitoring_with_config
from .config import (
    PelotermConfig,
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

@app.command()
def start(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to the configuration file. Uses default location if not specified."
    ),
    refresh_rate: int = typer.Option(1, "--refresh-rate", "-r", help="Display refresh rate in seconds"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode")
):
    """Start Peloterm with the specified configuration."""
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Start monitoring with configuration
        start_monitoring_with_config(
            config=config,
            refresh_rate=refresh_rate,
            debug=debug
        )
        
    except FileNotFoundError:
        console.print(
            "[red]Configuration file not found. "
            "Run [bold]peloterm scan[/bold] first to create a configuration.[/red]"
        )
        raise typer.Exit(1)
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
    timeout: int = typer.Option(10, "--timeout", "-t", help="Scan timeout in seconds")
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