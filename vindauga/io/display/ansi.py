# -*- coding: utf-8 -*-
"""
ANSI escape sequence display backend.
"""

import sys
import os
import struct
import fcntl
import termios
from typing import Tuple, Optional
from .base import Display
from .buffer import DisplayBuffer


class ANSIDisplay(Display):
    """ANSI escape sequence display backend."""
    
    def __init__(self):
        """Initialize ANSI display."""
        super().__init__()
        self.has_24bit_color = False
        self.has_256_color = False
        self._original_termios = None
    
    def initialize(self) -> bool:
        """Initialize ANSI display."""
        if self._initialized:
            return True
        
        try:
            # Save terminal settings
            if hasattr(sys.stdin, 'fileno'):
                try:
                    self._original_termios = termios.tcgetattr(sys.stdin.fileno())
                except:
                    pass
            
            # Get terminal size
            self._width, self._height = self.get_size()
            if self._width == 0 or self._height == 0:
                self._width, self._height = 80, 24
            
            # Detect color support
            self._detect_color_support()
            
            # Enter alternate screen buffer
            sys.stdout.write('\x1b[?1049h')
            # Clear screen
            sys.stdout.write('\x1b[2J')
            # Hide cursor
            sys.stdout.write('\x1b[?25l')
            # Reset attributes
            sys.stdout.write('\x1b[0m')
            sys.stdout.flush()
            
            self._initialized = True
            return True
        except Exception:
            return False
    
    def shutdown(self) -> None:
        """Shutdown ANSI display."""
        if not self._initialized:
            return
        
        try:
            # Show cursor
            sys.stdout.write('\x1b[?25h')
            # Reset attributes
            sys.stdout.write('\x1b[0m')
            # Exit alternate screen buffer
            sys.stdout.write('\x1b[?1049l')
            sys.stdout.flush()
            
            # Restore terminal settings
            if self._original_termios and hasattr(sys.stdin, 'fileno'):
                try:
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, 
                                    self._original_termios)
                except:
                    pass
        except:
            pass
        
        self._initialized = False
    
    def get_size(self) -> Tuple[int, int]:
        """Get terminal size."""
        try:
            # Try ioctl first
            if hasattr(sys.stdout, 'fileno'):
                data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b'\x00' * 8)
                rows, cols = struct.unpack('hh', data[:4])
                if rows > 0 and cols > 0:
                    return (cols, rows)
        except:
            pass
        
        # Fallback to environment variables
        try:
            cols = int(os.environ.get('COLUMNS', 80))
            rows = int(os.environ.get('LINES', 24))
            return (cols, rows)
        except:
            return (80, 24)
    
    def _detect_color_support(self) -> None:
        """Detect color support."""
        colorterm = os.environ.get('COLORTERM', '')
        term = os.environ.get('TERM', '')
        
        if colorterm in ['truecolor', '24bit']:
            self.has_24bit_color = True
            self.has_256_color = True
        elif '256color' in term:
            self.has_256_color = True
    
    def flush_buffer(self, buffer: DisplayBuffer) -> None:
        """Flush buffer to screen."""
        if not self._initialized:
            return
        
        output = []
        last_attr = -1
        
        for row in buffer.get_damaged_rows():
            damage = buffer.get_damage(row)
            if not damage:
                continue
            
            start, end = damage
            
            # Position cursor
            output.append(f'\x1b[{row + 1};{start + 1}H')
            
            # Output cells
            for col in range(start, end):
                cell = buffer.get_cell(col, row)
                if not cell:
                    continue
                
                # Handle attribute changes
                if cell.attr != last_attr:
                    output.append(self._attr_to_ansi(cell.attr))
                    last_attr = cell.attr
                
                # Output text
                if cell.text:
                    output.append(cell.text)
                else:
                    output.append(' ')
        
        if output:
            sys.stdout.write(''.join(output))
            sys.stdout.flush()
        
        buffer.commit_flush()
    
    def _attr_to_ansi(self, attr: int) -> str:
        """Convert attribute to ANSI escape sequence."""
        parts = ['\x1b[0']  # Reset
        
        # Extract colors
        fg = attr & 0x0F
        bg = (attr >> 4) & 0x0F
        
        # Handle intensity/bold
        if attr & 0x80:
            parts.append('1')  # Bold
        
        # Foreground color
        if fg < 8:
            parts.append(str(30 + fg))
        else:
            parts.append(str(90 + fg - 8))
        
        # Background color
        if bg < 8:
            parts.append(str(40 + bg))
        else:
            parts.append(str(100 + bg - 8))
        
        return ';'.join(parts) + 'm'
    
    def set_cursor_position(self, x: int, y: int) -> None:
        """Set cursor position."""
        if 0 <= x < self._width and 0 <= y < self._height:
            self._cursor_x = x
            self._cursor_y = y
            sys.stdout.write(f'\x1b[{y + 1};{x + 1}H')
            sys.stdout.flush()
    
    def set_cursor_visibility(self, visible: bool) -> None:
        """Set cursor visibility."""
        self._cursor_visible = visible
        if visible:
            sys.stdout.write('\x1b[?25h')
        else:
            sys.stdout.write('\x1b[?25l')
        sys.stdout.flush()
    
    def clear_screen(self) -> None:
        """Clear screen."""
        sys.stdout.write('\x1b[2J\x1b[H')
        sys.stdout.flush()
    
    def supports_colors(self) -> bool:
        """Check color support."""
        return True
    
    def supports_mouse(self) -> bool:
        """Check mouse support."""
        return True
    
    def get_color_count(self) -> int:
        """Get color count."""
        if self.has_24bit_color:
            return 16777216
        elif self.has_256_color:
            return 256
        else:
            return 16