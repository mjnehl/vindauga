# -*- coding: utf-8 -*-
"""
Fixed TermIO display backend with macOS compatibility.

This version works on both Linux and macOS by handling platform
differences in termios.
"""

import sys
import os
import struct
import fcntl
import termios
import signal
import platform
from typing import Tuple
from .base import Display
from ..display_buffer import DisplayBuffer
from ..screen_cell import ScreenCell


class FixedTermIODisplay(Display):
    """
    Fixed TermIO display backend with macOS support.
    
    Handles platform differences in termios between Linux and macOS.
    """
    
    def __init__(self):
        """Initialize TermIO display."""
        super().__init__()
        self.tty_fd = None
        self.original_termios = None
        self._resize_pending = False
        self.is_macos = platform.system() == 'Darwin'
        
    def initialize(self) -> bool:
        """Initialize TermIO display with platform compatibility."""
        if self._initialized:
            return True
        
        try:
            # Check if stdout is a TTY
            if not os.isatty(sys.stdout.fileno()):
                return False
            
            self.tty_fd = sys.stdout.fileno()
            
            # Save terminal settings
            self.original_termios = termios.tcgetattr(self.tty_fd)
            
            # Enter raw mode (platform-aware)
            if not self._enter_raw_mode():
                return False
            
            # Setup signal handlers
            self._setup_signals()
            
            # Get terminal size
            self._width, self._height = self.get_size()
            
            # Initialize terminal
            self._init_terminal()
            
            self._initialized = True
            return True
            
        except Exception as e:
            # Restore if initialization fails
            if self.original_termios:
                try:
                    termios.tcsetattr(self.tty_fd, termios.TCSADRAIN, self.original_termios)
                except:
                    pass
            return False
    
    def shutdown(self) -> None:
        """Shutdown TermIO display."""
        if not self._initialized:
            return
        
        try:
            # Restore screen
            sequences = [
                b'\x1b[?25h',    # Show cursor
                b'\x1b[0m',      # Reset attributes
                b'\x1b[?1049l',  # Exit alternate screen
                b'\x1b[?1000l',  # Disable mouse
                b'\x1b[?1006l',  # Disable SGR mouse
            ]
            
            for seq in sequences:
                try:
                    os.write(self.tty_fd, seq)
                except:
                    pass
            
            # Restore terminal settings
            if self.original_termios:
                termios.tcsetattr(self.tty_fd, termios.TCSADRAIN, self.original_termios)
            
            # Remove signal handlers
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)
            
        except:
            pass
        
        self._initialized = False
    
    def _enter_raw_mode(self) -> bool:
        """Enter raw terminal mode with platform compatibility."""
        try:
            new_termios = termios.tcgetattr(self.tty_fd)
            
            if self.is_macos:
                # macOS-compatible raw mode
                # Use simpler approach that works on Darwin
                import tty
                # Get raw mode settings
                tty.setraw(self.tty_fd)
                # But restore and modify manually for more control
                new_termios = termios.tcgetattr(self.tty_fd)
                
                # Restore original first
                termios.tcsetattr(self.tty_fd, termios.TCSANOW, self.original_termios)
                
                # Now apply selective changes
                # Disable echo and canonical mode
                new_termios[3] &= ~(termios.ECHO | termios.ICANON)
                
                # Disable signals (optional, keep if you want Ctrl+C)
                # new_termios[3] &= ~termios.ISIG
                
                # Set minimum characters and timeout
                new_termios[6][termios.VMIN] = 1
                new_termios[6][termios.VTIME] = 0
                
            else:
                # Linux raw mode (original implementation)
                # Input flags
                new_termios[0] &= ~(termios.IGNBRK | termios.BRKINT | 
                                   termios.PARMRK | termios.ISTRIP |
                                   termios.INLCR | termios.IGNCR | 
                                   termios.ICRNL | termios.IXON)
                
                # Output flags
                new_termios[1] &= ~termios.OPOST
                
                # Control flags
                new_termios[2] &= ~(termios.CSIZE | termios.PARENB)
                new_termios[2] |= termios.CS8
                
                # Local flags
                new_termios[3] &= ~(termios.ECHO | termios.ECHONL | 
                                   termios.ICANON | termios.ISIG | 
                                   termios.IEXTEN)
                
                # Control characters
                new_termios[6][termios.VMIN] = 1
                new_termios[6][termios.VTIME] = 0
            
            # Apply settings
            termios.tcsetattr(self.tty_fd, termios.TCSANOW, new_termios)
            return True
            
        except Exception as e:
            return False
    
    def _setup_signals(self) -> None:
        """Setup signal handlers."""
        def handle_resize(signum, frame):
            self._resize_pending = True
            self._width, self._height = self.get_size()
        
        try:
            signal.signal(signal.SIGWINCH, handle_resize)
        except:
            # SIGWINCH may not be available on all platforms
            pass
    
    def _init_terminal(self) -> None:
        """Initialize terminal for display."""
        sequences = [
            b'\x1b[?1049h',  # Enter alternate screen
            b'\x1b[2J',      # Clear screen
            b'\x1b[H',       # Home cursor
            b'\x1b[?25l',    # Hide cursor
            b'\x1b[0m',      # Reset attributes
        ]
        
        for seq in sequences:
            try:
                os.write(self.tty_fd, seq)
            except:
                pass
    
    def get_size(self) -> Tuple[int, int]:
        """Get terminal size."""
        try:
            # Try ioctl first (works on both Linux and macOS)
            data = fcntl.ioctl(self.tty_fd, termios.TIOCGWINSZ, b'\x00' * 8)
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
    
    def flush_buffer(self, buffer: DisplayBuffer) -> None:
        """Flush display buffer to screen."""
        if not self._initialized:
            return
        
        # Build output string
        output = []
        
        for row_idx, damage in buffer.get_damaged_regions():
            if not damage.is_dirty:
                continue
            
            bounds = damage.get_bounds()
            if bounds is None:
                continue
            
            start, end = bounds
            
            # Position cursor
            output.append(f'\x1b[{row_idx + 1};{start + 1}H')
            
            # Output cells
            current_attrs = (7, 0, 0)  # fg, bg, attrs
            
            for col in range(start, end):
                cell = buffer.get_cell(col, row_idx)
                if not cell:
                    output.append(' ')
                    continue
                
                # Check if attributes changed
                new_attrs = (cell.fg_color, cell.bg_color, cell.attrs)
                if new_attrs != current_attrs:
                    # Build attribute sequence
                    attr_seq = self._build_attr_sequence(
                        cell.fg_color, cell.bg_color, cell.attrs
                    )
                    output.append(attr_seq)
                    current_attrs = new_attrs
                
                output.append(cell.char)
        
        # Write output
        if output:
            try:
                output_bytes = ''.join(output).encode('utf-8', errors='replace')
                os.write(self.tty_fd, output_bytes)
            except:
                pass
        
        # Clear damage tracking
        buffer.clear_damage()
    
    def _build_attr_sequence(self, fg: int, bg: int, attrs: int) -> str:
        """Build attribute escape sequence."""
        parts = ['0']  # Reset first
        
        # Attributes
        if attrs & ScreenCell.ATTR_BOLD:
            parts.append('1')
        if attrs & ScreenCell.ATTR_UNDERLINE:
            parts.append('4')
        if attrs & ScreenCell.ATTR_REVERSE:
            parts.append('7')
        
        # Foreground color
        if fg < 8:
            parts.append(str(30 + fg))
        elif fg < 16:
            parts.append(str(90 + (fg - 8)))
        else:
            # 256 color
            parts.append(f'38;5;{fg}')
        
        # Background color
        if bg < 8:
            parts.append(str(40 + bg))
        elif bg < 16:
            parts.append(str(100 + (bg - 8)))
        else:
            # 256 color
            parts.append(f'48;5;{bg}')
        
        return f"\x1b[{';'.join(parts)}m"
    
    def set_cursor_position(self, x: int, y: int) -> None:
        """Set cursor position."""
        if 0 <= x < self._width and 0 <= y < self._height:
            self._cursor_x = x
            self._cursor_y = y
            seq = f'\x1b[{y + 1};{x + 1}H'.encode('utf-8')
            try:
                os.write(self.tty_fd, seq)
            except:
                pass
    
    def set_cursor_visibility(self, visible: bool) -> None:
        """Set cursor visibility."""
        self._cursor_visible = visible
        seq = b'\x1b[?25h' if visible else b'\x1b[?25l'
        try:
            os.write(self.tty_fd, seq)
        except:
            pass
    
    def clear_screen(self) -> None:
        """Clear screen."""
        sequences = [b'\x1b[2J', b'\x1b[H']
        for seq in sequences:
            try:
                os.write(self.tty_fd, seq)
            except:
                pass
    
    def supports_colors(self) -> bool:
        """Check color support."""
        return True
    
    def supports_mouse(self) -> bool:
        """Check mouse support."""
        return True
    
    def get_color_count(self) -> int:
        """Get number of supported colors."""
        # Check environment for color support
        term = os.environ.get('TERM', '')
        if '256color' in term:
            return 256
        elif 'color' in term:
            return 16
        return 8
    
    def enable_mouse(self, enable: bool = True) -> bool:
        """Enable or disable mouse support."""
        try:
            if enable:
                # Enable mouse reporting
                os.write(self.tty_fd, b'\x1b[?1000h')  # X11 mouse
                os.write(self.tty_fd, b'\x1b[?1006h')  # SGR mouse
            else:
                # Disable mouse reporting
                os.write(self.tty_fd, b'\x1b[?1000l')
                os.write(self.tty_fd, b'\x1b[?1006l')
            return True
        except:
            return False