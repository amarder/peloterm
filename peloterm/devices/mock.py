"""Mock device for testing UI without real hardware."""

import asyncio
import math
import random
import time
from typing import Optional, Callable, List, Dict, Any
from .base import Device
from rich.console import Console

console = Console()

class MockDevice(Device):
    """Mock device that simulates cycling metrics."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None):
        """Initialize the mock device.
        
        Args:
            device_name: Specific device name to connect to (optional)
            data_callback: Callback function when data is received (optional)
                          Called with metric_name, value, timestamp
        """
        super().__init__(device_name or "Mock Trainer", data_callback)
        
        # Initialize current values
        self.current_values = {
            "power": 0,
            "speed": 0,
            "cadence": 0,
            "heart_rate": 60
        }
        
        # Base values for simulation
        self._base_power = 150  # Watts
        self._base_speed = 25   # km/h
        self._base_cadence = 80 # RPM
        self._base_hr = 130     # BPM
        
        # Time tracking for simulation
        self._start_time = None
        self._update_task = None
        
        # Available metrics
        self.available_metrics = ["power", "speed", "cadence", "heart_rate"]
    
    def get_service_uuid(self) -> str:
        """Return a fake service UUID."""
        return "00000000-0000-0000-0000-000000000000"
    
    async def connect(self, address: Optional[str] = None, debug: bool = False) -> bool:
        """Simulate connecting to the device."""
        self.debug_mode = debug
        console.print(f"[blue][MockDevice] connect called. Debug: {self.debug_mode}[/blue]")
        self._start_time = asyncio.get_event_loop().time()
        
        # Start the simulation task
        try:
            self._update_task = asyncio.create_task(self.handle_data())
            console.print("[blue][MockDevice] Simulation task created successfully.[/blue]")
        except Exception as e:
            console.print(f"[red][MockDevice] Error creating simulation task: {e}[/red]")
            return False
        
        if self.debug_mode:
            self.add_debug_message("Mock device connected")
            console.print("[blue][MockDevice] Debug message added: Mock device connected[/blue]")
        
        console.print("[green][MockDevice] connect method returning True.[/green]")
        return True
    
    async def disconnect(self):
        """Simulate disconnecting from the device."""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
        
        if self.debug_mode:
            self.add_debug_message("Mock device disconnected")
    
    async def setup_notifications(self):
        """No need to set up notifications for mock device."""
        pass
    
    async def handle_data(self):
        """Simulate cycling metrics with realistic variations."""
        try:
            while True:
                timestamp = time.time()
                current_loop_time = asyncio.get_event_loop().time()
                elapsed = current_loop_time - self._start_time
                
                # Add some sinusoidal variation to make it more realistic
                variation = math.sin(elapsed / 10) * 0.1  # 10% variation over 10 seconds
                random_factor = random.uniform(-0.05, 0.05)  # 5% random noise
                
                # Update power
                power = self._base_power * (1 + variation + random_factor)
                power = round(max(0, power))
                self.current_values["power"] = power
                if self.data_callback:
                    self.data_callback("power", power, timestamp)
                
                # Update speed (correlates somewhat with power)
                speed = self._base_speed * (1 + variation * 0.8 + random_factor * 0.5)
                speed = round(max(0, speed), 1)
                self.current_values["speed"] = speed
                if self.data_callback:
                    self.data_callback("speed", speed, timestamp)
                
                # Update cadence
                cadence = self._base_cadence * (1 + variation * 0.3 + random_factor * 0.2)
                cadence = round(max(0, cadence))
                self.current_values["cadence"] = cadence
                if self.data_callback:
                    self.data_callback("cadence", cadence, timestamp)
                
                # Update heart rate (follows power with delay)
                hr_variation = math.sin((elapsed - 2) / 10) * 0.1  # Delayed response
                heart_rate = self._base_hr * (1 + hr_variation + random_factor * 0.1)
                heart_rate = round(max(60, heart_rate))
                self.current_values["heart_rate"] = heart_rate
                if self.data_callback:
                    self.data_callback("heart_rate", heart_rate, timestamp)
                
                if self.debug_mode:
                    self.add_debug_message(
                        f"Mock metrics - Power: {power}W, Speed: {speed}km/h, "
                        f"Cadence: {cadence}rpm, HR: {heart_rate}bpm"
                    )
                
                await asyncio.sleep(1)  # Update once per second
                
        except asyncio.CancelledError:
            if self.debug_mode:
                self.add_debug_message("Mock device simulation stopped")
            raise 