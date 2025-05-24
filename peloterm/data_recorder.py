"""Data recording and FIT file generation for ride sessions."""

import time
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import struct
import io


class DataPoint:
    """Single data point in a ride session."""
    
    def __init__(self, timestamp: float, metrics: Dict[str, Any]):
        self.timestamp = timestamp
        self.metrics = metrics
        self.datetime = datetime.fromtimestamp(timestamp, tz=timezone.utc)


class RideRecorder:
    """Records cycling metrics during a ride session and generates FIT files."""
    
    def __init__(self, ride_name: Optional[str] = None):
        """Initialize the ride recorder.
        
        Args:
            ride_name: Optional name for the ride (defaults to timestamp)
        """
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.data_points: List[DataPoint] = []
        self.ride_name = ride_name
        self.is_recording = False
        
        # Create rides directory if it doesn't exist
        self.rides_dir = Path.home() / ".peloterm" / "rides"
        self.rides_dir.mkdir(parents=True, exist_ok=True)
    
    def start_recording(self) -> None:
        """Start recording the ride session."""
        if self.is_recording:
            return
            
        self.start_time = time.time()
        self.data_points = []
        self.is_recording = True
        print(f"[green]🎬 Started recording ride session[/green]")
    
    def stop_recording(self) -> str:
        """Stop recording and generate FIT file.
        
        Returns:
            Path to the generated FIT file
        """
        if not self.is_recording:
            raise ValueError("Not currently recording")
            
        self.end_time = time.time()
        self.is_recording = False
        
        # Generate filename
        start_dt = datetime.fromtimestamp(self.start_time)
        if self.ride_name:
            filename = f"{start_dt.strftime('%Y%m%d_%H%M%S')}_{self.ride_name}.fit"
        else:
            filename = f"{start_dt.strftime('%Y%m%d_%H%M%S')}_ride.fit"
        
        fit_path = self.rides_dir / filename
        self._generate_fit_file(fit_path)
        
        duration = self.end_time - self.start_time
        print(f"[green]🏁 Ride recorded: {len(self.data_points)} data points over {duration:.1f} seconds[/green]")
        print(f"[blue]📁 FIT file saved: {fit_path}[/blue]")
        
        return str(fit_path)
    
    def add_data_point(self, timestamp: float, metrics: Dict[str, Any]) -> None:
        """Add a data point to the current recording.
        
        Args:
            timestamp: Unix timestamp when metrics were recorded
            metrics: Dictionary of metric name -> value
        """
        if not self.is_recording:
            return
            
        # Filter out None values and ensure we have valid numeric data
        cleaned_metrics = {}
        for key, value in metrics.items():
            if value is not None and isinstance(value, (int, float)):
                cleaned_metrics[key] = value
        
        if cleaned_metrics:  # Only add if we have valid data
            data_point = DataPoint(timestamp, cleaned_metrics)
            self.data_points.append(data_point)
    
    def _generate_fit_file(self, output_path: Path) -> None:
        """Generate a FIT file from the recorded data."""
        if not self.data_points:
            raise ValueError("No data points to export")
        
        fit_data = io.BytesIO()
        
        # FIT File Header (14 bytes implies a header CRC)
        header_size = 14  # Bytes
        protocol_version = 0x20  # FIT Protocol 2.0 (FIT SDK v Major.Minor -> (Major << 4) | Minor)
        profile_version = 2132   # Corresponds to a FIT SDK version (e.g., 21.32 -> 2132)
        data_size_placeholder = 0 # Placeholder, will be updated after data records are written
        data_type = b'.FIT'       # Standard FIT file signature
        header_crc_placeholder = 0 # Placeholder for header CRC, will be calculated and updated
        
        # Write initial header with placeholders
        fit_data.write(struct.pack(
            '<BBHL4sH',  # Little-endian format
            header_size,
            protocol_version,
            profile_version,
            data_size_placeholder,
            data_type,
            header_crc_placeholder  # CRC of the first 12 bytes of the header (bytes 12-13)
        ))
        
        # Record the starting position of data records (immediately after the header)
        data_records_start_offset = fit_data.tell()
        # Ensure our assumption about header_size matches current position
        assert data_records_start_offset == header_size, "Mismatch between header_size and data_records_start_offset"
        
        # Write all data record messages (definitions and data)
        self._write_file_id_message(fit_data)
        self._write_session_message(fit_data) # This method should handle if self.data_points is empty, though already checked
        self._write_record_messages(fit_data)
        
        # Calculate the actual size of the data records section
        data_records_end_offset = fit_data.tell()
        actual_data_size = data_records_end_offset - data_records_start_offset
        
        # Go back and update the data_size field in the header (at offset 4 from start of file)
        fit_data.seek(4) 
        fit_data.write(struct.pack('<L', actual_data_size))
        
        # Calculate and update the Header CRC (for a 14-byte header, CRC is of the first 12 bytes)
        # This is only done if header_size indicates a header CRC is present.
        if header_size == 14: # Or other sizes that include a header CRC
            fit_data.seek(0) # Rewind to start of header to read bytes for CRC calc
            header_bytes_for_crc = fit_data.read(12) # Read the first 12 bytes (0-11)
            actual_header_crc = self._calculate_crc(header_bytes_for_crc)
            fit_data.seek(12) # Go to the position of the header_crc field (bytes 12-13)
            fit_data.write(struct.pack('<H', actual_header_crc))
        
        # Now, the entire buffer fit_data contains the [Corrected Header] + [Data Records]
        # Calculate the File CRC over this entire content.
        fit_data.seek(0) # Rewind to the beginning of the buffer
        entire_content_before_file_crc = fit_data.getvalue() # Get all bytes written so far
        actual_file_crc = self._calculate_crc(entire_content_before_file_crc)
        
        # Write the finalized content (Header + Data Records) and then the File CRC to disk
        with open(output_path, 'wb') as f:
            f.write(entire_content_before_file_crc)
            f.write(struct.pack('<H', actual_file_crc))
    
    def _write_file_id_message(self, fit_data: io.BytesIO) -> None:
        """Write File ID message to FIT file."""
        # Definition message for File ID (Message 0)
        record_header = 0x40  # Definition message
        local_message_type = 0
        reserved = 0
        architecture = 0  # Little endian
        global_message_number = 0  # File ID
        num_fields = 5
        
        fit_data.write(struct.pack('B', record_header | local_message_type))
        fit_data.write(struct.pack('BBH', reserved, architecture, global_message_number))
        fit_data.write(struct.pack('B', num_fields))
        
        # Field definitions
        fit_data.write(struct.pack('BBB', 0, 1, 0))   # type: enum (1 byte)
        fit_data.write(struct.pack('BBB', 1, 2, 132)) # manufacturer: uint16
        fit_data.write(struct.pack('BBB', 2, 2, 132)) # product: uint16
        fit_data.write(struct.pack('BBB', 3, 4, 134)) # serial_number: uint32
        fit_data.write(struct.pack('BBB', 4, 4, 134)) # time_created: uint32
        
        # Data message for File ID
        fit_data.write(struct.pack('B', local_message_type))
        fit_data.write(struct.pack('B', 4))    # type: activity
        fit_data.write(struct.pack('<H', 255)) # manufacturer: development
        fit_data.write(struct.pack('<H', 0))   # product: 0
        fit_data.write(struct.pack('<L', 12345)) # serial_number
        
        # Convert start time to FIT timestamp (seconds since UTC 00:00 Dec 31 1989)
        fit_epoch = datetime(1989, 12, 31, tzinfo=timezone.utc).timestamp()
        fit_timestamp = int(self.start_time - fit_epoch)
        fit_data.write(struct.pack('<L', fit_timestamp))
    
    def _write_session_message(self, fit_data: io.BytesIO) -> None:
        """Write Session message to FIT file."""
        if not self.data_points:
            return
            
        # Calculate session totals
        duration = self.end_time - self.start_time
        # Ensure duration is not negative
        if duration < 0:
            duration = 0 # Or handle as an error, for now, clamp to 0
        total_distance = 0
        avg_power = 0
        max_power = 0
        avg_cadence = 0
        avg_heart_rate = 0
        
        power_values = []
        cadence_values = []
        heart_rate_values = []
        
        for point in self.data_points:
            if 'power' in point.metrics:
                power = point.metrics['power']
                power_values.append(power)
                max_power = max(max_power, power)
            if 'cadence' in point.metrics:
                cadence_values.append(point.metrics['cadence'])
            if 'heart_rate' in point.metrics:
                heart_rate_values.append(point.metrics['heart_rate'])
        
        if power_values:
            avg_power = sum(power_values) / len(power_values)
        if cadence_values:
            avg_cadence = sum(cadence_values) / len(cadence_values)
        if heart_rate_values:
            avg_heart_rate = sum(heart_rate_values) / len(heart_rate_values)
        
        # Definition message for Session (Message 18)
        record_header = 0x40  # Definition message
        local_message_type = 1
        fit_data.write(struct.pack('B', record_header | local_message_type))
        fit_data.write(struct.pack('BBH', 0, 0, 18))  # Session message
        fit_data.write(struct.pack('B', 8))  # num_fields
        
        # Field definitions
        fit_data.write(struct.pack('BBB', 253, 4, 134))  # timestamp: uint32
        fit_data.write(struct.pack('BBB', 0, 1, 0))     # event: enum
        fit_data.write(struct.pack('BBB', 1, 1, 0))     # event_type: enum
        fit_data.write(struct.pack('BBB', 7, 4, 134))   # total_elapsed_time: uint32
        fit_data.write(struct.pack('BBB', 5, 1, 0))     # sport: enum
        fit_data.write(struct.pack('BBB', 20, 2, 132))  # avg_power: uint16
        fit_data.write(struct.pack('BBB', 21, 2, 132))  # max_power: uint16
        fit_data.write(struct.pack('BBB', 22, 1, 2))    # avg_cadence: uint8
        
        # Data message for Session
        fit_epoch = datetime(1989, 12, 31, tzinfo=timezone.utc).timestamp()
        end_fit_timestamp = int(self.end_time - fit_epoch)
        
        fit_data.write(struct.pack('B', local_message_type))
        fit_data.write(struct.pack('<L', end_fit_timestamp))
        fit_data.write(struct.pack('B', 0))  # event: timer
        fit_data.write(struct.pack('B', 4))  # event_type: stop_all
        fit_data.write(struct.pack('<L', int(duration * 1000)))  # total_elapsed_time (ms)
        fit_data.write(struct.pack('B', 2))  # sport: cycling
        fit_data.write(struct.pack('<H', int(avg_power)))
        fit_data.write(struct.pack('<H', int(max_power)))
        fit_data.write(struct.pack('B', int(avg_cadence)))
    
    def _write_record_messages(self, fit_data: io.BytesIO) -> None:
        """Write Record messages (data points) to FIT file."""
        if not self.data_points:
            return
            
        # Definition message for Record (Message 20)
        record_header = 0x40  # Definition message
        local_message_type = 2
        fit_data.write(struct.pack('B', record_header | local_message_type))
        fit_data.write(struct.pack('BBH', 0, 0, 20))  # Record message
        fit_data.write(struct.pack('B', 5))  # num_fields
        
        # Field definitions  
        fit_data.write(struct.pack('BBB', 253, 4, 134))  # timestamp: uint32
        fit_data.write(struct.pack('BBB', 7, 2, 132))    # power: uint16
        fit_data.write(struct.pack('BBB', 3, 1, 2))      # heart_rate: uint8
        fit_data.write(struct.pack('BBB', 4, 1, 2))      # cadence: uint8
        fit_data.write(struct.pack('BBB', 6, 2, 132))    # speed: uint16 (m/s * 1000)
        
        # Data messages for each record
        fit_epoch = datetime(1989, 12, 31, tzinfo=timezone.utc).timestamp()
        
        for point in self.data_points:
            fit_timestamp = int(point.timestamp - fit_epoch)
            power = int(point.metrics.get('power', 0))
            heart_rate = int(point.metrics.get('heart_rate', 0))
            cadence = int(point.metrics.get('cadence', 0))
            speed = int(point.metrics.get('speed', 0) * 1000 / 3.6)  # Convert km/h to m/s * 1000
            
            fit_data.write(struct.pack('B', local_message_type))
            fit_data.write(struct.pack('<L', fit_timestamp))
            fit_data.write(struct.pack('<H', power))
            fit_data.write(struct.pack('B', heart_rate))
            fit_data.write(struct.pack('B', cadence))
            fit_data.write(struct.pack('<H', speed))
    
    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC-16 for FIT file."""
        crc_table = [
            0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
            0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400
        ]
        
        crc = 0
        for byte in data:
            # Compute checksum of lower four bits of byte
            tmp = crc_table[crc & 0xF]
            crc = (crc >> 4) & 0x0FFF
            crc = crc ^ tmp ^ crc_table[byte & 0xF]
            
            # Compute checksum of upper four bits of byte  
            tmp = crc_table[crc & 0xF]
            crc = (crc >> 4) & 0x0FFF
            crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0xF]
        
        return crc

    def get_ride_summary(self) -> Dict[str, Any]:
        """Get a summary of the recorded ride."""
        if not self.data_points:
            return {}
            
        duration = (self.end_time or time.time()) - (self.start_time or time.time())
        
        # Calculate statistics
        power_values = [p.metrics.get('power', 0) for p in self.data_points if 'power' in p.metrics]
        cadence_values = [p.metrics.get('cadence', 0) for p in self.data_points if 'cadence' in p.metrics] 
        heart_rate_values = [p.metrics.get('heart_rate', 0) for p in self.data_points if 'heart_rate' in p.metrics]
        speed_values = [p.metrics.get('speed', 0) for p in self.data_points if 'speed' in p.metrics]
        
        summary = {
            'duration': duration,
            'data_points': len(self.data_points),
            'start_time': self.start_time,
            'end_time': self.end_time
        }
        
        if power_values:
            summary.update({
                'avg_power': sum(power_values) / len(power_values),
                'max_power': max(power_values),
                'min_power': min(power_values)
            })
            
        if cadence_values:
            summary.update({
                'avg_cadence': sum(cadence_values) / len(cadence_values),
                'max_cadence': max(cadence_values)
            })
            
        if heart_rate_values:
            summary.update({
                'avg_heart_rate': sum(heart_rate_values) / len(heart_rate_values),
                'max_heart_rate': max(heart_rate_values),
                'min_heart_rate': min(heart_rate_values)
            })
            
        if speed_values:
            summary.update({
                'avg_speed': sum(speed_values) / len(speed_values),
                'max_speed': max(speed_values)
            })
        
        return summary 