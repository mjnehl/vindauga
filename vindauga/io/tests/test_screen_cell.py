# -*- coding: utf-8 -*-
"""Unit tests for ScreenCell class."""

import unittest
from vindauga.io.screen_cell import ScreenCell, WideCharCell


class TestScreenCell(unittest.TestCase):
    """Test cases for ScreenCell class."""
    
    def test_default_initialization(self):
        """Test default cell initialization."""
        cell = ScreenCell()
        self.assertEqual(cell.char, ' ')
        self.assertEqual(cell.fg_color, 7)
        self.assertEqual(cell.bg_color, 0)
        self.assertEqual(cell.attrs, 0)
        self.assertTrue(cell.dirty)
    
    def test_custom_initialization(self):
        """Test cell initialization with custom values."""
        cell = ScreenCell(char='A', fg_color=2, bg_color=4, attrs=ScreenCell.ATTR_BOLD)
        self.assertEqual(cell.char, 'A')
        self.assertEqual(cell.fg_color, 2)
        self.assertEqual(cell.bg_color, 4)
        self.assertEqual(cell.attrs, ScreenCell.ATTR_BOLD)
    
    def test_char_normalization(self):
        """Test that multi-character strings are normalized."""
        cell = ScreenCell(char='ABC')
        self.assertEqual(cell.char, 'A')
        
        cell = ScreenCell(char='')
        self.assertEqual(cell.char, ' ')
    
    def test_wide_character_detection(self):
        """Test detection of wide characters."""
        # Regular ASCII character
        cell = ScreenCell('A')
        self.assertFalse(cell.is_wide)
        self.assertEqual(cell.width, 1)
        
        # Wide CJK character
        cell = ScreenCell('中')
        self.assertTrue(cell.is_wide)
        self.assertEqual(cell.width, 2)
        
        # Emoji (should be wide)
        cell = ScreenCell('🎉')
        self.assertTrue(cell.is_wide)
        self.assertEqual(cell.width, 2)
    
    def test_set_char(self):
        """Test setting character and dirty flag."""
        cell = ScreenCell()
        cell.dirty = False
        
        cell.set_char('X')
        self.assertEqual(cell.char, 'X')
        self.assertTrue(cell.dirty)
        
        # Setting same char shouldn't mark dirty
        cell.dirty = False
        cell.set_char('X')
        self.assertFalse(cell.dirty)
    
    def test_set_colors(self):
        """Test setting colors."""
        cell = ScreenCell()
        cell.dirty = False
        
        cell.set_colors(fg=3, bg=5)
        self.assertEqual(cell.fg_color, 3)
        self.assertEqual(cell.bg_color, 5)
        self.assertTrue(cell.dirty)
        
        # Test partial update
        cell.dirty = False
        cell.set_colors(fg=4)
        self.assertEqual(cell.fg_color, 4)
        self.assertEqual(cell.bg_color, 5)  # Unchanged
        self.assertTrue(cell.dirty)
    
    def test_attributes(self):
        """Test attribute manipulation."""
        cell = ScreenCell()
        
        # Set attributes
        cell.set_attr(ScreenCell.ATTR_BOLD, True)
        self.assertTrue(cell.has_attr(ScreenCell.ATTR_BOLD))
        
        cell.set_attr(ScreenCell.ATTR_UNDERLINE, True)
        self.assertTrue(cell.has_attr(ScreenCell.ATTR_UNDERLINE))
        self.assertTrue(cell.has_attr(ScreenCell.ATTR_BOLD))  # Still set
        
        # Clear attribute
        cell.set_attr(ScreenCell.ATTR_BOLD, False)
        self.assertFalse(cell.has_attr(ScreenCell.ATTR_BOLD))
        self.assertTrue(cell.has_attr(ScreenCell.ATTR_UNDERLINE))  # Still set
    
    def test_clear(self):
        """Test clearing a cell."""
        cell = ScreenCell('X', fg_color=3, bg_color=5, 
                        attrs=ScreenCell.ATTR_BOLD | ScreenCell.ATTR_UNDERLINE)
        cell.dirty = False
        
        cell.clear()
        self.assertEqual(cell.char, ' ')
        self.assertEqual(cell.fg_color, 7)
        self.assertEqual(cell.bg_color, 0)
        self.assertEqual(cell.attrs, 0)
        self.assertTrue(cell.dirty)
    
    def test_copy_from(self):
        """Test copying from another cell."""
        source = ScreenCell('X', fg_color=3, bg_color=5, attrs=ScreenCell.ATTR_BOLD)
        target = ScreenCell()
        target.dirty = False
        
        target.copy_from(source)
        self.assertEqual(target.char, 'X')
        self.assertEqual(target.fg_color, 3)
        self.assertEqual(target.bg_color, 5)
        self.assertEqual(target.attrs, ScreenCell.ATTR_BOLD)
        self.assertTrue(target.dirty)
        
        # Copying identical content shouldn't mark dirty
        target.dirty = False
        target.copy_from(source)
        self.assertFalse(target.dirty)
    
    def test_equals_display(self):
        """Test display equality comparison."""
        cell1 = ScreenCell('A', fg_color=2, bg_color=3, attrs=ScreenCell.ATTR_BOLD)
        cell2 = ScreenCell('A', fg_color=2, bg_color=3, attrs=ScreenCell.ATTR_BOLD)
        cell3 = ScreenCell('B', fg_color=2, bg_color=3, attrs=ScreenCell.ATTR_BOLD)
        
        self.assertTrue(cell1.equals_display(cell2))
        self.assertFalse(cell1.equals_display(cell3))
        
        # Dirty flag shouldn't affect display equality
        cell2.dirty = False
        self.assertTrue(cell1.equals_display(cell2))
    
    def test_dirty_flag_management(self):
        """Test dirty flag management."""
        cell = ScreenCell()
        self.assertTrue(cell.dirty)
        
        cell.mark_clean()
        self.assertFalse(cell.dirty)
        
        cell.mark_dirty()
        self.assertTrue(cell.dirty)


class TestWideCharCell(unittest.TestCase):
    """Test cases for WideCharCell class."""
    
    def test_wide_trail_cell(self):
        """Test wide character trailing cell."""
        cell = WideCharCell()
        self.assertEqual(cell.char, '')
        self.assertTrue(cell.is_wide_trail)
        self.assertEqual(cell.width, 0)
        self.assertEqual(cell.fg_color, 0)
        self.assertEqual(cell.bg_color, 0)


if __name__ == '__main__':
    unittest.main()