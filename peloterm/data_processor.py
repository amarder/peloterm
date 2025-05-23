"""Data processing and buffering for cycling metrics."""

import time
from typing import Dict, Optional, Any
from collections import defaultdict

class DataProcessor:
    """Process and buffer cycling metrics data."""
    
    def __init__(self, stale_threshold: float = 2.0):
        """Initialize the data processor.
        
        Args:
            stale_threshold: Number of seconds after which data is considered stale
        """
        self.current_values = defaultdict(lambda: None)
        self.last_update_time = defaultdict(float)
        self.stale_threshold = stale_threshold
        
    def update_metric(self, metric_name: str, value: Any):
        """Update a metric with a new value."""
        # Format speed with one decimal point
        if metric_name == "speed" and value is not None:
            value = round(float(value), 1)
        else:
            # Round other numeric metrics to integers
            try:
                value = round(float(value))
            except (TypeError, ValueError):
                pass  # Keep original value if not numeric
                
        self.current_values[metric_name] = value
        self.last_update_time[metric_name] = time.time()
    
    def get_processed_metrics(self) -> Dict[str, Any]:
        """Get all current metrics, handling stale data.
        
        Returns:
            Dict containing current values for all metrics.
            If a metric hasn't been updated within stale_threshold seconds:
            - For cadence: returns 0 (not pedaling)
            - For other metrics: returns the last known value
        """
        current_time = time.time()
        processed_metrics = {}
        
        for metric, value in self.current_values.items():
            time_since_update = current_time - self.last_update_time[metric]
            
            if time_since_update > self.stale_threshold:
                # Handle stale data differently based on metric type
                if metric == "cadence":
                    processed_metrics[metric] = 0  # Not pedaling
                else:
                    processed_metrics[metric] = value  # Keep last known value
            else:
                processed_metrics[metric] = value
                
        return processed_metrics 