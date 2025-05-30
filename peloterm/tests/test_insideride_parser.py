#!/usr/bin/env python3
"""
Tests for InsideRide FTMS Parser

This test suite validates that the InsideRide-specific FTMS parser
correctly extracts power, speed, and timing data from real trainer packets.
"""

import json
import unittest
import sys
from pathlib import Path

# Add the peloterm package to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from peloterm.devices.insideride_ftms_parser import (
    parse_insideride_ftms_data,
    is_valid_insideride_data,
    format_insideride_data,
    InsideRideBikeData
)

class TestInsideRideParser(unittest.TestCase):
    """Test cases for InsideRide FTMS parser."""
    
    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests."""
        test_data_file = Path(__file__).parent / "raw_ftms_data.json"
        
        try:
            with open(test_data_file, 'r') as f:
                data = json.load(f)
            cls.test_packets = data.get('packets', [])
            cls.collection_info = data.get('collection_info', {})
        except FileNotFoundError:
            cls.test_packets = []
            cls.collection_info = {}
    
    def test_parser_with_real_data(self):
        """Test parser with real InsideRide data packets."""
        self.assertGreater(len(self.test_packets), 0, "No test data available")
        
        valid_packets = 0
        power_readings = []
        speed_readings = []
        
        for packet in self.test_packets:
            raw_bytes = packet.get('raw_bytes', [])
            if not raw_bytes:
                continue
                
            # Parse the packet
            bike_data = parse_insideride_ftms_data(bytearray(raw_bytes))
            
            # Validate the data
            if is_valid_insideride_data(bike_data):
                valid_packets += 1
                
                if bike_data.instant_power is not None:
                    power_readings.append(bike_data.instant_power)
                
                if bike_data.instant_speed is not None:
                    speed_readings.append(bike_data.instant_speed)
        
        # Assertions about data quality
        self.assertGreater(valid_packets, 0, "No valid packets parsed")
        self.assertGreater(len(power_readings), 0, "No power readings extracted")
        self.assertGreater(len(speed_readings), 0, "No speed readings extracted")
        
        # Test that we get reasonable power values
        max_power = max(power_readings)
        avg_power = sum(power_readings) / len(power_readings)
        non_zero_power = [p for p in power_readings if p > 0]
        
        self.assertGreater(max_power, 50, f"Max power too low: {max_power}W")
        self.assertLess(max_power, 300, f"Max power too high: {max_power}W")
        self.assertGreater(len(non_zero_power), 10, "Not enough non-zero power readings")
        
        # Test that we get reasonable speed values  
        max_speed = max(speed_readings)
        non_zero_speed = [s for s in speed_readings if s > 0]
        
        self.assertGreater(max_speed, 10, f"Max speed too low: {max_speed:.1f} km/h")
        self.assertLess(max_speed, 50, f"Max speed too high: {max_speed:.1f} km/h")
        self.assertGreater(len(non_zero_speed), 10, "Not enough non-zero speed readings")
        
        print(f"\n✅ Parser Test Results:")
        print(f"   📦 Total packets: {len(self.test_packets)}")
        print(f"   ✓ Valid packets: {valid_packets}")
        print(f"   ⚡ Power range: {min(power_readings)}-{max_power}W (avg: {avg_power:.1f}W)")
        print(f"   🚀 Speed range: {min(speed_readings):.1f}-{max_speed:.1f} km/h")
        print(f"   📊 Non-zero readings: {len(non_zero_power)} power, {len(non_zero_speed)} speed")
    
    def test_known_packet_values(self):
        """Test parser with specific known packet values."""
        # Test packet from the real data analysis
        test_packet = bytearray([0x70, 0x08, 0x9b, 0x05, 0x0e, 0x00, 0x00, 0x00, 0x00, 0x62, 0x00, 0x06, 0x00, 0x00, 0x00])
        
        bike_data = parse_insideride_ftms_data(test_packet)
        
        # Expected values based on analysis
        self.assertEqual(bike_data.instant_power, 98, "Power should be 98W")
        self.assertAlmostEqual(bike_data.instant_speed, 18.0, places=1, msg="Speed should be ~18 km/h (5 m/s)")
        self.assertEqual(bike_data.elapsed_time, 6, "Elapsed time should be 6 seconds")
        self.assertEqual(bike_data.resistance_level, 0, "Resistance should be 0")
        
        # Validate the data
        self.assertTrue(is_valid_insideride_data(bike_data), "Parsed data should be valid")
    
    def test_zero_power_packet(self):
        """Test parser with zero power packet."""
        # First packet from real data
        test_packet = bytearray([0x70, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        
        bike_data = parse_insideride_ftms_data(test_packet)
        
        self.assertEqual(bike_data.instant_power, 0, "Power should be 0W")
        self.assertEqual(bike_data.instant_speed, 0.0, "Speed should be 0 km/h")
        self.assertEqual(bike_data.elapsed_time, 0, "Elapsed time should be 0 seconds")
        
        self.assertTrue(is_valid_insideride_data(bike_data), "Zero values should be valid")
    
    def test_invalid_packet(self):
        """Test parser with invalid/short packet."""
        short_packet = bytearray([0x70, 0x08])  # Too short
        
        bike_data = parse_insideride_ftms_data(short_packet)
        
        # Should return None values for short packet
        self.assertIsNone(bike_data.instant_power)
        self.assertIsNone(bike_data.instant_speed)
        self.assertIsNone(bike_data.elapsed_time)
        self.assertIsNone(bike_data.resistance_level)
    
    def test_data_validation(self):
        """Test data validation function."""
        # Valid data
        valid_data = InsideRideBikeData(100, 25.2, 120, 0)
        self.assertTrue(is_valid_insideride_data(valid_data))
        
        # Invalid power (too high)
        invalid_power = InsideRideBikeData(600, 25.2, 120, 0)
        self.assertFalse(is_valid_insideride_data(invalid_power))
        
        # Invalid speed (too high)
        invalid_speed = InsideRideBikeData(100, 100.0, 120, 0)
        self.assertFalse(is_valid_insideride_data(invalid_speed))
        
        # Invalid time (negative)
        invalid_time = InsideRideBikeData(100, 25.2, -10, 0)
        self.assertFalse(is_valid_insideride_data(invalid_time))
    
    def test_data_formatting(self):
        """Test data formatting function."""
        bike_data = InsideRideBikeData(150, 27.5, 185, 0)
        formatted = format_insideride_data(bike_data)
        
        self.assertIn("150W", formatted)
        self.assertIn("27.5km/h", formatted)
        self.assertIn("3:05", formatted)  # 185 seconds = 3:05
        
        # Test with None values
        partial_data = InsideRideBikeData(100, None, None, None)
        formatted_partial = format_insideride_data(partial_data)
        self.assertEqual("Power: 100W", formatted_partial)
        
        # Test with all None values
        empty_data = InsideRideBikeData(None, None, None, None)
        formatted_empty = format_insideride_data(empty_data)
        self.assertEqual("No data", formatted_empty)
    
    def test_power_speed_correlation(self):
        """Test that power and speed show reasonable correlation."""
        if not self.test_packets:
            self.skipTest("No test data available")
        
        power_speed_pairs = []
        
        for packet in self.test_packets:
            raw_bytes = packet.get('raw_bytes', [])
            if not raw_bytes:
                continue
                
            bike_data = parse_insideride_ftms_data(bytearray(raw_bytes))
            
            if (bike_data.instant_power is not None and 
                bike_data.instant_speed is not None and
                bike_data.instant_power > 0 and 
                bike_data.instant_speed > 0):
                power_speed_pairs.append((bike_data.instant_power, bike_data.instant_speed))
        
        self.assertGreater(len(power_speed_pairs), 5, "Need multiple power/speed pairs to test correlation")
        
        # Simple correlation test: higher power should generally mean higher speed
        high_power_pairs = [(p, s) for p, s in power_speed_pairs if p > 120]
        low_power_pairs = [(p, s) for p, s in power_speed_pairs if p < 80]
        
        if high_power_pairs and low_power_pairs:
            avg_high_speed = sum(s for p, s in high_power_pairs) / len(high_power_pairs)
            avg_low_speed = sum(s for p, s in low_power_pairs) / len(low_power_pairs)
            
            self.assertGreater(avg_high_speed, avg_low_speed, 
                             f"Higher power should mean higher speed: {avg_high_speed:.1f} vs {avg_low_speed:.1f}")


def main():
    """Run the tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main() 