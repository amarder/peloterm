"""Tests for the display module."""

import pytest
from datetime import datetime, timedelta
from peloterm.display import MetricMonitor, MultiMetricDisplay

def test_metric_monitor_initialization():
    """Test MetricMonitor initialization with default values."""
    monitor = MetricMonitor(name="Heart Rate", color="red", unit="BPM")
    assert monitor.name == "Heart Rate"
    assert monitor.color == "red"
    assert monitor.unit == "BPM"
    assert monitor.current_value == 0
    assert len(monitor.values) == 0
    assert len(monitor.timestamps) == 0

def test_metric_monitor_update_value():
    """Test updating values in MetricMonitor."""
    monitor = MetricMonitor(name="Power", color="yellow", unit="W")
    monitor.update_value(150)
    assert monitor.current_value == 150
    assert len(monitor.values) == 1
    assert len(monitor.timestamps) == 1
    assert monitor.values[0] == 150

def test_metric_monitor_multiple_updates():
    """Test multiple value updates in MetricMonitor."""
    monitor = MetricMonitor(name="Cadence", color="blue", unit="RPM")
    test_values = [80, 85, 90]
    for value in test_values:
        monitor.update_value(value)
    
    assert monitor.current_value == test_values[-1]
    assert len(monitor.values) == len(test_values)
    assert monitor.values == test_values

def test_multi_metric_display_initialization():
    """Test MultiMetricDisplay initialization."""
    monitors = [
        MetricMonitor(name="Heart Rate", color="red", unit="BPM"),
        MetricMonitor(name="Power", color="yellow", unit="W")
    ]
    display = MultiMetricDisplay(monitors=monitors)
    assert len(display.monitors) == 2
    assert display.live is None

def test_multi_metric_display_x_limits():
    """Test calculation of shared x-axis limits."""
    monitors = [
        MetricMonitor(name="Heart Rate", color="red", unit="BPM"),
        MetricMonitor(name="Power", color="yellow", unit="W")
    ]
    display = MultiMetricDisplay(monitors=monitors)
    
    # Test with no data
    min_time, max_time = display.get_shared_x_limits()
    assert min_time == 0
    assert max_time == 5  # Default range when no data
    
    # Add some test data
    now = datetime.now()
    monitors[0].timestamps = [now - timedelta(minutes=1), now - timedelta(minutes=2)]
    monitors[0].values = [150, 155]
    
    min_time, max_time = display.get_shared_x_limits()
    assert min_time == 0
    assert max_time >= 2  # Should be at least 2 minutes (oldest data point) 