"""BLE device scanner for Peloterm."""

import asyncio
from bleak import BleakScanner
from rich.console import Console
from rich.table import Table
from typing import List, Dict

# Standard BLE Service UUIDs
HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
CYCLING_POWER_SERVICE = "00001818-0000-1000-8000-00805f9b34fb"
CYCLING_SPEED_CADENCE = "00001816-0000-1000-8000-00805f9b34fb"

# Known trainer names
KNOWN_TRAINERS = ["insideride"]

console = Console()

async def discover_devices(timeout: int) -> List[Dict]:
    """Discover BLE devices and their services."""
    devices = []
    
    with console.status("[bold blue]Scanning for devices...") as status:
        discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
        
        for device, adv_data in discovered.values():
            device_info = {
                "name": device.name or "Unknown",
                "address": device.address,
                "rssi": adv_data.rssi,
                "services": []
            }
            
            # Check for known trainers by name
            if device.name and any(trainer in device.name.lower() for trainer in KNOWN_TRAINERS):
                device_info["services"].append("Power")
            
            # Check advertised services
            if adv_data.service_uuids:
                uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                if HEART_RATE_SERVICE.lower() in uuids:
                    device_info["services"].append("Heart Rate")
                if CYCLING_POWER_SERVICE.lower() in uuids:
                    device_info["services"].append("Power")
                if CYCLING_SPEED_CADENCE.lower() in uuids:
                    device_info["services"].append("Speed/Cadence")
            
            devices.append(device_info)
    
    return devices

def display_devices(devices: List[Dict]):
    """Display discovered devices in a rich table."""
    table = Table(title="Discovered Devices")
    
    table.add_column("Name", style="cyan")
    table.add_column("Address", style="magenta")
    table.add_column("RSSI", justify="right", style="green")
    table.add_column("Services", style="yellow")
    
    for device in devices:
        table.add_row(
            device["name"],
            device["address"],
            f"{device['rssi']}dBm",
            ", ".join(device["services"]) if device["services"] else "None"
        )
    
    console.print(table)

def scan_sensors(timeout: int = 10):
    """Scan for available sensors."""
    try:
        devices = asyncio.run(discover_devices(timeout))
        display_devices(devices)
    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]") 