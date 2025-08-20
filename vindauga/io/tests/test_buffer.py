# -*- coding: utf-8 -*-
"""
Unit tests for display buffer system.

Tests for ScreenCell, DisplayBuffer, DamageRegion, and FPSLimiter classes.
"""

import unittest
import time
from vindauga.io.display.buffer import ScreenCell, DisplayBuffer, DamageRegion, FPSLimiter


class TestScreenCell(unittest.TestCase):
    """Test cases for ScreenCell class."""
    
    def test_basic_creation(self):
        """Test basic ScreenCell creation."""
        cell = ScreenCell('A', 0x07)
        self.assertEqual(cell.text, 'A')
        self.assertEqual(cell.attr, 0x07)
        self.assertEqual(cell.width, 1)
        self.assertFalse(cell.is_dirty())
        self.assertFalse(cell.is_wide())
    
    def test_empty_cell(self):
        """Test empty ScreenCell creation."""
        cell = ScreenCell()
        self.assertEqual(cell.text, ' ')
        self.assertEqual(cell.attr, 0)
        self.assertEqual(cell.width, 1)
    
    def test_wide_character(self):
        """Test wide character handling."""
        cell = ScreenCell('你', 0x07)
        self.assertEqual(cell.text, '你')
        self.assertEqual(cell.width, 2)
        self.assertTrue(cell.is_wide())
    
    def test_combining_character(self):
        """Test combining character handling."""
        # e with acute accent (combining)
        cell = ScreenCell('é', 0x07)
        self.assertEqual(cell.width, 1)
    
    def test_utf8_truncation(self):
        """Test UTF-8 text truncation at 15 bytes."""
        long_text = '你好世界测试' * 3  # Should exceed 15 bytes
        cell = ScreenCell(long_text, 0x07)
        # Ensure text is truncated but still valid UTF-8
        self.assertTrue(len(cell.text.encode('utf-8')) <= 15)
    
    def test_dirty_flag(self):
        """Test dirty flag operations."""
        cell = ScreenCell('A', 0x07)
        self.assertFalse(cell.is_dirty())
        
        cell.mark_dirty()
        self.assertTrue(cell.is_dirty())
        
        cell.clear_dirty()
        self.assertFalse(cell.is_dirty())
    
    def test_trail_cell(self):
        """Test trailing cell for wide characters."""
        cell = ScreenCell('你', 0x07)
        trail = cell.make_trail()
        
        self.assertEqual(trail.text, '')
        self.assertEqual(trail.attr, 0x07)
        self.assertEqual(trail.width, 0)
        self.assertTrue(trail.is_trail())
    
    def test_equality(self):
        """Test cell equality comparison."""
        cell1 = ScreenCell('A', 0x07)
        cell2 = ScreenCell('A', 0x07)
        cell3 = ScreenCell('B', 0x07)
        
        self.assertEqual(cell1, cell2)
        self.assertNotEqual(cell1, cell3)
        
        # Test equals method (ignores dirty flag)
        cell1.mark_dirty()
        self.assertTrue(cell1.equals(cell2))
        self.assertNotEqual(cell1, cell2)  # __eq__ includes dirty flag
    
    def test_copy(self):
        """Test cell copying."""
        original = ScreenCell('A', 0x07, ScreenCell.FLAG_DIRTY)
        copy = original.copy()
        
        self.assertEqual(original, copy)
        self.assertIsNot(original, copy)  # Different objects


class TestDamageRegion(unittest.TestCase):
    """Test cases for DamageRegion class."""
    
    def test_initial_state(self):
        """Test initial damage region state."""
        region = DamageRegion()
        self.assertFalse(region.is_dirty)
        self.assertEqual(region.start, 0)
        self.assertEqual(region.end, 0)
        self.assertEqual(region.length(), 0)
    
    def test_expand(self):
        """Test damage region expansion."""
        region = DamageRegion()
        
        region.expand(5, 10)
        self.assertTrue(region.is_dirty)
        self.assertEqual(region.start, 5)
        self.assertEqual(region.end, 10)
        self.assertEqual(region.length(), 5)
        
        # Test expansion
        region.expand(3, 7)
        self.assertEqual(region.start, 3)
        self.assertEqual(region.end, 10)
        
        region.expand(8, 15)
        self.assertEqual(region.start, 3)
        self.assertEqual(region.end, 15)
    
    def test_contains(self):
        """Test damage region containment."""
        region = DamageRegion()
        region.expand(5, 10)
        
        self.assertFalse(region.contains(4))
        self.assertTrue(region.contains(5))
        self.assertTrue(region.contains(7))
        self.assertTrue(region.contains(9))
        self.assertFalse(region.contains(10))
    
    def test_clear(self):
        """Test damage region clearing."""
        region = DamageRegion()
        region.expand(5, 10)
        
        region.clear()
        self.assertFalse(region.is_dirty)
        self.assertEqual(region.length(), 0)


class TestFPSLimiter(unittest.TestCase):
    """Test cases for FPSLimiter class."""
    
    def test_disabled_limiter(self):
        """Test FPS limiter when disabled."""
        limiter = FPSLimiter(0)  # Disabled
        self.assertFalse(limiter.enabled)
        self.assertTrue(limiter.should_update())
        self.assertTrue(limiter.should_update())  # Always true when disabled
    
    def test_enabled_limiter(self):
        """Test FPS limiter when enabled."""
        limiter = FPSLimiter(60)  # 60 FPS
        self.assertTrue(limiter.enabled)
        self.assertAlmostEqual(limiter.frame_time, 1.0/60, places=6)
        
        # First call should always return True
        self.assertTrue(limiter.should_update())
        
        # Immediate second call should return False
        self.assertFalse(limiter.should_update())
    
    def test_fps_change(self):
        """Test changing FPS limit."""
        limiter = FPSLimiter(60)
        limiter.set_fps(30)
        
        self.assertEqual(limiter.target_fps, 30)
        self.assertAlmostEqual(limiter.frame_time, 1.0/30, places=6)
        
        limiter.set_fps(0)
        self.assertFalse(limiter.enabled)


class TestDisplayBuffer(unittest.TestCase):
    """Test cases for DisplayBuffer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.buffer = DisplayBuffer(80, 25)
    
    def test_creation(self):
        """Test buffer creation."""
        self.assertEqual(self.buffer.width, 80)
        self.assertEqual(self.buffer.height, 25)
        self.assertEqual(len(self.buffer.primary_buffer), 25)
        self.assertEqual(len(self.buffer.primary_buffer[0]), 80)
        self.assertEqual(len(self.buffer.damage), 25)
    
    def test_put_char(self):
        """Test putting a single character."""
        self.buffer.put_char(10, 5, 'A', 0x07)
        
        cell = self.buffer.get_cell(10, 5)
        self.assertEqual(cell.text, 'A')
        self.assertEqual(cell.attr, 0x07)
        self.assertTrue(cell.is_dirty())
        
        # Check damage tracking
        self.assertTrue(self.buffer.damage[5].is_dirty)
        self.assertEqual(self.buffer.damage[5].start, 10)
        self.assertEqual(self.buffer.damage[5].end, 11)
    
    def test_put_text(self):
        """Test putting text."""
        self.buffer.put_text(10, 5, "Hello", 0x07)
        
        # Check each character
        for i, char in enumerate("Hello"):
            cell = self.buffer.get_cell(10 + i, 5)
            self.assertEqual(cell.text, char)
            self.assertEqual(cell.attr, 0x07)
        
        # Check damage tracking
        self.assertTrue(self.buffer.damage[5].is_dirty)
        self.assertEqual(self.buffer.damage[5].start, 10)
        self.assertEqual(self.buffer.damage[5].end, 15)
    
    def test_wide_character(self):
        """Test wide character handling in buffer."""
        self.buffer.put_char(10, 5, '你', 0x07)
        
        # Main cell
        cell = self.buffer.get_cell(10, 5)
        self.assertEqual(cell.text, '你')
        self.assertTrue(cell.is_wide())
        
        # Trail cell
        trail = self.buffer.get_cell(11, 5)
        self.assertTrue(trail.is_trail())
        self.assertEqual(trail.width, 0)
        
        # Damage should cover both cells
        self.assertEqual(self.buffer.damage[5].start, 10)
        self.assertEqual(self.buffer.damage[5].end, 12)
    
    def test_fill_rect(self):
        """Test rectangle filling."""
        self.buffer.fill_rect(10, 5, 5, 3, '#', 0x0F)
        
        # Check filled area
        for y in range(5, 8):
            for x in range(10, 15):
                cell = self.buffer.get_cell(x, y)
                self.assertEqual(cell.text, '#')
                self.assertEqual(cell.attr, 0x0F)
            
            # Check damage tracking
            self.assertTrue(self.buffer.damage[y].is_dirty)
            self.assertEqual(self.buffer.damage[y].start, 10)
            self.assertEqual(self.buffer.damage[y].end, 15)
    
    def test_clear(self):
        """Test buffer clearing."""
        # Put some content first
        self.buffer.put_text(10, 5, "Hello", 0x07)
        
        # Clear buffer
        self.buffer.clear(0x70)
        
        # Check that all cells are cleared
        for y in range(self.buffer.height):
            for x in range(self.buffer.width):
                cell = self.buffer.get_cell(x, y)
                self.assertEqual(cell.text, ' ')
                self.assertEqual(cell.attr, 0x70)
    
    def test_bounds_checking(self):
        """Test bounds checking for buffer operations."""
        # Should not crash or raise exceptions
        self.buffer.put_char(-1, 5, 'A', 0x07)
        self.buffer.put_char(100, 5, 'A', 0x07)
        self.buffer.put_char(10, -1, 'A', 0x07)
        self.buffer.put_char(10, 100, 'A', 0x07)
        
        # get_cell should return None for out of bounds
        self.assertIsNone(self.buffer.get_cell(-1, 5))
        self.assertIsNone(self.buffer.get_cell(100, 5))
        self.assertIsNone(self.buffer.get_cell(10, -1))
        self.assertIsNone(self.buffer.get_cell(10, 100))
    
    def test_damage_tracking(self):
        """Test damage tracking functionality."""
        # Initially no damage
        self.assertFalse(self.buffer.has_damage())
        
        # Add some content
        self.buffer.put_char(10, 5, 'A', 0x07)
        self.assertTrue(self.buffer.has_damage())
        
        # Get damaged rows
        damaged_rows = self.buffer.get_damaged_rows()
        self.assertEqual(damaged_rows, [5])
    
    def test_prepare_flush(self):
        """Test flush preparation."""
        # Disable FPS limiting for testing
        self.buffer.set_fps_limit(0)
        
        # Add some content
        self.buffer.put_text(10, 5, "Hello", 0x07)
        self.buffer.put_char(20, 10, 'X', 0x0F)
        
        # Prepare flush
        flush_data = self.buffer.prepare_flush()
        
        # Should have flush data for 2 rows
        self.assertEqual(len(flush_data), 2)
        
        # Check first row data
        row, start, end, cells = flush_data[0]
        self.assertEqual(row, 5)
        self.assertEqual(start, 10)
        self.assertEqual(end, 15)
        self.assertEqual(len(cells), 5)
        
        # Check second row data
        row, start, end, cells = flush_data[1]
        self.assertEqual(row, 10)
        self.assertEqual(start, 20)
        self.assertEqual(end, 21)
        self.assertEqual(len(cells), 1)
    
    def test_commit_flush(self):
        """Test flush commit."""
        # Add content and prepare flush
        self.buffer.put_char(10, 5, 'A', 0x07)
        self.buffer.prepare_flush()
        
        # Commit flush
        self.buffer.commit_flush()
        
        # Damage should be cleared
        self.assertFalse(self.buffer.has_damage())
        
        # Cell should no longer be dirty
        cell = self.buffer.get_cell(10, 5)
        self.assertFalse(cell.is_dirty())
    
    def test_resize(self):
        """Test buffer resizing."""
        # Add some content
        self.buffer.put_text(5, 5, "Hello", 0x07)
        
        # Resize buffer
        self.buffer.resize(100, 30)
        
        self.assertEqual(self.buffer.width, 100)
        self.assertEqual(self.buffer.height, 30)
        
        # Original content should be preserved
        for i, char in enumerate("Hello"):
            cell = self.buffer.get_cell(5 + i, 5)
            self.assertEqual(cell.text, char)
    
    def test_stats(self):
        """Test buffer statistics."""
        stats = self.buffer.get_stats()
        
        self.assertEqual(stats['width'], 80)
        self.assertEqual(stats['height'], 25)
        self.assertEqual(stats['total_cells'], 80 * 25)
        self.assertEqual(stats['dirty_cells'], 0)
        self.assertEqual(stats['damaged_rows'], 0)
        self.assertEqual(stats['damage_ratio'], 0.0)


if __name__ == '__main__':
    unittest.main()