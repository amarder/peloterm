"""Tests for FTMS (Fitness Machine Service) parsers."""

import pytest
from peloterm.devices.ftms_parsers import parse_indoor_bike_data, IndoorBikeData


class TestFTMSParsers:
    """Test FTMS parser functions."""

    def test_parse_indoor_bike_data_speed_present(self):
        """Test parsing when speed data is present (flag_more_data = 1)."""
        # Create FTMS message with speed data present
        # Flags: byte 0 = 0x01 (more_data=1), byte 1 = 0x00
        # Speed: 2500 (25.00 km/h) as little-endian uint16
        message = bytearray([
            0x01, 0x00,  # Flags: more_data=1, others=0
            0xC4, 0x09   # Speed: 2500 (25.00 km/h when divided by 100)
        ])
        
        result = parse_indoor_bike_data(message)
        
        assert result.instant_speed == 25.0
        assert result.average_speed is None
        assert result.instant_power is None
        assert result.instant_cadence is None

    def test_parse_indoor_bike_data_speed_absent(self):
        """Test parsing when speed data is absent (flag_more_data = 0)."""
        # Create FTMS message with no speed data
        # Flags: byte 0 = 0x00 (more_data=0), byte 1 = 0x00
        message = bytearray([
            0x00, 0x00   # Flags: more_data=0, others=0
        ])
        
        result = parse_indoor_bike_data(message)
        
        assert result.instant_speed is None
        assert result.average_speed is None
        assert result.instant_power is None
        assert result.instant_cadence is None

    def test_parse_indoor_bike_data_speed_and_power(self):
        """Test parsing when both speed and power data are present."""
        # Flags: byte 0 = 0x41 (more_data=1, instantaneous_power=1), byte 1 = 0x00
        # Speed: 3000 (30.00 km/h), Power: 200W
        message = bytearray([
            0x41, 0x00,  # Flags: more_data=1, instantaneous_power=1
            0xB8, 0x0B,  # Speed: 3000 (30.00 km/h)
            0xC8, 0x00   # Power: 200W
        ])
        
        result = parse_indoor_bike_data(message)
        
        assert result.instant_speed == 30.0
        assert result.instant_power == 200
        assert result.average_speed is None
        assert result.instant_cadence is None

    def test_parse_indoor_bike_data_realistic_speeds(self):
        """Test parsing with realistic cycling speeds."""
        test_cases = [
            (1500, 15.0),  # 15 km/h - slow indoor pace
            (2000, 20.0),  # 20 km/h - moderate pace
            (2500, 25.0),  # 25 km/h - good pace
            (3000, 30.0),  # 30 km/h - fast pace
            (3500, 35.0),  # 35 km/h - very fast
            (4000, 40.0),  # 40 km/h - sprint pace
            (5000, 50.0),  # 50 km/h - maximum realistic
        ]
        
        for raw_speed, expected_kmh in test_cases:
            message = bytearray([
                0x01, 0x00,  # Flags: more_data=1
                raw_speed & 0xFF, (raw_speed >> 8) & 0xFF  # Speed as little-endian
            ])
            
            result = parse_indoor_bike_data(message)
            assert result.instant_speed == expected_kmh, \
                f"Failed for raw speed {raw_speed}: expected {expected_kmh}, got {result.instant_speed}"

    def test_parse_indoor_bike_data_edge_cases(self):
        """Test parsing edge cases for speed data."""
        # Test zero speed
        message_zero = bytearray([
            0x01, 0x00,  # Flags: more_data=1
            0x00, 0x00   # Speed: 0 (0.00 km/h)
        ])
        result = parse_indoor_bike_data(message_zero)
        assert result.instant_speed == 0.0

        # Test maximum uint16 speed value
        message_max = bytearray([
            0x01, 0x00,  # Flags: more_data=1
            0xFF, 0xFF   # Speed: 65535 (655.35 km/h - unrealistic but valid)
        ])
        result = parse_indoor_bike_data(message_max)
        assert result.instant_speed == 655.35

    def test_parse_indoor_bike_data_average_speed(self):
        """Test parsing average speed when flag is set."""
        # Flags: byte 0 = 0x03 (more_data=1, average_speed=1), byte 1 = 0x00
        # Instant speed: 2500 (25.00 km/h), Average speed: 2200 (22.00 km/h)
        message = bytearray([
            0x03, 0x00,  # Flags: more_data=1, average_speed=1
            0xC4, 0x09,  # Instant speed: 2500 (25.00 km/h)
            0x98, 0x08   # Average speed: 2200 (22.00 km/h)
        ])
        
        result = parse_indoor_bike_data(message)
        
        assert result.instant_speed == 25.0
        assert result.average_speed == 22.0

    def test_parse_indoor_bike_data_cadence(self):
        """Test parsing cadence data."""
        # Flags: byte 0 = 0x05 (more_data=1, instantaneous_cadence=1), byte 1 = 0x00
        # Speed: 2500 (25.00 km/h), Cadence: 180 (90 RPM when divided by 2)
        message = bytearray([
            0x05, 0x00,  # Flags: more_data=1, instantaneous_cadence=1
            0xC4, 0x09,  # Speed: 2500 (25.00 km/h)
            0xB4, 0x00   # Cadence: 180 (90 RPM when divided by 2)
        ])
        
        result = parse_indoor_bike_data(message)
        
        assert result.instant_speed == 25.0
        assert result.instant_cadence == 90.0

    def test_parse_indoor_bike_data_complex_message(self):
        """Test parsing a complex message with multiple data fields."""
        # Flags: byte 0 = 0x47 (more_data=1, average_speed=1, instantaneous_cadence=1, instantaneous_power=1)
        #        byte 1 = 0x02 (heart_rate=1)
        # Data: instant_speed, average_speed, instant_cadence, instant_power, heart_rate
        message = bytearray([
            0x47, 0x02,  # Flags
            0xC4, 0x09,  # Instant speed: 2500 (25.00 km/h)
            0x98, 0x08,  # Average speed: 2200 (22.00 km/h)
            0xB4, 0x00,  # Cadence: 180 (90 RPM)
            0xC8, 0x00,  # Power: 200W
            0x96         # Heart rate: 150 BPM
        ])
        
        result = parse_indoor_bike_data(message)
        
        assert result.instant_speed == 25.0
        assert result.average_speed == 22.0
        assert result.instant_cadence == 90.0
        assert result.instant_power == 200
        assert result.heart_rate == 150

    def test_parse_indoor_bike_data_power_only(self):
        """Test parsing when only power data is present (no speed)."""
        # Flags: byte 0 = 0x40 (instantaneous_power=1), byte 1 = 0x00
        # Power: 250W
        message = bytearray([
            0x40, 0x00,  # Flags: instantaneous_power=1, more_data=0
            0xFA, 0x00   # Power: 250W
        ])
        
        result = parse_indoor_bike_data(message)
        
        assert result.instant_speed is None  # No speed data should be parsed
        assert result.instant_power == 250
        assert result.instant_cadence is None

    def test_parse_indoor_bike_data_regression_test(self):
        """Regression test to ensure the speed parsing bug doesn't return.
        
        This test specifically validates that we don't parse speed data
        when flag_more_data = 0, which was the original bug.
        """
        # This message has flag_more_data = 0 but contains power data
        # The old buggy code would try to parse the power bytes as speed
        message = bytearray([
            0x40, 0x00,  # Flags: more_data=0, instantaneous_power=1
            0xFA, 0x00   # Power: 250W (should NOT be parsed as speed)
        ])
        
        result = parse_indoor_bike_data(message)
        
        # Critical assertion: speed should be None, not some garbage value
        assert result.instant_speed is None, \
            "Speed should be None when flag_more_data=0 (regression test failed)"
        assert result.instant_power == 250, \
            "Power should still be parsed correctly"

    def test_parse_indoor_bike_data_empty_message(self):
        """Test parsing with minimal message (just flags)."""
        message = bytearray([0x00, 0x00])  # No data flags set
        
        result = parse_indoor_bike_data(message)
        
        # All values should be None
        assert result.instant_speed is None
        assert result.average_speed is None
        assert result.instant_cadence is None
        assert result.average_cadence is None
        assert result.instant_power is None
        assert result.average_power is None
        assert result.heart_rate is None

    def test_parse_indoor_bike_data_return_type(self):
        """Test that the function returns the correct type."""
        message = bytearray([0x01, 0x00, 0xC4, 0x09])  # Simple speed message
        
        result = parse_indoor_bike_data(message)
        
        assert isinstance(result, IndoorBikeData)
        assert hasattr(result, 'instant_speed')
        assert hasattr(result, 'instant_power')
        assert hasattr(result, 'instant_cadence') 