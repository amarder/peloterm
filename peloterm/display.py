"""Common display and plotting utilities."""

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from datetime import datetime
from typing import List, Optional

console = Console()

class MetricMonitor:
    """A generic monitor for displaying time-series metrics."""
    
    def __init__(self, name: str, color: str, unit: str = "", window_size: int = 60):
        """Initialize a metric monitor.
        
        Args:
            name: The name of the metric (e.g., "Heart Rate")
            color: The color to use for plotting (e.g., "red", "yellow")
            unit: The unit of measurement (e.g., "BPM", "W")
            window_size: Initial window size in data points
        """
        self.name = name
        self.color = color
        self.unit = unit
        self.timestamps = []
        self.values = []
        self.current_value = 0
        self.initial_capacity = window_size
        
    
    def update_value(self, value: float):
        """Update metric value and timestamps."""
        self.current_value = value
        self.values.append(value)
        self.timestamps.append(datetime.now())

class MultiMetricDisplay:
    """A display for multiple metrics shown simultaneously."""
    
    def __init__(self, monitors: List[MetricMonitor]):
        """Initialize with a list of metric monitors."""
        self.monitors = monitors
        self.live = None
    
    def update_display(self):
        """Update the display with all metrics."""
        if not self.monitors:
            return Panel("No metrics to display", title="Metrics Monitor", border_style="bright_blue")
        
        # For multiple monitors, use a layout
        layout = Layout(name="root")
        
        # Get terminal dimensions
        width, height = console.size
        
        # Calculate height per monitor
        total_panels_height = height - 2
        # Ensure at least 1 panel_height if there are monitors
        panel_height = total_panels_height // len(self.monitors) if self.monitors else total_panels_height

        
        # Split the layout for each monitor
        # Create simple text panels for now, since plotting is removed
        layout.split_column(*[
            Layout(
                Panel(
                    f"{monitor.name}: {monitor.current_value} {monitor.unit}", 
                    title=f"{monitor.name} Monitor", 
                    border_style=f"bright_{monitor.color}"
                ), 
                name=f"panel_{i}",
                size=panel_height
            )
            for i, monitor in enumerate(self.monitors)
        ])
        
        return layout
    
    def start_display(self):
        """Start the live display."""
        self.live = Live(self.update_display(), refresh_per_second=1, console=console)
        self.live.start()
    
    def stop_display(self):
        """Stop the live display."""
        if self.live:
            self.live.stop() 