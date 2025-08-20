# -*- coding: utf-8 -*-
"""
Screen cell implementation for the display buffer system.

This module provides the ScreenCell class which represents a single character
cell on the terminal screen, inspired by TVision's TScreenCell but implemented
with Python best practices.
"""

import unicodedata
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ScreenCell:
    """
    Represents a single cell on the terminal screen.
    
    A screen cell contains a single character (which may be wide or combining),
    its display attributes (colors, styles), and metadata about its state.
    
    Attributes:
        char: The character to display (default: space)
        fg_color: Foreground color (0-255 or RGB tuple)
        bg_color: Background color (0-255 or RGB tuple)
        attrs: Display attributes (bold, underline, etc.)
        dirty: Whether this cell has been modified
    """
    
    # Display attributes as bit flags
    ATTR_BOLD = 0x01
    ATTR_UNDERLINE = 0x02
    ATTR_REVERSE = 0x04
    ATTR_BLINK = 0x08
    ATTR_DIM = 0x10
    ATTR_ITALIC = 0x20
    ATTR_INVISIBLE = 0x40
    ATTR_STRIKETHROUGH = 0x80
    
    char: str = ' '
    fg_color: int = 7  # Default white
    bg_color: int = 0  # Default black
    attrs: int = 0
    dirty: bool = field(default=True, compare=False)
    
    def __post_init__(self):
        """Validate and normalize the character."""
        # Ensure we have at least one character
        if not self.char:
            self.char = ' '
        
        # Take only the first character if multiple provided
        # This handles the case where someone passes a string
        if len(self.char) > 1:
            self.char = self.char[0]
    
    @property
    def is_wide(self) -> bool:
        """
        Check if this cell contains a wide character.
        
        Wide characters (like CJK characters) take up two terminal columns.
        
        Returns:
            True if the character is wide, False otherwise
        """
        if not self.char or self.char == ' ':
            return False
        
        width = unicodedata.east_asian_width(self.char)
        return width in ('W', 'F')  # Wide or Fullwidth
    
    @property
    def width(self) -> int:
        """
        Get the display width of this cell's character.
        
        Returns:
            1 for normal characters, 2 for wide characters
        """
        return 2 if self.is_wide else 1
    
    def set_char(self, char: str) -> None:
        """
        Set the character and mark the cell as dirty.
        
        Args:
            char: The character to set
        """
        if char != self.char:
            self.char = char if char else ' '
            if len(self.char) > 1:
                self.char = self.char[0]
            self.dirty = True
    
    def set_colors(self, fg: Optional[int] = None, bg: Optional[int] = None) -> None:
        """
        Set the foreground and/or background colors.
        
        Args:
            fg: Foreground color (0-255), None to keep current
            bg: Background color (0-255), None to keep current
        """
        changed = False
        
        if fg is not None and fg != self.fg_color:
            self.fg_color = fg
            changed = True
        
        if bg is not None and bg != self.bg_color:
            self.bg_color = bg
            changed = True
        
        if changed:
            self.dirty = True
    
    def set_attr(self, attr: int, enabled: bool = True) -> None:
        """
        Enable or disable a display attribute.
        
        Args:
            attr: Attribute flag (e.g., ATTR_BOLD)
            enabled: Whether to enable or disable the attribute
        """
        old_attrs = self.attrs
        
        if enabled:
            self.attrs |= attr
        else:
            self.attrs &= ~attr
        
        if self.attrs != old_attrs:
            self.dirty = True
    
    def has_attr(self, attr: int) -> bool:
        """
        Check if a display attribute is set.
        
        Args:
            attr: Attribute flag to check
            
        Returns:
            True if the attribute is set, False otherwise
        """
        return bool(self.attrs & attr)
    
    def clear(self) -> None:
        """Reset the cell to default state."""
        self.char = ' '
        self.fg_color = 7
        self.bg_color = 0
        self.attrs = 0
        self.dirty = True
    
    def copy_from(self, other: 'ScreenCell') -> None:
        """
        Copy attributes from another cell.
        
        Args:
            other: The cell to copy from
        """
        if (self.char != other.char or 
            self.fg_color != other.fg_color or
            self.bg_color != other.bg_color or
            self.attrs != other.attrs):
            
            self.char = other.char
            self.fg_color = other.fg_color
            self.bg_color = other.bg_color
            self.attrs = other.attrs
            self.dirty = True
    
    def equals_display(self, other: 'ScreenCell') -> bool:
        """
        Check if two cells have the same display properties.
        
        This compares everything except the dirty flag.
        
        Args:
            other: The cell to compare with
            
        Returns:
            True if cells would display identically
        """
        return (self.char == other.char and
                self.fg_color == other.fg_color and
                self.bg_color == other.bg_color and
                self.attrs == other.attrs)
    
    def mark_clean(self) -> None:
        """Mark this cell as clean (not dirty)."""
        self.dirty = False
    
    def mark_dirty(self) -> None:
        """Mark this cell as dirty (needs redraw)."""
        self.dirty = True


class WideCharCell(ScreenCell):
    """
    Special cell type for the trailing part of wide characters.
    
    When a wide character is placed in the buffer, it occupies two cells.
    The first cell contains the actual character, and the second cell
    contains this special marker.
    """
    
    def __init__(self):
        """Initialize a wide character trailing cell."""
        super().__init__(char='', fg_color=0, bg_color=0, attrs=0)
        self.char = ''  # Force empty char, overriding normalization
    
    @property
    def is_wide_trail(self) -> bool:
        """This is always a wide character trail cell."""
        return True
    
    @property
    def width(self) -> int:
        """Trail cells have zero width."""
        return 0