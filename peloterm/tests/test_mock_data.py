"""Tests for mock data generation and streaming."""

import pytest
import asyncio
import time
from peloterm.web.mock_data import MockDataGenerator, start_mock_data_stream
from peloterm.web.server import WebServer


@pytest.fixture
def mock_generator():
    """Create a mock data generator with a fixed start time."""
    start_time = time.time()
    return MockDataGenerator(start_time=start_time)


def test_mock_data_generation(mock_generator):
    """Test that mock data generation produces valid metrics."""
    metrics = mock_generator.generate_metrics()
    
    # Check all required metrics are present
    assert set(metrics.keys()) == {"power", "speed", "cadence", "heart_rate"}
    
    # Check value ranges
    assert 0 <= metrics["power"] <= 400  # Reasonable power range
    assert 0 <= metrics["speed"] <= 50   # Reasonable speed range
    assert 0 <= metrics["cadence"] <= 120  # Reasonable cadence range
    assert 60 <= metrics["heart_rate"] <= 200  # Reasonable heart rate range


def test_mock_data_no_pedaling(mock_generator):
    """Test the no-pedaling simulation."""
    # Force no pedaling state
    mock_generator.last_no_pedaling = time.time()
    mock_generator.no_pedaling_duration = 5
    
    metrics = mock_generator.generate_metrics()
    
    # During no pedaling, power and cadence should be 0
    assert metrics["power"] == 0
    assert metrics["cadence"] == 0
    # Speed should be reduced but not zero (coasting)
    assert 0 < metrics["speed"] < mock_generator.base_speed
    # Heart rate should be lower but not below 60
    assert 60 <= metrics["heart_rate"] < mock_generator.base_heart_rate


@pytest.mark.asyncio
async def test_mock_data_stream():
    """Test the mock data streaming functionality."""
    server = WebServer(ride_duration_minutes=30)
    
    # Set the global web_server instance for the stream
    import peloterm.web.server
    original_web_server = peloterm.web.server.web_server
    peloterm.web.server.web_server = server
    
    # Store received metrics
    received_metrics = []
    
    async def mock_broadcast(metrics):
        received_metrics.append(metrics)
    
    stream_task = None
    try:
        # Start mock data stream in background task
        stream_task = asyncio.create_task(
            start_mock_data_stream(mock_broadcast, interval=0.1)
        )
        
        # Let it run for a short time
        await asyncio.sleep(0.3)
        
        # Stop the stream
        server.shutdown_event.set()
        await stream_task
        
        # Check that we received some metrics
        assert len(received_metrics) >= 2
        
        # Check that metrics are changing
        assert received_metrics[0] != received_metrics[1]
        
        # Verify metric structure
        for metrics_item in received_metrics:
            assert set(metrics_item.keys()) == {"power", "speed", "cadence", "heart_rate"}
            assert all(isinstance(v, (int, float)) for v in metrics_item.values())
    finally:
        # Clean up global instance and task
        peloterm.web.server.web_server = original_web_server
        if stream_task and not stream_task.done():
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_mock_data_stream_error_handling():
    """Test error handling in mock data stream."""
    server = WebServer(ride_duration_minutes=30)
    
    # Set the global web_server instance for the stream
    import peloterm.web.server
    original_web_server = peloterm.web.server.web_server
    peloterm.web.server.web_server = server

    # Counter for broadcast calls
    call_count = 0
    
    async def failing_broadcast(metrics):
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # Fail on second call
            raise Exception("Test error")
        # Ensure this is awaitable if it does something async in future
        await asyncio.sleep(0) 
    
    stream_task = None
    try:
        # Start mock data stream in background task
        stream_task = asyncio.create_task(
            start_mock_data_stream(failing_broadcast, interval=0.1)
        )
        
        # Let it run for a short time
        await asyncio.sleep(0.5)
        
        # Stop the stream
        server.shutdown_event.set()
        await stream_task
        
        # Should have continued past the error
        assert call_count > 2
    finally:
        # Clean up global instance and task
        peloterm.web.server.web_server = original_web_server
        if stream_task and not stream_task.done():
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_mock_data_stream_cancellation():
    """Test that mock data stream handles cancellation gracefully."""
    server = WebServer(ride_duration_minutes=30)

    # Set the global web_server instance for the stream
    import peloterm.web.server
    original_web_server = peloterm.web.server.web_server
    peloterm.web.server.web_server = server
    
    metrics_received = []
    
    async def mock_broadcast(metrics):
        metrics_received.append(metrics)
    
    stream_task = None
    try:
        # Start mock data stream in background task
        stream_task = asyncio.create_task(
            start_mock_data_stream(mock_broadcast, interval=0.1)
        )
        
        # Let it run briefly
        await asyncio.sleep(0.2)
        
        # Cancel the task
        stream_task.cancel()
        
        try:
            await stream_task
        except asyncio.CancelledError:
            pass # Expected
        
        # Should have received some metrics before cancellation
        assert len(metrics_received) > 0
    finally:
        # Clean up global instance and task
        peloterm.web.server.web_server = original_web_server
        if stream_task and not stream_task.done() and not stream_task.cancelled():
            # If not already cancelled and done, try to set shutdown and await
            server.shutdown_event.set()
            try:
                await stream_task # Allow it to finish based on shutdown_event
            except asyncio.CancelledError:
                 pass # if it gets cancelled again 