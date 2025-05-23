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
        
        # Add periods of no pedaling to simulate real-world scenarios
        self.last_no_pedaling = 0
        self.no_pedaling_duration = 0
        
    def generate_metrics(self) -> Dict[str, float]:
        """Generate a set of realistic cycling metrics."""
        elapsed = time.time() - self.start_time
        
        # Simulate periods of no pedaling
        current_time = time.time()
        if current_time - self.last_no_pedaling > 30:  # Every 30 seconds
            if random.random() < 0.2:  # 20% chance to stop pedaling
                self.last_no_pedaling = current_time
                self.no_pedaling_duration = random.uniform(2, 5)  # Stop for 2-5 seconds
        
        is_pedaling = (current_time - self.last_no_pedaling) > self.no_pedaling_duration
        
        # Add some variation using sine waves and random noise
        power_variation = math.sin(elapsed * 0.1) * 20 + random.uniform(-10, 10)
        speed_variation = math.sin(elapsed * 0.08) * 5 + random.uniform(-2, 2)
        cadence_variation = math.sin(elapsed * 0.12) * 10 + random.uniform(-5, 5)
        hr_variation = math.sin(elapsed * 0.06) * 15 + random.uniform(-5, 5)
        
        # If not pedaling, set cadence and power to 0, and gradually decrease speed
        if not is_pedaling:
            return {
                "power": 0,
                "speed": max(0, self.base_speed * 0.5 + speed_variation * 0.5),  # Coasting
                "cadence": 0,
                "heart_rate": max(60, self.base_heart_rate * 0.8 + hr_variation * 0.5),  # Heart rate drops slowly
            }
        
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
    
    if not web_server:
        print("Warning: No web server instance found for mock data stream")
        return
    
    start_time = web_server.ride_start_time if hasattr(web_server, 'ride_start_time') else time.time()
    generator = MockDataGenerator(start_time=start_time)
    
    try:
        while not web_server.shutdown_event.is_set():
            try:
                metrics = generator.generate_metrics()
                await broadcast_func(metrics)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in mock data stream: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error before retrying
    except asyncio.CancelledError:
        pass
    finally:
        print("Mock data stream stopped") 