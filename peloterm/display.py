"""Common display and plotting utilities."""

import plotext as plt
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
        
        # Configure plotext settings
        plt.theme('dark')
    
    def update_plot(self, width: Optional[int] = None, height: Optional[int] = None):
        """Update the plot with current metric data."""
        if len(self.values) <= 1:
            return Panel(
                f"Collecting {self.name.lower()} data...", 
                title=f"{self.name} Monitor", 
                border_style=f"bright_{self.color}"
            )
            
        # Convert timestamps to minutes ago
        now = datetime.now()
        times = [(now - ts).total_seconds() / 60 for ts in self.timestamps]
        
        # Clear previous plot
        plt.clf()
        plt.theme('dark')
        
        # Get terminal dimensions if not provided
        if width is None or height is None:
            width, height = console.size
            
        # Set plot dimensions - increase height by approximately 4 lines
        plot_width = width - 4
        plot_height = min(height - 2, 16)  # Increased from height-6 to height-2, and max from 12 to 16
        
        # Set plot size
        plt.plotsize(plot_width, plot_height)
        
        # Plot the data with the specified color as a scatter plot
        plt.scatter(times, self.values, color=self.color)
        
        # Set plot attributes
        plt.xlabel("Minutes ago")
        plt.grid(False)
        
        # Set axis limits
        plt.xlim(max(times), 0)  # Reverse x-axis to show newest data on right
        
        if len(self.values) > 0:
            min_val = min(self.values)
            max_val = max(self.values)
            y_padding = max(5, (max_val - min_val) * 0.1)
            plt.ylim(max(0, min_val - y_padding), max_val + y_padding)
        else:
            plt.ylim(0, 100)  # Default range
        
        # Build the plot
        plot_str = plt.build()
        plot_text = Text.from_ansi(plot_str)
        
        # Create panel with the plot
        title = f"[bold bright_{self.color}]{self.name}[/bold bright_{self.color}] - Current: [bold bright_{self.color}]{self.current_value}[/bold bright_{self.color}] {self.unit}"
        
        return Panel(
            plot_text,
            title=title,
            border_style=f"bright_{self.color}",
            padding=(0, 1)
        )
    
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
        plt.theme('dark')
    
    def update_display(self):
        """Update the display with all metrics."""
        if not self.monitors:
            return Panel("No metrics to display", title="Metrics Monitor", border_style="bright_blue")
        
        # If there's only one monitor, just return its plot
        if len(self.monitors) == 1:
            return self.monitors[0].update_plot()
        
        # For multiple monitors, use a layout
        layout = Layout(name="root")
        
        # Get terminal dimensions
        width, height = console.size
        
        # Calculate height per monitor (account for padding/borders) - increase height allocation
        # Add a bit more height per panel to make them taller
        total_panels_height = height - 2  # Use more of the available height
        panel_height = total_panels_height // len(self.monitors)
        
        # Split the layout for each monitor
        layout.split_column(*[
            Layout(
                monitor.update_plot(width=width, height=panel_height), 
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