"""Command-line interface for Peloterm."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint
from typing import Optional
from . import __version__
from .monitor import start_monitoring
from .scanner import scan_sensors

app = typer.Typer(
    help="Peloterm - A terminal-based cycling metrics visualization tool",
    add_completion=False,
)
console = Console()

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
    device_name: Optional[str] = typer.Option(None, "--device", "-d", help="Specific device name to connect to"),
):
    """Start monitoring cycling metrics."""
    console.print(Panel.fit("Starting Peloterm Monitor", style="bold green"))
    try:
        start_monitoring(refresh_rate=refresh_rate, device_name=device_name)
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