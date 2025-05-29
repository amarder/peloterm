#!/usr/bin/env python3
"""
Trainer Service Discovery

This script connects to your trainer and lists all available Bluetooth services
and characteristics to help identify alternative data sources for power, speed, 
and cadence beyond FTMS.
"""

import asyncio
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from typing import Optional

# Known trainer names
KNOWN_TRAINERS = ["insideride", "e-motion", "7578h"]

# Common Bluetooth service UUIDs
KNOWN_SERVICES = {
    "00001826-0000-1000-8000-00805f9b34fb": "Fitness Machine Service (FTMS)",
    "00001818-0000-1000-8000-00805f9b34fb": "Cycling Power Service",
    "00001816-0000-1000-8000-00805f9b34fb": "Cycling Speed and Cadence Service", 
    "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate Service",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information Service",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "6e400001-b5a3-f393-e0a9-e50e24dcca9e": "Nordic UART Service",
}

# Common characteristic UUIDs
KNOWN_CHARACTERISTICS = {
    "00002a63-0000-1000-8000-00805f9b34fb": "Cycling Power Measurement",
    "00002a5b-0000-1000-8000-00805f9b34fb": "CSC Measurement (Speed/Cadence)",
    "00002a37-0000-1000-8000-00805f9b34fb": "Heart Rate Measurement",
    "00002ad2-0000-1000-8000-00805f9b34fb": "Indoor Bike Data (FTMS)",
    "00002ada-0000-1000-8000-00805f9b34fb": "Fitness Machine Status",
    "00002ad9-0000-1000-8000-00805f9b34fb": "Fitness Machine Control Point",
    "6e400002-b5a3-f393-e0a9-e50e24dcca9e": "UART TX (Write)",
    "6e400003-b5a3-f393-e0a9-e50e24dcca9e": "UART RX (Notify)",
}

async def find_trainer() -> Optional[BLEDevice]:
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

async def discover_services(device: BLEDevice):
    """Discover all services and characteristics on the device."""
    print(f"\n🔗 Connecting to {device.name}...")
    
    async with BleakClient(device) as client:
        print(f"✅ Connected!")
        
        print(f"\n📋 Available Services and Characteristics:")
        print("=" * 60)
        
        services = client.services
        
        for service in services:
            service_name = KNOWN_SERVICES.get(service.uuid.lower(), "Unknown Service")
            print(f"\n🔧 Service: {service.uuid}")
            print(f"   Name: {service_name}")
            print(f"   Handle: {service.handle}")
            
            if service.characteristics:
                print(f"   Characteristics:")
                
                for char in service.characteristics:
                    char_name = KNOWN_CHARACTERISTICS.get(char.uuid.lower(), "Unknown Characteristic")
                    properties = []
                    
                    if "read" in char.properties:
                        properties.append("READ")
                    if "write" in char.properties:
                        properties.append("WRITE")
                    if "notify" in char.properties:
                        properties.append("NOTIFY")
                    if "indicate" in char.properties:
                        properties.append("INDICATE")
                    
                    print(f"     • {char.uuid}")
                    print(f"       Name: {char_name}")
                    print(f"       Properties: {', '.join(properties) if properties else 'None'}")
                    print(f"       Handle: {char.handle}")
                    
                    # Try to read current value if possible
                    if "read" in char.properties:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            hex_value = " ".join([f"{b:02x}" for b in value])
                            print(f"       Current Value: {hex_value}")
                        except Exception as e:
                            print(f"       Current Value: <error reading: {e}>")
                    
                    print()
            else:
                print(f"   No characteristics found")
        
        # Special analysis for power-related services
        print(f"\n⚡ Power Analysis:")
        
        # Check for Cycling Power Service
        power_service = services.get_service("00001818-0000-1000-8000-00805f9b34fb")
        if power_service:
            print(f"✅ Cycling Power Service found!")
            power_char = power_service.get_characteristic("00002a63-0000-1000-8000-00805f9b34fb")
            if power_char:
                print(f"✅ Power Measurement characteristic found - this could provide real power data!")
            else:
                print(f"❌ Power Measurement characteristic not found")
        else:
            print(f"❌ No dedicated Cycling Power Service found")
        
        # Check for Speed/Cadence Service  
        print(f"\n🚴 Speed/Cadence Analysis:")
        
        csc_service = services.get_service("00001816-0000-1000-8000-00805f9b34fb")
        if csc_service:
            print(f"✅ Cycling Speed and Cadence Service found!")
            csc_char = csc_service.get_characteristic("00002a5b-0000-1000-8000-00805f9b34fb")
            if csc_char:
                print(f"✅ CSC Measurement characteristic found - this could provide speed/cadence!")
            else:
                print(f"❌ CSC Measurement characteristic not found")
        else:
            print(f"❌ No dedicated Speed/Cadence Service found")
        
        # Check for Nordic UART (proprietary protocol)
        print(f"\n📡 Proprietary Protocol Analysis:")
        
        uart_service = services.get_service("6e400001-b5a3-f393-e0a9-e50e24dcca9e")
        if uart_service:
            print(f"✅ Nordic UART Service found - InsideRide may use proprietary protocol!")
            uart_rx = uart_service.get_characteristic("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
            uart_tx = uart_service.get_characteristic("6e400002-b5a3-f393-e0a9-e50e24dcca9e")
            
            if uart_rx and uart_tx:
                print(f"✅ UART TX/RX characteristics found - bidirectional communication possible")
                print(f"💡 This might be where the real power/speed/cadence data is transmitted!")
            else:
                print(f"❌ UART characteristics incomplete")
        else:
            print(f"❌ No Nordic UART Service found")

async def main():
    """Main function."""
    print("🔧 Trainer Service Discovery Tool")
    print("=" * 40)
    
    device = await find_trainer()
    if not device:
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure your trainer is powered on")
        print("   2. Ensure it's in pairing/discoverable mode") 
        print("   3. Check that it's within range (3-10 feet)")
        return
    
    await discover_services(device)
    
    print(f"\n🎯 Summary:")
    print(f"This analysis helps identify why FTMS shows power=0 and missing speed/cadence.")
    print(f"If alternative services are found, we can modify Peloterm to use those instead!")

if __name__ == "__main__":
    asyncio.run(main()) 