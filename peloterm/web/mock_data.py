"""Mock data generator for testing the web UI."""

import asyncio
import random
import math
import time
from typing import Dict, Optional


class MockDataGenerator:
    """Generate realistic mock cycling data."""
    
    def __init__(self, start_time: Optional[float] = None):
        self.start_time = start_time or time.time()
        self.base_power = 150
        self.base_speed = 25
        self.base_cadence = 80
        self.base_heart_rate = 130
        
    def generate_metrics(self) -> Dict[str, float]:
        """Generate a set of realistic cycling metrics."""
        elapsed = time.time() - self.start_time
        
        # Add some variation using sine waves and random noise
        power_variation = math.sin(elapsed * 0.1) * 20 + random.uniform(-10, 10)
        speed_variation = math.sin(elapsed * 0.08) * 5 + random.uniform(-2, 2)
        cadence_variation = math.sin(elapsed * 0.12) * 10 + random.uniform(-5, 5)
        hr_variation = math.sin(elapsed * 0.06) * 15 + random.uniform(-5, 5)
        
        return {
            "power": max(0, self.base_power + power_variation),
            "speed": max(0, self.base_speed + speed_variation),
            "cadence": max(0, self.base_cadence + cadence_variation),
            "heart_rate": max(60, self.base_heart_rate + hr_variation),
        }


async def start_mock_data_stream(broadcast_func, interval: float = 1.0):
    """Start streaming mock data using server start time."""
    # Get server start time by importing the global web_server
    from .server import web_server
    
    if web_server and hasattr(web_server, 'ride_start_time'):
        start_time = web_server.ride_start_time
    else:
        start_time = time.time()
    
    generator = MockDataGenerator(start_time=start_time)
    
    while True:
        metrics = generator.generate_metrics()
        await broadcast_func(metrics)
        await asyncio.sleep(interval) 