# -*- coding: utf-8 -*-
"""
Unit tests for abstract base classes.

Tests for Display and InputHandler abstract base classes.
"""

import unittest
from unittest.mock import MagicMock, patch
from vindauga.io.display.base import Display
from vindauga.io.display.buffer import DisplayBuffer, ScreenCell
from vindauga.io.input.base import InputHandler
from vindauga.events.event import Event


class MockDisplay(Display):
    """Mock implementation of Display for testing."""
    
    def __init__(self):
        super().__init__()
        self._mock_initialized = False
        self._mock_color_count = 256
        self._mock_supports_colors = True
        self._mock_supports_mouse = True
    
    def initialize(self) -> bool:
        self._mock_initialized = True
        self._initialized = True
        self._width = 80
        self._height = 25
        return True
    
    def shutdown(self) -> None:
        self._mock_initialized = False
        self._initialized = False
    
    def get_size(self) -> tuple:
        return (self._width, self._height)
    
    def flush_buffer(self, buffer: DisplayBuffer) -> None:
        # Mock implementation - just mark as flushed
        buffer.commit_flush()
    
    def set_cursor_position(self, x: int, y: int) -> None:
        self._cursor_x = x
        self._cursor_y = y
    
    def set_cursor_visibility(self, visible: bool) -> None:
        self._cursor_visible = visible
    
    def clear_screen(self) -> None:
        pass
    
    def supports_colors(self) -> bool:
        return self._mock_supports_colors
    
    def supports_mouse(self) -> bool:
        return self._mock_supports_mouse
    
    def get_color_count(self) -> int:
        return self._mock_color_count


class MockInputHandler(InputHandler):
    """Mock implementation of InputHandler for testing."""
    
    def __init__(self):
        super().__init__()
        self._mock_events = []
        self._mock_supports_mouse = True
    
    def initialize(self) -> bool:
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        self._initialized = False
    
    def get_event(self, timeout: float = 0.0) -> Event:
        if self._mock_events:
            return self._mock_events.pop(0)
        return None
    
    def has_events(self) -> bool:
        return len(self._mock_events) > 0
    
    def enable_mouse(self, enable: bool = True) -> bool:
        self._mouse_enabled = enable
        return True
    
    def supports_mouse(self) -> bool:
        return self._mock_supports_mouse
    
    def flush_input(self) -> None:
        self._mock_events.clear()
    
    def add_mock_event(self, event: Event) -> None:
        """Add a mock event for testing."""
        self._mock_events.append(event)


class TestDisplayBase(unittest.TestCase):
    """Test cases for Display abstract base class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.display = MockDisplay()
    
    def test_initialization(self):
        """Test display initialization."""
        self.assertFalse(self.display.is_initialized)
        
        result = self.display.initialize()
        self.assertTrue(result)
        self.assertTrue(self.display.is_initialized)
        self.assertEqual(self.display.width, 80)
        self.assertEqual(self.display.height, 25)
    
    def test_shutdown(self):
        """Test display shutdown."""
        self.display.initialize()
        self.assertTrue(self.display.is_initialized)
        
        self.display.shutdown()
        self.assertFalse(self.display.is_initialized)
    
    def test_properties(self):
        """Test display properties."""
        self.display.initialize()
        
        self.assertEqual(self.display.width, 80)
        self.assertEqual(self.display.height, 25)
        self.assertTrue(self.display.cursor_visible)
        self.assertEqual(self.display.cursor_position, (0, 0))
    
    def test_cursor_operations(self):
        """Test cursor operations."""
        self.display.initialize()
        
        # Test cursor position
        self.display.set_cursor_position(10, 5)
        self.assertEqual(self.display.cursor_position, (10, 5))
        
        # Test cursor visibility
        self.display.set_cursor_visibility(False)
        self.assertFalse(self.display.cursor_visible)
        
        self.display.set_cursor_visibility(True)
        self.assertTrue(self.display.cursor_visible)
    
    def test_capabilities(self):
        """Test capability queries."""
        self.assertTrue(self.display.supports_colors())
        self.assertTrue(self.display.supports_mouse())
        self.assertEqual(self.display.get_color_count(), 256)
    
    def test_put_cell(self):
        """Test putting a single cell."""
        self.display.initialize()
        
        cell = ScreenCell('A', 0x07)
        self.display.put_cell(10, 5, cell)
        
        # Mock implementation should handle this without errors
        # Real implementation would update the screen
    
    def test_put_text(self):
        """Test putting text."""
        self.display.initialize()
        
        self.display.put_text(10, 5, "Hello", 0x07)
        
        # Mock implementation should handle this without errors
    
    def test_put_operations_bounds_checking(self):
        """Test bounds checking for put operations."""
        self.display.initialize()
        
        # These should not cause errors (bounds checking in base class)
        self.display.put_text(-5, 5, "Hello", 0x07)
        self.display.put_text(100, 5, "Hello", 0x07)
        self.display.put_text(10, -5, "Hello", 0x07)
        self.display.put_text(10, 100, "Hello", 0x07)
        
        cell = ScreenCell('A', 0x07)
        self.display.put_cell(-5, 5, cell)
        self.display.put_cell(100, 5, cell)
        self.display.put_cell(10, -5, cell)
        self.display.put_cell(10, 100, cell)
    
    def test_resize(self):
        """Test display resize."""
        self.display.initialize()
        
        result = self.display.resize(100, 30)
        self.assertTrue(result)
        self.assertEqual(self.display.width, 100)
        self.assertEqual(self.display.height, 30)
        
        # Invalid sizes should fail
        result = self.display.resize(0, 30)
        self.assertFalse(result)
        
        result = self.display.resize(100, 0)
        self.assertFalse(result)
    
    def test_context_manager(self):
        """Test display as context manager."""
        with self.display as d:
            self.assertTrue(d.is_initialized)
            self.assertIs(d, self.display)
        
        self.assertFalse(self.display.is_initialized)
    
    def test_context_manager_init_failure(self):
        """Test context manager with initialization failure."""
        # Mock initialization failure
        self.display.initialize = MagicMock(return_value=False)
        
        with self.assertRaises(RuntimeError):
            with self.display:
                pass


class TestInputHandlerBase(unittest.TestCase):
    """Test cases for InputHandler abstract base class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.input_handler = MockInputHandler()
    
    def test_initialization(self):
        """Test input handler initialization."""
        self.assertFalse(self.input_handler.is_initialized)
        
        result = self.input_handler.initialize()
        self.assertTrue(result)
        self.assertTrue(self.input_handler.is_initialized)
    
    def test_shutdown(self):
        """Test input handler shutdown."""
        self.input_handler.initialize()
        self.assertTrue(self.input_handler.is_initialized)
        
        self.input_handler.shutdown()
        self.assertFalse(self.input_handler.is_initialized)
    
    def test_properties(self):
        """Test input handler properties."""
        self.assertFalse(self.input_handler.mouse_enabled)
        self.assertTrue(self.input_handler.supports_mouse())
    
    def test_mouse_operations(self):
        """Test mouse enable/disable."""
        result = self.input_handler.enable_mouse(True)
        self.assertTrue(result)
        self.assertTrue(self.input_handler.mouse_enabled)
        
        result = self.input_handler.enable_mouse(False)
        self.assertTrue(result)
        self.assertFalse(self.input_handler.mouse_enabled)
    
    def test_event_operations(self):
        """Test event operations."""
        # Initially no events
        self.assertFalse(self.input_handler.has_events())
        self.assertIsNone(self.input_handler.get_event(0.0))
        
        # Add a mock event
        mock_event = Event()
        self.input_handler.add_mock_event(mock_event)
        
        self.assertTrue(self.input_handler.has_events())
        
        event = self.input_handler.get_event(0.0)
        self.assertIs(event, mock_event)
        
        # Should be consumed
        self.assertFalse(self.input_handler.has_events())
    
    def test_peek_event(self):
        """Test event peeking."""
        mock_event = Event()
        self.input_handler.add_mock_event(mock_event)
        
        # Peek should return the event (base implementation uses get_event)
        event = self.input_handler.peek_event()
        self.assertIs(event, mock_event)
        
        # Event should be consumed (base implementation limitation)
        self.assertFalse(self.input_handler.has_events())
    
    def test_wait_for_event(self):
        """Test waiting for events."""
        mock_event = Event()
        self.input_handler.add_mock_event(mock_event)
        
        event = self.input_handler.wait_for_event(1.0)
        self.assertIs(event, mock_event)
        
        # No more events
        event = self.input_handler.wait_for_event(0.0)
        self.assertIsNone(event)
    
    def test_get_events_batch(self):
        """Test getting multiple events at once."""
        # Add multiple mock events
        events = [Event() for _ in range(5)]
        for event in events:
            self.input_handler.add_mock_event(event)
        
        # Get up to 3 events
        batch = self.input_handler.get_events(3)
        self.assertEqual(len(batch), 3)
        
        # Should be the first 3 events
        for i in range(3):
            self.assertIs(batch[i], events[i])
        
        # 2 events should remain
        self.assertTrue(self.input_handler.has_events())
        remaining = self.input_handler.get_events(10)
        self.assertEqual(len(remaining), 2)
    
    def test_flush_input(self):
        """Test input flushing."""
        # Add some events
        for _ in range(3):
            self.input_handler.add_mock_event(Event())
        
        self.assertTrue(self.input_handler.has_events())
        
        self.input_handler.flush_input()
        self.assertFalse(self.input_handler.has_events())
    
    def test_context_manager(self):
        """Test input handler as context manager."""
        with self.input_handler as ih:
            self.assertTrue(ih.is_initialized)
            self.assertIs(ih, self.input_handler)
        
        self.assertFalse(self.input_handler.is_initialized)
    
    def test_context_manager_init_failure(self):
        """Test context manager with initialization failure."""
        # Mock initialization failure
        self.input_handler.initialize = MagicMock(return_value=False)
        
        with self.assertRaises(RuntimeError):
            with self.input_handler:
                pass


if __name__ == '__main__':
    unittest.main()