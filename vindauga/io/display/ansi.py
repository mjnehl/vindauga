# -*- coding: utf-8 -*-
"""
ANSI escape sequence display backend.

This module provides an ANSI terminal display backend that uses escape
sequences to control terminal output, including colors, cursor positioning,
and screen management.
"""

import sys
import os
import struct
import fcntl
import termios
import signal
from typing import Tuple, Optional, Dict
from .base import Display
from ..display_buffer import DisplayBuffer
from ..screen_cell import ScreenCell
from ..terminal_cleanup import register_cleanup


class ANSIDisplay(Display):
    """
    ANSI escape sequence display backend.
    
    Supports:
    - 16/256/24-bit color
    - Cursor control
    - Alternate screen buffer
    - Terminal resize handling
    """
    
    # ANSI escape sequences
    ESC = '\x1b'
    CSI = ESC + '['
    
    # Screen control
    CLEAR_SCREEN = CSI + '2J'
    CLEAR_LINE = CSI + '2K'
    CLEAR_TO_EOL = CSI + 'K'
    
    # Cursor control
    CURSOR_HOME = CSI + 'H'
    CURSOR_SAVE = ESC + '7'
    CURSOR_RESTORE = ESC + '8'
    CURSOR_HIDE = CSI + '?25l'
    CURSOR_SHOW = CSI + '?25h'
    
    # Alternate screen
    ALT_SCREEN_ENTER = CSI + '?1049h'
    ALT_SCREEN_EXIT = CSI + '?1049l'
    
    # Mouse control
    MOUSE_ENABLE_X11 = CSI + '?1000h'
    MOUSE_DISABLE_X11 = CSI + '?1000l'
    MOUSE_ENABLE_SGR = CSI + '?1006h'
    MOUSE_DISABLE_SGR = CSI + '?1006l'
    
    # Attributes
    RESET_ATTRS = CSI + '0m'
    
    def __init__(self):
        """Initialize ANSI display."""
        super().__init__()
        self.stdout = sys.stdout
        self.has_24bit_color = False
        self.has_256_color = False
        self.color_cache: Dict[Tuple[int, int, int], str] = {}
        self._original_termios = None
        self._last_fg_color = -1
        self._last_bg_color = -1
        self._last_attrs = 0
        self._old_sigwinch_handler = None
        
    def initialize(self) -> bool:
        """Initialize ANSI display."""
        if self._initialized:
            return True
        
        try:
            # Save terminal settings (but don't modify them in display)
            # Terminal mode should be handled by input handler
            if hasattr(sys.stdin, 'fileno'):
                try:
                    self._original_termios = termios.tcgetattr(sys.stdin.fileno())
                except:
                    self._original_termios = None
            
            # Get terminal size
            self._width, self._height = self.get_size()
            if self._width == 0 or self._height == 0:
                self._width, self._height = 80, 24
            
            # Detect color support
            self._detect_color_support()
            
            # Set up signal handler for terminal resize
            self._setup_resize_handler()
            
            # Register cleanup handler
            register_cleanup(self.shutdown)
            
            # Initialize terminal
            self._write_sequence(self.ALT_SCREEN_ENTER)  # Enter alternate screen
            self._write_sequence(self.CLEAR_SCREEN)      # Clear screen
            self._write_sequence(self.CURSOR_HOME)       # Home cursor
            self._write_sequence(self.CURSOR_HIDE)       # Hide cursor
            self._write_sequence(self.RESET_ATTRS)       # Reset attributes
            try:
                self.stdout.flush()
            except BlockingIOError:
                pass
            
            self._initialized = True
            return True
            
        except Exception:
            return False
    
    def shutdown(self) -> None:
        """Shutdown ANSI display."""
        if not self._initialized:
            return
        
        try:
            # Disable mouse first
            self.enable_mouse(False)
            
            # Reset terminal
            self._write_sequence(self.CURSOR_SHOW)     # Show cursor
            self._write_sequence(self.RESET_ATTRS)     # Reset attributes
            self._write_sequence(self.ALT_SCREEN_EXIT) # Exit alternate screen
            try:
                self.stdout.flush()
            except BlockingIOError:
                pass
            
            # Restore terminal settings
            if self._original_termios and hasattr(sys.stdin, 'fileno'):
                try:
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN,
                                    self._original_termios)
                except:
                    pass
            
            # Restore signal handler
            if self._old_sigwinch_handler is not None:
                signal.signal(signal.SIGWINCH, self._old_sigwinch_handler)
                
        except:
            pass
        
        self._initialized = False
    
    def get_size(self) -> Tuple[int, int]:
        """Get terminal size."""
        try:
            # Try ioctl first
            if hasattr(self.stdout, 'fileno'):
                data = fcntl.ioctl(self.stdout.fileno(), termios.TIOCGWINSZ, b'\x00' * 8)
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
        """Detect color support from environment."""
        colorterm = os.environ.get('COLORTERM', '')
        term = os.environ.get('TERM', '')
        
        # Check for 24-bit color
        if colorterm in ['truecolor', '24bit']:
            self.has_24bit_color = True
            self.has_256_color = True
        # Check for 256 color
        elif '256color' in term:
            self.has_256_color = True
            self.has_24bit_color = False
        else:
            self.has_256_color = False
            self.has_24bit_color = False
    
    def _setup_resize_handler(self) -> None:
        """Set up terminal resize signal handler."""
        try:
            def handle_resize(signum, frame):
                """Handle terminal resize."""
                self._width, self._height = self.get_size()
            
            self._old_sigwinch_handler = signal.signal(signal.SIGWINCH, handle_resize)
        except:
            # Windows doesn't have SIGWINCH
            pass
    
    def _write_sequence(self, seq: str) -> None:
        """Write an escape sequence to stdout."""
        self.stdout.write(seq)
    
    def flush_buffer(self, buffer: DisplayBuffer) -> None:
        """
        Flush display buffer to screen using ANSI sequences.
        
        Optimizes output by:
        - Only updating damaged regions
        - Minimizing cursor movements
        - Caching color sequences
        - Coalescing adjacent cells with same attributes
        """
        if not self._initialized:
            return
        
        output = []
        
        # Process each damaged row
        for row_idx, damage in buffer.get_damaged_regions():
            if not damage.is_dirty:
                continue
                
            bounds = damage.get_bounds()
            if bounds is None:
                continue
                
            start, end = bounds
            
            # Position cursor at start of damaged region
            output.append(f'{self.CSI}{row_idx + 1};{start + 1}H')
            
            # Track current attributes to minimize escape sequences
            current_fg = -1
            current_bg = -1
            current_attrs = 0
            
            # Output cells in damaged region
            for col in range(start, end):
                cell = buffer.get_cell(col, row_idx)
                if not cell:
                    output.append(' ')
                    continue
                
                # Check if we need to update colors/attributes
                if (cell.fg_color != current_fg or 
                    cell.bg_color != current_bg or 
                    cell.attrs != current_attrs):
                    
                    seq = self._build_attr_sequence(cell.fg_color, cell.bg_color, cell.attrs)
                    output.append(seq)
                    current_fg = cell.fg_color
                    current_bg = cell.bg_color
                    current_attrs = cell.attrs
                
                # Output character
                output.append(cell.char)
        
        # Write all output at once for efficiency
        if output:
            try:
                self.stdout.write(''.join(output))
                self.stdout.flush()
            except BlockingIOError:
                # Handle non-blocking I/O
                pass
        
        # Clear damage tracking
        buffer.clear_damage()
    
    def _build_attr_sequence(self, fg: int, bg: int, attrs: int) -> str:
        """Build ANSI attribute sequence for colors and text attributes."""
        # Check cache first
        cache_key = (fg, bg, attrs)
        if cache_key in self.color_cache:
            return self.color_cache[cache_key]
        
        parts = []
        
        # Reset if needed
        if attrs == 0 and fg == 7 and bg == 0:
            seq = self.RESET_ATTRS
        else:
            parts.append('0')  # Reset first
            
            # Text attributes
            if attrs & ScreenCell.ATTR_BOLD:
                parts.append('1')
            if attrs & ScreenCell.ATTR_UNDERLINE:
                parts.append('4')
            if attrs & ScreenCell.ATTR_REVERSE:
                parts.append('7')
            
            # Foreground color
            if self.has_24bit_color and fg >= 16:
                # 24-bit RGB color
                r = (fg >> 16) & 0xFF
                g = (fg >> 8) & 0xFF
                b = fg & 0xFF
                parts.append(f'38;2;{r};{g};{b}')
            elif self.has_256_color and fg >= 16:
                # 256 color
                parts.append(f'38;5;{fg}')
            else:
                # 16 color
                if fg < 8:
                    parts.append(str(30 + fg))
                else:
                    parts.append(str(90 + (fg - 8)))
            
            # Background color
            if self.has_24bit_color and bg >= 16:
                # 24-bit RGB color
                r = (bg >> 16) & 0xFF
                g = (bg >> 8) & 0xFF
                b = bg & 0xFF
                parts.append(f'48;2;{r};{g};{b}')
            elif self.has_256_color and bg >= 16:
                # 256 color
                parts.append(f'48;5;{bg}')
            else:
                # 16 color
                if bg < 8:
                    parts.append(str(40 + bg))
                else:
                    parts.append(str(100 + (bg - 8)))
            
            seq = self.CSI + ';'.join(parts) + 'm'
        
        # Cache the sequence
        self.color_cache[cache_key] = seq
        return seq
    
    def set_cursor_position(self, x: int, y: int) -> None:
        """Set cursor position."""
        if 0 <= x < self._width and 0 <= y < self._height:
            self._cursor_x = x
            self._cursor_y = y
            self._write_sequence(f'{self.CSI}{y + 1};{x + 1}H')
            try:
                self.stdout.flush()
            except BlockingIOError:
                pass
    
    def set_cursor_visibility(self, visible: bool) -> None:
        """Set cursor visibility."""
        self._cursor_visible = visible
        if visible:
            self._write_sequence(self.CURSOR_SHOW)
        else:
            self._write_sequence(self.CURSOR_HIDE)
        try:
            self.stdout.flush()
        except BlockingIOError:
            pass
    
    def clear_screen(self) -> None:
        """Clear screen."""
        self._write_sequence(self.CLEAR_SCREEN)
        self._write_sequence(self.CURSOR_HOME)
        try:
            self.stdout.flush()
        except BlockingIOError:
            pass
    
    def supports_colors(self) -> bool:
        """Check color support."""
        return True
    
    def supports_mouse(self) -> bool:
        """Check mouse support."""
        # ANSI terminals generally support mouse
        return True
    
    def get_color_count(self) -> int:
        """Get number of supported colors."""
        if self.has_24bit_color:
            return 16777216
        elif self.has_256_color:
            return 256
        else:
            return 16
    
    def enable_mouse(self, enable: bool = True) -> bool:
        """Enable or disable mouse support."""
        try:
            if enable:
                # Enable SGR extended mouse protocol (supports large coordinates)
                self._write_sequence(self.MOUSE_ENABLE_SGR)
                # Also enable X11 protocol as fallback
                self._write_sequence(self.MOUSE_ENABLE_X11)
            else:
                self._write_sequence(self.MOUSE_DISABLE_SGR)
                self._write_sequence(self.MOUSE_DISABLE_X11)
            try:
                self.stdout.flush()
            except BlockingIOError:
                # Ignore if in non-blocking mode
                pass
            return True
        except:
            return False