# -*- coding: utf-8 -*-
"""
Damage region tracking for efficient screen updates.

This module provides the DamageRegion class which tracks modified areas
of the display buffer to minimize screen update operations.
"""

from typing import Optional, Tuple


class DamageRegion:
    """
    Tracks the dirty (modified) region of a single row in the display buffer.
    
    This class maintains the start and end columns of the modified region
    in a row, allowing the display system to update only the changed portions
    of the screen for better performance.
    
    Attributes:
        start: Starting column of the dirty region (inclusive)
        end: Ending column of the dirty region (exclusive)
    """
    
    def __init__(self):
        """Initialize an empty (clean) damage region."""
        self.start: Optional[int] = None
        self.end: Optional[int] = None
    
    @property
    def is_dirty(self) -> bool:
        """
        Check if this region has any damage.
        
        Returns:
            True if there is a dirty region, False if clean
        """
        return self.start is not None
    
    @property
    def is_clean(self) -> bool:
        """
        Check if this region is clean (no damage).
        
        Returns:
            True if clean, False if there is damage
        """
        return self.start is None
    
    def mark_dirty(self, start: int, end: int) -> None:
        """
        Mark a range as dirty, expanding the current region if necessary.
        
        Args:
            start: Starting column (inclusive)
            end: Ending column (exclusive)
            
        Raises:
            ValueError: If start >= end or if values are negative
        """
        if start >= end:
            raise ValueError(f"Invalid range: start ({start}) must be less than end ({end})")
        if start < 0 or end < 0:
            raise ValueError(f"Negative values not allowed: start={start}, end={end}")
        
        if self.is_clean:
            # First dirty region
            self.start = start
            self.end = end
        else:
            # Expand existing region
            self.start = min(self.start, start)
            self.end = max(self.end, end)
    
    def mark_cell_dirty(self, column: int) -> None:
        """
        Mark a single cell as dirty.
        
        Args:
            column: The column index to mark as dirty
            
        Raises:
            ValueError: If column is negative
        """
        if column < 0:
            raise ValueError(f"Negative column not allowed: {column}")
        
        self.mark_dirty(column, column + 1)
    
    def clear(self) -> None:
        """Clear the damage region, marking it as clean."""
        self.start = None
        self.end = None
    
    def get_bounds(self) -> Optional[Tuple[int, int]]:
        """
        Get the bounds of the dirty region.
        
        Returns:
            A tuple of (start, end) if dirty, None if clean
        """
        if self.is_dirty:
            return (self.start, self.end)
        return None
    
    @property
    def width(self) -> int:
        """
        Get the width of the dirty region.
        
        Returns:
            Number of columns in the dirty region, 0 if clean
        """
        if self.is_clean:
            return 0
        return self.end - self.start
    
    def contains(self, column: int) -> bool:
        """
        Check if a column is within the dirty region.
        
        Args:
            column: The column index to check
            
        Returns:
            True if the column is in the dirty region, False otherwise
        """
        if self.is_clean:
            return False
        return self.start <= column < self.end
    
    def intersects(self, start: int, end: int) -> bool:
        """
        Check if a range intersects with the dirty region.
        
        Args:
            start: Start of the range to check (inclusive)
            end: End of the range to check (exclusive)
            
        Returns:
            True if the ranges intersect, False otherwise
        """
        if self.is_clean:
            return False
        return not (end <= self.start or start >= self.end)
    
    def union(self, other: 'DamageRegion') -> None:
        """
        Merge another damage region into this one.
        
        Args:
            other: The damage region to merge
        """
        if other.is_clean:
            return
        
        if self.is_clean:
            self.start = other.start
            self.end = other.end
        else:
            self.start = min(self.start, other.start)
            self.end = max(self.end, other.end)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        if self.is_clean:
            return "DamageRegion(clean)"
        return f"DamageRegion(start={self.start}, end={self.end}, width={self.width})"
    
    def __bool__(self) -> bool:
        """Boolean evaluation returns True if dirty."""
        return self.is_dirty