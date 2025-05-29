"""FTMS (Fitness Machine Service) data parsers."""

from collections import namedtuple

IndoorBikeData = namedtuple(
    "IndoorBikeData",
    [
        "instant_speed",      # km/h
        "average_speed",      # km/h
        "instant_cadence",    # rpm
        "average_cadence",    # rpm
        "total_distance",     # m
        "resistance_level",   # unitless
        "instant_power",      # W
        "average_power",      # W
        "total_energy",       # kcal
        "energy_per_hour",    # kcal/h
        "energy_per_minute",  # kcal/min
        "heart_rate",         # bpm
        "metabolic_equivalent",  # unitless; metas
        "elapsed_time",       # s
        "remaining_time",     # s
    ]
)

def parse_indoor_bike_data(message) -> IndoorBikeData:
    """Parse FTMS Indoor Bike Data characteristic value.
    
    Args:
        message: Bytes received from the Indoor Bike Data characteristic
        
    Returns:
        IndoorBikeData object containing the parsed values
    """
    if len(message) < 2:
        return IndoorBikeData(*([None] * 15))
    
    # Try standard FTMS parsing first
    result = _parse_standard_ftms(message)
    
    # If standard parsing yields zero power but there are non-zero bytes that could be power,
    # try InsideRide-specific parsing
    if result.instant_power == 0 and len(message) >= 10:
        # Check if there's a reasonable power value at byte 9 (where InsideRide seems to put it)
        potential_power = message[9] if message[9] > 0 and message[9] < 255 else None
        if potential_power:
            result = _parse_insideride_format(message)
    
    return result

def _parse_standard_ftms(message) -> IndoorBikeData:
    """Parse standard FTMS Indoor Bike Data format."""
    # Parse flags
    flag_more_data = bool(message[0] & 0b00000001)
    flag_average_speed = bool(message[0] & 0b00000010)
    flag_instantaneous_cadence = bool(message[0] & 0b00000100)
    flag_average_cadence = bool(message[0] & 0b00001000)
    flag_total_distance = bool(message[0] & 0b00010000)
    flag_resistance_level = bool(message[0] & 0b00100000)
    flag_instantaneous_power = bool(message[0] & 0b01000000)
    flag_average_power = bool(message[0] & 0b10000000)
    flag_expended_energy = bool(message[1] & 0b00000001)
    flag_heart_rate = bool(message[1] & 0b00000010)
    flag_metabolic_equivalent = bool(message[1] & 0b00000100)
    flag_elapsed_time = bool(message[1] & 0b00001000)
    flag_remaining_time = bool(message[1] & 0b00010000)

    # Initialize values
    instant_speed = None
    average_speed = None
    instant_cadence = None
    average_cadence = None
    total_distance = None
    resistance_level = None
    instant_power = None
    average_power = None
    total_energy = None
    energy_per_hour = None
    energy_per_minute = None
    heart_rate = None
    metabolic_equivalent = None
    elapsed_time = None
    remaining_time = None

    # Parse data based on flags
    i = 2  # Start after flags

    if flag_more_data:
        if i + 2 <= len(message):
            # Speed comes in as km/h * 100
            speed_raw = int.from_bytes(message[i:i + 2], "little", signed=False)
            instant_speed = speed_raw / 100.0  # Convert to km/h
            i += 2

    if flag_average_speed:
        if i + 2 <= len(message):
            # Average speed comes in as km/h * 100
            avg_speed_raw = int.from_bytes(message[i:i + 2], "little", signed=False)
            average_speed = avg_speed_raw / 100.0  # Convert to km/h
            i += 2

    if flag_instantaneous_cadence:
        if i + 2 <= len(message):
            cadence_raw = int.from_bytes(message[i:i + 2], "little", signed=False)
            instant_cadence = cadence_raw / 2
            i += 2

    if flag_average_cadence:
        if i + 2 <= len(message):
            avg_cadence_raw = int.from_bytes(message[i:i + 2], "little", signed=False)
            average_cadence = avg_cadence_raw / 2
            i += 2

    if flag_total_distance:
        if i + 3 <= len(message):
            distance_raw = int.from_bytes(message[i:i + 3], "little", signed=False)
            total_distance = distance_raw
            i += 3

    if flag_resistance_level:
        if i + 2 <= len(message):
            resistance_raw = int.from_bytes(message[i:i + 2], "little", signed=True)
            resistance_level = resistance_raw
            i += 2

    if flag_instantaneous_power:
        if i + 2 <= len(message):
            power_raw = int.from_bytes(message[i:i + 2], "little", signed=True)
            instant_power = power_raw
            i += 2

    if flag_average_power:
        if i + 2 <= len(message):
            avg_power_raw = int.from_bytes(message[i:i + 2], "little", signed=True)
            average_power = avg_power_raw
            i += 2

    if flag_expended_energy:
        if i + 5 <= len(message):
            total_energy = int.from_bytes(message[i:i + 2], "little", signed=False)
            energy_per_hour = int.from_bytes(message[i + 2:i + 4], "little", signed=False)
            energy_per_minute = int.from_bytes(message[i + 4:i + 5], "little", signed=False)
            i += 5

    if flag_heart_rate:
        if i + 1 <= len(message):
            heart_rate = int.from_bytes(message[i:i + 1], "little", signed=False)
            i += 1

    if flag_metabolic_equivalent:
        if i + 1 <= len(message):
            metabolic_equivalent = int.from_bytes(message[i:i + 1], "little", signed=False) / 10
            i += 1

    if flag_elapsed_time:
        if i + 2 <= len(message):
            elapsed_time = int.from_bytes(message[i:i + 2], "little", signed=False)
            i += 2

    if flag_remaining_time:
        if i + 2 <= len(message):
            remaining_time = int.from_bytes(message[i:i + 2], "little", signed=False)
            i += 2

    return IndoorBikeData(
        instant_speed,
        average_speed,
        instant_cadence,
        average_cadence,
        total_distance,
        resistance_level,
        instant_power,
        average_power,
        total_energy,
        energy_per_hour,
        energy_per_minute,
        heart_rate,
        metabolic_equivalent,
        elapsed_time,
        remaining_time
    )

def _parse_insideride_format(message) -> IndoorBikeData:
    """Parse InsideRide-specific FTMS format.
    
    Based on analysis, InsideRide appears to encode power data at byte position 9
    instead of following the standard FTMS field ordering.
    """
    # Parse flags (same as standard)
    flag_total_distance = bool(message[0] & 0b00010000)
    flag_elapsed_time = bool(message[1] & 0b00001000)
    
    # Initialize values
    instant_speed = None
    average_speed = None
    instant_cadence = None
    average_cadence = None
    total_distance = None
    resistance_level = None
    instant_power = None
    average_power = None
    total_energy = None
    energy_per_hour = None
    energy_per_minute = None
    heart_rate = None
    metabolic_equivalent = None
    elapsed_time = None
    remaining_time = None
    
    # Parse InsideRide-specific layout
    # Based on observed data patterns:
    # Bytes 2-4: Distance (3 bytes, little endian)
    # Bytes 5-6: Resistance (2 bytes, always 0 in our data)
    # Bytes 7-8: Standard power location (always 0 in InsideRide data)
    # Byte 9: Actual power (1 byte, InsideRide-specific)
    # Bytes 9-10: Should be elapsed time but power seems to be at byte 9
    
    if flag_total_distance and len(message) >= 5:
        distance_raw = int.from_bytes(message[2:5], "little", signed=False)
        total_distance = distance_raw
    
    # InsideRide appears to put power at byte 9 (single byte)
    if len(message) >= 10:
        instant_power = message[9]
    
    # Try to extract elapsed time from remaining bytes
    if flag_elapsed_time and len(message) >= 12:
        # Elapsed time might be at bytes 11-12 instead of 9-10
        elapsed_time = int.from_bytes(message[11:13], "little", signed=False)
    
    return IndoorBikeData(
        instant_speed,
        average_speed,
        instant_cadence,
        average_cadence,
        total_distance,
        resistance_level,
        instant_power,
        average_power,
        total_energy,
        energy_per_hour,
        energy_per_minute,
        heart_rate,
        metabolic_equivalent,
        elapsed_time,
        remaining_time
    ) 