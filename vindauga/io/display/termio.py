# -*- coding: utf-8 -*-
"""
TermIO display backend using Linux/Unix terminal I/O.
"""

import sys
import os
import struct
import fcntl
import termios
import signal
from typing import Tuple
from .base import Display
from .buffer import DisplayBuffer


class TermIODisplay(Display):
    """TermIO display backend."""
    
    def __init__(self):
        """Initialize TermIO display."""
        super().__init__()
        self.tty_fd = None
        self.original_termios = None
        self._resize_pending = False
    
    def initialize(self) -> bool:
        """Initialize TermIO display."""
        if self._initialized:
            return True
        
        try:
            # Check if stdout is a TTY
            if not os.isatty(sys.stdout.fileno()):
                return False
            
            self.tty_fd = sys.stdout.fileno()
            
            # Save terminal settings
            self.original_termios = termios.tcgetattr(self.tty_fd)
            
            # Enter raw mode
            self._enter_raw_mode()
            
            # Setup signal handlers
            self._setup_signals()
            
            # Get terminal size
            self._width, self._height = self.get_size()
            
            # Initialize screen
            os.write(self.tty_fd, b'\x1b[?1049h')  # Alternate screen
            os.write(self.tty_fd, b'\x1b[2J')      # Clear screen
            os.write(self.tty_fd, b'\x1b[?25l')    # Hide cursor
            
            self._initialized = True
            return True
        except Exception:
            return False
    
    def shutdown(self) -> None:
        """Shutdown TermIO display."""
        if not self._initialized:
            return
        
        try:
            # Restore screen
            os.write(self.tty_fd, b'\x1b[?25h')    # Show cursor
            os.write(self.tty_fd, b'\x1b[0m')      # Reset attributes
            os.write(self.tty_fd, b'\x1b[?1049l')  # Exit alternate screen
            
            # Restore terminal settings
            if self.original_termios:
                termios.tcsetattr(self.tty_fd, termios.TCSADRAIN, self.original_termios)
            
            # Remove signal handlers
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)
        except:
            pass
        
        self._initialized = False
    
    def _enter_raw_mode(self) -> None:
        """Enter raw terminal mode."""
        new_termios = termios.tcgetattr(self.tty_fd)
        
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
                           termios.ICANON | termios.ISIG | termios.IEXTEN)
        
        # Control characters
        new_termios[6][termios.VMIN] = 1
        new_termios[6][termios.VTIME] = 0
        
        termios.tcsetattr(self.tty_fd, termios.TCSAFLUSH, new_termios)
    
    def _setup_signals(self) -> None:
        """Setup signal handlers."""
        signal.signal(signal.SIGWINCH, self._handle_sigwinch)
    
    def _handle_sigwinch(self, signum, frame) -> None:
        """Handle terminal resize signal."""
        self._resize_pending = True
    
    def get_size(self) -> Tuple[int, int]:
        """Get terminal size."""
        if self._resize_pending:
            self._resize_pending = False
        
        try:
            data = fcntl.ioctl(self.tty_fd if self.tty_fd else sys.stdout.fileno(),
                             termios.TIOCGWINSZ, b'\x00' * 8)
            rows, cols = struct.unpack('hh', data[:4])
            if rows > 0 and cols > 0:
                self._width = cols
                self._height = rows
                return (cols, rows)
        except:
            pass
        
        return (self._width or 80, self._height or 24)
    
    def flush_buffer(self, buffer: DisplayBuffer) -> None:
        """Flush buffer to screen."""
        if not self._initialized:
            return
        
        output = bytearray()
        last_attr = -1
        
        for row in buffer.get_damaged_rows():
            damage = buffer.get_damage(row)
            if not damage:
                continue
            
            start, end = damage
            
            # Position cursor
            output.extend(f'\x1b[{row + 1};{start + 1}H'.encode('utf-8'))
            
            # Output cells
            for col in range(start, end):
                cell = buffer.get_cell(col, row)
                if not cell:
                    continue
                
                # Handle attribute changes
                if cell.attr != last_attr:
                    output.extend(self._attr_to_ansi(cell.attr))
                    last_attr = cell.attr
                
                # Output text
                if cell.text:
                    output.extend(cell.text.encode('utf-8'))
                else:
                    output.extend(b' ')
        
        if output:
            os.write(self.tty_fd, output)
        
        buffer.commit_flush()
    
    def _attr_to_ansi(self, attr: int) -> bytes:
        """Convert attribute to ANSI escape sequence."""
        parts = [b'\x1b[0']  # Reset
        
        # Extract colors
        fg = attr & 0x0F
        bg = (attr >> 4) & 0x0F
        
        # Handle intensity/bold
        if attr & 0x80:
            parts.append(b'1')  # Bold
        
        # Foreground color
        if fg < 8:
            parts.append(str(30 + fg).encode())
        else:
            parts.append(str(90 + fg - 8).encode())
        
        # Background color
        if bg < 8:
            parts.append(str(40 + bg).encode())
        else:
            parts.append(str(100 + bg - 8).encode())
        
        return b';'.join(parts) + b'm'
    
    def set_cursor_position(self, x: int, y: int) -> None:
        """Set cursor position."""
        if 0 <= x < self._width and 0 <= y < self._height:
            self._cursor_x = x
            self._cursor_y = y
            os.write(self.tty_fd, f'\x1b[{y + 1};{x + 1}H'.encode())
    
    def set_cursor_visibility(self, visible: bool) -> None:
        """Set cursor visibility."""
        self._cursor_visible = visible
        if visible:
            os.write(self.tty_fd, b'\x1b[?25h')
        else:
            os.write(self.tty_fd, b'\x1b[?25l')
    
    def clear_screen(self) -> None:
        """Clear screen."""
        os.write(self.tty_fd, b'\x1b[2J\x1b[H')
    
    def supports_colors(self) -> bool:
        """Check color support."""
        term = os.environ.get('TERM', '')
        return term != 'dumb'
    
    def supports_mouse(self) -> bool:
        """Check mouse support."""
        return True
    
    def get_color_count(self) -> int:
        """Get color count."""
        term = os.environ.get('TERM', '')
        colorterm = os.environ.get('COLORTERM', '')
        
        if colorterm in ['truecolor', '24bit']:
            return 16777216
        elif '256color' in term:
            return 256
        elif term != 'dumb':
            return 16
        else:
            return 0