# -*- coding: utf-8 -*-
"""
Display buffer with damage tracking for efficient terminal updates.

This module provides the DisplayBuffer class which implements double-buffering
with damage tracking, inspired by TVision's TDisplayBuffer but using Python
best practices.
"""

from typing import List, Optional, Tuple, Iterator
from .screen_cell import ScreenCell, WideCharCell
from .damage_region import DamageRegion
from .fps_limiter import FPSLimiter


class DisplayBuffer:
    """
    A double-buffered display with damage tracking.
    
    This class manages a 2D grid of ScreenCells representing the terminal
    display. It tracks which regions have been modified (damage tracking)
    to enable efficient updates by only redrawing changed areas.
    
    The buffer supports:
    - Wide characters (that occupy two columns)
    - Damage tracking per row for efficient updates
    - FPS limiting to control update rate
    - Various text and attribute manipulation operations
    
    Attributes:
        width: Width of the buffer in columns
        height: Height of the buffer in rows
        cells: 2D list of ScreenCell objects
        damage: List of DamageRegion objects (one per row)
        fps_limiter: FPS limiter for controlling update rate
    """
    
    def __init__(self, width: int, height: int, fps: int = 60):
        """
        Initialize a display buffer.
        
        Args:
            width: Width in columns
            height: Height in rows
            fps: Target frames per second (0 for unlimited)
            
        Raises:
            ValueError: If width or height is less than 1
        """
        if width < 1 or height < 1:
            raise ValueError(f"Invalid buffer size: {width}x{height}")
        
        self.width = width
        self.height = height
        self.fps_limiter = FPSLimiter(fps)
        
        # Initialize cell buffer
        self.cells: List[List[ScreenCell]] = []
        for _ in range(height):
            row = [ScreenCell() for _ in range(width)]
            self.cells.append(row)
        
        # Initialize damage tracking (one region per row)
        self.damage: List[DamageRegion] = [DamageRegion() for _ in range(height)]
    
    def get_cell(self, x: int, y: int) -> Optional[ScreenCell]:
        """
        Get the cell at the specified position.
        
        Args:
            x: Column index (0-based)
            y: Row index (0-based)
            
        Returns:
            The ScreenCell at that position, or None if out of bounds
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return None
    
    def put_char(self, x: int, y: int, char: str, 
                 fg: Optional[int] = None, bg: Optional[int] = None,
                 attrs: int = 0) -> None:
        """
        Place a character at the specified position.
        
        Args:
            x: Column index
            y: Row index
            char: Character to place
            fg: Foreground color (None to keep current)
            bg: Background color (None to keep current)
            attrs: Display attributes
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        
        cell = self.cells[y][x]
        
        # Update cell properties
        cell.set_char(char)
        if fg is not None:
            cell.fg_color = fg
        if bg is not None:
            cell.bg_color = bg
        if attrs:
            cell.attrs = attrs
        
        # Handle wide characters
        if cell.is_wide and x + 1 < self.width:
            # Mark next cell as wide character trail
            self.cells[y][x + 1] = WideCharCell()
            self.damage[y].mark_dirty(x, x + 2)
        else:
            self.damage[y].mark_cell_dirty(x)
    
    def put_text(self, x: int, y: int, text: str,
                 fg: Optional[int] = None, bg: Optional[int] = None,
                 attrs: int = 0) -> int:
        """
        Place a string of text starting at the specified position.
        
        Text that extends beyond the buffer width is clipped.
        
        Args:
            x: Starting column
            y: Row index
            text: Text to place
            fg: Foreground color
            bg: Background color
            attrs: Display attributes
            
        Returns:
            Number of cells actually written
        """
        if not (0 <= y < self.height) or not text:
            return 0
        
        cells_written = 0
        current_x = x
        
        for char in text:
            if current_x >= self.width:
                break
            
            if current_x >= 0:  # Handle negative starting positions
                self.put_char(current_x, y, char, fg, bg, attrs)
                cell = self.cells[y][current_x]
                cells_written += cell.width
                current_x += cell.width
            else:
                current_x += 1
        
        return cells_written
    
    def clear(self, fg: int = 7, bg: int = 0) -> None:
        """
        Clear the entire buffer.
        
        Args:
            fg: Foreground color for cleared cells
            bg: Background color for cleared cells
        """
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                cell.clear()
                cell.fg_color = fg
                cell.bg_color = bg
            self.damage[y].mark_dirty(0, self.width)
    
    def clear_rect(self, x: int, y: int, width: int, height: int,
                   fg: int = 7, bg: int = 0) -> None:
        """
        Clear a rectangular region.
        
        Args:
            x: Starting column
            y: Starting row
            width: Width of rectangle
            height: Height of rectangle
            fg: Foreground color
            bg: Background color
        """
        # Clip to buffer bounds
        x_start = max(0, x)
        y_start = max(0, y)
        x_end = min(self.width, x + width)
        y_end = min(self.height, y + height)
        
        for row in range(y_start, y_end):
            for col in range(x_start, x_end):
                cell = self.cells[row][col]
                cell.clear()
                cell.fg_color = fg
                cell.bg_color = bg
            
            if x_start < x_end:
                self.damage[row].mark_dirty(x_start, x_end)
    
    def set_attrs(self, x: int, y: int, width: int, attrs: int) -> None:
        """
        Set attributes for a horizontal range of cells.
        
        Args:
            x: Starting column
            y: Row index
            width: Number of cells to modify
            attrs: Attributes to set
        """
        if not (0 <= y < self.height):
            return
        
        x_start = max(0, x)
        x_end = min(self.width, x + width)
        
        for col in range(x_start, x_end):
            self.cells[y][col].attrs = attrs
            self.cells[y][col].dirty = True
        
        if x_start < x_end:
            self.damage[y].mark_dirty(x_start, x_end)
    
    def scroll_up(self, lines: int = 1, top: int = 0, 
                  bottom: Optional[int] = None) -> None:
        """
        Scroll a region up by the specified number of lines.
        
        Args:
            lines: Number of lines to scroll
            top: Top row of scroll region (inclusive)
            bottom: Bottom row of scroll region (exclusive), None for end
        """
        if bottom is None:
            bottom = self.height
        
        if lines <= 0 or top >= bottom or top < 0 or bottom > self.height:
            return
        
        # Shift rows up
        for y in range(top, bottom - lines):
            self.cells[y] = self.cells[y + lines]
            self.damage[y].mark_dirty(0, self.width)
        
        # Clear the bottom rows
        for y in range(max(top, bottom - lines), bottom):
            self.cells[y] = [ScreenCell() for _ in range(self.width)]
            self.damage[y].mark_dirty(0, self.width)
    
    def scroll_down(self, lines: int = 1, top: int = 0,
                    bottom: Optional[int] = None) -> None:
        """
        Scroll a region down by the specified number of lines.
        
        Args:
            lines: Number of lines to scroll
            top: Top row of scroll region (inclusive)
            bottom: Bottom row of scroll region (exclusive), None for end
        """
        if bottom is None:
            bottom = self.height
        
        if lines <= 0 or top >= bottom or top < 0 or bottom > self.height:
            return
        
        # Shift rows down
        for y in range(bottom - 1, top + lines - 1, -1):
            self.cells[y] = self.cells[y - lines]
            self.damage[y].mark_dirty(0, self.width)
        
        # Clear the top rows
        for y in range(top, min(bottom, top + lines)):
            self.cells[y] = [ScreenCell() for _ in range(self.width)]
            self.damage[y].mark_dirty(0, self.width)
    
    def get_damaged_regions(self) -> Iterator[Tuple[int, DamageRegion]]:
        """
        Get all damaged regions that need updating.
        
        Yields:
            Tuples of (row_index, DamageRegion) for each dirty row
        """
        for y, region in enumerate(self.damage):
            if region.is_dirty:
                yield y, region
    
    def clear_damage(self) -> None:
        """Clear all damage tracking, marking everything as clean."""
        for region in self.damage:
            region.clear()
        
        for row in self.cells:
            for cell in row:
                cell.mark_clean()
    
    def mark_all_dirty(self) -> None:
        """Mark the entire buffer as dirty (needs complete redraw)."""
        for y in range(self.height):
            self.damage[y].mark_dirty(0, self.width)
            for cell in self.cells[y]:
                cell.mark_dirty()
    
    def resize(self, new_width: int, new_height: int) -> None:
        """
        Resize the buffer, preserving content where possible.
        
        Args:
            new_width: New width in columns
            new_height: New height in rows
            
        Raises:
            ValueError: If new dimensions are less than 1
        """
        if new_width < 1 or new_height < 1:
            raise ValueError(f"Invalid buffer size: {new_width}x{new_height}")
        
        # Create new cell buffer
        new_cells: List[List[ScreenCell]] = []
        
        for y in range(new_height):
            row: List[ScreenCell] = []
            for x in range(new_width):
                # Copy existing cell or create new one
                if y < self.height and x < self.width:
                    row.append(self.cells[y][x])
                else:
                    row.append(ScreenCell())
            new_cells.append(row)
        
        # Update buffer
        self.cells = new_cells
        self.width = new_width
        self.height = new_height
        
        # Reset damage tracking
        self.damage = [DamageRegion() for _ in range(new_height)]
        self.mark_all_dirty()
    
    def should_update(self) -> bool:
        """
        Check if an update should be performed based on FPS limiting.
        
        Returns:
            True if update should proceed, False to skip
        """
        return self.fps_limiter.should_update()
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        dirty_rows = sum(1 for region in self.damage if region.is_dirty)
        return (f"DisplayBuffer(size={self.width}x{self.height}, "
                f"dirty_rows={dirty_rows}/{self.height})")