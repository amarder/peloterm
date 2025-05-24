"""Tests for the web server functionality."""

import pytest
import asyncio
import json
import time
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from peloterm.web.server import WebServer, start_server, stop_server, broadcast_metrics
from peloterm.data_processor import DataProcessor
from peloterm.web.mock_data import MockDataGenerator, start_mock_data_stream


@pytest.fixture
async def web_server():
    """Create a test web server instance."""
    server = WebServer(ride_duration_minutes=30, update_interval=0.01)
    # Start update loop with a short timeout for testing
    server.update_task = asyncio.create_task(server.update_loop(timeout=1.0))

    # Ensure the global web_server points to this instance for the test duration
    import peloterm.web.server
    original_global_web_server = peloterm.web.server.web_server
    peloterm.web.server.web_server = server

    yield server

    # Cleanup: Restore original global web_server
    peloterm.web.server.web_server = original_global_web_server

    server.shutdown_event.set()
    if server.update_task and not server.update_task.done():
        server.update_task.cancel()
        try:
            await server.update_task
        except asyncio.CancelledError:
            pass
    # Clear any remaining connections
    for conn in server.active_connections.copy():
        try:
            await conn.close(code=1000)  # Use proper close code
        except Exception:
            pass
    server.active_connections.clear()


@pytest.fixture
def test_client(web_server):
    """Create a test client for the FastAPI app."""
    return TestClient(web_server.app)


def test_index_route(test_client):
    """Test the main index route returns HTML."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_config_endpoint(test_client):
    """Test the config endpoint returns expected configuration."""
    response = test_client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    
    # Check required config fields
    assert "ride_duration_minutes" in data
    assert "ride_start_time" in data
    assert isinstance(data["ride_start_time"], (int, float))
    assert "metrics" in data
    assert isinstance(data["metrics"], list)
    assert len(data["metrics"]) > 0
    
    # Check metric structure
    metric = data["metrics"][0]
    assert all(key in metric for key in ["name", "key", "symbol", "color"])
    
    # Verify all expected metrics are present
    metric_keys = {m["key"] for m in data["metrics"]}
    expected_metrics = {"power", "speed", "cadence", "heart_rate"}
    assert metric_keys == expected_metrics


@pytest.mark.asyncio
async def test_websocket_connection(web_server):
    """Test WebSocket connection and message broadcasting."""
    client = TestClient(web_server.app)
    with client.websocket_connect("/ws") as websocket:
        # Test metric broadcasting
        test_metrics = {"power": 200, "cadence": 90}
        broadcast_metrics(test_metrics)
        
        # Brief wait for processing
        await asyncio.sleep(0.1)
        
        # Receive message and verify it contains our metrics
        try:
            data = websocket.receive_json()
            assert isinstance(data, dict)
            assert "timestamp" in data
            assert data["power"] == 200
            assert data["cadence"] == 90
            assert isinstance(data["timestamp"], (int, float))
        except Exception as e:
            pytest.fail(f"Failed to receive or validate websocket data: {e}")


@pytest.mark.asyncio
async def test_websocket_error_handling(web_server):
    """Test WebSocket error handling and connection cleanup."""
    client = TestClient(web_server.app)
    
    # Test connection cleanup on error
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as websocket:
            # Force a connection error by closing the socket
            await websocket.close()
            # Try to send data after close
            await websocket.send_text("test")
    
    # Verify connection was removed from active set
    assert len(web_server.active_connections) == 0


@pytest.mark.asyncio
async def test_multiple_websocket_clients(web_server):
    """Test multiple WebSocket clients receiving updates."""
    client = TestClient(web_server.app)
    
    # Connect first client
    with client.websocket_connect("/ws") as ws1:
        # Connect second client
        with client.websocket_connect("/ws") as ws2:
            # Verify both connections are in the active set
            assert len(web_server.active_connections) == 2
            
            # Send test metrics
            test_metrics = {"heart_rate": 150}
            broadcast_metrics(test_metrics)
            
            # Brief wait for processing
            await asyncio.sleep(0.1)
            
            try:
                # Both clients should receive the update
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()
                
                assert isinstance(data1, dict)
                assert isinstance(data2, dict)
                assert "heart_rate" in data1
                assert data1["heart_rate"] == 150
                assert data1 == data2
                
                # Test that timestamps are identical
                assert data1["timestamp"] == data2["timestamp"]
            except Exception as e:
                pytest.fail(f"Failed to receive or validate websocket data: {e}")


@pytest.mark.asyncio
async def test_metrics_history(web_server):
    """Test metrics history management."""
    current_time = time.time()
    
    # Add some test metrics
    test_metrics = [
        {"power": 200, "timestamp": current_time - 3700},  # Old data
        {"power": 250, "timestamp": current_time - 1800},  # Within 1 hour
        {"power": 300, "timestamp": current_time}          # Current
    ]
    web_server.metrics_history.extend(test_metrics)
    
    # Run the update loop once with a short timeout
    await web_server.update_loop(timeout=0.1)
    
    # Check that old data is removed
    assert len(web_server.metrics_history) == 2
    assert all(m["timestamp"] > current_time - 3600 for m in web_server.metrics_history)
    
    # Verify the order is maintained
    assert web_server.metrics_history[0]["power"] == 250
    assert web_server.metrics_history[1]["power"] == 300


@pytest.mark.asyncio
async def test_historical_data_replay(web_server):
    """Test historical data replay for new WebSocket connections."""
    # Add some historical data
    current_time = time.time()
    historical_data = [
        {"power": 100, "timestamp": current_time - 300},
        {"power": 150, "timestamp": current_time - 200},
        {"power": 200, "timestamp": current_time - 100}
    ]
    web_server.metrics_history.extend(historical_data)
    
    # Connect a new client
    client = TestClient(web_server.app)
    with client.websocket_connect("/ws") as websocket:
        # Should receive historical data in order
        received_data = []
        for _ in range(len(historical_data)):
            data = websocket.receive_json()
            received_data.append(data)
        
        # Verify data order and values
        assert len(received_data) == len(historical_data)
        for hist, recv in zip(historical_data, received_data):
            assert hist["power"] == recv["power"]
            assert abs(hist["timestamp"] - recv["timestamp"]) < 0.1


@pytest.mark.asyncio
async def test_server_shutdown(web_server):
    """Test proper server shutdown and cleanup using the web_server fixture."""
    # web_server fixture already provides a running server with a TestClient implicitly
    # The fixture also handles setting the global web_server instance
    
    server = web_server # Get the server instance from the fixture
    client = TestClient(server.app) # Create a client for this specific test scope if needed for clarity
                                    # though web_server fixture usually implies one is used by its tests.

    connections = []
    try:
        # Connect multiple test clients
        for _ in range(3):
            websocket = client.websocket_connect("/ws")
            connections.append(websocket)
            websocket.__enter__() # Manually enter context for later exit
        
        assert len(server.active_connections) == 3
        
        # Signal server to stop (this sets events for lifespan manager to act upon)
        server.stop()
        
        # Lifespan manager (triggered by TestClient exiting context or app shutdown)
        # should handle closing connections and cancelling tasks.
        # We need to give it a moment to process the shutdown signals.
        await asyncio.sleep(0.2) # Allow time for lifespan and update_loop to react

        # Check cleanup (active_connections should be cleared by lifespan shutdown)
        assert len(server.active_connections) == 0, "Active connections not cleared"
        assert server.shutdown_event.is_set(), "Shutdown event not set"
        if server.update_task:
            assert server.update_task.done() or server.update_task.cancelled(), "Update task not done/cancelled"

    finally:
        # Ensure all client-side WebSocket connections are closed
        for ws_context in connections:
            try:
                # Attempt to exit context, which will try to close WebSocket
                ws_context.__exit__(None, None, None)
            except Exception:
                pass # Ignore errors if already closed by server
        
        # The web_server fixture's cleanup part will handle final server task cancellation and cleanup.


@pytest.mark.asyncio
async def test_data_processor_integration(web_server):
    """Test integration with DataProcessor."""
    # Update multiple metrics
    test_metrics = {
        "power": 250,
        "cadence": 90,
        "speed": 30.5,
        "heart_rate": 160
    }
    
    for metric, value in test_metrics.items():
        web_server.update_metric(metric, value)
    
    # Get processed metrics
    metrics = web_server.data_processor.get_processed_metrics()
    
    # Verify all metrics were updated correctly
    for metric, value in test_metrics.items():
        assert metrics[metric] == value


@pytest.mark.asyncio
async def test_mock_data_integration():
    """Test integration with mock data generator."""
    server = WebServer(ride_duration_minutes=30)
    
    # Create mock data generator with fixed start time
    start_time = time.time()
    generator = MockDataGenerator(start_time=start_time)
    
    # Generate and verify mock metrics
    metrics = generator.generate_metrics()
    
    # Verify all expected metrics are present
    expected_metrics = {"power", "speed", "cadence", "heart_rate"}
    assert set(metrics.keys()) == expected_metrics
    
    # Verify values are within reasonable ranges
    assert 0 <= metrics["power"] <= 400  # Reasonable power range
    assert 0 <= metrics["speed"] <= 50   # Reasonable speed range
    assert 0 <= metrics["cadence"] <= 120  # Reasonable cadence range
    assert 60 <= metrics["heart_rate"] <= 200  # Reasonable heart rate range


@pytest.mark.asyncio
async def test_broadcast_metrics_function():
    """Test the standalone broadcast_metrics function."""
    server = WebServer(ride_duration_minutes=30, update_interval=0.01)
    
    # Set the global web_server instance for this test
    import peloterm.web.server
    original_global_web_server = peloterm.web.server.web_server
    peloterm.web.server.web_server = server
    
    # Start the update_loop for this server instance as it's not managed by a fixture here
    # The update_loop is what processes metrics from data_processor into metrics_history
    update_task = asyncio.create_task(server.update_loop(timeout=0.2)) 

    try:
        # Test broadcasting metrics
        test_metrics = {"speed": 30.5, "heart_rate": 160}
        broadcast_metrics(test_metrics) # This updates server.data_processor
        
        # Verify metrics were updated in the data processor IMMEDIATELY
        processed = server.data_processor.get_processed_metrics()
        assert "speed" in processed, "Speed metric not found in processor after broadcast"
        assert processed["speed"] == 30.5
        assert "heart_rate" in processed, "Heart rate metric not found in processor after broadcast"
        assert processed["heart_rate"] == 160
        
        # Now, re-populate the data processor for the update_loop to consume,
        # as get_processed_metrics clears them.
        # This is a bit artificial but necessary to test both parts.
        # A more robust test might involve mocking get_processed_metrics or
        # having a way to peek into DataProcessor without clearing.
        for metric, value in test_metrics.items():
            server.data_processor.update_metric(metric, value)

        # Allow the update_loop to process the metrics from data_processor to history
        await asyncio.sleep(0.1) 
        
        # Verify metrics were added to history by the update_loop
        assert len(server.metrics_history) == 1
        assert server.metrics_history[0]["speed"] == 30.5
        assert server.metrics_history[0]["heart_rate"] == 160
        assert "timestamp" in server.metrics_history[0]
    finally:
        # Clean up global instance
        peloterm.web.server.web_server = original_global_web_server
        # Stop and clean up the update_task for this server
        server.shutdown_event.set()
        if update_task and not update_task.done():
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass 