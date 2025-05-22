"""Device classes for Peloterm."""

from .base import Device
from .heart_rate import HeartRateDevice
from .trainer import TrainerDevice
from .speed_cadence import SpeedCadenceDevice

__all__ = [
    'Device',
    'HeartRateDevice',
    'TrainerDevice',
    'SpeedCadenceDevice'
] 