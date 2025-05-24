"""Smart trainer device."""

import asyncio
from bleak import BleakClient, BleakScanner
from rich.console import Console
from typing import Optional, Callable, List, Dict, Any
from .base import Device
from .ftms_parsers import parse_indoor_bike_data

# InsideRide E-Motion Service UUIDs
UART_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write to trainer
UART_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Receive from trainer

# Fitness Machine Service
FITNESS_MACHINE_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_FEATURE = "00002acc-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_STATUS = "00002ada-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_INDOOR_BIKE_DATA = "00002ad2-0000-1000-8000-00805f9b34fb"

# Known trainer names
KNOWN_TRAINERS = ["insideride", "e-motion", "7578h"]

console = Console()

class TrainerDevice(Device):
    """Smart trainer device."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None, metrics: Optional[List[str]] = None):
        """Initialize the trainer device.
        
        Args:
            device_name: Specific device name to connect to (optional)
            data_callback: Callback function when data is received (optional)
                          Called with metric_name, value, timestamp
            metrics: List of metrics to monitor (optional)
        """
        super().__init__(device_name, data_callback)
        self.metrics = metrics or ["power", "speed", "cadence"]  # Default to all metrics if none specified
        
        # Initialize current values
        self.current_values = {
            "power": None,
            "speed": None,
            "cadence": None,
            "heart_rate": None,
            "distance": None
        }
    
    def get_service_uuid(self) -> str:
        """Return the service UUID for trainer devices."""
        return FITNESS_MACHINE_SERVICE
    
    async def setup_notifications(self):
        """Set up notifications for indoor bike data."""
        # Try to enable notifications for Indoor Bike Data
        indoor_bike_data_success = False
        try:
            await self.client.start_notify(
                FITNESS_MACHINE_INDOOR_BIKE_DATA,
                self.handle_data
            )
            indoor_bike_data_success = True
            if self.debug_mode:
                self.add_debug_message("Enabled Indoor Bike Data notifications")
        except Exception as e:
            if self.debug_mode:
                self.add_debug_message(f"Error enabling Indoor Bike Data notifications: {e}")
        
        # Try UART as a fallback
        uart_success = False
        if not indoor_bike_data_success:
            try:
                await self.client.start_notify(UART_RX, self.handle_data)
                uart_success = True
                if self.debug_mode:
                    self.add_debug_message("Enabled UART notifications")
            except Exception as e:
                if self.debug_mode:
                    self.add_debug_message(f"Error enabling UART notifications: {e}")
        
        # Check if either notification method was successful
        if not indoor_bike_data_success and not uart_success:
            if self.debug_mode:
                self.add_debug_message("Failed to enable any notifications")
            return False
        
        return True
    
    def handle_data(self, _, data: bytearray):
        """Handle incoming indoor bike data."""
        try:
            if self.debug_mode:
                hex_data = " ".join([f"{b:02x}" for b in data])
                self.add_debug_message(f"Received bike data: {hex_data}")
            
            # Parse the data using our FTMS parser
            bike_data = parse_indoor_bike_data(data)
            if self.debug_mode:
                self.add_debug_message(f"Parsed bike data: {bike_data}")
            timestamp = asyncio.get_event_loop().time()
            
            # Update current values and notify callback for each available metric
            if bike_data.instant_power is not None and "power" in self.metrics:
                self.current_values["power"] = bike_data.instant_power
                if self.data_callback:
                    self.data_callback("power", bike_data.instant_power, timestamp)
                if "power" not in self.available_metrics:
                    self.available_metrics.append("power")
                    if self.debug_mode:
                        self.add_debug_message(f"Added power metric: {bike_data.instant_power} W")
            
            if bike_data.instant_speed is not None and "speed" in self.metrics:
                self.current_values["speed"] = bike_data.instant_speed  # Already in km/h
                if self.data_callback:
                    self.data_callback("speed", bike_data.instant_speed, timestamp)
                if "speed" not in self.available_metrics:
                    self.available_metrics.append("speed")
                    if self.debug_mode:
                        self.add_debug_message(f"Added speed metric: {bike_data.instant_speed} km/h")
            
            if bike_data.instant_cadence is not None and "cadence" in self.metrics:
                self.current_values["cadence"] = bike_data.instant_cadence
                if self.data_callback:
                    self.data_callback("cadence", bike_data.instant_cadence, timestamp)
                if "cadence" not in self.available_metrics:
                    self.available_metrics.append("cadence")
                    if self.debug_mode:
                        self.add_debug_message(f"Added cadence metric: {bike_data.instant_cadence} RPM")
            
            # Add heart rate if available
            if bike_data.heart_rate is not None:
                self.current_values["heart_rate"] = bike_data.heart_rate
                if self.data_callback:
                    self.data_callback("heart_rate", bike_data.heart_rate, timestamp)
                if "heart_rate" not in self.available_metrics:
                    self.available_metrics.append("heart_rate")
                    if self.debug_mode:
                        self.add_debug_message(f"Added heart rate metric: {bike_data.heart_rate} BPM")
            
            # Add distance if available
            if bike_data.total_distance is not None:
                self.current_values["distance"] = bike_data.total_distance
                if self.data_callback:
                    self.data_callback("distance", bike_data.total_distance, timestamp)
                if "distance" not in self.available_metrics:
                    self.available_metrics.append("distance")
                    if self.debug_mode:
                        self.add_debug_message(f"Added distance metric: {bike_data.total_distance} m")
                
        except Exception as e:
            if self.debug_mode:
                self.add_debug_message(f"Error parsing bike data: {e}") 