"""Tests for data recording and FIT file generation."""

import pytest
import time
import tempfile
from pathlib import Path
from peloterm.data_recorder import RideRecorder, DataPoint


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