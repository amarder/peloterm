"""FastAPI web server for PeloTerm."""

import json
import asyncio
import time
from pathlib import Path
from typing import Dict, Set, List, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from ..data_processor import DataProcessor


class WebServer:
    def __init__(self, ride_duration_minutes: int = 30, update_interval: float = 1.0):
        self.app = FastAPI(title="PeloTerm", description="Cycling Metrics Dashboard")
        self.active_connections: Set[WebSocket] = set()
        self.ride_duration_minutes = ride_duration_minutes
        self.ride_start_time = time.time()  # Server-side ride start time
        self.metrics_history: List[Dict] = []  # Store all metrics with timestamps
        self.data_processor = DataProcessor()
        self.update_interval = update_interval
        self.update_task = None
        self.setup_routes()
        
        # Set up startup and shutdown events
        @self.app.on_event("startup")
        async def startup_event():
            # Create the update task when the app starts
            self.update_task = asyncio.create_task(self.update_loop())
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            # Cancel the update task when the app shuts down
            if self.update_task:
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass

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
            # This will be populated from the actual config
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
            
            # Send historical data to newly connected client with small delays
            if self.metrics_history:
                print(f"Sending {len(self.metrics_history)} historical data points to new client")
                for i, historical_metrics in enumerate(self.metrics_history):
                    try:
                        await websocket.send_text(json.dumps(historical_metrics))
                        # Small delay to prevent overwhelming the client
                        if i % 10 == 0:  # Every 10 messages
                            await asyncio.sleep(0.01)
                    except Exception as e:
                        print(f"Error sending historical data: {e}")
                        break
                print("Finished sending historical data")
            
            try:
                # Keep connection alive and handle incoming messages
                while True:
                    data = await websocket.receive_text()
                    # For now, just echo back - could handle client messages here
                    # await websocket.send_text(f"Echo: {data}")
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
            except Exception:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)

    async def update_loop(self):
        """Regular update loop to process and broadcast metrics."""
        while True:
            try:
                # Get processed metrics
                metrics = self.data_processor.get_processed_metrics()
                if metrics:
                    await self.broadcast_metrics(metrics)
            except Exception as e:
                print(f"Error in update loop: {e}")
            await asyncio.sleep(self.update_interval)

    async def broadcast_metrics(self, metrics: Dict):
        """Broadcast metrics to all connected clients."""
        if not self.active_connections:
            return
        
        # Add timestamp and store in history
        timestamped_metrics = {
            **metrics,
            "timestamp": time.time()
        }
        self.metrics_history.append(timestamped_metrics)
        
        # Keep only recent history (e.g., last hour worth of data)
        max_history_seconds = 3600  # 1 hour
        cutoff_time = time.time() - max_history_seconds
        self.metrics_history = [m for m in self.metrics_history if m["timestamp"] > cutoff_time]
            
        message = json.dumps(timestamped_metrics)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)
        
        # Remove disconnected clients
        self.active_connections -= disconnected

    def update_metric(self, metric_name: str, value: Any):
        """Update a metric in the data processor."""
        self.data_processor.update_metric(metric_name, value)

    def start(self, host: str = "127.0.0.1", port: int = 8000):
        """Start the web server."""
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run()


# Global instance
web_server = None


def start_server(host: str = "127.0.0.1", port: int = 8000, ride_duration_minutes: int = 30):
    """Start the web server."""
    global web_server
    web_server = WebServer(ride_duration_minutes=ride_duration_minutes)
    web_server.start(host, port)


async def broadcast_metrics(metrics: Dict):
    """Update metrics in the data processor."""
    if web_server:
        for metric_name, value in metrics.items():
            web_server.update_metric(metric_name, value) 