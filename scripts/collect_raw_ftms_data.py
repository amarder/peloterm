#!/usr/bin/env python3
"""
Raw FTMS Data Collector

This script connects to your InsideRide trainer and collects raw FTMS data
packets for analysis and testing of the FTMS parser.

Usage:
    python collect_raw_ftms_data.py [--device-name NAME] [--duration SECONDS] [--output FILE]

The script will:
1. Scan for and connect to your trainer device
2. Subscribe to FTMS Indoor Bike Data notifications
3. Log all raw data packets with timestamps
4. Save data to a file for later analysis
"""

import asyncio
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import argparse
from dataclasses import dataclass, asdict

# BLE imports
try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.device import BLEDevice
except ImportError:
    print("Error: bleak library not found. Install it with: pip install bleak")
    exit(1)

# Fitness Machine Service UUIDs
FITNESS_MACHINE_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
FITNESS_MACHINE_INDOOR_BIKE_DATA = "00002ad2-0000-1000-8000-00805f9b34fb"

# Known trainer names to look for
KNOWN_TRAINERS = ["insideride", "e-motion", "7578h"]

@dataclass
class RawFTMSData:
    """Container for raw FTMS data packet."""
    timestamp: float
    iso_timestamp: str
    raw_bytes: List[int]
    hex_string: str
    packet_length: int


class FTMSDataCollector:
    """Collects raw FTMS data from a trainer device."""
    
    def __init__(self, device_name: Optional[str] = None, output_file: str = "raw_ftms_data.json"):
        self.device_name = device_name
        self.output_file = output_file
        self.device: Optional[BLEDevice] = None
        self.client: Optional[BleakClient] = None
        self.data_packets: List[RawFTMSData] = []
        self.packet_count = 0
        self.start_time = None
        self.is_collecting = False
        
    async def find_trainer_device(self) -> Optional[BLEDevice]:
        """Find a trainer device to connect to."""
        print("🔍 Scanning for trainer devices...")
        
        # Try multiple scan attempts with increasing timeouts
        scan_timeouts = [5, 8, 10]
        
        for attempt, timeout in enumerate(scan_timeouts, 1):
            print(f"   Scan attempt {attempt}/{len(scan_timeouts)} (timeout: {timeout}s)")
            
            try:
                discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
                
                for device, adv_data in discovered.values():
                    # Check by name if specified
                    if self.device_name:
                        if device.name and self.device_name.lower() in device.name.lower():
                            print(f"✅ Found target device: {device.name} ({device.address})")
                            return device
                    else:
                        # Look for known trainer names
                        if device.name:
                            for trainer_name in KNOWN_TRAINERS:
                                if trainer_name.lower() in device.name.lower():
                                    print(f"✅ Found trainer: {device.name} ({device.address})")
                                    return device
                        
                        # Check for FITNESS_MACHINE_SERVICE in advertisements
                        if adv_data.service_uuids:
                            uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                            if FITNESS_MACHINE_SERVICE.lower() in uuids:
                                print(f"✅ Found fitness machine: {device.name or 'Unknown'} ({device.address})")
                                return device
                
                if attempt < len(scan_timeouts):
                    print(f"   Device not found, trying again with longer timeout...")
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"   Error during scan attempt {attempt}: {e}")
                await asyncio.sleep(1)
        
        return None
    
    def handle_ftms_data(self, sender, data: bytearray):
        """Handle incoming FTMS data packets."""
        if not self.is_collecting:
            return
            
        timestamp = time.time()
        iso_timestamp = datetime.fromtimestamp(timestamp).isoformat()
        raw_bytes = list(data)
        hex_string = " ".join([f"{b:02x}" for b in data])
        
        packet = RawFTMSData(
            timestamp=timestamp,
            iso_timestamp=iso_timestamp,
            raw_bytes=raw_bytes,
            hex_string=hex_string,
            packet_length=len(data)
        )
        
        self.data_packets.append(packet)
        self.packet_count += 1
        
        # Print real-time data
        elapsed = timestamp - self.start_time if self.start_time else 0
        print(f"[{elapsed:6.1f}s] Packet #{self.packet_count:4d}: {hex_string}")
        
    async def connect_to_device(self) -> bool:
        """Connect to the trainer device."""
        if not self.device:
            print("❌ No device to connect to")
            return False
            
        try:
            print(f"🔗 Connecting to {self.device.name or 'Unknown'} ({self.device.address})...")
            
            self.client = BleakClient(self.device)
            await self.client.connect()
            
            if not self.client.is_connected:
                print("❌ Failed to connect to device")
                return False
                
            print(f"✅ Connected to {self.device.name}")
            
            # Check if the device has the required service
            services = self.client.services
            ftms_service = services.get_service(FITNESS_MACHINE_SERVICE)
            
            if not ftms_service:
                print(f"❌ Device doesn't have Fitness Machine Service ({FITNESS_MACHINE_SERVICE})")
                return False
                
            print("✅ Fitness Machine Service found")
            
            # Check for Indoor Bike Data characteristic
            indoor_bike_char = ftms_service.get_characteristic(FITNESS_MACHINE_INDOOR_BIKE_DATA)
            
            if not indoor_bike_char:
                print(f"❌ Indoor Bike Data characteristic not found ({FITNESS_MACHINE_INDOOR_BIKE_DATA})")
                return False
                
            print("✅ Indoor Bike Data characteristic found")
            
            # Subscribe to notifications
            await self.client.start_notify(FITNESS_MACHINE_INDOOR_BIKE_DATA, self.handle_ftms_data)
            print("✅ Subscribed to FTMS data notifications")
            
            return True
            
        except Exception as e:
            print(f"❌ Error connecting to device: {e}")
            return False
    
    async def collect_data(self, duration: int = 60):
        """Collect FTMS data for the specified duration."""
        print(f"\n🎬 Starting data collection for {duration} seconds...")
        print("💡 Start pedaling or interacting with your trainer to generate data")
        print("   Press Ctrl+C to stop collection early\n")
        
        self.start_time = time.time()
        self.is_collecting = True
        
        try:
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            print("\n⏹️  Collection stopped by user")
        finally:
            self.is_collecting = False
            
        print(f"\n✅ Collection completed! Captured {self.packet_count} data packets")
    
    def save_data(self):
        """Save collected data to file."""
        if not self.data_packets:
            print("⚠️  No data packets to save")
            return
            
        # Prepare metadata
        metadata = {
            "collection_info": {
                "device_name": self.device.name if self.device else "Unknown",
                "device_address": self.device.address if self.device else "Unknown",
                "target_device_name": self.device_name,
                "start_time": self.start_time,
                "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                "packet_count": self.packet_count,
                "duration_seconds": self.data_packets[-1].timestamp - self.start_time if self.data_packets else 0,
                "collection_script": "collect_raw_ftms_data.py"
            },
            "packets": [asdict(packet) for packet in self.data_packets]
        }
        
        # Save to file
        output_path = Path(self.output_file)
        try:
            with open(output_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"💾 Saved {self.packet_count} packets to {output_path}")
            print(f"📊 File size: {output_path.stat().st_size / 1024:.1f} KB")
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")
    
    def print_summary(self):
        """Print a summary of collected data."""
        if not self.data_packets:
            print("📊 No data collected")
            return
            
        print("\n📊 Collection Summary:")
        print(f"   • Total packets: {self.packet_count}")
        print(f"   • Duration: {self.data_packets[-1].timestamp - self.start_time:.1f} seconds")
        print(f"   • Average rate: {self.packet_count / (self.data_packets[-1].timestamp - self.start_time):.1f} packets/second")
        
        # Analyze packet lengths
        lengths = [p.packet_length for p in self.data_packets]
        unique_lengths = set(lengths)
        print(f"   • Packet sizes: {sorted(unique_lengths)} bytes")
        
        # Show first few packets as samples
        print(f"\n📋 Sample packets:")
        for i, packet in enumerate(self.data_packets[:5]):
            print(f"   {i+1}: {packet.hex_string}")
        
        if len(self.data_packets) > 5:
            print(f"   ... ({len(self.data_packets) - 5} more packets)")
    
    async def disconnect(self):
        """Disconnect from the device."""
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
                print("🔌 Disconnected from device")
            except Exception as e:
                print(f"⚠️  Error disconnecting: {e}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Collect raw FTMS data from trainer device")
    parser.add_argument("--device-name", "-d", help="Specific device name to connect to")
    parser.add_argument("--duration", "-t", type=int, default=60, help="Collection duration in seconds (default: 60)")
    parser.add_argument("--output", "-o", default="raw_ftms_data.json", help="Output file path (default: raw_ftms_data.json)")
    
    args = parser.parse_args()
    
    print("🚴‍♂️ FTMS Raw Data Collector")
    print("=" * 40)
    
    collector = FTMSDataCollector(
        device_name=args.device_name,
        output_file=args.output
    )
    
    try:
        # Find and connect to device
        collector.device = await collector.find_trainer_device()
        
        if not collector.device:
            print("❌ No trainer device found!")
            print("\n💡 Troubleshooting tips:")
            print("   1. Make sure your trainer is powered on")
            print("   2. Ensure it's in pairing/discoverable mode")
            print("   3. Check that it's within range (3-10 feet)")
            print("   4. Try specifying --device-name if you know the exact name")
            return
        
        if not await collector.connect_to_device():
            print("❌ Failed to connect to device")
            return
        
        # Collect data
        await collector.collect_data(args.duration)
        
        # Save and summarize
        collector.save_data()
        collector.print_summary()
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        await collector.disconnect()


if __name__ == "__main__":
    asyncio.run(main()) 