# -*- coding: utf-8 -*-
"""
Unit tests for TermIO display and input backends.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import signal
import select
import termios

from vindauga.io.display.termio import TermIODisplay
from vindauga.io.input.termio import TermIOInput
from vindauga.io.display.buffer import DisplayBuffer, ScreenCell
from vindauga.events.event import Event
from vindauga.constants.event_codes import evKeyDown, evMouseDown, evMouseUp, evMouseMove
from vindauga.constants import keys as Keys


class TestTermIODisplay(unittest.TestCase):
    """Test cases for TermIO display backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.display = TermIODisplay()
        
    def test_initialization(self):
        """Test display initialization."""
        with patch('sys.stdout.fileno', return_value=1):
            with patch('os.isatty', return_value=True):
                with patch('termios.tcgetattr', return_value=[0, 0, 0, 0, 0, 0, []]):
                    with patch('termios.tcsetattr'):
                        with patch('signal.signal'):
                            with patch('fcntl.ioctl', return_value=b'\x18\x00\x50\x00'):
                                with patch('os.write'):
                                    result = self.display.initialize()
                                    self.assertTrue(result)
                                    self.assertTrue(self.display.is_initialized)
    
    def test_initialization_not_tty(self):
        """Test initialization fails when not a TTY."""
        with patch('sys.stdout.fileno', return_value=1):
            with patch('os.isatty', return_value=False):
                result = self.display.initialize()
                self.assertFalse(result)
                self.assertFalse(self.display.is_initialized)
    
    def test_shutdown(self):
        """Test display shutdown."""
        self.display._initialized = True
        self.display.tty_fd = 1
        self.display.original_termios = [0, 0, 0, 0, 0, 0, []]
        
        with patch('os.write'):
            with patch('termios.tcsetattr'):
                with patch('signal.signal'):
                    self.display.shutdown()
                    self.assertFalse(self.display.is_initialized)
    
    def test_raw_mode(self):
        """Test entering and exiting raw mode."""
        self.display.tty_fd = 1
        
        # Test entering raw mode
        mock_termios = [
            termios.BRKINT | termios.ICRNL,  # Input flags
            termios.OPOST,  # Output flags
            termios.CSIZE,  # Control flags
            termios.ECHO | termios.ICANON,  # Local flags
            0, 0,  # Speed
            {}  # Control chars
        ]
        
        with patch('termios.tcgetattr', return_value=mock_termios.copy()):
            with patch('termios.tcsetattr') as mock_set:
                self.display._enter_raw_mode()
                
                # Verify flags were modified correctly
                args = mock_set.call_args[0]
                new_termios = args[2]
                
                # Check input flags cleared
                self.assertEqual(new_termios[0] & termios.BRKINT, 0)
                self.assertEqual(new_termios[0] & termios.ICRNL, 0)
                
                # Check output flags cleared
                self.assertEqual(new_termios[1] & termios.OPOST, 0)
                
                # Check local flags cleared
                self.assertEqual(new_termios[3] & termios.ECHO, 0)
                self.assertEqual(new_termios[3] & termios.ICANON, 0)
    
    def test_signal_handling(self):
        """Test SIGWINCH signal handling."""
        self.display._setup_signals()
        
        # Simulate SIGWINCH
        self.display._handle_sigwinch(signal.SIGWINCH, None)
        self.assertTrue(self.display._resize_pending)
        
        # Test size update on get_size
        with patch('fcntl.ioctl', return_value=b'\x20\x00\x64\x00'):
            width, height = self.display.get_size()
            self.assertEqual(width, 100)
            self.assertEqual(height, 32)
            self.assertFalse(self.display._resize_pending)
    
    def test_flush_buffer(self):
        """Test buffer flushing with damage tracking."""
        self.display._initialized = True
        self.display.tty_fd = 1
        self.display._width = 10
        self.display._height = 5
        
        # Create a buffer with content
        buffer = DisplayBuffer(10, 5)
        buffer.put_text(0, 0, "Test")
        buffer.put_text(0, 1, "Line", attr=0x1F)
        
        with patch('os.write') as mock_write:
            self.display.flush_buffer(buffer)
            
            # Verify writes were made
            self.assertTrue(mock_write.called)
            
            # Check that damage was cleared
            self.assertIsNone(buffer.get_damage(0))
            self.assertIsNone(buffer.get_damage(1))
    
    def test_cursor_operations(self):
        """Test cursor positioning and visibility."""
        self.display.tty_fd = 1
        self.display._width = 80
        self.display._height = 24
        
        with patch('os.write') as mock_write:
            # Test cursor positioning
            self.display.set_cursor_position(10, 5)
            self.assertEqual(self.display.cursor_position, (10, 5))
            
            # Verify ANSI sequence was written
            calls = mock_write.call_args_list
            self.assertTrue(any(b'\x1b[6;11H' in call[0][1] for call in calls))
            
            # Test cursor visibility
            mock_write.reset_mock()
            self.display.set_cursor_visibility(True)
            calls = mock_write.call_args_list
            self.assertTrue(any(b'\x1b[?25h' in call[0][1] for call in calls))
            
            mock_write.reset_mock()
            self.display.set_cursor_visibility(False)
            calls = mock_write.call_args_list
            self.assertTrue(any(b'\x1b[?25l' in call[0][1] for call in calls))
    
    def test_color_support(self):
        """Test color support detection."""
        # Test with color terminal
        with patch.dict(os.environ, {'TERM': 'xterm-256color'}):
            self.assertTrue(self.display.supports_colors())
            self.assertEqual(self.display.get_color_count(), 256)
        
        # Test with basic color terminal
        with patch.dict(os.environ, {'TERM': 'xterm'}):
            self.assertTrue(self.display.supports_colors())
            self.assertEqual(self.display.get_color_count(), 16)
        
        # Test with no color support
        with patch.dict(os.environ, {'TERM': 'dumb'}):
            self.assertFalse(self.display.supports_colors())
            self.assertEqual(self.display.get_color_count(), 0)


class TestTermIOInput(unittest.TestCase):
    """Test cases for TermIO input backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.input_handler = TermIOInput()
        
    def test_initialization(self):
        """Test input handler initialization."""
        with patch('sys.stdin.fileno', return_value=0):
            with patch('os.isatty', return_value=True):
                with patch('termios.tcgetattr', return_value=[]):
                    with patch('tty.setraw'):
                        with patch('select.poll') as mock_poll:
                            mock_poller = MagicMock()
                            mock_poll.return_value = mock_poller
                            
                            result = self.input_handler.initialize()
                            self.assertTrue(result)
                            self.assertTrue(self.input_handler.is_initialized)
                            mock_poller.register.assert_called_once()
    
    def test_initialization_not_tty(self):
        """Test initialization fails when stdin is not a TTY."""
        with patch('sys.stdin.fileno', return_value=0):
            with patch('os.isatty', return_value=False):
                result = self.input_handler.initialize()
                self.assertFalse(result)
                self.assertFalse(self.input_handler.is_initialized)
    
    def test_shutdown(self):
        """Test input handler shutdown."""
        self.input_handler._initialized = True
        self.input_handler.stdin_fd = 0
        self.input_handler._poller = MagicMock()
        
        with patch('termios.tcsetattr'):
            self.input_handler.shutdown()
            self.assertFalse(self.input_handler.is_initialized)
            self.input_handler._poller.unregister.assert_called_once()
    
    def test_mouse_enable(self):
        """Test mouse event enabling."""
        self.input_handler._initialized = True
        self.input_handler.stdin_fd = 0
        
        with patch('os.write') as mock_write:
            with patch('sys.stdout.fileno', return_value=1):
                # Enable mouse
                result = self.input_handler.enable_mouse(True)
                self.assertTrue(result)
                self.assertTrue(self.input_handler.mouse_enabled)
                mock_write.assert_called_with(1, b'\x1b[?1006h')
                
                # Disable mouse
                mock_write.reset_mock()
                result = self.input_handler.enable_mouse(False)
                self.assertTrue(result)
                self.assertFalse(self.input_handler.mouse_enabled)
                mock_write.assert_called_with(1, b'\x1b[?1006l\x1b[?1000l')
    
    def test_wait_for_input_with_poll(self):
        """Test waiting for input using poll."""
        self.input_handler.stdin_fd = 0
        self.input_handler._use_poll = True
        self.input_handler._poller = MagicMock()
        
        # Test with input available
        self.input_handler._poller.poll.return_value = [(0, select.POLLIN)]
        result = self.input_handler._wait_for_input(0.1)
        self.assertTrue(result)
        self.input_handler._poller.poll.assert_called_with(100)
        
        # Test with no input
        self.input_handler._poller.poll.return_value = []
        result = self.input_handler._wait_for_input(0.1)
        self.assertFalse(result)
    
    def test_wait_for_input_with_select(self):
        """Test waiting for input using select."""
        self.input_handler.stdin_fd = 0
        self.input_handler._use_poll = False
        
        # Test with input available
        with patch('select.select', return_value=([0], [], [])):
            result = self.input_handler._wait_for_input(0.1)
            self.assertTrue(result)
        
        # Test with no input
        with patch('select.select', return_value=([], [], [])):
            result = self.input_handler._wait_for_input(0.1)
            self.assertFalse(result)
    
    def test_read_input(self):
        """Test reading input into buffer."""
        self.input_handler.stdin_fd = 0
        
        with patch('os.read', return_value=b'Hello'):
            self.input_handler._read_input()
            self.assertEqual(self.input_handler.buffer_len, 5)
            self.assertEqual(bytes(self.input_handler.input_buffer[:5]), b'Hello')
    
    def test_process_buffer(self):
        """Test processing input buffer."""
        self.input_handler._initialized = True
        
        # Add some data to buffer
        test_data = b'ABC'
        self.input_handler.input_buffer[:len(test_data)] = test_data
        self.input_handler.buffer_len = len(test_data)
        self.input_handler.buffer_pos = 0
        
        # Process buffer
        self.input_handler._process_buffer()
        
        # Check that events were generated
        self.assertEqual(len(self.input_handler.event_queue), 3)
        for i, event in enumerate(self.input_handler.event_queue):
            self.assertEqual(event.what, evKeyDown)
            self.assertEqual(event.keyDown.keyCode, ord('A') + i)
    
    def test_mouse_event_coalescing(self):
        """Test that mouse move events are coalesced."""
        self.input_handler._initialized = True
        
        # Create two mouse move events
        event1 = Event(evMouseMove)
        event1.mouse.x = 10
        event1.mouse.y = 5
        
        event2 = Event(evMouseMove)
        event2.mouse.x = 11
        event2.mouse.y = 5
        
        # Add first event
        self.input_handler.event_queue.append(event1)
        
        # Simulate adding second move event (should replace first)
        if (event2.what == evMouseMove and
            self.input_handler.event_queue and
            self.input_handler.event_queue[-1].what == evMouseMove):
            self.input_handler.event_queue[-1] = event2
        else:
            self.input_handler.event_queue.append(event2)
        
        # Should only have one event (the second one)
        self.assertEqual(len(self.input_handler.event_queue), 1)
        self.assertEqual(self.input_handler.event_queue[0].mouse.x, 11)
    
    def test_flush_input(self):
        """Test flushing input buffer."""
        self.input_handler._initialized = True
        self.input_handler.stdin_fd = 0
        self.input_handler.buffer_len = 10
        self.input_handler.buffer_pos = 5
        self.input_handler.event_queue = [Event(evKeyDown)]
        
        with patch('os.read', side_effect=OSError):
            self.input_handler.flush_input()
            
            self.assertEqual(self.input_handler.buffer_pos, 0)
            self.assertEqual(self.input_handler.buffer_len, 0)
            self.assertEqual(len(self.input_handler.event_queue), 0)


if __name__ == '__main__':
    unittest.main()