# -*- coding: utf-8 -*-
"""
Abstract base class for display backends.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class Display(ABC):
    """Abstract base class for display backends."""
    
    def __init__(self):
        """Initialize display backend."""
        self._initialized = False
        self._width = 0
        self._height = 0
        self._cursor_x = 0
        self._cursor_y = 0
        self._cursor_visible = True
    
    @property
    def is_initialized(self) -> bool:
        """Check if display is initialized."""
        return self._initialized
    
    @property
    def width(self) -> int:
        """Get display width."""
        return self._width
    
    @property
    def height(self) -> int:
        """Get display height."""
        return self._height
    
    @property
    def cursor_position(self) -> Tuple[int, int]:
        """Get cursor position."""
        return (self._cursor_x, self._cursor_y)
    
    @property
    def cursor_visible(self) -> bool:
        """Get cursor visibility."""
        return self._cursor_visible
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the display backend."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the display backend."""
        pass
    
    @abstractmethod
    def get_size(self) -> Tuple[int, int]:
        """Get terminal size."""
        pass
    
    @abstractmethod
    def flush_buffer(self, buffer) -> None:
        """Flush display buffer to screen."""
        pass
    
    @abstractmethod
    def set_cursor_position(self, x: int, y: int) -> None:
        """Set cursor position."""
        pass
    
    @abstractmethod
    def set_cursor_visibility(self, visible: bool) -> None:
        """Set cursor visibility."""
        pass
    
    @abstractmethod
    def clear_screen(self) -> None:
        """Clear the screen."""
        pass
    
    @abstractmethod
    def supports_colors(self) -> bool:
        """Check if display supports colors."""
        pass
    
    @abstractmethod
    def supports_mouse(self) -> bool:
        """Check if display supports mouse."""
        pass
    
    @abstractmethod
    def get_color_count(self) -> int:
        """Get number of supported colors."""
        pass
    
    def resize(self, width: int, height: int) -> bool:
        """Resize the display."""
        if width <= 0 or height <= 0:
            return False
        
        self._width = width
        self._height = height
        return True
    
    def put_cell(self, x: int, y: int, cell) -> None:
        """Put a single cell at position."""
        if 0 <= x < self._width and 0 <= y < self._height:
            from .buffer import DisplayBuffer
            buffer = DisplayBuffer(1, 1)
            buffer.primary_buffer[0][0] = cell
            buffer.damage[0].expand(0, 1)
            self.flush_buffer(buffer)
    
    def put_text(self, x: int, y: int, text: str, attr: int = 0) -> None:
        """Put text at position."""
        if y < 0 or y >= self._height:
            return
        
        from .buffer import DisplayBuffer, ScreenCell
        length = len(text)
        if x < 0:
            text = text[-x:]
            length = len(text)
            x = 0
        
        if x >= self._width:
            return
        
        if x + length > self._width:
            text = text[:self._width - x]
        
        buffer = DisplayBuffer(self._width, 1)
        for i, char in enumerate(text):
            if x + i < self._width:
                buffer.primary_buffer[0][x + i] = ScreenCell(char, attr)
        buffer.damage[0].expand(x, x + len(text))
        
        # Position buffer at correct y coordinate
        temp_buffer = DisplayBuffer(self._width, self._height)
        temp_buffer.primary_buffer[y] = buffer.primary_buffer[0]
        temp_buffer.damage[y] = buffer.damage[0]
        self.flush_buffer(temp_buffer)
    
    def __enter__(self):
        """Context manager entry."""
        if not self.initialize():
            raise RuntimeError("Failed to initialize display")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()