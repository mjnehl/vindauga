# -*- coding: utf-8 -*-
"""
Unit tests for ANSI display and input backends.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
from io import StringIO

from vindauga.io.display.ansi import ANSIDisplay
from vindauga.io.input.ansi import ANSIInput, ANSIEscapeParser, ParsedKey, ParsedMouse, ParserState
from vindauga.io.display_buffer import DisplayBuffer
from vindauga.io.screen_cell import ScreenCell
from vindauga.events.event import Event
from vindauga.constants.event_codes import evKeyDown, evMouseDown, evMouseUp, evMouseMove
from vindauga.constants import keys as Keys


class TestANSIDisplay(unittest.TestCase):
    """Test cases for ANSI display backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.display = ANSIDisplay()
        self.mock_stdout = StringIO()
        
    def test_initialization(self):
        """Test display initialization."""
        with patch('sys.stdout', self.mock_stdout):
            with patch('termios.tcgetattr', return_value=[]):
                with patch('fcntl.ioctl', return_value=b'\x18\x00\x50\x00'):
                    result = self.display.initialize()
                    self.assertTrue(result)
                    self.assertTrue(self.display.is_initialized)
                    
                    # Check that initialization sequences were sent
                    output = self.mock_stdout.getvalue()
                    self.assertIn('\x1b[?1049h', output)  # Alternate screen
                    self.assertIn('\x1b[2J', output)  # Clear screen
                    self.assertIn('\x1b[?25l', output)  # Hide cursor
    
    def test_shutdown(self):
        """Test display shutdown."""
        self.display._initialized = True
        
        with patch('sys.stdout', self.mock_stdout):
            with patch('termios.tcsetattr'):
                self.display.shutdown()
                
                # Check that cleanup sequences were sent
                output = self.mock_stdout.getvalue()
                self.assertIn('\x1b[?25h', output)  # Show cursor
                self.assertIn('\x1b[0m', output)  # Reset attributes
                self.assertIn('\x1b[?1049l', output)  # Exit alternate screen
                
                self.assertFalse(self.display.is_initialized)
    
    def test_get_size(self):
        """Test terminal size detection."""
        with patch('fcntl.ioctl', return_value=b'\x18\x00\x50\x00'):
            width, height = self.display.get_size()
            self.assertEqual(width, 80)
            self.assertEqual(height, 24)
    
    def test_color_support_detection(self):
        """Test color capability detection."""
        # Test 24-bit color detection
        with patch.dict(os.environ, {'COLORTERM': 'truecolor'}):
            self.display._detect_color_support()
            self.assertTrue(self.display.has_24bit_color)
            self.assertEqual(self.display.get_color_count(), 16777216)
        
        # Test 256 color detection
        with patch.dict(os.environ, {'TERM': 'xterm-256color', 'COLORTERM': ''}):
            self.display.has_24bit_color = False
            self.display._detect_color_support()
            self.assertTrue(self.display.has_256_color)
            self.assertEqual(self.display.get_color_count(), 256)
    
    def test_flush_buffer(self):
        """Test buffer flushing with damage tracking."""
        self.display._initialized = True
        self.display._width = 10
        self.display._height = 5
        
        # Create a buffer with some content
        buffer = DisplayBuffer(10, 5)
        buffer.put_text(0, 0, "Hello")
        buffer.put_text(0, 1, "World", attr=0x1F)  # White on blue
        
        with patch('sys.stdout', self.mock_stdout):
            self.display.flush_buffer(buffer)
            
            output = self.mock_stdout.getvalue()
            # Check cursor positioning
            self.assertIn('\x1b[1;1H', output)  # Row 1
            self.assertIn('\x1b[2;1H', output)  # Row 2
            # Check text content
            self.assertIn('Hello', output)
            self.assertIn('World', output)
    
    def test_cursor_operations(self):
        """Test cursor positioning and visibility."""
        with patch('sys.stdout', self.mock_stdout):
            # Test cursor positioning
            self.display._width = 80
            self.display._height = 24
            self.display.set_cursor_position(10, 5)
            self.assertEqual(self.display.cursor_position, (10, 5))
            self.assertIn('\x1b[6;11H', self.mock_stdout.getvalue())
            
            # Test cursor visibility
            self.mock_stdout.truncate(0)
            self.mock_stdout.seek(0)
            self.display.set_cursor_visibility(True)
            self.assertIn('\x1b[?25h', self.mock_stdout.getvalue())
            
            self.mock_stdout.truncate(0)
            self.mock_stdout.seek(0)
            self.display.set_cursor_visibility(False)
            self.assertIn('\x1b[?25l', self.mock_stdout.getvalue())
    
    def test_clear_screen(self):
        """Test screen clearing."""
        with patch('sys.stdout', self.mock_stdout):
            self.display.clear_screen()
            output = self.mock_stdout.getvalue()
            self.assertIn('\x1b[2J', output)  # Clear screen
            self.assertIn('\x1b[H', output)  # Home cursor


class TestANSIInput(unittest.TestCase):
    """Test cases for ANSI input backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.input_handler = ANSIInput()
        
    def test_initialization(self):
        """Test input handler initialization."""
        with patch('sys.stdin.fileno', return_value=0):
            with patch('termios.tcgetattr', return_value=[]):
                with patch('tty.setraw'):
                    result = self.input_handler.initialize()
                    self.assertTrue(result)
                    self.assertTrue(self.input_handler.is_initialized)
    
    def test_mouse_enable(self):
        """Test mouse event enabling."""
        self.input_handler._initialized = True
        
        with patch('sys.stdout.write') as mock_write:
            with patch('sys.stdout.flush'):
                # Enable mouse
                result = self.input_handler.enable_mouse(True)
                self.assertTrue(result)
                self.assertTrue(self.input_handler.mouse_enabled)
                mock_write.assert_called_with('\x1b[?1006h')  # SGR protocol
                
                # Disable mouse
                result = self.input_handler.enable_mouse(False)
                self.assertTrue(result)
                self.assertFalse(self.input_handler.mouse_enabled)
                mock_write.assert_called_with('\x1b[?1006l\x1b[?1000l')
    
    def test_event_processing(self):
        """Test keyboard event processing."""
        self.input_handler._initialized = True
        
        # Simulate 'A' key press
        self.input_handler.input_buffer = bytearray(b'A')
        event = self.input_handler._process_buffer()
        
        self.assertIsNotNone(event)
        self.assertEqual(event.what, evKeyDown)
        self.assertEqual(event.keyDown.keyCode, ord('A'))
    
    def test_escape_sequence_processing(self):
        """Test escape sequence processing."""
        self.input_handler._initialized = True
        
        # Simulate arrow key (ESC [ A)
        self.input_handler.input_buffer = bytearray(b'\x1b[A')
        event = self.input_handler._process_buffer()
        
        self.assertIsNotNone(event)
        self.assertEqual(event.what, evKeyDown)
        self.assertEqual(event.keyDown.keyCode, Keys.kbUp)


class TestANSIEscapeParser(unittest.TestCase):
    """Test cases for ANSI escape sequence parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = ANSIEscapeParser()
    
    def test_normal_characters(self):
        """Test parsing of normal ASCII characters."""
        result = self.parser.parse_byte(ord('A'))
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'normal')
        self.assertEqual(result.char, 'A')
        self.assertEqual(result.key_code, ord('A'))
    
    def test_control_characters(self):
        """Test parsing of control characters."""
        # Test Ctrl+A
        result = self.parser.parse_byte(0x01)
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'control')
        self.assertTrue(result.ctrl)
        
        # Test Tab
        result = self.parser.parse_byte(0x09)
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'special')
        self.assertEqual(result.key_name, 'tab')
        
        # Test Enter
        result = self.parser.parse_byte(0x0D)
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'special')
        self.assertEqual(result.key_name, 'enter')
    
    def test_csi_sequences(self):
        """Test parsing of CSI escape sequences."""
        # Arrow key: ESC [ A
        self.assertIsNone(self.parser.parse_byte(0x1B))  # ESC
        self.assertIsNone(self.parser.parse_byte(ord('[')))  # [
        result = self.parser.parse_byte(ord('A'))  # A
        
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'special')
        self.assertEqual(result.key_name, 'up')
        
        # Reset parser for next test
        self.parser.reset()
        
        # Function key: ESC [ 1 1 ~
        self.assertIsNone(self.parser.parse_byte(0x1B))
        self.assertIsNone(self.parser.parse_byte(ord('[')))
        self.assertIsNone(self.parser.parse_byte(ord('1')))
        self.assertIsNone(self.parser.parse_byte(ord('1')))
        result = self.parser.parse_byte(ord('~'))
        
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'function')
        self.assertEqual(result.key_num, 1)  # F1
    
    def test_ss3_sequences(self):
        """Test parsing of SS3 sequences."""
        # F1 key: ESC O P
        self.assertIsNone(self.parser.parse_byte(0x1B))  # ESC
        self.assertIsNone(self.parser.parse_byte(ord('O')))  # O
        result = self.parser.parse_byte(ord('P'))  # P
        
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'function')
        self.assertEqual(result.key_num, 1)  # F1
    
    def test_sgr_mouse_sequences(self):
        """Test parsing of SGR mouse sequences."""
        # Mouse click: ESC [ < 0 ; 10 ; 20 M
        self.assertIsNone(self.parser.parse_byte(0x1B))
        self.assertIsNone(self.parser.parse_byte(ord('[')))
        self.assertIsNone(self.parser.parse_byte(ord('<')))
        self.assertIsNone(self.parser.parse_byte(ord('0')))
        self.assertIsNone(self.parser.parse_byte(ord(';')))
        self.assertIsNone(self.parser.parse_byte(ord('1')))
        self.assertIsNone(self.parser.parse_byte(ord('0')))
        self.assertIsNone(self.parser.parse_byte(ord(';')))
        self.assertIsNone(self.parser.parse_byte(ord('2')))
        self.assertIsNone(self.parser.parse_byte(ord('0')))
        result = self.parser.parse_byte(ord('M'))
        
        self.assertIsInstance(result, ParsedMouse)
        self.assertEqual(result.x, 10)
        self.assertEqual(result.y, 20)
        self.assertEqual(result.button, 0)  # Left button
        self.assertEqual(result.action, 'press')
    
    def test_utf8_parsing(self):
        """Test UTF-8 character parsing."""
        # Parse UTF-8 character '€' (0xE2 0x82 0xAC)
        self.assertIsNone(self.parser.parse_byte(0xE2))
        self.assertIsNone(self.parser.parse_byte(0x82))
        result = self.parser.parse_byte(0xAC)
        
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key_type, 'normal')
        self.assertEqual(result.char, '€')
    
    def test_parser_reset(self):
        """Test parser reset functionality."""
        # Start a sequence
        self.assertIsNone(self.parser.parse_byte(0x1B))
        self.assertEqual(self.parser.state, ParserState.ESCAPE)
        
        # Reset
        self.parser.reset()
        self.assertEqual(self.parser.state, ParserState.NORMAL)
        self.assertEqual(len(self.parser.sequence_buffer), 0)


if __name__ == '__main__':
    unittest.main()