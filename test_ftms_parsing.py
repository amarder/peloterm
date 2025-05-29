#!/usr/bin/env python3

"""Test script to debug FTMS parsing issues."""

from peloterm.devices.ftms_parsers import parse_indoor_bike_data

def test_ftms_parsing():
    """Test FTMS parsing with various sample data."""
    print("=" * 60)
    print("FTMS Parsing Test")
    print("=" * 60)
    
    # Test case 1: Minimal message with just flags
    print("\nTest 1: Minimal message with just flags")
    minimal_data = bytearray([0x00, 0x00])  # No flags set
    result = parse_indoor_bike_data(minimal_data)
    
    # Test case 2: Message with speed flag set
    print("\nTest 2: Message with speed flag set")
    speed_data = bytearray([0x01, 0x00, 0x10, 0x27])  # flag_more_data=1, speed=100.00 km/h (0x2710 = 10000 centikm/h)
    result = parse_indoor_bike_data(speed_data)
    
    # Test case 3: Message with power flag set
    print("\nTest 3: Message with power flag set")
    power_data = bytearray([0x40, 0x00, 0x96, 0x00])  # flag_instantaneous_power=1, power=150W (0x0096 = 150)
    result = parse_indoor_bike_data(power_data)
    
    # Test case 4: Message with both speed and power
    print("\nTest 4: Message with both speed and power")
    combined_data = bytearray([0x41, 0x00, 0x88, 0x13, 0x96, 0x00])  # speed + power flags, 50 km/h, 150W
    result = parse_indoor_bike_data(combined_data)
    
    # Test case 5: Message with cadence flag
    print("\nTest 5: Message with cadence flag")
    cadence_data = bytearray([0x04, 0x00, 0xA0, 0x00])  # flag_instantaneous_cadence=1, cadence=80 rpm (0x00A0 = 160, /2 = 80)
    result = parse_indoor_bike_data(cadence_data)
    
    # Test case 6: Message with distance flag
    print("\nTest 6: Message with distance flag")
    distance_data = bytearray([0x10, 0x00, 0x10, 0x27, 0x00])  # flag_total_distance=1, distance=10000m (0x002710)
    result = parse_indoor_bike_data(distance_data)
    
    # Test case 7: Message with heart rate flag
    print("\nTest 7: Message with heart rate flag")
    hr_data = bytearray([0x00, 0x02, 0x78])  # flag_heart_rate=1, hr=120 bpm (0x78 = 120)
    result = parse_indoor_bike_data(hr_data)
    
    # Test case 8: Realistic trainer data (common combination)
    print("\nTest 8: Realistic trainer data combination")
    realistic_data = bytearray([
        0x54, 0x02,  # Flags: speed + cadence + distance + heart_rate
        0x88, 0x13,  # Speed: 50.00 km/h (0x1388 = 5000 centikm/h)
        0xA0, 0x00,  # Cadence: 80 rpm (0x00A0 = 160, /2 = 80)
        0x10, 0x27, 0x00,  # Distance: 10000m (0x002710)
        0x78  # Heart rate: 120 bpm (0x78 = 120)
    ])
    result = parse_indoor_bike_data(realistic_data)
    
    print("\n" + "=" * 60)
    print("FTMS Parsing Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_ftms_parsing() 