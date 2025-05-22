"""Configuration handling for Peloterm."""

import os
import yaml
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Standard metric names and their display versions
METRIC_DISPLAY_NAMES = {
    'heart_rate': 'Heart Rate',
    'power': 'Power',
    'speed': 'Speed',
    'cadence': 'Cadence'
}

# Standard service to metric name mapping
SERVICE_TO_METRIC = {
    'Heart Rate': ['heart_rate'],
    'Power': ['power', 'speed'],  # Trainer provides power and speed by default
    'Speed/Cadence': ['speed', 'cadence']
}

# Standard colors for different metric types
DEFAULT_COLORS = {
    'heart_rate': 'red',
    'power': 'red',
    'speed': 'red',
    'cadence': 'red'
}

# Standard units for different metrics
DEFAULT_UNITS = {
    'heart_rate': 'BPM',
    'power': 'W',
    'speed': 'km/h',
    'cadence': 'RPM'
}

@dataclass
class DeviceConfig:
    """Configuration for a BLE device."""
    name: str
    address: str
    services: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            'name': str(self.name),
            'address': str(self.address),
            'services': self.services
        }

@dataclass
class MetricConfig:
    """Configuration for a metric to display."""
    name: str  # Display name (e.g., "Heart Rate")
    device: str  # Name of the device this metric comes from
    service: str  # BLE service name
    metric: str  # Internal metric name (e.g., "heart_rate")
    color: str
    unit: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            'name': str(self.name),
            'device': str(self.device),
            'service': str(self.service),
            'color': str(self.color),
            'unit': str(self.unit)
        }

@dataclass
class PelotermConfig:
    """Main configuration class."""
    devices: List[DeviceConfig]
    display: List[MetricConfig]

    @classmethod
    def from_dict(cls, data: Dict) -> 'PelotermConfig':
        """Create a configuration from a dictionary."""
        devices = [
            DeviceConfig(**device_data)
            for device_data in data.get('devices', [])
        ]
        
        display = []
        for metric_data in data.get('display', []):
            # Get the internal metric name from the display name
            display_name = metric_data['name']
            # Find the internal metric name that matches this display name
            metric_name = next(
                (k for k, v in METRIC_DISPLAY_NAMES.items() if v == display_name),
                display_name.lower()
            )
            
            # Create MetricConfig with both display name and internal metric name
            display.append(MetricConfig(
                name=display_name,
                device=metric_data['device'],
                service=metric_data['service'],
                metric=metric_name,
                color=metric_data['color'],
                unit=metric_data['unit']
            ))
        
        return cls(devices=devices, display=display)

    def to_dict(self) -> Dict:
        """Convert configuration to a dictionary."""
        return {
            'devices': [device.to_dict() for device in self.devices],
            'display': [metric.to_dict() for metric in self.display]
        }

def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / '.config' / 'peloterm' / 'config.yaml'

def load_config(config_path: Optional[Path] = None) -> PelotermConfig:
    """Load configuration from a YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return PelotermConfig.from_dict(data)

def save_config(config: PelotermConfig, config_path: Optional[Path] = None) -> None:
    """Save configuration to a YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dictionary and save as YAML
    config_dict = config.to_dict()
    with open(config_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

def create_default_config_from_scan(devices: List[Dict]) -> PelotermConfig:
    """Create a default configuration from scan results."""
    device_configs = []
    metric_configs = []
    processed_metrics = set()  # Track which metrics we've already added
    
    for device in devices:
        if not device['services']:  # Skip devices with no services
            continue
            
        device_configs.append(DeviceConfig(
            name=str(device['name']),
            address=str(device['address']),
            services=device['services']
        ))
        
        # Create metric configs for each service
        for service in device['services']:
            # Get the list of metrics this service can provide
            service_metrics = SERVICE_TO_METRIC.get(service, [service.lower()])
            
            # Add each metric this service provides (if not already added)
            for metric_name in service_metrics:
                # Create a unique key for this device+metric combination
                metric_key = f"{device['name']}:{metric_name}"
                if metric_key not in processed_metrics:
                    processed_metrics.add(metric_key)
                    metric_configs.append(MetricConfig(
                        name=METRIC_DISPLAY_NAMES.get(metric_name, metric_name.title()),
                        device=str(device['name']),
                        service=service,
                        metric=metric_name,
                        color=DEFAULT_COLORS.get(metric_name, 'white'),
                        unit=DEFAULT_UNITS.get(metric_name, '')
                    ))
    
    return PelotermConfig(devices=device_configs, display=metric_configs) 