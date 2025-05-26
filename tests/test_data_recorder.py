"""Tests for data recording and FIT file generation."""

import pytest
import time
import tempfile
from pathlib import Path
from peloterm.data_recorder import RideRecorder, DataPoint
from datetime import datetime, timezone
from fitparse import FitFile, FitParseError


class TestDataPoint:
    """Test DataPoint class."""
    
    def test_data_point_creation(self):
        """Test creating a data point."""
        timestamp = time.time()
        metrics = {"power": 250, "cadence": 90, "heart_rate": 150}
        
        data_point = DataPoint(timestamp, metrics)
        
        assert data_point.timestamp == timestamp
        assert data_point.metrics == metrics
        assert data_point.datetime is not None


class TestRideRecorder:
    """Test RideRecorder class."""
    
    @pytest.fixture
    def recorder(self):
        """Create a test recorder."""
        return RideRecorder()
    
    def test_recorder_initialization(self, recorder):
        """Test recorder initialization."""
        assert recorder.start_time is None
        assert recorder.end_time is None
        assert len(recorder.data_points) == 0
        assert not recorder.is_recording
        assert recorder.rides_dir.exists()
    
    def test_start_recording(self, recorder):
        """Test starting a recording."""
        recorder.start_recording()
        
        assert recorder.is_recording
        assert recorder.start_time is not None
        assert len(recorder.data_points) == 0
    
    def test_add_data_point(self, recorder):
        """Test adding data points."""
        recorder.start_recording()
        
        timestamp = time.time()
        metrics = {"power": 200, "cadence": 85}
        
        recorder.add_data_point(timestamp, metrics)
        
        assert len(recorder.data_points) == 1
        assert recorder.data_points[0].timestamp == timestamp
        assert recorder.data_points[0].metrics == metrics
    
    def test_add_data_point_filters_none(self, recorder):
        """Test that None values are filtered out."""
        recorder.start_recording()
        
        timestamp = time.time()
        metrics = {"power": 200, "cadence": None, "heart_rate": 150}
        
        recorder.add_data_point(timestamp, metrics)
        
        assert len(recorder.data_points) == 1
        assert recorder.data_points[0].metrics == {"power": 200, "heart_rate": 150}
    
    def test_add_data_point_when_not_recording(self, recorder):
        """Test that data points are not added when not recording."""
        timestamp = time.time()
        metrics = {"power": 200}
        
        recorder.add_data_point(timestamp, metrics)
        
        assert len(recorder.data_points) == 0
    
    def test_stop_recording_without_data(self, recorder):
        """Test stopping recording without data points raises error."""
        recorder.start_recording()
        
        with pytest.raises(ValueError, match="No data points to export"):
            recorder.stop_recording()
    
    def test_stop_recording_not_started(self, recorder):
        """Test stopping recording when not started raises error."""
        with pytest.raises(ValueError, match="Not currently recording"):
            recorder.stop_recording()
    
    def test_complete_recording_flow(self, recorder):
        """Test a complete recording flow."""
        # Start recording
        recorder.start_recording()
        assert recorder.is_recording
        
        # Add some data points
        base_time = time.time()
        for i in range(10):
            timestamp = base_time + i
            metrics = {
                "power": 200 + i * 10,
                "cadence": 85 + i,
                "heart_rate": 150 + i,
                "speed": 25.0 + i * 0.5
            }
            recorder.add_data_point(timestamp, metrics)
        
        assert len(recorder.data_points) == 10
        
        # Stop recording
        fit_file_path = recorder.stop_recording()
        
        assert not recorder.is_recording
        assert recorder.end_time is not None
        assert fit_file_path is not None
        assert Path(fit_file_path).exists()
        assert Path(fit_file_path).suffix == ".fit"
        
        # Clean up
        Path(fit_file_path).unlink()
    
    def test_ride_summary(self, recorder):
        """Test ride summary generation."""
        recorder.start_recording()
        
        # Add test data
        base_time = time.time()
        power_values = [100, 200, 300, 250, 150]
        
        for i, power in enumerate(power_values):
            timestamp = base_time + i
            metrics = {
                "power": power,
                "cadence": 80 + i,
                "heart_rate": 140 + i
            }
            recorder.add_data_point(timestamp, metrics)
        
        recorder.end_time = base_time + len(power_values)
        
        summary = recorder.get_ride_summary()
        
        assert summary["data_points"] == 5
        assert summary["avg_power"] == sum(power_values) / len(power_values)
        assert summary["max_power"] == max(power_values)
        assert summary["min_power"] == min(power_values)
        assert "avg_cadence" in summary
        assert "avg_heart_rate" in summary
    
    def test_fit_file_generation(self, recorder):
        """Test FIT file generation with valid data."""
        recorder.start_recording()
        
        # Add realistic cycling data
        base_time = time.time()
        for i in range(60):  # 1 minute of data
            timestamp = base_time + i
            metrics = {
                "power": 250 + (i % 20) * 5,  # Power varies between 250-345W
                "cadence": 90 + (i % 10),      # Cadence varies between 90-99 RPM
                "heart_rate": 150 + (i % 15),  # HR varies between 150-164 BPM
                "speed": 30.0 + (i % 5) * 0.5  # Speed varies between 30-32 km/h
            }
            recorder.add_data_point(timestamp, metrics)
        
        # Stop recording and generate FIT file
        fit_file_path = recorder.stop_recording()
        
        # Verify file exists and has reasonable size
        fit_path = Path(fit_file_path)
        assert fit_path.exists()
        assert fit_path.suffix == ".fit"
        assert fit_path.stat().st_size > 100  # Should be larger than 100 bytes
        
        # Check file can be read as binary
        with open(fit_path, 'rb') as f:
            content = f.read()
            assert content.startswith(b'\x0e')  # FIT file header size
            assert b'.FIT' in content  # FIT file signature
        
        # Clean up
        fit_path.unlink()
    
    def test_custom_ride_name(self, recorder):
        """Test recording with custom ride name."""
        custom_name = "test_ride"
        recorder.start_recording()
        recorder.ride_name = custom_name
        
        # Add minimal data
        timestamp = time.time()
        recorder.add_data_point(timestamp, {"power": 200})
        
        fit_file_path = recorder.stop_recording()
        
        # Check filename contains custom name
        assert custom_name in Path(fit_file_path).name
        
        # Clean up
        Path(fit_file_path).unlink()

@pytest.fixture
def ride_recorder(tmp_path):
    """Fixture to create a RideRecorder instance with a temporary rides_dir."""
    recorder = RideRecorder()
    # Override the default rides_dir to use a temporary directory for tests
    recorder.rides_dir = tmp_path / "rides"
    recorder.rides_dir.mkdir(parents=True, exist_ok=True)
    return recorder

def test_generate_and_parse_fit_file(ride_recorder):
    """
    Test that a generated FIT file can be parsed by fitparse
    and contains the expected data.
    """
    recorder = ride_recorder
    
    recorder.start_recording()
    
    ts1 = time.time()
    recorder.add_data_point(ts1, {"power": 100, "cadence": 80, "heart_rate": 120, "speed": 25.0})
    time.sleep(0.01) # Ensure distinct timestamps if tests run very fast
    ts2 = time.time()
    recorder.add_data_point(ts2, {"power": 110, "cadence": 82, "heart_rate": 122, "speed": 26.0})
    time.sleep(0.01)
    ts3 = time.time()
    recorder.add_data_point(ts3, {"power": 105, "cadence": 81, "heart_rate": 121, "speed": 25.5})
    
    fit_file_path_str = recorder.stop_recording()
    fit_file_path = Path(fit_file_path_str)
    
    assert fit_file_path.exists(), "FIT file was not created"
    
    try:
        fitfile = FitFile(str(fit_file_path))
        fitfile.parse()
    except FitParseError as e:
        pytest.fail(f"Fitparse failed to parse the generated FIT file: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during FIT file parsing: {e}")
        
    record_messages = list(fitfile.get_messages("record"))
    assert len(record_messages) == 3, "Incorrect number of record messages"
    
    first_record = record_messages[0]
    fit_epoch_start = datetime(1989, 12, 31, tzinfo=timezone.utc)

    # Helper to get field value from a message
    def get_value_from_message(message, field_name):
        for field_data in message:
            if field_data.name == field_name:
                return field_data.value
        return None

    record_timestamp_value = get_value_from_message(first_record, "timestamp")
    assert record_timestamp_value is not None, "Timestamp field missing in record message"
    
    # record_timestamp_value from fitparse is a naive datetime representing UTC.
    # We need to make it timezone-aware before calling .timestamp() to ensure correct conversion.
    record_datetime_utc = record_timestamp_value.replace(tzinfo=timezone.utc)
    
    assert abs(record_datetime_utc.timestamp() - ts1) <= 1, f"Timestamp mismatch. Expected {ts1}, got {record_datetime_utc.timestamp()} (original naive was {record_timestamp_value})"

    power_value = get_value_from_message(first_record, "power")
    assert power_value is not None, "Power field missing in record message"
    assert power_value == 100, "Power value mismatch in first record"
    
    cadence_value = get_value_from_message(first_record, "cadence")
    assert cadence_value is not None, "Cadence field missing in record message"
    assert cadence_value == 80, "Cadence value mismatch in first record"

    heart_rate_value = get_value_from_message(first_record, "heart_rate")
    assert heart_rate_value is not None, "Heart rate field missing in record message"
    assert heart_rate_value == 120, "Heart rate value mismatch in first record"

    speed_value = get_value_from_message(first_record, "speed")
    assert speed_value is not None, "Speed field missing in record message"
    
    # Original speed was 25.0 km/h. This is 25.0 / 3.6 m/s.
    # fitparse applies the scale factor (1000 for speed) and should return the value in m/s.
    expected_speed_mps = 25.0 / 3.6
    assert abs(speed_value - expected_speed_mps) < 0.001, f"Speed value mismatch. Expected approx {expected_speed_mps:.3f} m/s, got {speed_value}"

    session_messages = list(fitfile.get_messages("session"))
    assert len(session_messages) == 1, "Should have one session message"
    session_msg = session_messages[0]
    
    avg_power_value = get_value_from_message(session_msg, "avg_power")
    assert avg_power_value is not None, "avg_power field missing in session message"
    assert avg_power_value == 105, f"Average power mismatch. Expected 105, got {avg_power_value}"

    total_elapsed_time_value = get_value_from_message(session_msg, "total_elapsed_time")
    assert total_elapsed_time_value is not None, "total_elapsed_time field missing"
    
    # total_elapsed_time from fitparse is in seconds (it applies the scale factor of 1000).
    # Original duration was recorder.end_time - recorder.start_time in seconds.
    expected_duration_s = recorder.end_time - recorder.start_time
    assert abs(total_elapsed_time_value - expected_duration_s) < 0.001, f"Total elapsed time mismatch. Expected {expected_duration_s:.3f} s, got {total_elapsed_time_value}"

def test_empty_ride_does_not_generate_file(ride_recorder):
    """Test that stop_recording raises an error if no data points."""
    recorder = ride_recorder
    recorder.start_recording()
    with pytest.raises(ValueError, match="No data points to export"):
        recorder.stop_recording()

def test_stop_recording_without_start_raises_error(ride_recorder):
    """Test that stop_recording raises an error if not recording."""
    recorder = ride_recorder
    with pytest.raises(ValueError, match="Not currently recording"):
        recorder.stop_recording()

def test_add_data_point_when_not_recording(ride_recorder):
    """Test that add_data_point does nothing if not recording."""
    recorder = ride_recorder
    recorder.add_data_point(time.time(), {"power": 100})
    assert len(recorder.data_points) == 0

def test_ride_name_in_filename(ride_recorder):
    """Test that the ride name is included in the FIT file name if provided."""
    recorder = ride_recorder
    recorder.ride_name = "TestRide"
    recorder.start_recording()
    recorder.add_data_point(time.time(), {"power": 100})
    fit_file_path_str = recorder.stop_recording()
    assert "TestRide" in fit_file_path_str
    assert Path(fit_file_path_str).exists()

def test_no_ride_name_in_filename(ride_recorder):
    """Test that a default name is used if no ride name is provided."""
    recorder = ride_recorder
    # recorder.ride_name is None by default
    recorder.start_recording()
    recorder.add_data_point(time.time(), {"power": 100})
    fit_file_path_str = recorder.stop_recording()
    assert "_ride.fit" in fit_file_path_str # Default suffix
    assert Path(fit_file_path_str).exists()

# Example of a helper to print messages for debugging
# from fitparse.utils import FitParseError
# def print_fit_messages(file_path):
#     try:
#         fitfile = FitFile(file_path)
#         for message in fitfile.get_messages():
#             print(f"Message Type: {message.name}")
#             for field in message:
#                 print(f"  {field.name}: {field.value} ({field.units})")
#             print("-" * 20)
#     except FitParseError as e:
#         print(f"Error parsing FIT file: {e}")

# If you want to run this test standalone for quick checks:
# if __name__ == "__main__":
#     # Create a temporary directory for this specific run
#     import tempfile
#     with tempfile.TemporaryDirectory() as tmpdir:
#         mock_tmp_path = Path(tmpdir)
        
#         # Manually create a recorder instance for the test
#         recorder_instance = RideRecorder()
#         recorder_instance.rides_dir = mock_tmp_path / "rides"
#         recorder_instance.rides_dir.mkdir(parents=True, exist_ok=True)

#         print(f"Running test_generate_and_parse_fit_file in {recorder_instance.rides_dir}...")
#         test_generate_and_parse_fit_file(recorder_instance)
#         print("Test completed.")

#         # Example of printing a generated file for manual inspection:
#         # Assuming the test creates a file. You'd need to know its name or find it.
#         # generated_files = list((mock_tmp_path / "rides").glob("*.fit"))
#         # if generated_files:
#         #     print_fit_messages(str(generated_files[0])) 


class TestStravaCompatibility:
    """Test FIT file compatibility with Strava requirements.
    
    This comprehensive test suite validates that FIT files generated by Peloterm
    contain all the required fields and data structures that Strava expects for
    successful activity uploads. The tests cover:
    
    - Required message types (file_id, session, record)
    - Essential fields in each message type
    - Data quality and consistency checks
    - Monotonic progression of timestamps and distance
    - Realistic value ranges for all metrics
    - Edge cases and minimal ride requirements
    
    These tests help ensure that users can successfully upload their Peloterm
    rides to Strava without encountering parsing or validation errors.
    """
    
    @pytest.fixture
    def strava_recorder(self, tmp_path):
        """Create a recorder for Strava compatibility tests."""
        recorder = RideRecorder()
        recorder.rides_dir = tmp_path / "rides"
        recorder.rides_dir.mkdir(parents=True, exist_ok=True)
        return recorder
    
    def _get_field_value(self, message, field_name):
        """Helper to extract field value from FIT message."""
        for field_data in message:
            if field_data.name == field_name:
                return field_data.value
        return None
    
    def _create_realistic_ride_data(self, recorder, duration_minutes=30):
        """Create realistic cycling data for testing."""
        recorder.start_recording()
        
        base_time = time.time()
        data_points = duration_minutes * 60  # 1 data point per second
        cumulative_distance = 0.0
        
        for i in range(data_points):
            timestamp = base_time + i  # Each data point is 1 second apart
            
            # Simulate realistic cycling metrics with some variation
            power_base = 200
            power_variation = 50 * (0.5 - abs((i % 120) - 60) / 60)  # Varies over 2-minute intervals
            power = max(0, power_base + power_variation + (i % 10 - 5) * 5)
            
            cadence = 85 + (i % 20) - 10  # Varies between 75-95 RPM
            heart_rate = 140 + min(30, i // 60) + (i % 15) - 7  # Gradually increases, then varies
            speed = 28.0 + (i % 30) * 0.2 - 3  # Varies between 25-31 km/h
            speed = max(0, speed)  # Ensure speed is never negative
            
            # Calculate cumulative distance properly
            if i > 0:
                time_delta = 1.0  # 1 second between data points
                distance_increment = (speed / 3.6) * time_delta  # meters
                cumulative_distance += distance_increment
            
            metrics = {
                "power": int(power),
                "cadence": max(0, int(cadence)),
                "heart_rate": max(60, int(heart_rate)),
                "speed": speed,
                "distance": cumulative_distance
            }
            
            recorder.add_data_point(timestamp, metrics)
        
        return recorder.stop_recording()
    
    def test_strava_required_file_structure(self, strava_recorder):
        """Test that FIT file has the basic structure Strava expects."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=5)
        
        # Parse the FIT file
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        # Check for required message types
        file_id_messages = list(fitfile.get_messages("file_id"))
        assert len(file_id_messages) == 1, "FIT file must contain exactly one file_id message"
        
        session_messages = list(fitfile.get_messages("session"))
        assert len(session_messages) == 1, "FIT file must contain exactly one session message"
        
        record_messages = list(fitfile.get_messages("record"))
        assert len(record_messages) > 0, "FIT file must contain record messages"
        
        # Verify file_id message has required fields
        file_id = file_id_messages[0]
        assert self._get_field_value(file_id, "type") == "activity", "File type must be 'activity'"
        assert self._get_field_value(file_id, "time_created") is not None, "File must have creation time"
    
    def test_strava_session_message_requirements(self, strava_recorder):
        """Test that session message contains all fields Strava expects."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=10)
        
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        session_messages = list(fitfile.get_messages("session"))
        session = session_messages[0]
        
        # Required session fields for Strava
        required_fields = [
            "timestamp",
            "total_elapsed_time", 
            "total_distance",
            "sport",
            "avg_speed",
            "max_speed",
            "avg_power",
            "max_power"
        ]
        
        for field_name in required_fields:
            value = self._get_field_value(session, field_name)
            assert value is not None, f"Session message missing required field: {field_name}"
            
            # Validate field values are reasonable
            if field_name == "sport":
                assert value == "cycling", "Sport must be cycling"
            elif field_name == "total_elapsed_time":
                assert value > 0, "Total elapsed time must be positive"
            elif field_name == "total_distance":
                assert value > 0, "Total distance must be positive"
            elif "speed" in field_name:
                assert value >= 0, f"{field_name} must be non-negative"
            elif "power" in field_name:
                assert value >= 0, f"{field_name} must be non-negative"
    
    def test_strava_record_message_requirements(self, strava_recorder):
        """Test that record messages contain all fields Strava expects."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=3)
        
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        record_messages = list(fitfile.get_messages("record"))
        assert len(record_messages) >= 60, "Should have at least 60 record messages for 3-minute ride"
        
        # Check first few records for required fields
        required_fields = ["timestamp", "distance", "speed", "power", "heart_rate", "cadence"]
        
        for i, record in enumerate(record_messages[:10]):  # Check first 10 records
            for field_name in required_fields:
                value = self._get_field_value(record, field_name)
                assert value is not None, f"Record {i} missing required field: {field_name}"
                
                # Validate field values are reasonable
                if field_name == "distance":
                    assert value >= 0, f"Distance must be non-negative in record {i}"
                elif field_name == "speed":
                    assert value >= 0, f"Speed must be non-negative in record {i}"
                elif field_name == "power":
                    assert value >= 0, f"Power must be non-negative in record {i}"
                elif field_name == "heart_rate":
                    assert 60 <= value <= 220, f"Heart rate must be realistic in record {i}"
                elif field_name == "cadence":
                    assert 0 <= value <= 200, f"Cadence must be realistic in record {i}"
    
    def test_strava_distance_progression(self, strava_recorder):
        """Test that distance values progress monotonically (required by Strava)."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=5)
        
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        record_messages = list(fitfile.get_messages("record"))
        
        previous_distance = 0
        for i, record in enumerate(record_messages):
            distance = self._get_field_value(record, "distance")
            assert distance >= previous_distance, f"Distance must be monotonically increasing at record {i}"
            previous_distance = distance
        
        # Verify total distance in session matches final record distance
        session_messages = list(fitfile.get_messages("session"))
        session_distance = self._get_field_value(session_messages[0], "total_distance")
        final_record_distance = self._get_field_value(record_messages[-1], "distance")
        
        # Allow small rounding differences (session distance is in cm, record in m)
        assert abs(session_distance - final_record_distance) < 1.0, \
            "Session total distance should match final record distance"
    
    def test_strava_timestamp_progression(self, strava_recorder):
        """Test that timestamps progress correctly (required by Strava)."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=2)
        
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        record_messages = list(fitfile.get_messages("record"))
        
        previous_timestamp = None
        for i, record in enumerate(record_messages):
            timestamp = self._get_field_value(record, "timestamp")
            
            if previous_timestamp is not None:
                # Convert to UTC timestamp for comparison
                current_ts = timestamp.replace(tzinfo=timezone.utc).timestamp()
                prev_ts = previous_timestamp.replace(tzinfo=timezone.utc).timestamp()
                
                assert current_ts > prev_ts, f"Timestamps must be monotonically increasing at record {i}"
                
                # Check that time difference is reasonable (should be ~1 second)
                time_diff = current_ts - prev_ts
                assert 0.5 <= time_diff <= 2.0, f"Time difference between records should be ~1 second, got {time_diff}"
            
            previous_timestamp = timestamp
    
    def test_strava_power_data_quality(self, strava_recorder):
        """Test power data quality for Strava compatibility."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=5)
        
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        # Check session power statistics
        session_messages = list(fitfile.get_messages("session"))
        session = session_messages[0]
        
        avg_power = self._get_field_value(session, "avg_power")
        max_power = self._get_field_value(session, "max_power")
        
        assert avg_power > 0, "Average power must be positive"
        assert max_power >= avg_power, "Max power must be >= average power"
        assert max_power <= 2000, "Max power should be realistic (< 2000W)"
        
        # Check individual power values
        record_messages = list(fitfile.get_messages("record"))
        power_values = [self._get_field_value(record, "power") for record in record_messages]
        
        # Verify no extreme outliers
        for i, power in enumerate(power_values):
            assert 0 <= power <= 1500, f"Power value {power} at record {i} is unrealistic"
        
        # Verify calculated average matches session average (within tolerance)
        calculated_avg = sum(power_values) / len(power_values)
        assert abs(calculated_avg - avg_power) < 5, \
            f"Session average power {avg_power} doesn't match calculated average {calculated_avg}"
    
    def test_strava_speed_data_consistency(self, strava_recorder):
        """Test speed data consistency for Strava compatibility."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=3)
        
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        record_messages = list(fitfile.get_messages("record"))
        
        for i, record in enumerate(record_messages):
            speed = self._get_field_value(record, "speed")  # m/s
            
            # Speed should be realistic for cycling
            assert 0 <= speed <= 25, f"Speed {speed} m/s at record {i} is unrealistic for cycling"
            
            # Convert to km/h for more intuitive checking
            speed_kmh = speed * 3.6
            assert speed_kmh <= 90, f"Speed {speed_kmh} km/h at record {i} is too high for indoor cycling"
    
    def test_strava_file_size_and_structure(self, strava_recorder):
        """Test that FIT file size and structure are reasonable for Strava."""
        fit_file_path = self._create_realistic_ride_data(strava_recorder, duration_minutes=30)
        
        # Check file size is reasonable
        file_size = Path(fit_file_path).stat().st_size
        assert file_size > 1000, "FIT file should be larger than 1KB for 30-minute ride"
        assert file_size < 1000000, "FIT file should be smaller than 1MB for 30-minute ride"
        
        # Parse and check message counts
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        record_messages = list(fitfile.get_messages("record"))
        expected_records = 30 * 60  # 30 minutes * 60 seconds
        
        # Allow some tolerance for timing variations
        assert abs(len(record_messages) - expected_records) < 10, \
            f"Expected ~{expected_records} records, got {len(record_messages)}"
    
    def test_strava_minimal_ride_requirements(self, strava_recorder):
        """Test that even minimal rides meet Strava requirements."""
        # Create a very short ride (30 seconds)
        strava_recorder.start_recording()
        
        base_time = time.time()
        cumulative_distance = 0.0
        
        for i in range(30):  # 30 seconds of data
            timestamp = base_time + i  # Each data point is 1 second apart
            
            # Calculate cumulative distance properly
            if i > 0:
                distance_increment = (25.0 / 3.6) * 1.0  # 25 km/h for 1 second
                cumulative_distance += distance_increment
            
            metrics = {
                "power": 150,
                "cadence": 80,
                "heart_rate": 140,
                "speed": 25.0,
                "distance": cumulative_distance
            }
            strava_recorder.add_data_point(timestamp, metrics)
        
        # Add a small delay to ensure end_time > start_time
        time.sleep(0.1)
        fit_file_path = strava_recorder.stop_recording()
        
        # Verify file can be parsed
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        # Check minimum requirements
        session_messages = list(fitfile.get_messages("session"))
        assert len(session_messages) == 1
        
        session = session_messages[0]
        total_time = self._get_field_value(session, "total_elapsed_time")
        total_distance = self._get_field_value(session, "total_distance")
        
        assert total_time >= 25, "Minimum ride duration should be recorded"
        assert total_distance > 0, "Minimum distance should be recorded"
    
    def test_strava_edge_cases(self, strava_recorder):
        """Test edge cases that might cause Strava upload issues."""
        strava_recorder.start_recording()
        
        base_time = time.time()
        
        # Test with some zero values and missing data
        test_cases = [
            {"power": 0, "cadence": 0, "heart_rate": 60, "speed": 0, "distance": 0},
            {"power": 200, "cadence": 90, "heart_rate": 150, "speed": 30.0, "distance": 8.33},
            {"power": 500, "cadence": 120, "heart_rate": 180, "speed": 45.0, "distance": 25.0},
            {"power": 100, "cadence": 60, "heart_rate": 120, "speed": 15.0, "distance": 29.17},
        ]
        
        for i, metrics in enumerate(test_cases):
            timestamp = base_time + i
            strava_recorder.add_data_point(timestamp, metrics)
        
        fit_file_path = strava_recorder.stop_recording()
        
        # Verify file can be parsed despite edge cases
        fitfile = FitFile(fit_file_path)
        fitfile.parse()
        
        record_messages = list(fitfile.get_messages("record"))
        assert len(record_messages) == len(test_cases)
        
        # Verify all records have required fields
        for record in record_messages:
            assert self._get_field_value(record, "power") is not None
            assert self._get_field_value(record, "distance") is not None
            assert self._get_field_value(record, "speed") is not None 