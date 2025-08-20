# -*- coding: utf-8 -*-
"""
Unit tests for Curses display and input backends.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import curses

from vindauga.io.display.curses import CursesDisplay
from vindauga.io.input.curses import CursesInput
from vindauga.io.display.buffer import DisplayBuffer, ScreenCell
from vindauga.events.event import Event
from vindauga.constants.event_codes import evKeyDown, evMouseDown, evMouseUp, evMouseMove
from vindauga.constants import keys as Keys


class TestCursesDisplay(unittest.TestCase):
    """Test cases for Curses display backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.display = CursesDisplay()
        
    def test_initialization(self):
        """Test display initialization."""
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        with patch('curses.initscr', return_value=mock_stdscr):
            with patch('curses.noecho'):
                with patch('curses.cbreak'):
                    with patch('curses.has_colors', return_value=True):
                        with patch('curses.start_color'):
                            with patch('curses.use_default_colors'):
                                with patch('curses.can_change_color', return_value=False):
                                    with patch('curses.curs_set'):
                                        with patch.object(curses, 'COLOR_PAIRS', 256):
                                            result = self.display.initialize()
                                            
                                            self.assertTrue(result)
                                            self.assertTrue(self.display.is_initialized)
                                            self.assertEqual(self.display.width, 80)
                                            self.assertEqual(self.display.height, 24)
                                            self.assertTrue(self.display.has_colors)
                                            
                                            # Verify curses setup
                                            mock_stdscr.keypad.assert_called_with(True)
                                            mock_stdscr.clear.assert_called()
                                            mock_stdscr.refresh.assert_called()
    
    def test_initialization_no_colors(self):
        """Test initialization without color support."""
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        with patch('curses.initscr', return_value=mock_stdscr):
            with patch('curses.noecho'):
                with patch('curses.cbreak'):
                    with patch('curses.has_colors', return_value=False):
                        with patch('curses.curs_set'):
                            result = self.display.initialize()
                            
                            self.assertTrue(result)
                            self.assertFalse(self.display.has_colors)
                            self.assertEqual(self.display.get_color_count(), 0)
    
    def test_shutdown(self):
        """Test display shutdown."""
        self.display._initialized = True
        self.display.stdscr = MagicMock()
        
        with patch('curses.curs_set'):
            with patch('curses.nocbreak'):
                with patch('curses.echo'):
                    with patch('curses.endwin'):
                        self.display.shutdown()
                        
                        self.assertFalse(self.display.is_initialized)
                        self.display.stdscr.clear.assert_called()
                        self.display.stdscr.refresh.assert_called()
                        self.display.stdscr.keypad.assert_called_with(False)
    
    def test_get_size(self):
        """Test getting terminal size."""
        self.display.stdscr = MagicMock()
        self.display.stdscr.getmaxyx.return_value = (30, 100)
        
        width, height = self.display.get_size()
        self.assertEqual(width, 100)
        self.assertEqual(height, 30)
    
    def test_flush_buffer(self):
        """Test buffer flushing to curses screen."""
        self.display._initialized = True
        self.display.stdscr = MagicMock()
        self.display._width = 10
        self.display._height = 5
        self.display.has_colors = True
        self.display.color_pairs = {(7, 0): 1}  # White on black
        
        # Create a buffer with content
        buffer = DisplayBuffer(10, 5)
        buffer.put_text(0, 0, "Test")
        buffer.put_text(0, 1, "Line")
        
        with patch('curses.color_pair', return_value=0x100):
            self.display.flush_buffer(buffer)
            
            # Verify text was written
            calls = self.display.stdscr.addstr.call_args_list
            self.assertTrue(any('Test' in str(call) for call in calls))
            self.assertTrue(any('Line' in str(call) for call in calls))
            
            # Verify refresh was called
            self.display.stdscr.refresh.assert_called()
            
            # Check damage was cleared
            self.assertIsNone(buffer.get_damage(0))
            self.assertIsNone(buffer.get_damage(1))
    
    def test_cursor_operations(self):
        """Test cursor positioning and visibility."""
        self.display.stdscr = MagicMock()
        self.display._width = 80
        self.display._height = 24
        
        # Test cursor positioning
        self.display.set_cursor_position(10, 5)
        self.assertEqual(self.display.cursor_position, (10, 5))
        self.display.stdscr.move.assert_called_with(5, 10)
        
        # Test cursor visibility
        with patch('curses.curs_set') as mock_curs:
            self.display.set_cursor_visibility(True)
            mock_curs.assert_called_with(1)
            
            self.display.set_cursor_visibility(False)
            mock_curs.assert_called_with(0)
    
    def test_clear_screen(self):
        """Test screen clearing."""
        self.display.stdscr = MagicMock()
        
        self.display.clear_screen()
        self.display.stdscr.clear.assert_called()
        self.display.stdscr.refresh.assert_called()
    
    def test_color_support(self):
        """Test color support checking."""
        self.display.has_colors = True
        self.assertTrue(self.display.supports_colors())
        
        self.display.has_colors = False
        self.assertFalse(self.display.supports_colors())
        
        # Test color count
        self.display.has_colors = True
        with patch.object(curses, 'COLORS', 256):
            self.assertEqual(self.display.get_color_count(), 256)
    
    def test_mouse_support(self):
        """Test mouse support detection."""
        with patch('curses.has_mouse', return_value=True):
            self.assertTrue(self.display.supports_mouse())
        
        with patch('curses.has_mouse', return_value=False):
            self.assertFalse(self.display.supports_mouse())
    
    def test_color_pair_management(self):
        """Test color pair initialization and mapping."""
        self.display.has_colors = True
        self.display.max_pairs = 64
        
        with patch('curses.init_pair'):
            self.display._init_color_pairs()
            
            # Check that basic color pairs were created
            self.assertGreater(len(self.display.color_pairs), 0)
            
            # Test color mapping
            self.assertEqual(self.display._map_color(0), curses.COLOR_BLACK)
            self.assertEqual(self.display._map_color(1), curses.COLOR_RED)
            self.assertEqual(self.display._map_color(7), curses.COLOR_WHITE)
    
    def test_curses_attr_conversion(self):
        """Test attribute conversion to curses format."""
        self.display.has_colors = True
        self.display.color_pairs = {(7, 0): 1}  # White on black
        
        with patch('curses.color_pair', return_value=0x100):
            # Test basic color
            attr = self.display._get_curses_attr(0x07)  # White on black
            self.assertNotEqual(attr, 0)
            
            # Test with bold
            attr = self.display._get_curses_attr(0x87)  # Bold white on black
            self.assertTrue(attr & curses.A_BOLD)


class TestCursesInput(unittest.TestCase):
    """Test cases for Curses input backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_stdscr = MagicMock()
        self.input_handler = CursesInput(self.mock_stdscr)
        
    def test_initialization(self):
        """Test input handler initialization."""
        with patch('curses.has_mouse', return_value=True):
            with patch('curses.mousemask'):
                result = self.input_handler.initialize()
                self.assertTrue(result)
                self.assertTrue(self.input_handler.is_initialized)
    
    def test_initialization_without_screen(self):
        """Test initialization without provided screen."""
        input_handler = CursesInput()
        mock_stdscr = MagicMock()
        
        with patch('curses.initscr', return_value=mock_stdscr):
            with patch('curses.noecho'):
                with patch('curses.cbreak'):
                    with patch('curses.has_mouse', return_value=False):
                        result = input_handler.initialize()
                        self.assertTrue(result)
                        self.assertEqual(input_handler.stdscr, mock_stdscr)
    
    def test_shutdown(self):
        """Test input handler shutdown."""
        self.input_handler._initialized = True
        self.input_handler._mouse_enabled = True
        
        with patch('curses.mousemask'):
            self.input_handler.shutdown()
            self.assertFalse(self.input_handler.is_initialized)
    
    def test_get_event_keyboard(self):
        """Test getting keyboard events."""
        self.input_handler._initialized = True
        
        # Test regular character
        self.mock_stdscr.getch.return_value = ord('A')
        event = self.input_handler.get_event(0.0)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.what, evKeyDown)
        self.assertEqual(event.keyDown.keyCode, ord('A'))
        
        # Test special key
        self.mock_stdscr.getch.return_value = curses.KEY_UP
        event = self.input_handler.get_event(0.0)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.keyDown.keyCode, Keys.kbUp)
        
        # Test no input
        self.mock_stdscr.getch.return_value = -1
        event = self.input_handler.get_event(0.0)
        self.assertIsNone(event)
    
    def test_get_event_mouse(self):
        """Test getting mouse events."""
        self.input_handler._initialized = True
        
        # Simulate mouse event
        self.mock_stdscr.getch.return_value = curses.KEY_MOUSE
        
        with patch('curses.getmouse', return_value=(0, 10, 5, 0, curses.BUTTON1_PRESSED)):
            event = self.input_handler.get_event(0.0)
            
            self.assertIsNotNone(event)
            self.assertEqual(event.what, evMouseDown)
            self.assertEqual(event.mouse.x, 10)
            self.assertEqual(event.mouse.y, 5)
            self.assertEqual(event.mouse.buttons & 0x01, 0x01)  # Left button
    
    def test_get_event_resize(self):
        """Test terminal resize event."""
        self.input_handler._initialized = True
        
        self.mock_stdscr.getch.return_value = curses.KEY_RESIZE
        event = self.input_handler.get_event(0.0)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.what, evKeyDown)
        self.assertEqual(event.keyDown.keyCode, Keys.kbNoKey)
    
    def test_has_events(self):
        """Test checking for available events."""
        self.input_handler._initialized = True
        
        # Test with event available
        self.mock_stdscr.getch.return_value = ord('A')
        with patch('curses.ungetch'):
            result = self.input_handler.has_events()
            self.assertTrue(result)
        
        # Test with no event
        self.mock_stdscr.getch.return_value = -1
        result = self.input_handler.has_events()
        self.assertFalse(result)
    
    def test_mouse_enable(self):
        """Test enabling/disabling mouse events."""
        self.input_handler._initialized = True
        
        with patch('curses.has_mouse', return_value=True):
            with patch('curses.mousemask', return_value=(0xFFFF, 0)) as mock_mask:
                # Enable mouse
                result = self.input_handler.enable_mouse(True)
                self.assertTrue(result)
                self.assertTrue(self.input_handler.mouse_enabled)
                
                # Check that appropriate mouse mask was set
                args = mock_mask.call_args[0]
                mask = args[0]
                self.assertTrue(mask & curses.BUTTON1_PRESSED)
                self.assertTrue(mask & curses.BUTTON1_RELEASED)
                
                # Disable mouse
                mock_mask.reset_mock()
                result = self.input_handler.enable_mouse(False)
                self.assertTrue(result)
                self.assertFalse(self.input_handler.mouse_enabled)
                mock_mask.assert_called_with(0)
    
    def test_flush_input(self):
        """Test flushing input buffer."""
        self.input_handler._initialized = True
        
        with patch('curses.flushinp'):
            self.input_handler.flush_input()
            # Just verify it doesn't raise an exception
    
    def test_key_mapping(self):
        """Test curses key to Vindauga key mapping."""
        # Test function keys
        self.assertEqual(self.input_handler.key_map[curses.KEY_F1], Keys.kbF1)
        self.assertEqual(self.input_handler.key_map[curses.KEY_F12], Keys.kbF12)
        
        # Test special keys
        self.assertEqual(self.input_handler.key_map[curses.KEY_UP], Keys.kbUp)
        self.assertEqual(self.input_handler.key_map[curses.KEY_DOWN], Keys.kbDown)
        self.assertEqual(self.input_handler.key_map[curses.KEY_HOME], Keys.kbHome)
        self.assertEqual(self.input_handler.key_map[curses.KEY_END], Keys.kbEnd)
        
        # Test control characters
        self.assertEqual(self.input_handler.key_map[0x01], Keys.kbCtrlA)
        self.assertEqual(self.input_handler.key_map[0x1B], Keys.kbEsc)
    
    def test_mouse_event_handling(self):
        """Test detailed mouse event handling."""
        self.input_handler._initialized = True
        
        # Test different button states
        test_cases = [
            (curses.BUTTON1_PRESSED, 0x01, 0x01),  # Left press
            (curses.BUTTON1_RELEASED, 0x01, 0x02),  # Left release
            (curses.BUTTON2_PRESSED, 0x04, 0x01),  # Middle press
            (curses.BUTTON3_PRESSED, 0x02, 0x01),  # Right press
            (curses.BUTTON4_PRESSED, 0, 0x10),  # Wheel up
            (curses.BUTTON5_PRESSED, 0, 0x10),  # Wheel down
        ]
        
        for bstate, expected_buttons, expected_type in test_cases:
            with patch('curses.getmouse', return_value=(0, 5, 10, 0, bstate)):
                event = self.input_handler._handle_mouse()
                
                if expected_buttons:
                    self.assertEqual(event.mouse.buttons & expected_buttons, expected_buttons)
                # Check event type based on expected_type
                if expected_type == 0x01:  # Down
                    self.assertEqual(event.what, evMouseDown)
                elif expected_type == 0x02:  # Up
                    self.assertEqual(event.what, evMouseUp)
                else:  # Move
                    self.assertEqual(event.what, evMouseMove)


if __name__ == '__main__':
    unittest.main()