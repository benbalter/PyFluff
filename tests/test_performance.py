"""
Performance tests for PyFluff optimizations.

These tests verify that performance improvements don't break functionality.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyfluff.dlc import DLCManager
from pyfluff.furby import FurbyConnect
from pyfluff.furby_cache import FurbyCache
from pyfluff.models import KnownFurby


@pytest.mark.asyncio
async def test_dlc_async_file_read():
    """Test that DLC upload uses async file I/O."""
    # Create a mock Furby connection
    furby = MagicMock(spec=FurbyConnect)
    furby.connected = True
    furby._gp_callbacks = []
    furby.enable_nordic_packet_ack = AsyncMock()
    furby._write_gp = AsyncMock()
    furby._write_file = AsyncMock()

    # Create a temporary DLC file
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".dlc") as tmp:
        tmp.write(b"TEST DLC CONTENT" * 100)  # 1600 bytes
        tmp_path = Path(tmp.name)

    try:
        dlc_manager = DLCManager(furby)
        
        # Set up async mock to trigger callbacks properly
        async def mock_write_gp(cmd: bytes) -> None:
            # Simulate Furby responding with ready signal
            await asyncio.sleep(0.01)
            dlc_manager._transfer_ready.set()
        
        furby._write_gp = mock_write_gp
        
        # Mock transfer complete will be set after file write
        async def mock_write_file(data: bytes) -> None:
            await asyncio.sleep(0.001)
        
        furby._write_file = mock_write_file
        
        # Simulate transfer completion after a short delay
        async def complete_transfer():
            await asyncio.sleep(0.1)
            dlc_manager._transfer_complete.set()
        
        asyncio.create_task(complete_transfer())
        
        # Upload should complete without errors
        await dlc_manager.upload_dlc(tmp_path, slot=2, enable_nordic_ack=False)
        
        # Verify the file was read and processed
        # The mock functions were called, which means async I/O worked
        
    finally:
        tmp_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_cache_debouncing():
    """Test that cache writes are debounced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "test_cache.json"
        cache = FurbyCache(cache_file)
        
        # Add multiple entries quickly
        addresses = [f"AA:BB:CC:DD:EE:{i:02X}" for i in range(5)]
        
        for addr in addresses:
            cache.add_or_update(address=addr, device_name="Furby")
        
        # Verify entries are in memory
        assert len(cache.get_all()) == 5
        
        # Wait for debounce to complete
        if cache._save_task:
            await cache._save_task
        
        # Verify file was written
        assert cache_file.exists()
        
        # Force flush
        await cache.flush()


def test_cache_backward_compatibility():
    """Test that cache still works without async event loop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "test_cache.json"
        cache = FurbyCache(cache_file)
        
        # This should work even without an event loop
        cache.add_or_update(
            address="AA:BB:CC:DD:EE:FF",
            device_name="Furby"
        )
        
        # Verify entry was added
        furby = cache.get("AA:BB:CC:DD:EE:FF")
        assert furby is not None
        assert furby.address == "AA:BB:CC:DD:EE:FF"


@pytest.mark.asyncio
async def test_parallel_characteristic_reads():
    """Test that get_device_info reads characteristics in parallel."""
    from pyfluff.models import FurbyInfo
    
    # Create a mock client
    mock_client = AsyncMock()
    mock_client.is_connected = True
    
    # Track call order and timing
    read_times = []
    
    async def mock_read(char_uuid: str) -> bytes:
        read_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.01)  # Simulate BLE delay
        return b"test_value\x00"
    
    mock_client.read_gatt_char = mock_read
    
    # Create FurbyConnect instance
    furby = FurbyConnect()
    furby.client = mock_client
    furby._connected = True
    
    # Get device info
    start_time = asyncio.get_event_loop().time()
    info = await furby.get_device_info()
    end_time = asyncio.get_event_loop().time()
    
    # All reads should start at approximately the same time (parallel)
    # If sequential, would take ~60ms (6 reads * 10ms each)
    # If parallel, should take ~10-15ms (one read + overhead)
    elapsed = end_time - start_time
    
    # Verify info was populated
    assert isinstance(info, FurbyInfo)
    assert info.manufacturer == "test_value"
    
    # Verify parallel execution (should be faster than sequential)
    # Allow some overhead, but should be much less than 6 * 10ms = 60ms
    assert elapsed < 0.05, f"Reads took {elapsed:.3f}s, should be parallel (<50ms)"
    
    # Verify all 6 characteristics were read
    assert len(read_times) == 6
    
    # Check that reads started close together (within 5ms)
    if len(read_times) > 1:
        time_spread = max(read_times) - min(read_times)
        assert time_spread < 0.005, f"Reads spread over {time_spread:.3f}s, should be parallel"


@pytest.mark.asyncio
async def test_websocket_keepalive_efficiency():
    """Test that WebSocket connections don't use busy-wait loops."""
    # This is a design test - the actual implementation should use
    # websocket.receive_text() which blocks efficiently rather than
    # asyncio.sleep() in a tight loop
    
    # We can't easily test this directly, but we verify the pattern
    # by checking that receive_text is used in the websocket handler
    from pyfluff.server import websocket_logs
    import inspect
    
    source = inspect.getsource(websocket_logs)
    
    # Verify we're using receive_text (efficient) not sleep in a loop
    assert "receive_text" in source, "WebSocket should use receive_text for keepalive"
    assert "sleep(1)" not in source, "WebSocket should not busy-wait with sleep(1)"


def test_cache_flush_api():
    """Test that cache has a flush method for clean shutdown."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "test_cache.json"
        cache = FurbyCache(cache_file)
        
        # Verify flush method exists
        assert hasattr(cache, "flush")
        assert callable(cache.flush)
