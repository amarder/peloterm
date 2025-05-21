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
    refresh_rate: int = typer.Option(1, "--refresh-rate", "-r", help="Graph refresh rate in seconds"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode with detailed logging"),
):
    """Start monitoring all available devices and metrics."""
    debug_str = " [bold yellow](DEBUG MODE)[/bold yellow]" if debug else ""
    console.print(Panel.fit(f"Starting Auto-Discovery and Monitoring{debug_str}", style="bold magenta"))
    
    if debug:
        console.print("[bold yellow]Debug mode enabled - showing detailed logs[/bold yellow]")
    
    try:
        start_auto_monitoring(refresh_rate=refresh_rate, debug=debug)
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