"""Command-line interface for Peloterm."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint
from typing import Optional, List
from enum import Enum
from . import __version__
from .monitor import start_monitoring as start_hr_monitoring
from .trainer import start_trainer_monitoring
from .scanner import scan_sensors
from .controller import start_auto_monitoring

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
    devices: Optional[List[DeviceType]] = typer.Option(
        None,
        "--device", "-d",
        help="Specific device types to connect to (heart_rate, trainer, speed_cadence). If not specified, will try to connect to all available devices.",
    ),
    metrics: Optional[List[MetricType]] = typer.Option(
        None,
        "--metric", "-m",
        help="Specific metrics to monitor (heart_rate, power, speed, cadence). If not specified, will monitor all available metrics.",
    ),
    device_names: Optional[List[str]] = typer.Option(
        None,
        "--name", "-n",
        help="Names of specific devices to connect to. Use quotes if name contains spaces.",
    ),
    refresh_rate: int = typer.Option(1, "--refresh-rate", "-r", help="Graph refresh rate in seconds"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode with detailed logging"),
):
    """Start monitoring specific devices and metrics."""
    debug_str = " [bold yellow](DEBUG MODE)[/bold yellow]" if debug else ""
    
    # Show what we're going to monitor
    if devices:
        device_str = ", ".join([d.value for d in devices])
        console.print(Panel.fit(f"Starting Monitoring for devices: {device_str}{debug_str}", style="bold magenta"))
    else:
        console.print(Panel.fit(f"Starting Auto-Discovery and Monitoring{debug_str}", style="bold magenta"))
    
    if metrics:
        metric_str = ", ".join([m.value for m in metrics])
        console.print(f"[blue]Will monitor metrics: {metric_str}[/blue]")
    
    if device_names:
        name_str = ", ".join(device_names)
        console.print(f"[blue]Will look for devices named: {name_str}[/blue]")
    
    if debug:
        console.print("[bold yellow]Debug mode enabled - showing detailed logs[/bold yellow]")
    
    try:
        start_auto_monitoring(
            refresh_rate=refresh_rate,
            debug=debug,
            device_types=devices,
            metric_types=metrics,
            device_names=device_names
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")

@app.command()
def scan(
    timeout: int = typer.Option(10, "--timeout", "-t", help="Scan timeout in seconds"),
):
    """Scan for available sensors."""
    console.print(Panel.fit("Scanning for Sensors", style="bold blue"))
    try:
        scan_sensors(timeout=timeout)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")

if __name__ == "__main__":
    app()