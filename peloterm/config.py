"""Configuration management for peloterm."""

import os
import yaml
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Standard metric names and their display versions
METRIC_DISPLAY_NAMES = {
    'power': 'Power ⚡',
    'speed': 'Speed 🚴',
    'cadence': 'Cadence 🔄',
    'heart_rate': 'Heart Rate 💓',
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
    """Configuration for a single device."""
    name: str
    address: str
    services: List[str]

@dataclass
class MetricConfig:
    """Configuration for a single metric display."""
    metric: str  # Internal metric name
    display_name: str  # Display name shown in UI
    device: Optional[str] = None  # Device name to get metric from
    color: Optional[str] = None  # Color for the metric display

@dataclass
class Config:
    """Configuration for peloterm."""
    devices: List[DeviceConfig] = field(default_factory=list)
    display: List[MetricConfig] = field(default_factory=list)
    mock_mode: bool = False  # Enable mock device mode for testing

    @classmethod
    def load(cls, source: Union[str, Path, Dict]) -> 'Config':
        """Load configuration from a file path or dictionary.
        
        Args:
            source: Either a file path (str/Path) or a dictionary with config data
        """
        if isinstance(source, (str, Path)):
            if not os.path.exists(source):
                return cls()
            
            with open(source, 'r') as f:
                data = yaml.safe_load(f)
        else:
            data = source
        
        if not data:
            return cls()
        
        devices = []
        for device_data in data.get('devices', []):
            devices.append(DeviceConfig(
                name=device_data['name'],
                address=device_data['address'],
                services=device_data['services']
            ))
        
        display = []
        for metric_data in data.get('display', []):
            display.append(MetricConfig(
                metric=metric_data['metric'],
                display_name=metric_data.get('display_name', metric_data['metric']),
                device=metric_data.get('device'),
                color=metric_data.get('color')
            ))
        
        return cls(
            devices=devices,
            display=display,
            mock_mode=data.get('mock_mode', False)
        )
    
    def save(self, target: Union[str, Path, Dict]):
        """Save configuration to a file path or dictionary.
        
        Args:
            target: Either a file path (str/Path) or a dictionary to update
        """
        data = {
            'mock_mode': self.mock_mode,
            'devices': [
                {
                    'name': device.name,
                    'address': device.address,
                    'services': device.services
                }
                for device in self.devices
            ],
            'display': [
                {
                    'metric': metric.metric,
                    'display_name': metric.display_name,
                    'device': metric.device,
                    'color': metric.color
                }
                for metric in self.display
            ]
        }
        
        if isinstance(target, (str, Path)):
            os.makedirs(os.path.dirname(str(target)), exist_ok=True)
            with open(target, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        else:
            target.update(data)

def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / '.config' / 'peloterm' / 'config.yaml'

def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from a YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return Config.load(str(config_path))

def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to a YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dictionary and save as YAML
    config.save(str(config_path))

def create_default_config_from_scan(devices: List[Dict]) -> Config:
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
                        metric=metric_name,
                        display_name=METRIC_DISPLAY_NAMES.get(metric_name, metric_name.title()),
                        device=str(device['name']),
                        color=DEFAULT_COLORS.get(metric_name, 'white')
                    ))
    
    return Config(devices=device_configs, display=metric_configs) 