"""
InsideRide-specific FTMS data parser.

InsideRide uses a non-standard FTMS implementation where data is encoded differently
than the standard FTMS specification:
- Power: Single byte at position 9 (instead of standard 2-byte field)
- Speed: Single byte at position 3 in m/s (converted to km/h)
- Time: Standard 2-byte field at positions 11-12
- Resistance: Standard 2-byte field at positions 5-6 (typically 0)

This parser was developed through analysis of real InsideRide E-Motion trainer data.
"""

from collections import namedtuple
from typing import Optional, Union

InsideRideBikeData = namedtuple(
    "InsideRideBikeData",
    [
        "instant_power",      # W (int, single byte at position 9)
        "instant_speed",      # km/h (float, converted from m/s at position 3)
        "elapsed_time",       # s (int, 2 bytes at positions 11-12)
        "resistance_level",   # unitless (int, 2 bytes at positions 5-6)
    ]
)

def parse_insideride_ftms_data(message: Union[bytes, bytearray]) -> InsideRideBikeData:
    """Parse InsideRide FTMS Indoor Bike Data.
    
    InsideRide FTMS packet format (based on real data analysis):
    - Bytes 0-1: FTMS flags (standard)
    - Byte 2: Unknown field (part of distance encoding?)
    - Byte 3: Instant speed (m/s, converted to km/h)
    - Byte 4: Unknown field (part of distance encoding?)
    - Bytes 5-6: Resistance level (2 bytes, little endian, typically 0)
    - Bytes 7-8: Standard power location (always 0 in InsideRide)
    - Byte 9: Actual power (1 byte, InsideRide-specific location)
    - Byte 10: Unknown field
    - Bytes 11-12: Elapsed time (2 bytes, little endian)
    - Bytes 13-14: Padding/unknown
    
    Args:
        message: Raw bytes from InsideRide FTMS Indoor Bike Data characteristic
        
    Returns:
        InsideRideBikeData namedtuple with extracted values (None if not available)
        
    Raises:
        None - handles invalid data gracefully by returning None values
    """
    if len(message) < 10:
        return InsideRideBikeData(None, None, None, None)
    
    # Extract power from byte 9 (InsideRide-specific location)
    instant_power = message[9] if len(message) > 9 else None
    
    # Extract speed from byte 3 (m/s, convert to km/h)
    # This position showed 83% correlation with power in data analysis
    instant_speed = None
    if len(message) > 3:
        speed_ms = message[3]  # Speed in m/s
        instant_speed = speed_ms * 3.6  # Convert to km/h (1 m/s = 3.6 km/h)
    
    # Extract resistance from bytes 5-6 (2 bytes, little endian)  
    resistance_level = None
    if len(message) >= 7:
        resistance_level = int.from_bytes(message[5:7], "little", signed=True)
    
    # Extract elapsed time from bytes 11-12 (2 bytes, little endian)
    elapsed_time = None
    if len(message) >= 13:
        elapsed_time = int.from_bytes(message[11:13], "little", signed=False)
    
    return InsideRideBikeData(
        instant_power=instant_power,
        instant_speed=instant_speed,
        elapsed_time=elapsed_time,
        resistance_level=resistance_level
    )

def is_valid_insideride_data(data: InsideRideBikeData) -> bool:
    """Validate that parsed InsideRide data contains reasonable values.
    
    Args:
        data: Parsed InsideRide bike data
        
    Returns:
        True if data appears valid for indoor cycling, False otherwise
    """
    # Power should be reasonable (0-500W covers most cyclists)
    if data.instant_power is not None:
        if data.instant_power < 0 or data.instant_power > 500:
            return False
    
    # Speed should be reasonable (0-50 km/h for indoor cycling)
    if data.instant_speed is not None:
        if data.instant_speed < 0 or data.instant_speed > 50:
            return False
    
    # Elapsed time should be reasonable (0-24 hours)
    if data.elapsed_time is not None:
        if data.elapsed_time < 0 or data.elapsed_time > 86400:
            return False
    
    return True

def format_insideride_data(data: InsideRideBikeData) -> str:
    """Format InsideRide data for human-readable display.
    
    Args:
        data: Parsed InsideRide bike data
        
    Returns:
        Formatted string representation of the data
        
    Example:
        "Power: 150W | Speed: 25.2km/h | Time: 3:05 | Resistance: 0"
    """
    parts = []
    
    if data.instant_power is not None:
        parts.append(f"Power: {data.instant_power}W")
    
    if data.instant_speed is not None:
        parts.append(f"Speed: {data.instant_speed:.1f}km/h")
    
    if data.elapsed_time is not None:
        # Convert seconds to minutes:seconds format
        minutes = data.elapsed_time // 60
        seconds = data.elapsed_time % 60
        parts.append(f"Time: {minutes}:{seconds:02d}")
    
    if data.resistance_level is not None:
        parts.append(f"Resistance: {data.resistance_level}")
    
    return " | ".join(parts) if parts else "No data"

# Constants for easy access to the byte positions
class InsideRideFormat:
    """Byte position constants for InsideRide FTMS format."""
    FLAG_BYTE_0 = 0
    FLAG_BYTE_1 = 1
    SPEED_BYTE = 3      # m/s
    RESISTANCE_START = 5  # 2 bytes, little endian
    POWER_BYTE = 9      # W
    TIME_START = 11     # 2 bytes, little endian 