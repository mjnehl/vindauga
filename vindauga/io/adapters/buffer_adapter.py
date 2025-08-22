"""
Buffer adapter that bridges the new DisplayBuffer with Vindauga's DrawBuffer.

This adapter provides a compatible interface for the DrawBuffer class to use
the new display buffer system while maintaining backward compatibility.
"""

import logging
from typing import Optional, List, Tuple
from ..display_buffer import DisplayBuffer
from ..screen_cell import ScreenCell

logger = logging.getLogger(__name__)


class BufferAdapter:
    """Adapts new DisplayBuffer for use with Vindauga DrawBuffer class."""
    
    def __init__(self, width: int = 80, height: int = 25):
        """
        Initialize the buffer adapter.
        
        Args:
            width: Buffer width
            height: Buffer height
        """
        self.buffer = DisplayBuffer(width, height)
        self._attr_cache = {}  # Cache for attribute lookups
        
    def moveChar(self, dst: int, ch: str, attr: int, count: int):
        """
        Move character with attribute to buffer position.
        
        Args:
            dst: Destination position (linear index)
            ch: Character to write
            attr: Attribute byte (fg/bg packed)
            count: Number of times to repeat
        """
        # Convert linear position to x,y
        width = self.buffer.width
        
        for i in range(count):
            pos = dst + i
            x = pos % width
            y = pos // width
            
            if y < self.buffer.height:
                # Unpack attribute (compatible with old format)
                fg, bg = self._unpack_attr(attr)
                cell = ScreenCell(ch, fg, bg)
                self.buffer.put_cell(x, y, cell)
    
    def moveBuf(self, dst: int, src: List, count: int):
        """
        Move buffer data to destination.
        
        Args:
            dst: Destination position (linear index)
            src: Source buffer (list of (char, attr) tuples)
            count: Number of items to copy
        """
        width = self.buffer.width
        
        for i in range(min(count, len(src))):
            pos = dst + i
            x = pos % width
            y = pos // width
            
            if y < self.buffer.height:
                if isinstance(src[i], tuple):
                    ch, attr = src[i]
                    fg, bg = self._unpack_attr(attr)
                else:
                    # Handle single character
                    ch = src[i]
                    fg, bg = 7, 0
                
                cell = ScreenCell(ch, fg, bg)
                self.buffer.put_cell(x, y, cell)
    
    def putAttribute(self, dst: int, attr: int, count: int):
        """
        Set attribute at destination positions.
        
        Args:
            dst: Destination position (linear index)
            attr: Attribute byte to set
            count: Number of positions to update
        """
        width = self.buffer.width
        fg, bg = self._unpack_attr(attr)
        
        for i in range(count):
            pos = dst + i
            x = pos % width
            y = pos // width
            
            if y < self.buffer.height:
                # Get existing character, update attributes
                cell = self.buffer.get_cell(x, y)
                if cell:
                    new_cell = ScreenCell(cell.char, fg, bg)
                else:
                    new_cell = ScreenCell(' ', fg, bg)
                self.buffer.put_cell(x, y, new_cell)
    
    def putChar(self, dst: int, ch: str):
        """
        Put single character at destination.
        
        Args:
            dst: Destination position (linear index)
            ch: Character to write
        """
        width = self.buffer.width
        x = dst % width
        y = dst // width
        
        if y < self.buffer.height:
            # Preserve existing attributes
            cell = self.buffer.get_cell(x, y)
            if cell:
                new_cell = ScreenCell(ch, cell.fg, cell.bg)
            else:
                new_cell = ScreenCell(ch, 7, 0)  # Default white on black
            self.buffer.put_cell(x, y, new_cell)
    
    def getChar(self, pos: int) -> Tuple[str, int]:
        """
        Get character and attribute at position.
        
        Args:
            pos: Linear position
            
        Returns:
            Tuple of (character, attribute)
        """
        width = self.buffer.width
        x = pos % width
        y = pos // width
        
        if y < self.buffer.height:
            cell = self.buffer.get_cell(x, y)
            if cell:
                attr = self._pack_attr(cell.fg, cell.bg)
                return (cell.char, attr)
        
        return (' ', 0)
    
    def getText(self, pos: int, length: int) -> str:
        """
        Get text from buffer.
        
        Args:
            pos: Starting position (linear index)
            length: Number of characters to get
            
        Returns:
            String of characters
        """
        width = self.buffer.width
        result = []
        
        for i in range(length):
            x = (pos + i) % width
            y = (pos + i) // width
            
            if y < self.buffer.height:
                cell = self.buffer.get_cell(x, y)
                if cell:
                    result.append(cell.char)
                else:
                    result.append(' ')
            else:
                break
        
        return ''.join(result)
    
    def _unpack_attr(self, attr: int) -> Tuple[int, int]:
        """
        Unpack attribute byte to foreground and background colors.
        
        Old format: bg << 4 | fg (for 16 colors)
        We'll map to 256 color space.
        """
        if attr in self._attr_cache:
            return self._attr_cache[attr]
        
        fg = attr & 0x0F
        bg = (attr >> 4) & 0x0F
        
        # Map 16-color to 256-color if needed
        # (keeping simple for now, can enhance later)
        self._attr_cache[attr] = (fg, bg)
        return fg, bg
    
    def _pack_attr(self, fg: int, bg: int) -> int:
        """
        Pack foreground and background colors to attribute byte.
        
        Returns old format for compatibility.
        """
        # Map 256-color back to 16-color if needed
        fg_16 = fg if fg < 16 else fg % 16
        bg_16 = bg if bg < 16 else bg % 16
        
        return (bg_16 << 4) | fg_16
    
    def resize(self, width: int, height: int):
        """Resize the buffer."""
        old_buffer = self.buffer
        self.buffer = DisplayBuffer(width, height)
        
        # Copy old content that fits
        for y in range(min(old_buffer.height, height)):
            for x in range(min(old_buffer.width, width)):
                cell = old_buffer.get_cell(x, y)
                if cell:
                    self.buffer.put_cell(x, y, cell)
    
    def clear(self):
        """Clear the buffer."""
        self.buffer.clear()
    
    def get_dirty_regions(self):
        """Get dirty regions for optimized updates."""
        return self.buffer.get_dirty_regions()
    
    def clear_dirty(self):
        """Clear dirty state."""
        self.buffer.clear_dirty()
    
    @property
    def width(self):
        """Get buffer width."""
        return self.buffer.width
    
    @property
    def height(self):
        """Get buffer height."""
        return self.buffer.height