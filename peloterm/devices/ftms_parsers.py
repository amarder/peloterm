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

    if flag_more_data == 0:
        # Speed comes in as km/h * 100
        instant_speed = int.from_bytes(message[i:i + 2], "little", signed=False) / 100.0  # Convert to km/h
        i += 2

    if flag_average_speed:
        # Average speed comes in as km/h * 100
        average_speed = int.from_bytes(message[i:i + 2], "little", signed=False) / 100.0  # Convert to km/h
        i += 2

    if flag_instantaneous_cadence:
        instant_cadence = int.from_bytes(message[i:i + 2], "little", signed=False) / 2
        i += 2

    if flag_average_cadence:
        average_cadence = int.from_bytes(message[i:i + 2], "little", signed=False) / 2
        i += 2

    if flag_total_distance:
        total_distance = int.from_bytes(message[i:i + 3], "little", signed=False)
        i += 3

    if flag_resistance_level:
        resistance_level = int.from_bytes(message[i:i + 2], "little", signed=True)
        i += 2

    if flag_instantaneous_power:
        instant_power = int.from_bytes(message[i:i + 2], "little", signed=True)
        i += 2

    if flag_average_power:
        average_power = int.from_bytes(message[i:i + 2], "little", signed=True)
        i += 2

    if flag_expended_energy:
        total_energy = int.from_bytes(message[i:i + 2], "little", signed=False)
        energy_per_hour = int.from_bytes(message[i + 2:i + 4], "little", signed=False)
        energy_per_minute = int.from_bytes(message[i + 4:i + 5], "little", signed=False)
        i += 5

    if flag_heart_rate:
        heart_rate = int.from_bytes(message[i:i + 1], "little", signed=False)
        i += 1

    if flag_metabolic_equivalent:
        metabolic_equivalent = int.from_bytes(message[i:i + 1], "little", signed=False) / 10
        i += 1

    if flag_elapsed_time:
        elapsed_time = int.from_bytes(message[i:i + 2], "little", signed=False)
        i += 2

    if flag_remaining_time:
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