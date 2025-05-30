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
        self._max_reconnect_attempts = 5  # Increased from 3
        self._reconnect_delay = 1.5  # Reduced from 2.0 for faster retries
        self._disconnect_callback = None
        self._reconnect_callback = None
        self._reconnect_task = None  # Track the reconnection task
        
        # Enhanced connection settings
        self._scan_timeout = 8.0  # Longer scan timeout for device discovery
        self._connection_timeout = 10.0  # Timeout for individual connection attempts
        self._wake_up_attempts = 3  # Number of wake-up attempts for sleepy devices
        self._connection_backoff = [1, 2, 4]  # Progressive delay between connection attempts
    
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
        """Find a device with the specified service UUID with enhanced discovery.
        
        Args:
            service_uuid: The service UUID to look for
        """
        console.log(f"[blue]🔍 Searching for {self.device_name or self.__class__.__name__}...[/blue]")
        
        # If we have a device name, try multiple scan attempts with different timeouts
        if self.device_name:
            scan_attempts = [3, 5, 8]  # Progressive scan timeout
            for attempt, timeout in enumerate(scan_attempts, 1):
                console.log(f"[dim]Scan attempt {attempt}/{len(scan_attempts)} (timeout: {timeout}s)[/dim]")
                
                discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
                
                for device, adv_data in discovered.values():
                    if device.name:
                        # Flexible name matching
                        if (self.device_name.lower() in device.name.lower() or 
                            device.name.lower() in self.device_name.lower()):
                            console.log(f"[green]✓ Found device: {device.name} ({device.address})[/green]")
                            return device
                
                if attempt < len(scan_attempts):
                    console.log(f"[yellow]Device not found in scan {attempt}, retrying with longer timeout...[/yellow]")
                    await asyncio.sleep(1)  # Brief pause between scans
        else:
            # Original service-based discovery with longer timeout
            discovered = await BleakScanner.discover(timeout=self._scan_timeout, return_adv=True)
            
            for device, adv_data in discovered.values():
                if adv_data.service_uuids:
                    uuids = [str(uuid).lower() for uuid in adv_data.service_uuids]
                    if service_uuid.lower() in uuids:
                        console.log(f"[green]✓ Found {self.__class__.__name__}: {device.name or 'Unknown'}[/green]")
                        return device
        
        # Enhanced user guidance
        device_type = self.__class__.__name__.replace("Device", "")
        if self.device_name:
            console.log(f"[yellow]❌ Could not find '{self.device_name}' device[/yellow]")
            console.log(f"[blue]💡 Try these steps:[/blue]")
            console.log(f"   1. Make sure '{self.device_name}' is turned on and in pairing mode")
            console.log(f"   2. Check the device is within 3 feet of your computer") 
            console.log(f"   3. Try pressing any button on the device to wake it up")
            console.log(f"   4. If it still doesn't connect, try restarting the device")
        else:
            console.log(f"[yellow]❌ No {device_type} found[/yellow]")
            console.log(f"[blue]💡 Make sure your {device_type.lower()} device is:[/blue]")
            console.log(f"   1. Powered on and awake")
            console.log(f"   2. In pairing/discoverable mode")
            console.log(f"   3. Close to your computer (within 3 feet)")
        
        return None
    
    async def connect(self, address: Optional[str] = None, debug: bool = False) -> bool:
        """Connect to the device with enhanced retry logic and user guidance.
        
        Args:
            address: Optional Bluetooth address to connect to directly
            debug: Whether to enable debug mode
        """
        self.debug_mode = debug
        
        # Enhanced connection with retry logic
        for attempt in range(len(self._connection_backoff)):
            try:
                console.log(f"[blue]🔗 Connection attempt {attempt + 1}...[/blue]")
                
                # If address is provided, try to connect directly
                if address:
                    self.device = await self.find_device_by_address(address, timeout=self._scan_timeout)
                    if not self.device:
                        console.log(f"[red]Could not find {self.__class__.__name__} with address {address}[/red]")
                        if attempt < len(self._connection_backoff) - 1:
                            delay = self._connection_backoff[attempt]
                            console.log(f"[yellow]Retrying in {delay} seconds...[/yellow]")
                            await asyncio.sleep(delay)
                            continue
                        return False
                else:
                    # Fall back to scanning if no address provided
                    self.device = await self.find_device(self.get_service_uuid())
                    if not self.device:
                        if attempt < len(self._connection_backoff) - 1:
                            delay = self._connection_backoff[attempt]
                            console.log(f"[yellow]Retrying device discovery in {delay} seconds...[/yellow]")
                            await asyncio.sleep(delay)
                            continue
                        return False
                
                self._last_known_address = self.device.address
                
                # Create client with enhanced settings
                self.client = BleakClient(
                    self.device, 
                    disconnected_callback=lambda _: asyncio.create_task(self._handle_disconnect()),
                    timeout=self._connection_timeout
                )
                
                # Wake up device before connection if needed
                console.log(f"[blue]⚡ Connecting to {self.device.name}...[/blue]")
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
                
                console.log(f"[green]✅ Successfully connected to {self.device.name}![/green]")
                return True
                
            except Exception as e:
                error_msg = f"Connection attempt {attempt + 1} failed: {e}"
                console.log(f"[red]❌ {error_msg}[/red]")
                if self.debug_mode:
                    self.add_debug_message(error_msg)
                
                if attempt < len(self._connection_backoff) - 1:
                    delay = self._connection_backoff[attempt]
                    console.log(f"[yellow]⏳ Retrying in {delay} seconds... (attempt {attempt + 2}/{len(self._connection_backoff)})[/yellow]")
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed - provide user guidance
                    device_name = self.device_name or self.__class__.__name__.replace("Device", "")
                    console.log(f"[red]❌ Failed to connect to {device_name} after {len(self._connection_backoff)} attempts[/red]")
                    console.log(f"[blue]💡 Troubleshooting suggestions:[/blue]")
                    console.log(f"   1. Turn the device off and on again")
                    console.log(f"   2. Move closer to your computer (within 3 feet)")
                    console.log(f"   3. Check if the device is already connected to another app")
                    console.log(f"   4. Try running: peloterm scan --timeout 15")
        
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