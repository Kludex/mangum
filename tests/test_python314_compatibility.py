"""
Test Python 3.14 compatibility for event loop handling.

This test specifically addresses the issue where asyncio.get_event_loop()
raises RuntimeError in Python 3.14 when no current event loop exists.
"""

import asyncio
import sys
import threading
from unittest.mock import patch

import pytest

from mangum.protocols.lifespan import LifespanCycle


class TestPython314Compatibility:
    """Test cases for Python 3.14 event loop compatibility."""

    def test_event_loop_helper_method_exists(self):
        """Test that the helper method exists and is callable."""
        assert hasattr(LifespanCycle, '_get_or_create_event_loop')
        assert callable(LifespanCycle._get_or_create_event_loop)

    def test_event_loop_helper_method_returns_loop(self):
        """Test that the helper method returns an event loop."""
        loop = LifespanCycle._get_or_create_event_loop()
        assert isinstance(loop, asyncio.AbstractEventLoop)
        # Clean up the loop to avoid resource warnings
        if not loop.is_running():
            loop.close()

    def test_lifespan_cycle_creation_without_existing_loop(self):
        """
        Test LifespanCycle creation when no event loop exists.
        
        This simulates the Python 3.14 scenario where get_event_loop()
        would raise RuntimeError.
        """
        async def simple_app(scope, receive, send):
            if scope["type"] == "lifespan":
                while True:
                    message = await receive()
                    if message["type"] == "lifespan.startup":
                        await send({"type": "lifespan.startup.complete"})
                    elif message["type"] == "lifespan.shutdown":
                        await send({"type": "lifespan.shutdown.complete"})
                        return

        # This should not raise RuntimeError
        lifespan_cycle = LifespanCycle(simple_app, "auto")
        assert lifespan_cycle.loop is not None
        assert isinstance(lifespan_cycle.loop, asyncio.AbstractEventLoop)

    @pytest.mark.skipif(
        sys.version_info < (3, 7),
        reason="asyncio.get_running_loop() not available in Python < 3.7"
    )
    def test_helper_method_with_running_loop(self):
        """Test helper method when there's already a running event loop."""
        async def test_with_running_loop():
            # Inside an async function, there should be a running loop
            loop = LifespanCycle._get_or_create_event_loop()
            running_loop = asyncio.get_running_loop()
            assert loop is running_loop

        # Run the test in an event loop
        asyncio.run(test_with_running_loop())

    def test_helper_method_without_running_loop(self):
        """Test helper method when there's no running event loop."""
        def test_in_thread():
            # In a separate thread, there should be no running loop
            loop = LifespanCycle._get_or_create_event_loop()
            assert isinstance(loop, asyncio.AbstractEventLoop)
            # Clean up the loop to avoid resource warnings
            loop.close()

        # Run in a separate thread to ensure no running loop
        thread = threading.Thread(target=test_in_thread)
        thread.start()
        thread.join()

    @pytest.mark.skipif(
        sys.version_info < (3, 7),
        reason="This test simulates Python 3.14 behavior"
    )
    def test_helper_method_handles_runtime_error(self):
        """
        Test that helper method handles RuntimeError from get_running_loop().
        
        This simulates the Python 3.14 scenario.
        """
        with patch('asyncio.get_running_loop') as mock_get_running:
            mock_get_running.side_effect = RuntimeError("no running event loop")
            
            with patch('asyncio.new_event_loop') as mock_new_loop:
                # Create the mock loop without calling the real function
                from unittest.mock import MagicMock
                mock_loop = MagicMock()
                mock_new_loop.return_value = mock_loop
                
                result = LifespanCycle._get_or_create_event_loop()
                
                mock_get_running.assert_called_once()
                mock_new_loop.assert_called_once()
                assert result is mock_loop

    @pytest.mark.skipif(
        sys.version_info >= (3, 7),
        reason="This test is for Python < 3.7 compatibility"
    )
    def test_helper_method_handles_attribute_error(self):
        """
        Test that helper method handles AttributeError for Python < 3.7.
        
        In Python < 3.7, asyncio.get_running_loop() doesn't exist.
        """
        with patch('asyncio.get_running_loop') as mock_get_running:
            mock_get_running.side_effect = AttributeError("no get_running_loop")
            
            with patch('asyncio.get_event_loop') as mock_get_event_loop:
                from unittest.mock import MagicMock
                mock_loop = MagicMock()
                mock_get_event_loop.return_value = mock_loop
                
                result = LifespanCycle._get_or_create_event_loop()
                
                mock_get_running.assert_called_once()
                mock_get_event_loop.assert_called_once()
                assert result is mock_loop

    def test_lifespan_cycle_uses_helper_method(self):
        """Test that LifespanCycle.__init__ uses the helper method."""
        async def simple_app(scope, receive, send):
            pass

        with patch.object(LifespanCycle, '_get_or_create_event_loop') as mock_helper:
            from unittest.mock import MagicMock
            mock_loop = MagicMock()
            mock_helper.return_value = mock_loop
            
            lifespan_cycle = LifespanCycle(simple_app, "auto")
            
            mock_helper.assert_called_once()
            assert lifespan_cycle.loop is mock_loop