# -*- coding: utf-8 -*-
"""Unit tests for DamageRegion class."""

import unittest
from vindauga.io.damage_region import DamageRegion


class TestDamageRegion(unittest.TestCase):
    """Test cases for DamageRegion class."""
    
    def test_initial_state(self):
        """Test initial clean state."""
        region = DamageRegion()
        self.assertFalse(region.is_dirty)
        self.assertTrue(region.is_clean)
        self.assertIsNone(region.get_bounds())
        self.assertEqual(region.width, 0)
        self.assertFalse(region)  # Boolean evaluation
    
    def test_mark_dirty(self):
        """Test marking a range as dirty."""
        region = DamageRegion()
        
        region.mark_dirty(5, 10)
        self.assertTrue(region.is_dirty)
        self.assertFalse(region.is_clean)
        self.assertEqual(region.get_bounds(), (5, 10))
        self.assertEqual(region.width, 5)
        self.assertTrue(region)  # Boolean evaluation
    
    def test_mark_dirty_expansion(self):
        """Test that marking dirty expands the region."""
        region = DamageRegion()
        
        region.mark_dirty(5, 10)
        self.assertEqual(region.get_bounds(), (5, 10))
        
        # Expand to the left
        region.mark_dirty(2, 7)
        self.assertEqual(region.get_bounds(), (2, 10))
        
        # Expand to the right
        region.mark_dirty(8, 15)
        self.assertEqual(region.get_bounds(), (2, 15))
        
        # Mark within existing region (no change)
        region.mark_dirty(5, 10)
        self.assertEqual(region.get_bounds(), (2, 15))
    
    def test_mark_cell_dirty(self):
        """Test marking a single cell."""
        region = DamageRegion()
        
        region.mark_cell_dirty(5)
        self.assertEqual(region.get_bounds(), (5, 6))
        self.assertEqual(region.width, 1)
        
        region.mark_cell_dirty(10)
        self.assertEqual(region.get_bounds(), (5, 11))
        self.assertEqual(region.width, 6)
    
    def test_clear(self):
        """Test clearing damage."""
        region = DamageRegion()
        region.mark_dirty(5, 10)
        
        region.clear()
        self.assertTrue(region.is_clean)
        self.assertIsNone(region.get_bounds())
        self.assertEqual(region.width, 0)
    
    def test_contains(self):
        """Test checking if a column is in the dirty region."""
        region = DamageRegion()
        region.mark_dirty(5, 10)
        
        self.assertFalse(region.contains(4))
        self.assertTrue(region.contains(5))
        self.assertTrue(region.contains(7))
        self.assertTrue(region.contains(9))
        self.assertFalse(region.contains(10))
        
        # Clean region contains nothing
        region.clear()
        self.assertFalse(region.contains(7))
    
    def test_intersects(self):
        """Test checking range intersection."""
        region = DamageRegion()
        region.mark_dirty(5, 10)
        
        # Various intersection cases
        self.assertTrue(region.intersects(3, 7))   # Overlaps left
        self.assertTrue(region.intersects(8, 12))   # Overlaps right
        self.assertTrue(region.intersects(6, 9))    # Contained within
        self.assertTrue(region.intersects(3, 12))   # Contains region
        self.assertTrue(region.intersects(5, 10))   # Exact match
        
        # No intersection
        self.assertFalse(region.intersects(1, 5))   # Touches left edge
        self.assertFalse(region.intersects(10, 15)) # Touches right edge
        self.assertFalse(region.intersects(1, 4))   # Before
        self.assertFalse(region.intersects(11, 15)) # After
    
    def test_union(self):
        """Test merging damage regions."""
        region1 = DamageRegion()
        region2 = DamageRegion()
        
        # Union with clean region (no change)
        region1.mark_dirty(5, 10)
        region1.union(region2)
        self.assertEqual(region1.get_bounds(), (5, 10))
        
        # Union of two dirty regions
        region2.mark_dirty(8, 15)
        region1.union(region2)
        self.assertEqual(region1.get_bounds(), (5, 15))
        
        # Union when first is clean
        region3 = DamageRegion()
        region4 = DamageRegion()
        region4.mark_dirty(2, 7)
        region3.union(region4)
        self.assertEqual(region3.get_bounds(), (2, 7))
    
    def test_invalid_ranges(self):
        """Test error handling for invalid ranges."""
        region = DamageRegion()
        
        # Invalid range (start >= end)
        with self.assertRaises(ValueError):
            region.mark_dirty(10, 5)
        
        with self.assertRaises(ValueError):
            region.mark_dirty(5, 5)
        
        # Negative values
        with self.assertRaises(ValueError):
            region.mark_dirty(-1, 5)
        
        with self.assertRaises(ValueError):
            region.mark_dirty(5, -1)
        
        with self.assertRaises(ValueError):
            region.mark_cell_dirty(-1)
    
    def test_repr(self):
        """Test string representation."""
        region = DamageRegion()
        self.assertEqual(repr(region), "DamageRegion(clean)")
        
        region.mark_dirty(5, 10)
        self.assertEqual(repr(region), "DamageRegion(start=5, end=10, width=5)")


if __name__ == '__main__':
    unittest.main()