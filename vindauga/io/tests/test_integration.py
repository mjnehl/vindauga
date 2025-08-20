# -*- coding: utf-8 -*-
"""
Integration tests for platform switching and I/O subsystem.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

from vindauga.io import PlatformIO, PlatformType, PlatformDetector
from vindauga.io.display.buffer import DisplayBuffer, ScreenCell
from vindauga.events.event import Event
from vindauga.constants.event_codes import evKeyDown, evMouseDown, evMouseUp, evMouseMove


class TestPlatformIntegration(unittest.TestCase):
    """Integration tests for platform detection and switching."""
    
    def test_platform_detection(self):
        """Test automatic platform detection."""
        detector = PlatformDetector()
        
        # Test ANSI detection
        with patch.dict(os.environ, {'TERM': 'xterm-256color'}):
            with patch('os.isatty', return_value=True):
                with patch('sys.platform', 'linux'):
                    caps = detector.get_ansi_capabilities()
                    self.assertTrue(caps.is_available)
                    self.assertGreater(caps.score(), 0)
        
        # Test TermIO detection
        with patch('sys.platform', 'linux'):
            with patch('os.isatty', return_value=True):
                caps = detector.get_termio_capabilities()
                self.assertTrue(caps.is_available)
                self.assertGreater(caps.score(), 0)
        
        # Test Curses detection
        with patch('curses.initscr', MagicMock()):
            caps = detector.get_curses_capabilities()
            # Curses should always be available as fallback
            self.assertTrue(caps.is_available)
    
    def test_platform_factory_creation(self):
        """Test creating platform I/O instances."""
        # Test ANSI platform
        with patch('vindauga.io.display.ansi.ANSIDisplay'):
            with patch('vindauga.io.input.ansi.ANSIInput'):
                io_system = PlatformIO.create('ansi')
                self.assertEqual(io_system.platform_type, PlatformType.ANSI)
                self.assertIsNotNone(io_system.display)
                self.assertIsNotNone(io_system.input)
        
        # Test TermIO platform
        with patch('vindauga.io.display.termio.TermIODisplay'):
            with patch('vindauga.io.input.termio.TermIOInput'):
                io_system = PlatformIO.create('termio')
                self.assertEqual(io_system.platform_type, PlatformType.TERMIO)
        
        # Test Curses platform
        with patch('vindauga.io.display.curses.CursesDisplay'):
            with patch('vindauga.io.input.curses.CursesInput'):
                io_system = PlatformIO.create('curses')
                self.assertEqual(io_system.platform_type, PlatformType.CURSES)
    
    def test_automatic_platform_selection(self):
        """Test automatic platform selection."""
        detector = PlatformDetector()
        
        # Mock capabilities to control selection
        with patch.object(detector, 'get_ansi_capabilities') as mock_ansi:
            with patch.object(detector, 'get_termio_capabilities') as mock_termio:
                with patch.object(detector, 'get_curses_capabilities') as mock_curses:
                    # Make ANSI the best option
                    mock_ansi.return_value.is_available = True
                    mock_ansi.return_value.score = lambda: 150
                    mock_termio.return_value.is_available = True
                    mock_termio.return_value.score = lambda: 100
                    mock_curses.return_value.is_available = True
                    mock_curses.return_value.score = lambda: 50
                    
                    platform = detector.detect_best_platform()
                    self.assertEqual(platform, PlatformType.ANSI)
                    
                    # Make TermIO the best option
                    mock_ansi.return_value.is_available = False
                    platform = detector.detect_best_platform()
                    self.assertEqual(platform, PlatformType.TERMIO)
                    
                    # Fall back to Curses
                    mock_termio.return_value.is_available = False
                    platform = detector.detect_best_platform()
                    self.assertEqual(platform, PlatformType.CURSES)
    
    def test_io_system_initialization(self):
        """Test I/O system initialization and shutdown."""
        mock_display = MagicMock()
        mock_input = MagicMock()
        
        # Successful initialization
        mock_display.initialize.return_value = True
        mock_input.initialize.return_value = True
        
        io_system = PlatformIO(mock_display, mock_input, PlatformType.ANSI)
        result = io_system.initialize()
        
        self.assertTrue(result)
        self.assertTrue(io_system._initialized)
        mock_display.initialize.assert_called_once()
        mock_input.initialize.assert_called_once()
        
        # Test shutdown
        io_system.shutdown()
        self.assertFalse(io_system._initialized)
        mock_display.shutdown.assert_called_once()
        mock_input.shutdown.assert_called_once()
    
    def test_io_system_partial_failure(self):
        """Test handling of partial initialization failure."""
        mock_display = MagicMock()
        mock_input = MagicMock()
        
        # Display fails to initialize
        mock_display.initialize.return_value = False
        mock_input.initialize.return_value = True
        
        io_system = PlatformIO(mock_display, mock_input, PlatformType.ANSI)
        result = io_system.initialize()
        
        self.assertFalse(result)
        self.assertFalse(io_system._initialized)
        
        # Verify cleanup was called
        mock_display.shutdown.assert_called()
        mock_input.shutdown.assert_called()
    
    def test_context_manager(self):
        """Test I/O system as context manager."""
        mock_display = MagicMock()
        mock_input = MagicMock()
        mock_display.initialize.return_value = True
        mock_input.initialize.return_value = True
        
        io_system = PlatformIO(mock_display, mock_input, PlatformType.ANSI)
        
        with io_system as io:
            self.assertTrue(io._initialized)
            mock_display.initialize.assert_called_once()
            mock_input.initialize.assert_called_once()
        
        # After exiting context, should be shutdown
        self.assertFalse(io_system._initialized)
        mock_display.shutdown.assert_called_once()
        mock_input.shutdown.assert_called_once()
    
    def test_context_manager_with_exception(self):
        """Test context manager handles exceptions properly."""
        mock_display = MagicMock()
        mock_input = MagicMock()
        mock_display.initialize.return_value = True
        mock_input.initialize.return_value = True
        
        io_system = PlatformIO(mock_display, mock_input, PlatformType.ANSI)
        
        try:
            with io_system:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still shutdown properly
        self.assertFalse(io_system._initialized)
        mock_display.shutdown.assert_called_once()
        mock_input.shutdown.assert_called_once()


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end tests for complete I/O workflows."""
    
    def test_display_buffer_workflow(self):
        """Test complete display buffer workflow."""
        # Create a display buffer
        buffer = DisplayBuffer(80, 24)
        
        # Add some content
        buffer.put_text(0, 0, "Hello, World!")
        buffer.put_text(0, 1, "Line 2", attr=0x1F)
        
        # Verify damage tracking
        damage = buffer.get_damage(0)
        self.assertIsNotNone(damage)
        self.assertEqual(damage[0], 0)
        self.assertGreaterEqual(damage[1], 13)  # At least "Hello, World!" length
        
        damage = buffer.get_damage(1)
        self.assertIsNotNone(damage)
        
        # Clear damage
        buffer.clear_damage(0)
        self.assertIsNone(buffer.get_damage(0))
    
    def test_screen_cell_operations(self):
        """Test ScreenCell operations."""
        # Test basic cell
        cell = ScreenCell('A', attr=0x07)
        self.assertEqual(cell.text, 'A')
        self.assertEqual(cell.attr, 0x07)
        self.assertEqual(cell.width, 1)
        self.assertFalse(cell.is_wide())
        
        # Test wide character
        cell = ScreenCell('中', attr=0x07)
        self.assertEqual(cell.text, '中')
        self.assertEqual(cell.width, 2)
        self.assertTrue(cell.is_wide())
        
        # Test dirty flag
        cell.mark_dirty()
        self.assertTrue(cell.is_dirty())
        cell.clear_dirty()
        self.assertFalse(cell.is_dirty())
        
        # Test trailing cell
        trail = cell.make_trail()
        self.assertTrue(trail.is_trail())
        self.assertEqual(trail.width, 0)
    
    def test_platform_type_conversion(self):
        """Test PlatformType enum conversions."""
        # String to enum
        self.assertEqual(PlatformType.from_string('ansi'), PlatformType.ANSI)
        self.assertEqual(PlatformType.from_string('termio'), PlatformType.TERMIO)
        self.assertEqual(PlatformType.from_string('curses'), PlatformType.CURSES)
        
        # Case insensitive
        self.assertEqual(PlatformType.from_string('ANSI'), PlatformType.ANSI)
        
        # Invalid string
        with self.assertRaises(ValueError):
            PlatformType.from_string('invalid')
        
        # Enum to string
        self.assertEqual(str(PlatformType.ANSI), 'ansi')
        self.assertEqual(str(PlatformType.TERMIO), 'termio')
        self.assertEqual(str(PlatformType.CURSES), 'curses')
    
    @patch('vindauga.io.platform.PlatformDetector.detect_best_platform')
    def test_lazy_imports(self, mock_detect):
        """Test lazy import functionality."""
        # Import should work without circular dependencies
        from vindauga.io import ScreenCell, DisplayBuffer, DamageRegion
        
        self.assertIsNotNone(ScreenCell)
        self.assertIsNotNone(DisplayBuffer)
        self.assertIsNotNone(DamageRegion)
        
        # Test creating instances
        cell = ScreenCell('X')
        self.assertEqual(cell.text, 'X')
        
        buffer = DisplayBuffer(10, 10)
        self.assertEqual(buffer.width, 10)
        self.assertEqual(buffer.height, 10)
    
    def test_full_stack_initialization(self):
        """Test full stack initialization with mocked backends."""
        with patch('vindauga.io.display.ansi.ANSIDisplay') as MockDisplay:
            with patch('vindauga.io.input.ansi.ANSIInput') as MockInput:
                with patch('vindauga.io.platform.PlatformDetector.detect_best_platform') as mock_detect:
                    # Configure mocks
                    mock_detect.return_value = PlatformType.ANSI
                    mock_display = MockDisplay.return_value
                    mock_input = MockInput.return_value
                    mock_display.initialize.return_value = True
                    mock_input.initialize.return_value = True
                    
                    # Create and initialize I/O system
                    io_system = PlatformIO.create()
                    self.assertEqual(io_system.platform_type, PlatformType.ANSI)
                    
                    result = io_system.initialize()
                    self.assertTrue(result)
                    
                    # Verify components were created
                    MockDisplay.assert_called_once()
                    MockInput.assert_called_once()
                    
                    # Clean up
                    io_system.shutdown()


if __name__ == '__main__':
    unittest.main()