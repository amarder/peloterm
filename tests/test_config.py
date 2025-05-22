"""Tests for the configuration module."""

import pytest
from pathlib import Path
import yaml
from peloterm.config import (
    DeviceConfig,
    MetricConfig,
    PelotermConfig,
    create_default_config_from_scan,
    load_config,
    save_config
)

@pytest.fixture
def sample_config_dict():
    """Create a sample configuration dictionary."""
    return {
        'devices': [
            {
                'name': 'Wahoo KICKR',
                'address': '00:11:22:33:44:55',
                'services': ['Power', 'Speed/Cadence']
            },
            {
                'name': 'Polar H10',
                'address': '66:77:88:99:AA:BB',
                'services': ['Heart Rate']
            }
        ],
        'display': [
            {
                'name': 'Power Output',
                'device': 'Wahoo KICKR',
                'service': 'Power',
                'color': 'yellow',
                'unit': 'W'
            },
            {
                'name': 'Heart Rate',
                'device': 'Polar H10',
                'service': 'Heart Rate',
                'color': 'red',
                'unit': 'BPM'
            }
        ]
    }

@pytest.fixture
def sample_scan_results():
    """Create sample device scan results."""
    return [
        {
            'name': 'Wahoo KICKR',
            'address': '00:11:22:33:44:55',
            'rssi': -65,
            'services': ['Power', 'Speed/Cadence']
        },
        {
            'name': 'Polar H10',
            'address': '66:77:88:99:AA:BB',
            'rssi': -70,
            'services': ['Heart Rate']
        }
    ]

def test_device_config_creation():
    """Test creating a DeviceConfig object."""
    device = DeviceConfig(
        name='Test Device',
        address='00:11:22:33:44:55',
        services=['Power']
    )
    assert device.name == 'Test Device'
    assert device.address == '00:11:22:33:44:55'
    assert device.services == ['Power']

def test_metric_config_creation():
    """Test creating a MetricConfig object."""
    metric = MetricConfig(
        name='Power',
        device='Test Device',
        service='Power',
        metric='power',
        color='yellow',
        unit='W'
    )
    assert metric.name == 'Power'
    assert metric.device == 'Test Device'
    assert metric.service == 'Power'
    assert metric.metric == 'power'
    assert metric.color == 'yellow'
    assert metric.unit == 'W'

def test_config_from_dict(sample_config_dict):
    """Test creating PelotermConfig from dictionary."""
    config = PelotermConfig.from_dict(sample_config_dict)
    
    assert len(config.devices) == 2
    assert len(config.display) == 2
    
    # Check first device
    device = config.devices[0]
    assert device.name == 'Wahoo KICKR'
    assert device.address == '00:11:22:33:44:55'
    assert 'Power' in device.services
    
    # Check first metric
    metric = config.display[0]
    assert metric.name == 'Power Output'
    assert metric.device == 'Wahoo KICKR'
    assert metric.color == 'yellow'

def test_config_to_dict(sample_config_dict):
    """Test converting PelotermConfig to dictionary."""
    config = PelotermConfig.from_dict(sample_config_dict)
    result = config.to_dict()
    
    assert len(result['devices']) == len(sample_config_dict['devices'])
    assert len(result['display']) == len(sample_config_dict['display'])
    
    # Check device serialization
    device = result['devices'][0]
    assert device['name'] == 'Wahoo KICKR'
    assert device['address'] == '00:11:22:33:44:55'
    assert 'Power' in device['services']

def test_create_default_config_from_scan(sample_scan_results):
    """Test creating default configuration from scan results."""
    config = create_default_config_from_scan(sample_scan_results)

    assert len(config.devices) == 2
    assert len(config.display) == 4  # Power and Speed from trainer, Heart Rate from HR monitor

    # Check devices
    devices = {d.name: d for d in config.devices}
    assert 'Wahoo KICKR' in devices
    assert 'Polar H10' in devices

    # Check metrics
    metrics = {m.metric: m for m in config.display}
    assert 'power' in metrics
    assert 'speed' in metrics
    assert 'heart_rate' in metrics

    # Check specific metric configurations
    power_metric = metrics['power']
    assert power_metric.name == 'Power'
    assert power_metric.device == 'Wahoo KICKR'
    assert power_metric.service == 'Power'
    assert power_metric.unit == 'W'

    speed_metric = metrics['speed']
    assert speed_metric.name == 'Speed'
    assert speed_metric.device == 'Wahoo KICKR'
    assert speed_metric.unit == 'km/h'

    hr_metric = metrics['heart_rate']
    assert hr_metric.name == 'Heart Rate'
    assert hr_metric.device == 'Polar H10'
    assert hr_metric.service == 'Heart Rate'
    assert hr_metric.unit == 'BPM'

def test_save_and_load_config(tmp_path, sample_config_dict):
    """Test saving and loading configuration to/from file."""
    config_path = tmp_path / 'test_config.yaml'
    
    # Create and save config
    config = PelotermConfig.from_dict(sample_config_dict)
    save_config(config, config_path)
    
    # Verify file exists and contains valid YAML
    assert config_path.exists()
    with open(config_path) as f:
        saved_data = yaml.safe_load(f)
    assert 'devices' in saved_data
    assert 'display' in saved_data
    
    # Load config and verify contents
    loaded_config = load_config(config_path)
    assert len(loaded_config.devices) == len(config.devices)
    assert len(loaded_config.display) == len(config.display)
    
    # Verify specific values
    assert loaded_config.devices[0].name == 'Wahoo KICKR'
    assert loaded_config.display[0].name == 'Power Output'

def test_load_config_missing_file(tmp_path):
    """Test loading configuration from non-existent file."""
    non_existent_path = tmp_path / 'does_not_exist.yaml'
    with pytest.raises(FileNotFoundError):
        load_config(non_existent_path) 