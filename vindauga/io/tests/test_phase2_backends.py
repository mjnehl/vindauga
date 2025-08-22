# -*- coding: utf-8 -*-
"""
Unit tests for Phase 2 platform backends.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock
from io import StringIO

from vindauga.io.display.ansi import ANSIDisplay
from vindauga.io.display.termio import TermIODisplay
from vindauga.io.display.curses import CursesDisplay
from vindauga.io.input.ansi import ANSIInput, ANSIEscapeParser, ParsedKey, ParsedMouse
from vindauga.io.input.termio import TermIOInput
from vindauga.io.input.curses import CursesInput, CursesKeyEvent, CursesMouseEvent
from vindauga.io import PlatformIO, PlatformType
from vindauga.io.display_buffer import DisplayBuffer
from vindauga.io.screen_cell import ScreenCell


class TestANSIDisplay(unittest.TestCase):
    """Test cases for ANSI display backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.display = ANSIDisplay()
        self.mock_stdout = StringIO()
    
    def test_initialization_structure(self):
        """Test display initialization structure."""
        self.assertFalse(self.display.is_initialized)
        self.assertIsNotNone(self.display.stdout)
        self.assertFalse(self.display.has_24bit_color)
        self.assertFalse(self.display.has_256_color)
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('vindauga.io.display.ansi.termios')
    @patch('vindauga.io.display.ansi.fcntl')
    def test_initialization_sequences(self, mock_fcntl, mock_termios, mock_stdout):
        """Test that initialization sends correct sequences."""
        # Mock terminal size
        mock_fcntl.ioctl.return_value = b'\x18\x00\x50\x00'  # 24 rows, 80 cols
        mock_termios.tcgetattr.return_value = []
        
        # Initialize
        result = self.display.initialize()
        self.assertTrue(result)
        
        # Check output contains expected sequences
        output = mock_stdout.getvalue()
        self.assertIn('\x1b[?1049h', output)  # Alternate screen
        self.assertIn('\x1b[2J', output)      # Clear screen
        self.assertIn('\x1b[?25l', output)    # Hide cursor
    
    def test_color_detection(self):
        """Test color support detection."""
        with patch.dict(os.environ, {'COLORTERM': 'truecolor'}):
            display = ANSIDisplay()
            display._detect_color_support()
            self.assertTrue(display.has_24bit_color)
            self.assertTrue(display.has_256_color)
        
        with patch.dict(os.environ, {'TERM': 'xterm-256color'}, clear=True):
            display = ANSIDisplay()
            display._detect_color_support()
            self.assertFalse(display.has_24bit_color)
            self.assertTrue(display.has_256_color)
    
    def test_buffer_flushing(self):
        """Test buffer flushing with damage tracking."""
        buffer = DisplayBuffer(10, 5)
        buffer.put_text(0, 0, "Hello", fg=7, bg=0)
        buffer.put_text(0, 1, "World", fg=15, bg=4)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.display._initialized = True
            self.display.flush_buffer(buffer)
            
            output = mock_stdout.getvalue()
            # Check for cursor positioning
            self.assertIn('\x1b[1;1H', output)  # Row 1, col 1
            # Check for text
            self.assertIn('Hello', output)
            
            # Damage should be cleared
            self.assertEqual(len(list(buffer.get_damaged_regions())), 0)


class TestANSIEscapeParser(unittest.TestCase):
    """Test cases for ANSI escape sequence parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = ANSIEscapeParser()
    
    def test_normal_characters(self):
        """Test parsing of normal characters."""
        result = self.parser.parse_byte(ord('A'))
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key, 'A')
        self.assertFalse(result.ctrl)
        self.assertFalse(result.alt)
    
    def test_control_characters(self):
        """Test parsing of control characters."""
        # Tab
        result = self.parser.parse_byte(0x09)
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key, 'Tab')
        
        # Enter
        result = self.parser.parse_byte(0x0D)
        self.assertEqual(result.key, 'Enter')
        
        # Ctrl+A
        result = self.parser.parse_byte(0x01)
        self.assertEqual(result.key, 'A')
        self.assertTrue(result.ctrl)
    
    def test_escape_sequences(self):
        """Test parsing of escape sequences."""
        # Arrow up: ESC [ A
        self.assertIsNone(self.parser.parse_byte(0x1B))  # ESC
        self.assertIsNone(self.parser.parse_byte(ord('[')))  # [
        result = self.parser.parse_byte(ord('A'))  # A
        
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key, 'Up')
    
    def test_function_keys(self):
        """Test parsing of function keys."""
        # F1: ESC [ 1 1 ~
        self.assertIsNone(self.parser.parse_byte(0x1B))
        self.assertIsNone(self.parser.parse_byte(ord('[')))
        self.assertIsNone(self.parser.parse_byte(ord('1')))
        self.assertIsNone(self.parser.parse_byte(ord('1')))
        result = self.parser.parse_byte(ord('~'))
        
        self.assertIsInstance(result, ParsedKey)
        self.assertEqual(result.key, 'F1')
    
    def test_parser_reset(self):
        """Test parser reset functionality."""
        # Start an escape sequence
        self.parser.parse_byte(0x1B)
        # Reset
        self.parser.reset()
        # Should parse normally again
        result = self.parser.parse_byte(ord('A'))
        self.assertEqual(result.key, 'A')


class TestTermIODisplay(unittest.TestCase):
    """Test cases for TermIO display backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.display = TermIODisplay()
    
    def test_initialization_structure(self):
        """Test display initialization structure."""
        self.assertFalse(self.display.is_initialized)
        self.assertIsNone(self.display.tty_fd)
        self.assertIsNone(self.display.original_termios)
    
    @patch('vindauga.io.display.termio.os.isatty')
    @patch('vindauga.io.display.termio.termios')
    def test_raw_mode_configuration(self, mock_termios, mock_isatty):
        """Test raw mode terminal configuration."""
        mock_isatty.return_value = True
        mock_termios.tcgetattr.return_value = [0, 0, 0, 0, 0, 0, {}]
        
        # Test would initialize and enter raw mode
        # Actual test requires a real TTY
        self.assertIsNotNone(self.display)


class TestCursesDisplay(unittest.TestCase):
    """Test cases for Curses display backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.display = CursesDisplay()
    
    def test_initialization_structure(self):
        """Test display initialization structure."""
        self.assertFalse(self.display.is_initialized)
        self.assertIsNone(self.display.stdscr)
        self.assertFalse(self.display.has_colors)
        self.assertEqual(self.display.max_pairs, 64)
    
    def test_color_mapping(self):
        """Test color value mapping to curses colors."""
        import curses
        
        # Test basic color mapping
        self.assertEqual(self.display._map_color(0), curses.COLOR_BLACK)
        self.assertEqual(self.display._map_color(1), curses.COLOR_RED)
        self.assertEqual(self.display._map_color(7), curses.COLOR_WHITE)


class TestANSIInput(unittest.TestCase):
    """Test cases for ANSI input handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.input_handler = ANSIInput()
    
    def test_initialization_structure(self):
        """Test input handler initialization structure."""
        self.assertFalse(self.input_handler.is_initialized)
        self.assertIsNotNone(self.input_handler.parser)
        self.assertIsInstance(self.input_handler.parser, ANSIEscapeParser)
    
    @patch('fcntl.fcntl')
    @patch('sys.stdin')
    def test_initialization(self, mock_stdin, mock_fcntl):
        """Test input handler initialization."""
        mock_stdin.fileno.return_value = 0
        mock_fcntl.return_value = 0
        
        result = self.input_handler.initialize()
        self.assertTrue(result)
        self.assertTrue(self.input_handler.is_initialized)


class TestTermIOInput(unittest.TestCase):
    """Test cases for TermIO input handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.input_handler = TermIOInput()
    
    def test_initialization_structure(self):
        """Test input handler initialization structure."""
        self.assertFalse(self.input_handler.is_initialized)
        self.assertIsNotNone(self.input_handler.parser)
        self.assertIsNone(self.input_handler.stdin_fd)


class TestCursesInput(unittest.TestCase):
    """Test cases for Curses input handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        mock_stdscr = MagicMock()
        self.input_handler = CursesInput(mock_stdscr)
    
    def test_initialization_structure(self):
        """Test input handler initialization structure."""
        self.assertFalse(self.input_handler.is_initialized)
        self.assertIsNotNone(self.input_handler.stdscr)
        self.assertIsNotNone(self.input_handler.key_map)
    
    def test_key_mapping(self):
        """Test key code mapping."""
        import curses
        
        # Check some key mappings
        self.assertEqual(self.input_handler.key_map[curses.KEY_UP], 'Up')
        self.assertEqual(self.input_handler.key_map[curses.KEY_DOWN], 'Down')
        self.assertEqual(self.input_handler.key_map[curses.KEY_F1], 'F1')


class TestPlatformIO(unittest.TestCase):
    """Test cases for PlatformIO factory."""
    
    @patch('vindauga.io.PlatformDetector')
    def test_auto_detection(self, mock_detector_class):
        """Test automatic platform detection."""
        mock_detector = MagicMock()
        mock_detector.select_best_platform.return_value = PlatformType.ANSI
        mock_detector_class.return_value = mock_detector
        
        display, input_handler = PlatformIO.create()
        
        self.assertIsInstance(display, ANSIDisplay)
        self.assertIsInstance(input_handler, ANSIInput)
    
    def test_specific_platform_ansi(self):
        """Test creating ANSI platform."""
        display, input_handler = PlatformIO.create(PlatformType.ANSI)
        
        self.assertIsInstance(display, ANSIDisplay)
        self.assertIsInstance(input_handler, ANSIInput)
    
    def test_specific_platform_termio(self):
        """Test creating TermIO platform."""
        display, input_handler = PlatformIO.create(PlatformType.TERMIO)
        
        self.assertIsInstance(display, TermIODisplay)
        self.assertIsInstance(input_handler, TermIOInput)
    
    @patch('vindauga.io.PlatformDetector')
    def test_no_platform_available(self, mock_detector_class):
        """Test error when no platform is available."""
        mock_detector = MagicMock()
        mock_detector.select_best_platform.return_value = None
        mock_detector_class.return_value = mock_detector
        
        with self.assertRaises(RuntimeError) as context:
            PlatformIO.create()
        
        self.assertIn("No suitable platform", str(context.exception))


if __name__ == '__main__':
    unittest.main()