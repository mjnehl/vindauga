# -*- coding: utf-8 -*-
"""Unit tests for DisplayBuffer class."""

import unittest
from vindauga.io.display_buffer import DisplayBuffer
from vindauga.io.screen_cell import ScreenCell


class TestDisplayBuffer(unittest.TestCase):
    """Test cases for DisplayBuffer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.buffer = DisplayBuffer(80, 25)
    
    def test_initialization(self):
        """Test buffer initialization."""
        self.assertEqual(self.buffer.width, 80)
        self.assertEqual(self.buffer.height, 25)
        self.assertEqual(len(self.buffer.cells), 25)
        self.assertEqual(len(self.buffer.cells[0]), 80)
        self.assertEqual(len(self.buffer.damage), 25)
        
        # All cells should be empty spaces
        for row in self.buffer.cells:
            for cell in row:
                self.assertEqual(cell.char, ' ')
                self.assertEqual(cell.fg_color, 7)
                self.assertEqual(cell.bg_color, 0)
    
    def test_invalid_size(self):
        """Test error handling for invalid buffer size."""
        with self.assertRaises(ValueError):
            DisplayBuffer(0, 25)
        
        with self.assertRaises(ValueError):
            DisplayBuffer(80, 0)
        
        with self.assertRaises(ValueError):
            DisplayBuffer(-1, 25)
    
    def test_get_cell(self):
        """Test getting cells."""
        # Valid positions
        cell = self.buffer.get_cell(0, 0)
        self.assertIsNotNone(cell)
        self.assertIsInstance(cell, ScreenCell)
        
        cell = self.buffer.get_cell(79, 24)
        self.assertIsNotNone(cell)
        
        # Out of bounds
        self.assertIsNone(self.buffer.get_cell(-1, 0))
        self.assertIsNone(self.buffer.get_cell(80, 0))
        self.assertIsNone(self.buffer.get_cell(0, -1))
        self.assertIsNone(self.buffer.get_cell(0, 25))
    
    def test_put_char(self):
        """Test putting single characters."""
        self.buffer.put_char(10, 5, 'A', fg=2, bg=4, attrs=ScreenCell.ATTR_BOLD)
        
        cell = self.buffer.get_cell(10, 5)
        self.assertEqual(cell.char, 'A')
        self.assertEqual(cell.fg_color, 2)
        self.assertEqual(cell.bg_color, 4)
        self.assertEqual(cell.attrs, ScreenCell.ATTR_BOLD)
        
        # Check damage tracking
        self.assertTrue(self.buffer.damage[5].is_dirty)
        self.assertTrue(self.buffer.damage[5].contains(10))
    
    def test_put_char_wide(self):
        """Test putting wide characters."""
        self.buffer.put_char(10, 5, '中')
        
        # Main cell
        cell = self.buffer.get_cell(10, 5)
        self.assertEqual(cell.char, '中')
        self.assertTrue(cell.is_wide)
        
        # Trail cell should be WideCharCell
        trail = self.buffer.get_cell(11, 5)
        self.assertEqual(trail.char, '')
        
        # Damage should cover both cells
        damage = self.buffer.damage[5]
        self.assertTrue(damage.contains(10))
        self.assertTrue(damage.contains(11))
    
    def test_put_text(self):
        """Test putting text strings."""
        written = self.buffer.put_text(10, 5, "Hello", fg=3, bg=5)
        self.assertEqual(written, 5)
        
        # Check each character
        for i, char in enumerate("Hello"):
            cell = self.buffer.get_cell(10 + i, 5)
            self.assertEqual(cell.char, char)
            self.assertEqual(cell.fg_color, 3)
            self.assertEqual(cell.bg_color, 5)
        
        # Check damage
        damage = self.buffer.damage[5]
        self.assertEqual(damage.get_bounds(), (10, 15))
    
    def test_put_text_clipping(self):
        """Test text clipping at buffer edges."""
        # Text extending past right edge
        written = self.buffer.put_text(76, 5, "Hello")
        self.assertEqual(written, 4)  # Only "Hell" fits
        
        # Negative starting position
        written = self.buffer.put_text(-2, 5, "Hello")
        self.assertEqual(written, 3)  # Only "llo" fits
        
        # Out of bounds row
        written = self.buffer.put_text(10, 25, "Hello")
        self.assertEqual(written, 0)
    
    def test_clear(self):
        """Test clearing the buffer."""
        # Put some content
        self.buffer.put_text(10, 5, "Hello")
        
        # Clear with custom colors
        self.buffer.clear(fg=2, bg=3)
        
        # Check all cells are cleared
        for row in self.buffer.cells:
            for cell in row:
                self.assertEqual(cell.char, ' ')
                self.assertEqual(cell.fg_color, 2)
                self.assertEqual(cell.bg_color, 3)
        
        # All rows should be marked dirty
        for damage in self.buffer.damage:
            self.assertTrue(damage.is_dirty)
            self.assertEqual(damage.get_bounds(), (0, 80))
    
    def test_clear_rect(self):
        """Test clearing a rectangular region."""
        # Fill buffer with 'X'
        for y in range(self.buffer.height):
            self.buffer.put_text(0, y, 'X' * self.buffer.width)
        
        # Clear a rectangle
        self.buffer.clear_rect(10, 5, 20, 10, fg=1, bg=2)
        
        # Check cleared area
        for y in range(5, 15):
            for x in range(10, 30):
                cell = self.buffer.get_cell(x, y)
                self.assertEqual(cell.char, ' ')
                self.assertEqual(cell.fg_color, 1)
                self.assertEqual(cell.bg_color, 2)
        
        # Check outside area still has 'X'
        self.assertEqual(self.buffer.get_cell(9, 5).char, 'X')
        self.assertEqual(self.buffer.get_cell(30, 5).char, 'X')
        self.assertEqual(self.buffer.get_cell(10, 4).char, 'X')
        self.assertEqual(self.buffer.get_cell(10, 15).char, 'X')
    
    def test_set_attrs(self):
        """Test setting attributes for a range."""
        # Put some text
        self.buffer.put_text(10, 5, "Hello World")
        
        # Set attributes
        self.buffer.set_attrs(10, 5, 5, ScreenCell.ATTR_BOLD | ScreenCell.ATTR_UNDERLINE)
        
        # Check first 5 chars have attributes
        for x in range(10, 15):
            cell = self.buffer.get_cell(x, 5)
            self.assertTrue(cell.has_attr(ScreenCell.ATTR_BOLD))
            self.assertTrue(cell.has_attr(ScreenCell.ATTR_UNDERLINE))
        
        # Rest shouldn't have attributes
        for x in range(15, 21):
            cell = self.buffer.get_cell(x, 5)
            self.assertFalse(cell.has_attr(ScreenCell.ATTR_BOLD))
    
    def test_scroll_up(self):
        """Test scrolling content up."""
        # Put content on lines 0-4
        for y in range(5):
            self.buffer.put_text(0, y, f"Line {y}")
        
        # Scroll up by 2 lines
        self.buffer.scroll_up(2)
        
        # Lines 0-1 should now have content from lines 2-3
        self.assertEqual(self.buffer.get_cell(5, 0).char, '2')  # "Line 2"
        self.assertEqual(self.buffer.get_cell(5, 1).char, '3')  # "Line 3"
        
        # Line 2 should have content from line 4
        self.assertEqual(self.buffer.get_cell(5, 2).char, '4')  # "Line 4"
        
        # Lines 3-4 should be cleared
        self.assertEqual(self.buffer.get_cell(5, 3).char, ' ')
        self.assertEqual(self.buffer.get_cell(5, 4).char, ' ')
    
    def test_scroll_down(self):
        """Test scrolling content down."""
        # Put content on lines 0-4
        for y in range(5):
            self.buffer.put_text(0, y, f"Line {y}")
        
        # Scroll down by 2 lines
        self.buffer.scroll_down(2, bottom=5)
        
        # Lines 0-1 should be cleared
        self.assertEqual(self.buffer.get_cell(5, 0).char, ' ')
        self.assertEqual(self.buffer.get_cell(5, 1).char, ' ')
        
        # Lines 2-4 should have content from lines 0-2
        self.assertEqual(self.buffer.get_cell(5, 2).char, '0')  # "Line 0"
        self.assertEqual(self.buffer.get_cell(5, 3).char, '1')  # "Line 1"
        self.assertEqual(self.buffer.get_cell(5, 4).char, '2')  # "Line 2"
    
    def test_get_damaged_regions(self):
        """Test getting damaged regions."""
        # Initially no damage
        regions = list(self.buffer.get_damaged_regions())
        self.assertEqual(len(regions), 0)
        
        # Add some content
        self.buffer.put_text(10, 5, "Hello")
        self.buffer.put_text(20, 10, "World")
        
        # Should have 2 damaged regions
        regions = list(self.buffer.get_damaged_regions())
        self.assertEqual(len(regions), 2)
        
        rows = [r[0] for r in regions]
        self.assertIn(5, rows)
        self.assertIn(10, rows)
    
    def test_clear_damage(self):
        """Test clearing damage tracking."""
        # Add content to create damage
        self.buffer.put_text(10, 5, "Hello")
        self.assertTrue(self.buffer.damage[5].is_dirty)
        
        # Clear damage
        self.buffer.clear_damage()
        self.assertFalse(self.buffer.damage[5].is_dirty)
        
        # Cells should also be marked clean
        for x in range(10, 15):
            self.assertFalse(self.buffer.get_cell(x, 5).dirty)
    
    def test_mark_all_dirty(self):
        """Test marking entire buffer as dirty."""
        self.buffer.mark_all_dirty()
        
        # All damage regions should be dirty
        for damage in self.buffer.damage:
            self.assertTrue(damage.is_dirty)
            self.assertEqual(damage.get_bounds(), (0, 80))
        
        # All cells should be dirty
        for row in self.buffer.cells:
            for cell in row:
                self.assertTrue(cell.dirty)
    
    def test_resize(self):
        """Test buffer resizing."""
        # Put some content
        self.buffer.put_text(5, 5, "Hello")
        self.buffer.put_text(5, 10, "World")
        
        # Resize larger
        self.buffer.resize(100, 30)
        self.assertEqual(self.buffer.width, 100)
        self.assertEqual(self.buffer.height, 30)
        
        # Original content should be preserved
        self.assertEqual(self.buffer.get_cell(5, 5).char, 'H')
        self.assertEqual(self.buffer.get_cell(5, 10).char, 'W')
        
        # New cells should be empty
        self.assertEqual(self.buffer.get_cell(90, 25).char, ' ')
        
        # Resize smaller
        self.buffer.resize(10, 8)
        self.assertEqual(self.buffer.width, 10)
        self.assertEqual(self.buffer.height, 8)
        
        # Content within bounds should be preserved
        self.assertEqual(self.buffer.get_cell(5, 5).char, 'H')
        # Content at (5, 10) is now out of bounds
        self.assertIsNone(self.buffer.get_cell(5, 10))
    
    def test_should_update(self):
        """Test FPS limiting integration."""
        # With FPS limiting
        buffer = DisplayBuffer(80, 25, fps=60)
        self.assertTrue(buffer.should_update())  # First frame
        
        # Without FPS limiting
        buffer = DisplayBuffer(80, 25, fps=0)
        self.assertTrue(buffer.should_update())
        self.assertTrue(buffer.should_update())  # Always true


if __name__ == '__main__':
    unittest.main()