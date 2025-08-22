# -*- coding: utf-8 -*-
"""
Fixed ANSI escape sequence input handler with proper Ctrl+C handling.

This module provides an ANSI terminal input handler that parses escape
sequences and generates input events while allowing Ctrl+C to work normally.
"""

import sys
import os
import select
import signal
import atexit
from typing import Optional, List
from enum import Enum
from .base import InputHandler


class ParserState(Enum):
    """ANSI escape parser states."""
    NORMAL = 0
    ESC = 1
    CSI = 2
    SS3 = 3


class ParsedKey:
    """Parsed key event."""
    def __init__(self, key: str, ctrl: bool = False, alt: bool = False, shift: bool = False):
        self.key = key
        self.ctrl = ctrl
        self.alt = alt
        self.shift = shift


class MouseEvent:
    """Mouse event."""
    def __init__(self, x: int, y: int, button: int, action: str):
        self.x = x
        self.y = y
        self.button = button
        self.action = action


class ANSIEscapeParser:
    """
    ANSI escape sequence parser.
    
    Parses ANSI escape sequences and generates events.
    """
    
    def __init__(self, allow_ctrl_c: bool = True):
        """
        Initialize parser.
        
        Args:
            allow_ctrl_c: If True, Ctrl+C triggers SIGINT instead of being captured
        """
        self.state = ParserState.NORMAL
        self.sequence_buffer = bytearray()
        self.sequence_params = []
        self.allow_ctrl_c = allow_ctrl_c
    
    def reset(self):
        """Reset parser state."""
        self.state = ParserState.NORMAL
        self.sequence_buffer.clear()
        self.sequence_params.clear()
    
    def parse_byte(self, byte: int) -> Optional[object]:
        """
        Parse a single byte.
        
        Args:
            byte: Input byte
            
        Returns:
            Parsed event or None
        """
        if self.state == ParserState.NORMAL:
            return self._parse_normal(byte)
        elif self.state == ParserState.ESC:
            return self._parse_esc(byte)
        elif self.state == ParserState.CSI:
            return self._parse_csi(byte)
        elif self.state == ParserState.SS3:
            return self._parse_ss3(byte)
        else:
            # Unknown state, reset
            self.reset()
            return None
    
    def _parse_normal(self, byte: int) -> Optional[ParsedKey]:
        """Parse normal state byte."""
        if byte == 0x1B:  # ESC
            self.state = ParserState.ESC
            return None
        elif byte < 0x20:  # Control character
            # When allow_ctrl_c is True and ISIG is enabled,
            # Ctrl+C (0x03) will be handled by the terminal and won't reach here.
            # But if it does somehow, we should not process it.
            if byte == 0x03 and self.allow_ctrl_c:
                # Don't process Ctrl+C when it should trigger SIGINT
                return None
            
            # Handle other control characters
            if byte == 0x09:  # Tab
                return ParsedKey('Tab')
            elif byte == 0x0D:  # Enter
                return ParsedKey('Enter')
            elif byte == 0x08 or byte == 0x7F:  # Backspace
                return ParsedKey('Backspace')
            elif 0x01 <= byte <= 0x1A:  # Ctrl+A through Ctrl+Z
                return ParsedKey(chr(byte + 0x40), ctrl=True)
            else:
                return None
        else:
            # Regular character
            try:
                char = chr(byte)
                return ParsedKey(char)
            except:
                return None
    
    def _parse_esc(self, byte: int) -> Optional[object]:
        """Parse ESC state byte."""
        if byte == ord('['):  # CSI
            self.state = ParserState.CSI
            self.sequence_buffer.clear()
            self.sequence_params.clear()
            return None
        elif byte == ord('O'):  # SS3
            self.state = ParserState.SS3
            return None
        else:
            # Alt+key combination
            self.reset()
            if byte < 0x80:
                return ParsedKey(chr(byte), alt=True)
            return None
    
    def _parse_csi(self, byte: int) -> Optional[object]:
        """Parse CSI state byte."""
        if 0x30 <= byte <= 0x3F:  # Parameter byte
            self.sequence_buffer.append(byte)
            return None
        elif 0x40 <= byte <= 0x7E:  # Final byte
            # Parse sequence
            result = self._parse_csi_sequence(byte)
            self.reset()
            return result
        else:
            # Invalid sequence
            self.reset()
            return None
    
    def _parse_ss3(self, byte: int) -> Optional[ParsedKey]:
        """Parse SS3 state byte."""
        self.reset()
        
        # Function keys
        key_map = {
            ord('P'): 'F1',
            ord('Q'): 'F2',
            ord('R'): 'F3',
            ord('S'): 'F4',
        }
        
        if byte in key_map:
            return ParsedKey(key_map[byte])
        
        return None
    
    def _parse_csi_sequence(self, final: int) -> Optional[object]:
        """Parse complete CSI sequence."""
        # Parse parameters
        params = []
        if self.sequence_buffer:
            param_str = self.sequence_buffer.decode('ascii', errors='ignore')
            for p in param_str.split(';'):
                try:
                    params.append(int(p))
                except:
                    params.append(0)
        
        # Handle different sequences
        if final == ord('~'):
            # Special keys
            if params:
                key_map = {
                    1: 'Home', 2: 'Insert', 3: 'Delete', 4: 'End',
                    5: 'PageUp', 6: 'PageDown',
                    15: 'F5', 17: 'F6', 18: 'F7', 19: 'F8',
                    20: 'F9', 21: 'F10', 23: 'F11', 24: 'F12',
                }
                if params[0] in key_map:
                    return ParsedKey(key_map[params[0]])
        
        elif final == ord('A'):
            return ParsedKey('Up')
        elif final == ord('B'):
            return ParsedKey('Down')
        elif final == ord('C'):
            return ParsedKey('Right')
        elif final == ord('D'):
            return ParsedKey('Left')
        
        elif final == ord('M') or final == ord('m'):
            # Mouse event
            if len(params) >= 3:
                button = params[0] if params else 0
                x = params[1] - 1 if len(params) > 1 else 0
                y = params[2] - 1 if len(params) > 2 else 0
                
                # Determine action
                if final == ord('M'):
                    action = 'press'
                else:
                    action = 'release'
                
                return MouseEvent(x, y, button, action)
        
        return None


class ANSIInput(InputHandler):
    """
    ANSI terminal input handler with improved Ctrl+C handling.
    
    Features:
    - Configurable Ctrl+C behavior (passthrough or capture)
    - Proper cleanup on exit
    - Terminal state restoration
    """
    
    def __init__(self, allow_ctrl_c: bool = True):
        """
        Initialize ANSI input handler.
        
        Args:
            allow_ctrl_c: If True, Ctrl+C triggers SIGINT normally
        """
        super().__init__()
        self.stdin = sys.stdin
        self.stdin_fd = None
        self.parser = ANSIEscapeParser(allow_ctrl_c=allow_ctrl_c)
        self.event_queue: List[object] = []
        self._initialized = False
        self.original_termios = None
        self.allow_ctrl_c = allow_ctrl_c
        self._cleanup_registered = False
    
    def _cleanup(self):
        """Internal cleanup method for atexit."""
        if self._initialized:
            self.shutdown()
    
    def initialize(self) -> bool:
        """Initialize input handler with improved cleanup."""
        if self._initialized:
            return True
        
        try:
            # Get stdin file descriptor
            if hasattr(self.stdin, 'fileno'):
                self.stdin_fd = self.stdin.fileno()
            else:
                return False
            
            # Save original terminal settings
            import termios
            import tty
            try:
                self.original_termios = termios.tcgetattr(self.stdin_fd)
                
                # Configure terminal mode based on Ctrl+C handling
                if self.allow_ctrl_c:
                    # Custom mode: disable echo but keep ISIG for signals
                    new_termios = termios.tcgetattr(self.stdin_fd)
                    # Disable echo and canonical mode
                    new_termios[3] &= ~(termios.ECHO | termios.ICANON)
                    # Keep ISIG enabled for signal handling
                    new_termios[3] |= termios.ISIG
                    # Set VMIN and VTIME for non-blocking read
                    new_termios[6][termios.VMIN] = 0
                    new_termios[6][termios.VTIME] = 0
                    termios.tcsetattr(self.stdin_fd, termios.TCSANOW, new_termios)
                else:
                    # Use raw mode - captures everything including Ctrl+C
                    tty.setraw(self.stdin_fd)
                    
            except:
                self.original_termios = None
            
            # Set non-blocking mode
            import fcntl
            flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            # Register cleanup handler
            if not self._cleanup_registered:
                atexit.register(self._cleanup)
                self._cleanup_registered = True
            
            self._initialized = True
            return True
            
        except:
            return False
    
    def shutdown(self) -> None:
        """Shutdown input handler with thorough cleanup."""
        if not self._initialized:
            return
        
        try:
            # Restore original terminal settings
            if self.original_termios and self.stdin_fd is not None:
                import termios
                try:
                    termios.tcsetattr(self.stdin_fd, termios.TCSADRAIN, self.original_termios)
                except:
                    # Try immediate if drain fails
                    try:
                        termios.tcsetattr(self.stdin_fd, termios.TCSANOW, self.original_termios)
                    except:
                        pass
            
            # Restore blocking mode
            if self.stdin_fd is not None:
                import fcntl
                try:
                    flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
                    fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
                except:
                    pass
                    
        except:
            pass
        
        self._initialized = False
    
    def get_event(self, timeout: float = 0.0) -> Optional[object]:
        """
        Get next event with optional timeout.
        
        Args:
            timeout: Timeout in seconds (0 = non-blocking, -1 = blocking)
            
        Returns:
            Event object or None
        """
        if not self._initialized:
            return None
        
        # Check queued events first
        if self.event_queue:
            return self.event_queue.pop(0)
        
        # Read available input
        if timeout < 0:
            # Blocking read
            ready = True
        elif timeout == 0:
            # Non-blocking check
            ready, _, _ = select.select([self.stdin_fd], [], [], 0)
        else:
            # Timed wait
            ready, _, _ = select.select([self.stdin_fd], [], [], timeout)
        
        if not ready:
            return None
        
        # Read available bytes
        try:
            data = os.read(self.stdin_fd, 4096)
            if not data:
                return None
        except (OSError, IOError):
            return None
        
        # Parse input bytes
        for byte in data:
            result = self.parser.parse_byte(byte)
            if result:
                # Convert parsed result to event
                event = self._convert_to_event(result)
                if event:
                    self.event_queue.append(event)
        
        # Return first event if available
        if self.event_queue:
            return self.event_queue.pop(0)
        
        return None
    
    def _convert_to_event(self, parsed: object) -> Optional[object]:
        """Convert parsed result to event object."""
        # For now, just return the parsed object
        # In a full implementation, this would convert to a common event type
        return parsed
    
    def supports_mouse(self) -> bool:
        """Check if mouse is supported."""
        return True
    
    def has_events(self) -> bool:
        """Check if events are available."""
        if not self._initialized:
            return False
        
        # Check queued events
        if self.event_queue:
            return True
        
        # Check for available input
        if self.stdin_fd is not None:
            ready, _, _ = select.select([self.stdin_fd], [], [], 0)
            return bool(ready)
        
        return False
    
    def enable_mouse(self, enable: bool = True) -> bool:
        """Enable or disable mouse events."""
        if not self._initialized:
            return False
        
        self._mouse_enabled = enable
        # Mouse enable/disable is handled by the display backend
        return True
    
    def flush_input(self) -> None:
        """Flush input buffer."""
        if not self._initialized:
            return
        
        # Clear event queue
        self.event_queue.clear()
        
        # Read and discard available input
        if self.stdin_fd is not None:
            while True:
                ready, _, _ = select.select([self.stdin_fd], [], [], 0)
                if not ready:
                    break
                try:
                    os.read(self.stdin_fd, 4096)
                except:
                    break
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.shutdown()