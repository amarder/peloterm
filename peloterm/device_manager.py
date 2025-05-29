"""Enhanced device connection and management utilities."""

import asyncio
from typing import List, Dict, Optional, Set
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from bleak import BleakScanner
from .devices.base import Device
from .config import Config

console = Console()

class SmartDeviceManager:
    """Smart device manager with enhanced connection strategies."""
    
    def __init__(self, config: Config):
        self.config = config
        self.known_devices: Dict[str, Dict] = {}  # Cache of known devices
        self.connection_history: Dict[str, List[float]] = {}  # Track connection success
        self.user_guidance_shown: Set[str] = set()  # Track shown guidance messages
    
    async def smart_device_discovery(self, target_devices: List[str], timeout: int = 60) -> Dict[str, Optional[Dict]]:
        """Intelligently discover devices with adaptive strategies."""
        console.print(f"[blue]🧠 Smart discovery for {len(target_devices)} target devices...[/blue]")
        
        found_devices = {}
        remaining_devices = set(target_devices)
        scan_timeout = min(15, timeout // 3)  # Start with shorter scans
        
        # Phase 1: Quick discovery for responsive devices
        console.print("[dim]Phase 1: Quick discovery scan...[/dim]")
        discovered = await self._discover_with_caching(scan_timeout)
        found_count = self._match_target_devices(discovered, remaining_devices, found_devices)
        
        if found_count == len(target_devices):
            console.print("[green]🎉 All devices found in quick scan![/green]")
            return found_devices
        
        # Phase 2: Extended discovery for sleepy devices
        if remaining_devices and timeout > 20:
            console.print(f"[dim]Phase 2: Extended scan for {len(remaining_devices)} missing devices...[/dim]")
            self._show_device_wake_guidance(remaining_devices)
            
            extended_timeout = min(20, (timeout - scan_timeout) // 2)
            discovered = await self._discover_with_caching(extended_timeout)
            found_count += self._match_target_devices(discovered, remaining_devices, found_devices)
        
        # Phase 3: Deep discovery with maximum effort
        if remaining_devices and timeout > 40:
            console.print(f"[dim]Phase 3: Deep scan for stubborn devices...[/dim]")
            self._show_troubleshooting_guidance(remaining_devices)
            
            deep_timeout = timeout - scan_timeout - (extended_timeout if 'extended_timeout' in locals() else 0)
            discovered = await self._discover_with_caching(deep_timeout)
            found_count += self._match_target_devices(discovered, remaining_devices, found_devices)
        
        return found_devices
    
    async def _discover_with_caching(self, timeout: int) -> Dict:
        """Discover devices and cache results for faster future lookups."""
        try:
            discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
            
            # Update cache with new discoveries
            for device, adv_data in discovered.values():
                if device.name:  # Only cache named devices
                    self.known_devices[device.address] = {
                        'name': device.name,
                        'address': device.address,
                        'rssi': adv_data.rssi,
                        'last_seen': asyncio.get_event_loop().time()
                    }
            
            return discovered
        except Exception as e:
            console.print(f"[yellow]Discovery warning: {e}[/yellow]")
            return {}
    
    def _match_target_devices(self, discovered: Dict, remaining_devices: Set[str], found_devices: Dict) -> int:
        """Match discovered devices to target devices."""
        found_count = 0
        
        for device, adv_data in discovered.values():
            if not device.name:
                continue
                
            # Check if this device matches any remaining target
            for target_name in list(remaining_devices):
                if self._is_device_match(device.name, target_name):
                    found_devices[target_name] = {
                        'device': device,
                        'adv_data': adv_data,
                        'rssi': adv_data.rssi
                    }
                    remaining_devices.remove(target_name)
                    found_count += 1
                    console.print(f"[green]✓ Found {target_name}: {device.name} (RSSI: {adv_data.rssi}dBm)[/green]")
                    break
        
        return found_count
    
    def _is_device_match(self, discovered_name: str, target_name: str) -> bool:
        """Check if a discovered device matches a target device."""
        discovered_lower = discovered_name.lower()
        target_lower = target_name.lower()
        
        # Exact match
        if discovered_lower == target_lower:
            return True
        
        # Substring match (either direction)
        if target_lower in discovered_lower or discovered_lower in target_lower:
            return True
        
        # Handle common device naming patterns
        # E.g., "Wahoo CADENCE D9E1" matches "CADENCE D9E1"
        target_words = target_lower.split()
        discovered_words = discovered_lower.split()
        
        # Check if all target words are in discovered name
        if len(target_words) <= len(discovered_words):
            if all(word in discovered_words for word in target_words):
                return True
        
        return False
    
    def _show_device_wake_guidance(self, missing_devices: Set[str]):
        """Show guidance for waking up missing devices."""
        if not missing_devices or 'wake_guidance' in self.user_guidance_shown:
            return
        
        self.user_guidance_shown.add('wake_guidance')
        
        device_list = "', '".join(missing_devices)
        
        guidance_panel = Panel.fit(
            f"[yellow]⚡ Wake-up Tips for Missing Devices[/yellow]\n\n"
            f"Missing: [cyan]'{device_list}'[/cyan]\n\n"
            f"[blue]Try these steps:[/blue]\n"
            f"• Press any button on the device to wake it\n"
            f"• Check if the device is in pairing mode\n"
            f"• Move the device closer (within 3 feet)\n"
            f"• Make sure device battery isn't too low",
            title="💡 Device Wake-up Guide",
            border_style="yellow"
        )
        console.print(guidance_panel)
    
    def _show_troubleshooting_guidance(self, missing_devices: Set[str]):
        """Show troubleshooting guidance for persistent connection issues."""
        if not missing_devices or 'troubleshoot_guidance' in self.user_guidance_shown:
            return
        
        self.user_guidance_shown.add('troubleshoot_guidance')
        
        device_list = "', '".join(missing_devices)
        
        troubleshoot_panel = Panel.fit(
            f"[red]🔧 Troubleshooting Persistent Connection Issues[/red]\n\n"
            f"Still missing: [cyan]'{device_list}'[/cyan]\n\n"
            f"[blue]Advanced troubleshooting:[/blue]\n"
            f"• Turn device off/on completely\n"
            f"• Check if connected to another app (Zwift, etc.)\n"
            f"• Try forgetting/re-pairing in system Bluetooth\n"
            f"• Restart computer's Bluetooth service\n"
            f"• Check device manual for pairing mode\n\n"
            f"[dim]Run 'peloterm scan --timeout 20' to test discovery[/dim]",
            title="🛠️ Advanced Troubleshooting",
            border_style="red"
        )
        console.print(troubleshoot_panel)
    
    async def monitor_connections(self, devices: List[Device], callback=None):
        """Monitor device connections and handle automatic reconnection."""
        while True:
            try:
                disconnected_devices = []
                for device in devices:
                    if device.client and not device.client.is_connected:
                        disconnected_devices.append(device)
                
                if disconnected_devices:
                    console.print(f"[yellow]⚠️ {len(disconnected_devices)} device(s) disconnected. Attempting reconnection...[/yellow]")
                    
                    # Trigger reconnection for disconnected devices
                    for device in disconnected_devices:
                        if not device._is_reconnecting:
                            asyncio.create_task(device._attempt_reconnection())
                
                # Call user callback if provided
                if callback:
                    await callback(devices, disconnected_devices)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                console.print(f"[red]Connection monitoring error: {e}[/red]")
                await asyncio.sleep(10)  # Wait longer on error
    
    def get_connection_status_table(self, devices: List[Device]) -> Table:
        """Generate a status table for current device connections."""
        table = Table(title="Device Connection Status", show_header=True)
        table.add_column("Device", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Signal", style="green")
        table.add_column("Last Update", style="dim")
        
        for device in devices:
            if device.client and device.client.is_connected:
                status = "[green]✅ Connected[/green]"
                signal = "Strong"  # Could be enhanced with actual RSSI
                last_update = "Live"
            elif device._is_reconnecting:
                status = "[yellow]🔄 Reconnecting[/yellow]"
                signal = "Unknown"
                last_update = "Reconnecting..."
            else:
                status = "[red]❌ Disconnected[/red]"
                signal = "None"
                last_update = "Offline"
            
            device_name = device.device_name or device.__class__.__name__.replace("Device", "")
            table.add_row(device_name, status, signal, last_update)
        
        return table 