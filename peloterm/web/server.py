"""FastAPI web server for PeloTerm."""

import json
import asyncio
import time
import threading
from pathlib import Path
from typing import Dict, Set, List, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from ..data_processor import DataProcessor
from ..data_recorder import RideRecorder
from ..strava_integration import StravaUploader


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    if hasattr(app.state, "web_server"):
        app.state.web_server.update_task = asyncio.create_task(app.state.web_server.update_loop())
    
    yield
    
    # Shutdown
    if hasattr(app.state, "web_server"):
        # Set shutdown event first
        app.state.web_server.shutdown_event.set()
        
        # Cancel update task
        if app.state.web_server.update_task:
            app.state.web_server.update_task.cancel()
            try:
                await app.state.web_server.update_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections with a close code
        for connection in app.state.web_server.active_connections.copy():
            try:
                await connection.close(code=1000)  # Normal closure
            except Exception:
                pass
        app.state.web_server.active_connections.clear()
        
        for connection in app.state.web_server.control_connections.copy():
            try:
                await connection.close(code=1000)  # Normal closure
            except Exception:
                pass
        app.state.web_server.control_connections.clear()


class WebServer:
    def __init__(self, ride_duration_minutes: int = 30, update_interval: float = 1.0):
        self.app = FastAPI(
            title="PeloTerm",
            description="Cycling Metrics Dashboard",
            lifespan=lifespan
        )
        
        # Add CORS middleware to allow Vue dev server connections
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:5173",  # Vue dev server
                "http://127.0.0.1:5173", # Vue dev server alternative
                "http://localhost:8000",  # FastAPI server itself
                "http://127.0.0.1:8000",  # FastAPI server alternative
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.active_connections: Set[WebSocket] = set()
        self.control_connections: Set[WebSocket] = set()
        self.ride_duration_minutes = ride_duration_minutes
        self.ride_start_time = time.time()  # Server-side ride start time
        self.data_processor = DataProcessor()
        self.update_interval = update_interval
        self.update_task = None
        self.server = None  # Store the uvicorn server instance
        self.shutdown_event = threading.Event()  # Add shutdown event
        
        # Recording functionality
        self.ride_recorder = RideRecorder()
        self.strava_uploader = StravaUploader()
        self.is_recording = False
        self.is_paused = False
        
        # Store web server instance in app state for lifespan access
        self.app.state.web_server = self
        
        self.setup_routes()

    def setup_routes(self):
        """Set up FastAPI routes."""
        # Mount static files
        static_path = Path(__file__).parent / "static"
        self.app.mount("/assets", StaticFiles(directory=str(static_path / "assets")), name="assets")
        
        @self.app.get("/")
        async def get_index():
            """Serve the main application page."""
            return FileResponse(static_path / "index.html")
        
        @self.app.get("/api/config")
        async def get_config():
            """Return the current configuration.""" 
            return {
                "iframe_url": "https://watch.marder.me/web/#/home.html",
                "ride_duration_minutes": self.ride_duration_minutes,
                "ride_start_time": self.ride_start_time,
                "iframe_options": {
                    "vimeo_cycling": "https://player.vimeo.com/video/888488151?autoplay=1&loop=1&title=0&byline=0&portrait=0",
                    "twitch_cycling": "https://player.twitch.tv/?channel=giro&parent=localhost",
                    "openstreetmap": "https://www.openstreetmap.org/export/embed.html?bbox=-0.1,51.48,-0.08,51.52&layer=mapnik",
                    "codepen_demo": "https://codepen.io/collection/DQvYpQ/embed/preview",
                    "simple_placeholder": "data:text/html,<html><body style='background:#161b22;color:#e6edf3;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'><div style='text-align:center'><h1>🚴 PeloTerm</h1><p>Configure your iframe URL in the settings</p><p style='color:#7d8590;font-size:14px'>Edit iframe_url in your config</p></div></body></html>"
                },
                "metrics": [
                    {"name": "Power", "key": "power", "symbol": "⚡", "color": "#51cf66"},
                    {"name": "Speed", "key": "speed", "symbol": "🚴", "color": "#339af0"},
                    {"name": "Cadence", "key": "cadence", "symbol": "🔄", "color": "#fcc419"},
                    {"name": "Heart Rate", "key": "heart_rate", "symbol": "💓", "color": "#ff6b6b"},
                ]
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Handle WebSocket connections for real-time metrics."""
            await websocket.accept()
            self.active_connections.add(websocket)
            
            try:
                # No historical data sending - clients get real-time data immediately
                print("New WebSocket client connected - will receive real-time data")
                
                # Keep connection alive and handle incoming messages
                while not self.shutdown_event.is_set():
                    try:
                        # Short timeout to check shutdown event frequently
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                        # Handle any incoming messages here if needed
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketDisconnect:
                        break
                    except Exception:
                        break
            finally:
                # Always clean up the connection
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                try:
                    await websocket.close(code=1000)  # Normal closure
                except Exception:
                    pass
        
        @self.app.websocket("/ws/control")
        async def control_websocket_endpoint(websocket: WebSocket):
            """Handle WebSocket connections for recording control commands."""
            await websocket.accept()
            self.control_connections.add(websocket)
            
            try:
                print("New control WebSocket client connected")
                
                # Send current recording state
                await self._send_control_message(websocket, {
                    'type': 'status',
                    'is_recording': self.is_recording,
                    'is_paused': self.is_paused,
                    'has_data': len(self.ride_recorder.data_points) > 0
                })
                
                # Handle incoming control commands
                while not self.shutdown_event.is_set():
                    try:
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                        await self._handle_control_command(websocket, json.loads(data))
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        print(f"Error handling control command: {e}")
                        await self._send_control_message(websocket, {
                            'type': 'error',
                            'message': str(e)
                        })
            finally:
                # Always clean up the connection
                if websocket in self.control_connections:
                    self.control_connections.remove(websocket)
                try:
                    await websocket.close(code=1000)  # Normal closure
                except Exception:
                    pass

    async def update_loop(self, timeout: Optional[float] = None):
        """Regular update loop to process and broadcast metrics."""
        start_time = time.time()
        
        while not self.shutdown_event.is_set():
            # Check timeout in testing environment
            if timeout and (time.time() - start_time) > timeout:
                break
                
            try:
                # Get processed metrics
                metrics = self.data_processor.get_processed_metrics()
                current_time = time.time() # Get current time for consistent timestamping and pruning

                if metrics:
                    # Add timestamp for real-time broadcasting
                    timestamped_metrics = {
                        **metrics,
                        "timestamp": current_time
                    }

                    # Broadcast to all connected clients immediately
                    message = json.dumps(timestamped_metrics)
                    disconnected = set()
                    
                    for connection in self.active_connections.copy():
                        try:
                            await connection.send_text(message)
                        except Exception:
                            disconnected.add(connection)
                            try:
                                await connection.close(code=1000)
                            except Exception:
                                pass
                    
                    # Remove disconnected clients
                    self.active_connections -= disconnected

            except Exception as e:
                print(f"Error in update loop: {e}")
            
            try:
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break

    def update_metric(self, metric_name: str, value: Any):
        """Update a metric in the data processor."""
        self.data_processor.update_metric(metric_name, value)
        
        # If recording (and not paused), add data point to recorder
        if self.is_recording and not self.is_paused:
            current_metrics = self.data_processor.get_processed_metrics()
            if current_metrics:
                self.ride_recorder.add_data_point(time.time(), current_metrics)
    
    async def _send_control_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a control message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending control message: {e}")
    
    async def _broadcast_control_message(self, message: Dict[str, Any]):
        """Broadcast a control message to all control WebSocket connections."""
        if not self.control_connections:
            return
            
        message_text = json.dumps(message)
        disconnected = set()
        
        for connection in self.control_connections.copy():
            try:
                await connection.send_text(message_text)
            except Exception:
                disconnected.add(connection)
                try:
                    await connection.close(code=1000)
                except Exception:
                    pass
        
        # Remove disconnected clients
        self.control_connections -= disconnected
    
    async def _handle_control_command(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle incoming control commands."""
        command = data.get('command')
        
        try:
            if command == 'start_recording':
                await self._start_recording(websocket)
            elif command == 'pause_recording':
                await self._pause_recording(websocket)
            elif command == 'resume_recording':
                await self._resume_recording(websocket)
            elif command == 'save_recording':
                await self._save_recording(websocket)
            elif command == 'upload_to_strava':
                await self._upload_to_strava(websocket)
            elif command == 'clear_recording':
                await self._clear_recording(websocket)
            else:
                await self._send_control_message(websocket, {
                    'type': 'error',
                    'message': f'Unknown command: {command}'
                })
        except Exception as e:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': str(e)
            })
    
    async def _start_recording(self, websocket: WebSocket):
        """Start recording ride data."""
        if self.is_recording:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': 'Already recording'
            })
            return
        
        self.ride_recorder.start_recording()
        self.is_recording = True
        self.is_paused = False
        
        message = {'type': 'recording_started'}
        await self._broadcast_control_message(message)
        print("🎬 Recording started via web UI")
    
    async def _pause_recording(self, websocket: WebSocket):
        """Pause recording ride data."""
        if not self.is_recording:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': 'Not currently recording'
            })
            return
        
        self.is_recording = False
        self.is_paused = True
        
        message = {'type': 'recording_paused'}
        await self._broadcast_control_message(message)
        print("⏸️ Recording paused via web UI")
    
    async def _resume_recording(self, websocket: WebSocket):
        """Resume recording ride data."""
        if not self.is_paused:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': 'Not currently paused'
            })
            return
        
        self.is_recording = True
        self.is_paused = False
        
        message = {'type': 'recording_resumed'}
        await self._broadcast_control_message(message)
        print("▶️ Recording resumed via web UI")
    
    async def _save_recording(self, websocket: WebSocket):
        """Save recorded data to FIT file."""
        if self.is_recording:
            # Stop recording first
            self.ride_recorder.end_time = time.time()
            self.is_recording = False
            self.is_paused = False
            
            await self._broadcast_control_message({'type': 'recording_stopped'})
        
        if not self.ride_recorder.data_points:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': 'No recorded data to save'
            })
            return
        
        try:
            # Generate FIT file
            fit_path = self.ride_recorder.stop_recording()
            filename = Path(fit_path).name
            
            message = {
                'type': 'save_success',
                'filename': filename,
                'path': fit_path
            }
            await self._broadcast_control_message(message)
            print(f"💾 Ride saved to {fit_path}")
            
        except Exception as e:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': f'Failed to save recording: {str(e)}'
            })
    
    async def _upload_to_strava(self, websocket: WebSocket):
        """Upload recorded data to Strava."""
        if self.is_recording:
            # Stop recording first
            self.ride_recorder.end_time = time.time()
            self.is_recording = False
            self.is_paused = False
            
            await self._broadcast_control_message({'type': 'recording_stopped'})
        
        if not self.ride_recorder.data_points:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': 'No recorded data to upload'
            })
            return
        
        try:
            # First save to FIT file
            fit_path = self.ride_recorder.stop_recording()
            
            # Then upload to Strava
            success = self.strava_uploader.upload_ride(
                fit_path, 
                name="PeloTerm Ride",
                description="Recorded with PeloTerm"
            )
            
            if success:
                message = {'type': 'upload_success'}
                await self._broadcast_control_message(message)
                print("📤 Ride uploaded to Strava successfully")
            else:
                await self._send_control_message(websocket, {
                    'type': 'error',
                    'message': 'Failed to upload to Strava'
                })
                
        except Exception as e:
            await self._send_control_message(websocket, {
                'type': 'error',
                'message': f'Failed to upload to Strava: {str(e)}'
            })
    
    async def _clear_recording(self, websocket: WebSocket):
        """Clear/reset the current recording."""
        # Stop recording if currently active
        self.is_recording = False
        self.is_paused = False
        
        # Create a new recorder instance to clear data
        self.ride_recorder = RideRecorder()
        
        message = {'type': 'recording_cleared'}
        await self._broadcast_control_message(message)
        print("🗑️ Recording cleared via web UI")

    def start(self, host: str = "127.0.0.1", port: int = 8000):
        """Start the web server."""
        import logging
        # Reduce uvicorn logging verbosity
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
        
        config = uvicorn.Config(
            self.app, 
            host=host, 
            port=port, 
            log_level="warning",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        self.server.run()
    
    async def shutdown(self):
        """Gracefully shut down the web server. (Primarily for internal/lifespan use)"""
        self.shutdown_event.set() # Signal all loops and operations to stop
        
        # Attempt to cancel the update_task if it's running
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass # Expected
            except Exception as e:
                print(f"Error cancelling update_task during shutdown: {e}")

        # Close all WebSocket connections
        # This is also done in lifespan, but good to have here for direct shutdown calls
        for connection in self.active_connections.copy():
            try:
                await connection.close(code=1000)
            except Exception:
                pass # Ignore errors during mass close
        self.active_connections.clear()
        
        for connection in self.control_connections.copy():
            try:
                await connection.close(code=1000)
            except Exception:
                pass # Ignore errors during mass close
        self.control_connections.clear()
        
        # Signal uvicorn server to exit if it's running
        if self.server:
            self.server.should_exit = True
            # Give the server a moment to shut down. This sleep is okay here as it's an async def.
            await asyncio.sleep(0.1) # Shorter sleep, uvicorn should respond to should_exit
    
    def stop(self):
        """Stop the web server by signaling shutdown events.
        The actual async cleanup is handled by the lifespan manager or if shutdown() is awaited.
        """
        print("WebServer.stop() called, signaling shutdown.")
        self.shutdown_event.set() # Signal tasks like update_loop and websocket handlers
        if self.server:
            print("Signaling uvicorn server to exit.")
            self.server.should_exit = True # Signal uvicorn server instance to stop
        
        # Note: We are not running an event loop here. 
        # If this `stop` is called from a non-async context (like a signal handler),
        # the running asyncio loops (like uvicorn's or the update_loop's) need to 
        # pick up the shutdown_event.


# Global instance
web_server = None


def start_server(host: str = "127.0.0.1", port: int = 8000, ride_duration_minutes: int = 30):
    """Start the web server."""
    global web_server
    web_server = WebServer(ride_duration_minutes=ride_duration_minutes)
    web_server.start(host, port)


def stop_server():
    """Stop the web server."""
    global web_server
    if web_server:
        web_server.stop()
        web_server = None


# Make this synchronous as it only calls a synchronous method on web_server
def broadcast_metrics(metrics: Dict):
    """Update metrics in the data processor."""
    if web_server:
        # Update the data processor
        for metric_name, value in metrics.items():
            web_server.update_metric(metric_name, value)
    else:
        print("❌ No web_server instance found for broadcast_metrics")


def start_server_with_mock_data(host: str = "127.0.0.1", port: int = 8000, ride_duration_minutes: int = 30):
    """Start the web server with integrated mock data generation for development."""
    global web_server
    web_server = WebServer(ride_duration_minutes=ride_duration_minutes)
    
    # Set up mock data generation
    import asyncio
    from contextlib import asynccontextmanager
    from ..config import Config, DeviceConfig, MetricConfig
    from ..controller import DeviceController
    
    # Create mock configuration
    config = Config()
    config.mock_mode = True
    config.devices = [DeviceConfig(
        name="Mock Trainer",
        address="00:00:00:00:00:00",
        services=["Power", "Heart Rate"]
    )]
    config.display = [
        MetricConfig(metric="power", display_name="Power ⚡", device="Mock Trainer", color="red"),
        MetricConfig(metric="speed", display_name="Speed 🚴", device="Mock Trainer", color="blue"),
        MetricConfig(metric="cadence", display_name="Cadence 🔄", device="Mock Trainer", color="yellow"),
        MetricConfig(metric="heart_rate", display_name="Heart Rate 💓", device="Mock Trainer", color="red"),
    ]
    
    # Create controller and set up mock device
    controller = DeviceController(config=config, show_display=False, enable_recording=False)
    
    def mock_broadcast_metrics(metrics):
        """Local broadcast function that has access to the web_server instance."""
        if web_server:
            for metric_name, value in metrics.items():
                web_server.update_metric(metric_name, value)
        else:
            print("❌ No web_server instance in mock_broadcast_metrics")
    
    controller.set_web_ui_callbacks(mock_broadcast_metrics)
    
    async def setup_mock_devices():
        """Set up mock devices after the server starts."""
        await asyncio.sleep(1)  # Give server time to start
        print("🔍 Setting up mock devices...")
        try:
            connected = await controller.connect_configured_devices(debug=False)
            if connected:
                print("🤖 Mock devices connected and generating data!")
            else:
                print("❌ Failed to connect mock devices")
        except Exception as e:
            print(f"❌ Error setting up mock devices: {e}")
            import traceback
            traceback.print_exc()
    
    # Add mock device setup to the server's lifespan
    original_lifespan = web_server.app.router.lifespan_context
    
    @asynccontextmanager
    async def enhanced_lifespan(app: FastAPI):
        # Start the original lifespan
        async with original_lifespan(app):
            # Start mock device setup task
            mock_task = asyncio.create_task(setup_mock_devices())
            try:
                yield
            finally:
                mock_task.cancel()
                try:
                    await mock_task
                except asyncio.CancelledError:
                    pass
    
    web_server.app.router.lifespan_context = enhanced_lifespan
    
    # Start the server
    web_server.start(host, port)


if __name__ == "__main__":
    start_server() 