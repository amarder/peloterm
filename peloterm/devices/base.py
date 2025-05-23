"""Base device class for all BLE devices."""

import asyncio
from bleak import BleakClient, BleakScanner
from rich.console import Console
from typing import Optional, Callable, List, Dict, Any

console = Console()

class Device:
    """Base class for all BLE devices."""
    
    def __init__(self, device_name: Optional[str] = None, data_callback: Optional[Callable] = None):
        """Initialize the device.
        
        Args:
            device_name: Specific device name to connect to (optional)
            data_callback: Callback function when data is received (optional)
                          Called with metric_name, value, timestamp
        """
        self.device_name = device_name
        self.data_callback = data_callback
        self.device = None
        self.client = None
        self.debug_mode = False
        self.available_metrics = []
        self.current_values = {}
        self._debug_messages = []
        self._last_known_address = None
        self._is_reconnecting = False
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 2.0  # seconds
        self._disconnect_callback = None
        self._reconnect_callback = None
        self._reconnect_task = None  # Track the reconnection task
    
    def add_debug_message(self, message: str):
        """Add a debug message."""
        self._debug_messages.append(message)
        if self.debug_mode:
            console.log(f"[dim]{message}[/dim]")
    
    async def set_callbacks(self, disconnect_callback: Optional[Callable] = None, reconnect_callback: Optional[Callable] = None):
        """Set callbacks for disconnect and reconnect events."""
        self._disconnect_callback = disconnect_callback
        self._reconnect_callback = reconnect_callback
    
    async def _handle_disconnect(self):
        """Handle device disconnection."""
        if self._disconnect_callback:
            await self._disconnect_callback(self)
        
        if not self._is_reconnecting:
            self._is_reconnecting = True
            self._reconnect_task = asyncio.create_task(self._attempt_reconnection())
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect to the device."""
        attempts = 0
        try:
            while attempts < self._max_reconnect_attempts:
                attempts += 1
                try:
                    if self.debug_mode:
                        console.log(f"[yellow]Attempting to reconnect to {self.device_name or 'device'} (attempt {attempts}/{self._max_reconnect_attempts})[/yellow]")
                    
                    if await self.connect(address=self._last_known_address, debug=self.debug_mode):
                        console.log(f"[green]Successfully reconnected to {self.device_name or 'device'}![/green]")
                        if self._reconnect_callback:
                            await self._reconnect_callback(self)
                        self._is_reconnecting = False
                        return True
                    
                    await asyncio.sleep(self._reconnect_delay)
                except Exception as e:
                    if self.debug_mode:
                        self.add_debug_message(f"Reconnection attempt {attempts} failed: {e}")
                    await asyncio.sleep(self._reconnect_delay)
            
            console.log(f"[red]Failed to reconnect to {self.device_name or 'device'} after {self._max_reconnect_attempts} attempts[/red]")
            self._is_reconnecting = False
            return False
        finally:
            # Clear the task reference when done
            self._reconnect_task = None
    
    async def find_device_by_address(self, address: str, timeout: float = 5.0):
        """Find a device by its Bluetooth address."""
        try:
            device = await BleakScanner.find_device_by_address(address, timeout=timeout)
            if device:
                return device
            
            # If direct lookup fails, try a full scan
            discovered = await BleakScanner.discover(timeout=timeout)
            for d in discovered:
                if d.address.lower() == address.lower():
                    return d
            
            return None
        except Exception as e:
            console.log(f"[red]Error finding device by address: {e}[/red]")
            return None
    
    async def find_device(self, service_uuid: str):
        """Find a device with the specified service UUID.
        
        Args:
            service_uuid: The service UUID to look for
        """
        console.log(f"[blue]Searching for {self.__class__.__name__}...[/blue]")
        
        discovered = await BleakScanner.discover(return_adv=True)
        
        for device, adv_data in discovered.values():
            if self.device_name:
                if device.name and self.device_name.lower() in device.name.lower():
                    console.log(f"[green]✓ Matched requested device: {device.name}[/green]")
                    return device
                continue
            
            if adv_data.service_uuids:
                uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                if service_uuid.lower() in uuids:
                    console.log(f"[green]✓ Found {self.__class__.__name__}: {device.name or 'Unknown'}[/green]")
                    return device
        
        console.log(f"[yellow]No {self.__class__.__name__} found. Make sure your device is awake and nearby.[/yellow]")
        return None
    
    async def connect(self, address: Optional[str] = None, debug: bool = False) -> bool:
        """Connect to the device.
        
        Args:
            address: Optional Bluetooth address to connect to directly
            debug: Whether to enable debug mode
        """
        self.debug_mode = debug
        
        try:
            # If address is provided, try to connect directly
            if address:
                self.device = await self.find_device_by_address(address)
                if not self.device:
                    console.log(f"[red]Could not find {self.__class__.__name__} with address {address}[/red]")
                    return False
            else:
                # Fall back to scanning if no address provided
                self.device = await self.find_device(self.get_service_uuid())
                if not self.device:
                    return False
            
            self._last_known_address = self.device.address
            self.client = BleakClient(self.device, disconnected_callback=lambda _: asyncio.create_task(self._handle_disconnect()))
            await self.client.connect()
            
            if self.debug_mode:
                services = await self.client.get_services()
                console.log("\n[yellow]Available Services:[/yellow]")
                for service in services:
                    console.log(f"[dim]Service:[/dim] {service.uuid}")
                    for char in service.characteristics:
                        console.log(f"  [dim]Characteristic:[/dim] {char.uuid}")
                        self.add_debug_message(f"Found characteristic: {char.uuid}")
            
            # Set up notifications (to be implemented by subclasses)
            await self.setup_notifications()
            
            return True
        except Exception as e:
            console.log(f"[red]Error connecting to {self.__class__.__name__}: {e}[/red]")
            if self.debug_mode:
                self.add_debug_message(f"Error during connection: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the device."""
        try:
            # Cancel any running reconnection task
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
                except Exception:
                    pass  # Ignore other errors during cancellation
            self._reconnect_task = None
            self._is_reconnecting = False
            
            # Clear callbacks to prevent issues during shutdown
            original_callback = self.data_callback
            self.data_callback = None
            self._disconnect_callback = None
            self._reconnect_callback = None
            
            if self.client and self.client.is_connected:
                try:
                    # Remove the disconnected callback to prevent loops during shutdown
                    self.client._disconnected_callback = None
                    await self.client.disconnect()
                    console.log(f"[dim]✓ Disconnected from {self.device_name or self.__class__.__name__}[/dim]")
                except Exception as disconnect_error:
                    # If disconnect fails, still log it but don't raise
                    if self.debug_mode:
                        console.log(f"[dim]Warning: Disconnect error for {self.device_name or self.__class__.__name__}: {disconnect_error}[/dim]")
                    else:
                        console.log(f"[dim]✓ Disconnected from {self.device_name or self.__class__.__name__}[/dim]")
            
            # Clean up references
            self.client = None
            self.device = None
            
        except Exception as e:
            console.log(f"[yellow]Warning: Error during {self.__class__.__name__} disconnect: {e}[/yellow]")
    
    def get_available_metrics(self) -> List[str]:
        """Return list of available metrics from this device."""
        if self.debug_mode:
            self.add_debug_message(f"Available metrics: {self.available_metrics}")
        return self.available_metrics
    
    def get_current_values(self) -> Dict[str, Any]:
        """Return dictionary of current values."""
        if self.debug_mode:
            self.add_debug_message(f"Current values: {self.current_values}")
        return self.current_values
    
    def get_service_uuid(self) -> str:
        """Return the service UUID for this device type.
        
        To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_service_uuid()")
    
    async def setup_notifications(self):
        """Set up notifications for the device.
        
        To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement setup_notifications()") 