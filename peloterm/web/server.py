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
import uvicorn
from ..data_processor import DataProcessor


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
        
        # Clear metrics history
        app.state.web_server.metrics_history.clear()


class WebServer:
    def __init__(self, ride_duration_minutes: int = 30, update_interval: float = 1.0):
        self.app = FastAPI(
            title="PeloTerm",
            description="Cycling Metrics Dashboard",
            lifespan=lifespan
        )
        self.active_connections: Set[WebSocket] = set()
        self.ride_duration_minutes = ride_duration_minutes
        self.ride_start_time = time.time()  # Server-side ride start time
        self.metrics_history: List[Dict] = []  # Store all metrics with timestamps
        self.data_processor = DataProcessor()
        self.update_interval = update_interval
        self.update_task = None
        self.server = None  # Store the uvicorn server instance
        self.shutdown_event = threading.Event()  # Add shutdown event
        
        # Store web server instance in app state for lifespan access
        self.app.state.web_server = self
        
        self.setup_routes()

    def setup_routes(self):
        """Set up FastAPI routes."""
        # Mount static files
        static_path = Path(__file__).parent / "static"
        self.app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        
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
                # Send historical data to newly connected client
                if self.metrics_history:
                    # Sort historical data by timestamp before sending
                    sorted_history = sorted(self.metrics_history, key=lambda x: x["timestamp"])
                    
                    print(f"Sending {len(sorted_history)} historical data points to new client")
                    for i, historical_metrics in enumerate(sorted_history):
                        try:
                            await websocket.send_text(json.dumps(historical_metrics))
                            # Small delay every 10 messages to prevent overwhelming the client
                            if i % 10 == 0:
                                await asyncio.sleep(0.01)
                        except Exception as e:
                            print(f"Error sending historical data: {e}")
                            break
                    print("Finished sending historical data")
                
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
                    # Add timestamp and store in history
                    timestamped_metrics = {
                        **metrics,
                        "timestamp": current_time
                    }
                    # self.metrics_history.append(timestamped_metrics) # Append after pruning

                    # Broadcast to all connected clients
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
                
                # Prune metrics history and add new metric if available
                # This should happen regardless of new metrics from data_processor
                # to ensure manually added history in tests is also pruned.
                max_history_seconds = 3600  # 1 hour
                cutoff_time = current_time - max_history_seconds
                
                # Prune old metrics
                self.metrics_history = [m for m in self.metrics_history if m["timestamp"] > cutoff_time]

                if metrics: # Add the new metric *after* pruning old ones
                    self.metrics_history.append(timestamped_metrics)

            except Exception as e:
                print(f"Error in update loop: {e}")
            
            try:
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break

    def update_metric(self, metric_name: str, value: Any):
        """Update a metric in the data processor."""
        self.data_processor.update_metric(metric_name, value)

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
        
        # Clear metrics history
        self.metrics_history.clear()
        
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