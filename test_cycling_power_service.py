#!/usr/bin/env python3
"""
Cycling Power Service Tester

This script connects to the Cycling Power Service on your InsideRide trainer
to test if it provides real power data (vs FTMS which shows 0).

Usage:
    python test_cycling_power_service.py [--duration SECONDS]
"""

import asyncio
import time
import struct
from datetime import datetime
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from typing import Optional
import argparse

# Service UUIDs
CYCLING_POWER_SERVICE = "00001818-0000-1000-8000-00805f9b34fb"
CYCLING_POWER_MEASUREMENT = "00002a63-0000-1000-8000-00805f9b34fb"
FTMS_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
FTMS_INDOOR_BIKE_DATA = "00002ad2-0000-1000-8000-00805f9b34fb"

# Known trainer names
KNOWN_TRAINERS = ["insideride", "e-motion", "7578h"]

class PowerDataCollector:
    """Collects power data from both services for comparison."""
    
    def __init__(self):
        self.device: Optional[BLEDevice] = None
        self.client: Optional[BleakClient] = None
        self.start_time = None
        self.is_collecting = False
        self.cycling_power_values = []
        self.ftms_power_values = []
        
    async def find_trainer(self) -> Optional[BLEDevice]:
        """Find a trainer device."""
        print("🔍 Scanning for trainer devices...")
        
        discovered = await BleakScanner.discover(timeout=10, return_adv=True)
        
        for device, adv_data in discovered.values():
            if device.name:
                for trainer_name in KNOWN_TRAINERS:
                    if trainer_name.lower() in device.name.lower():
                        print(f"✅ Found trainer: {device.name} ({device.address})")
                        return device
        
        print("❌ No trainer found")
        return None
    
    def parse_cycling_power_data(self, data: bytearray) -> dict:
        """Parse Cycling Power Service data according to BLE spec."""
        if len(data) < 4:
            return {"error": "Data too short"}
        
        # Parse flags (2 bytes)
        flags = struct.unpack('<H', data[0:2])[0]
        
        # Parse instantaneous power (2 bytes, signed)
        power = struct.unpack('<h', data[2:4])[0]
        
        result = {
            "flags": f"0x{flags:04x}",
            "power_watts": power,
            "raw_bytes": " ".join([f"{b:02x}" for b in data])
        }
        
        # Additional fields based on flags (if needed)
        offset = 4
        
        # Pedal Power Balance (if flag bit 0 is set)
        if flags & 0x0001 and offset < len(data):
            balance = data[offset]
            result["pedal_balance"] = balance
            offset += 1
        
        # Accumulated Torque (if flag bit 2 is set)
        if flags & 0x0004 and offset + 1 < len(data):
            torque = struct.unpack('<H', data[offset:offset+2])[0]
            result["accumulated_torque"] = torque
            offset += 2
        
        return result
    
    def parse_ftms_power_data(self, data: bytearray) -> dict:
        """Parse FTMS Indoor Bike Data for power (simplified)."""
        if len(data) < 4:
            return {"error": "Data too short"}
        
        # Check power flag (bit 6 of first byte)
        power_flag = bool(data[0] & 0x40)
        
        if not power_flag:
            return {"power_watts": None, "power_flag": False}
        
        # Power is typically at offset 8-10 in FTMS, but depends on other flags
        # For simplicity, let's extract from known position based on our analysis
        try:
            # Based on our previous analysis, power is at bytes 2-3
            power = struct.unpack('<h', data[2:4])[0] if len(data) >= 4 else 0
            return {
                "power_watts": power,
                "power_flag": True,
                "raw_bytes": " ".join([f"{b:02x}" for b in data])
            }
        except:
            return {"error": "Parse error"}
    
    def handle_cycling_power_data(self, sender, data: bytearray):
        """Handle Cycling Power Service notifications."""
        if not self.is_collecting:
            return
        
        timestamp = time.time()
        elapsed = timestamp - self.start_time if self.start_time else 0
        
        parsed = self.parse_cycling_power_data(data)
        self.cycling_power_values.append({
            "timestamp": timestamp,
            "elapsed": elapsed,
            "data": parsed
        })
        
        if "power_watts" in parsed:
            print(f"[{elapsed:6.1f}s] 🔋 Cycling Power: {parsed['power_watts']:3d}W | Raw: {parsed['raw_bytes']}")
        else:
            print(f"[{elapsed:6.1f}s] 🔋 Cycling Power: Parse Error | Raw: {parsed.get('raw_bytes', 'N/A')}")
    
    def handle_ftms_data(self, sender, data: bytearray):
        """Handle FTMS Indoor Bike Data notifications."""
        if not self.is_collecting:
            return
        
        timestamp = time.time()
        elapsed = timestamp - self.start_time if self.start_time else 0
        
        parsed = self.parse_ftms_power_data(data)
        self.ftms_power_values.append({
            "timestamp": timestamp,
            "elapsed": elapsed,
            "data": parsed
        })
        
        if "power_watts" in parsed and parsed["power_watts"] is not None:
            print(f"[{elapsed:6.1f}s] 📊 FTMS Power:   {parsed['power_watts']:3d}W | Raw: {parsed.get('raw_bytes', 'N/A')}")
    
    async def connect_and_test(self, duration: int = 30):
        """Connect to trainer and test both power services."""
        if not self.device:
            return False
        
        print(f"\n🔗 Connecting to {self.device.name}...")
        
        self.client = BleakClient(self.device)
        await self.client.connect()
        
        if not self.client.is_connected:
            print("❌ Failed to connect")
            return False
        
        print("✅ Connected!")
        
        # Check services
        services = self.client.services
        
        cycling_power_service = services.get_service(CYCLING_POWER_SERVICE)
        ftms_service = services.get_service(FTMS_SERVICE)
        
        if not cycling_power_service:
            print("❌ Cycling Power Service not found")
            return False
        
        if not ftms_service:
            print("❌ FTMS Service not found") 
            return False
        
        print("✅ Both power services found")
        
        # Subscribe to notifications
        try:
            await self.client.start_notify(CYCLING_POWER_MEASUREMENT, self.handle_cycling_power_data)
            print("✅ Subscribed to Cycling Power notifications")
        except Exception as e:
            print(f"❌ Failed to subscribe to Cycling Power: {e}")
            return False
        
        try:
            await self.client.start_notify(FTMS_INDOOR_BIKE_DATA, self.handle_ftms_data)
            print("✅ Subscribed to FTMS notifications")
        except Exception as e:
            print(f"⚠️  Failed to subscribe to FTMS: {e}")
        
        # Start data collection
        print(f"\n🎬 Starting power comparison for {duration} seconds...")
        print("💡 Start pedaling to generate power data!")
        print("📊 Comparing: Cycling Power Service vs FTMS")
        print("-" * 60)
        
        self.start_time = time.time()
        self.is_collecting = True
        
        try:
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            print("\n⏹️  Stopped by user")
        finally:
            self.is_collecting = False
        
        await self.client.disconnect()
        print("\n🔌 Disconnected")
        
        return True
    
    def print_summary(self):
        """Print summary of collected data."""
        print(f"\n📊 Power Data Comparison Summary")
        print("=" * 50)
        
        cycling_powers = [v["data"].get("power_watts", 0) for v in self.cycling_power_values if "power_watts" in v["data"]]
        ftms_powers = [v["data"].get("power_watts", 0) for v in self.ftms_power_values if v["data"].get("power_watts") is not None]
        
        print(f"🔋 Cycling Power Service:")
        print(f"   • Total readings: {len(cycling_powers)}")
        if cycling_powers:
            print(f"   • Power range: {min(cycling_powers)}-{max(cycling_powers)} watts")
            print(f"   • Average power: {sum(cycling_powers)/len(cycling_powers):.1f} watts")
            print(f"   • Non-zero readings: {sum(1 for p in cycling_powers if p > 0)}")
        
        print(f"\n📊 FTMS Service:")
        print(f"   • Total readings: {len(ftms_powers)}")
        if ftms_powers:
            print(f"   • Power range: {min(ftms_powers)}-{max(ftms_powers)} watts")
            print(f"   • Average power: {sum(ftms_powers)/len(ftms_powers):.1f} watts")
            print(f"   • Non-zero readings: {sum(1 for p in ftms_powers if p > 0)}")
        
        # Recommendation
        print(f"\n🎯 Recommendation:")
        cycling_has_data = any(p > 0 for p in cycling_powers)
        ftms_has_data = any(p > 0 for p in ftms_powers)
        
        if cycling_has_data and not ftms_has_data:
            print("✅ Use Cycling Power Service - it has real power data!")
            print("💡 Peloterm should connect to Cycling Power Service instead of FTMS for power")
        elif ftms_has_data and not cycling_has_data:
            print("✅ FTMS actually works - continue using it")
        elif cycling_has_data and ftms_has_data:
            print("✅ Both services work - compare which is more accurate")
        else:
            print("⚠️  Neither service shows power data - trainer may need calibration or setup")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Cycling Power Service vs FTMS")
    parser.add_argument("--duration", "-t", type=int, default=30, help="Test duration in seconds (default: 30)")
    
    args = parser.parse_args()
    
    print("🔋 Cycling Power Service Tester")
    print("=" * 40)
    
    collector = PowerDataCollector()
    
    # Find and connect to trainer
    collector.device = await collector.find_trainer()
    
    if not collector.device:
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure your trainer is powered on")
        print("   2. Ensure it's in pairing/discoverable mode")
        print("   3. Check that it's within range (3-10 feet)")
        return
    
    # Test both services
    if await collector.connect_and_test(args.duration):
        collector.print_summary()
    else:
        print("❌ Test failed")

if __name__ == "__main__":
    asyncio.run(main()) 