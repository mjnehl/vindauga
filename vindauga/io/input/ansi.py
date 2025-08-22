# -*- coding: utf-8 -*-
"""
ANSI input handler for terminal input processing.

This module handles keyboard and mouse input from ANSI terminals,
including escape sequence parsing and event generation.
"""

import sys
import select
import time
import os
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum, auto
from .base import InputHandler


class ParserState(Enum):
    """ANSI escape sequence parser states."""
    NORMAL = auto()
    ESC = auto()
    CSI = auto()
    SS3 = auto()
    DCS = auto()
    OSC = auto()


@dataclass
class ParsedKey:
    """Parsed keyboard event."""
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    

@dataclass
class ParsedMouse:
    """Parsed mouse event."""
    x: int
    y: int
    button: int
    action: str  # 'press', 'release', 'move', 'wheel'
    ctrl: bool = False
    alt: bool = False
    shift: bool = False


class ANSIEscapeParser:
    """
    ANSI escape sequence parser.
    
    Handles parsing of:
    - Single characters
    - Control sequences (CSI)
    - SS3 sequences (function keys)
    - Mouse events (X11, SGR protocols)
    """
    
    def __init__(self):
        """Initialize parser."""
        self.state = ParserState.NORMAL
        self.sequence_buffer = bytearray()
        self.sequence_params = []
        self.intermediate = ''
        
        # Build key mappings
        self._build_key_maps()
    
    def _build_key_maps(self):
        """Build key code mappings."""
        # CSI sequences (with optional modifiers)
        self.csi_keys = {
            'A': 'Up',
            'B': 'Down',
            'C': 'Right',
            'D': 'Left',
            'H': 'Home',
            'F': 'End',
            '2~': 'Insert',
            '3~': 'Delete',
            '5~': 'PageUp',
            '6~': 'PageDown',
            '11~': 'F1',
            '12~': 'F2',
            '13~': 'F3',
            '14~': 'F4',
            '15~': 'F5',
            '17~': 'F6',
            '18~': 'F7',
            '19~': 'F8',
            '20~': 'F9',
            '21~': 'F10',
            '23~': 'F11',
            '24~': 'F12',
        }
        
        # SS3 sequences (numpad/function keys)
        self.ss3_keys = {
            'P': 'F1',
            'Q': 'F2',
            'R': 'F3',
            'S': 'F4',
        }
    
    def reset(self):
        """Reset parser state."""
        self.state = ParserState.NORMAL
        self.sequence_buffer.clear()
        self.sequence_params.clear()
        self.intermediate = ''
    
    def parse_byte(self, byte: int) -> Optional[object]:
        """
        Parse a single byte.
        
        Returns:
            ParsedKey, ParsedMouse, or None if sequence incomplete
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
            # Unsupported sequence, reset
            self.reset()
            return None
    
    def _parse_normal(self, byte: int) -> Optional[ParsedKey]:
        """Parse normal state byte."""
        if byte == 0x1B:  # ESC
            self.state = ParserState.ESC
            return None
        elif byte < 0x20:  # Control character
            # Handle common control characters
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
        elif 0x20 <= byte <= 0x2F:  # Intermediate byte
            self.intermediate = chr(byte)
            return None
        elif 0x40 <= byte <= 0x7E:  # Final byte
            # Parse parameters
            params_str = self.sequence_buffer.decode('ascii', errors='ignore')
            if params_str:
                self.sequence_params = params_str.split(';')
            else:
                self.sequence_params = []
            
            # Check for mouse event
            if chr(byte) == 'M' and len(self.sequence_params) >= 3:
                return self._parse_x11_mouse()
            elif chr(byte) == '<' and self.intermediate:
                return self._parse_sgr_mouse(chr(byte))
            
            # Parse key event
            return self._parse_csi_key(chr(byte))
        else:
            # Invalid sequence
            self.reset()
            return None
    
    def _parse_ss3(self, byte: int) -> Optional[ParsedKey]:
        """Parse SS3 state byte."""
        self.reset()
        key_char = chr(byte)
        if key_char in self.ss3_keys:
            return ParsedKey(self.ss3_keys[key_char])
        return None
    
    def _parse_csi_key(self, final_char: str) -> Optional[ParsedKey]:
        """Parse CSI key sequence."""
        # Build full sequence
        if self.sequence_params:
            seq = self.sequence_params[0] + final_char
        else:
            seq = final_char
        
        # Check for known key
        if seq in self.csi_keys:
            key_name = self.csi_keys[seq]
            
            # Check for modifiers
            ctrl = False
            alt = False
            shift = False
            
            if len(self.sequence_params) >= 2:
                modifier = int(self.sequence_params[1]) if self.sequence_params[1] else 1
                # Modifier encoding: 1=none, 2=shift, 3=alt, 4=shift+alt, 
                #                   5=ctrl, 6=shift+ctrl, 7=alt+ctrl, 8=shift+alt+ctrl
                shift = (modifier - 1) & 1 != 0
                alt = (modifier - 1) & 2 != 0
                ctrl = (modifier - 1) & 4 != 0
            
            self.reset()
            return ParsedKey(key_name, ctrl=ctrl, alt=alt, shift=shift)
        
        self.reset()
        return None
    
    def _parse_x11_mouse(self) -> Optional[ParsedMouse]:
        """Parse X11 mouse protocol event."""
        if len(self.sequence_params) < 3:
            self.reset()
            return None
        
        try:
            button_code = int(self.sequence_params[0])
            x = int(self.sequence_params[1]) - 1  # Convert to 0-based
            y = int(self.sequence_params[2]) - 1
            
            # Decode button and modifiers
            button = button_code & 0x03
            shift = (button_code & 0x04) != 0
            alt = (button_code & 0x08) != 0
            ctrl = (button_code & 0x10) != 0
            
            # Determine action
            if button_code & 0x20:
                action = 'move'
            elif button_code & 0x40:
                action = 'wheel'
            else:
                action = 'press'  # X11 doesn't distinguish press/release
            
            self.reset()
            return ParsedMouse(x, y, button, action, ctrl=ctrl, alt=alt, shift=shift)
            
        except:
            self.reset()
            return None
    
    def _parse_sgr_mouse(self, final_char: str) -> Optional[ParsedMouse]:
        """Parse SGR mouse protocol event."""
        if len(self.sequence_params) < 3:
            self.reset()
            return None
        
        try:
            button_code = int(self.sequence_params[0])
            x = int(self.sequence_params[1]) - 1  # Convert to 0-based
            y = int(self.sequence_params[2]) - 1
            
            # Decode button and modifiers
            button = button_code & 0x03
            shift = (button_code & 0x04) != 0
            alt = (button_code & 0x08) != 0
            ctrl = (button_code & 0x10) != 0
            
            # Determine action based on final character
            if final_char == 'M':
                action = 'press'
            elif final_char == 'm':
                action = 'release'
            else:
                action = 'move'
            
            # Check for wheel events
            if button_code >= 64:
                action = 'wheel'
                button = 4 if button_code == 64 else 5  # Wheel up/down
            
            self.reset()
            return ParsedMouse(x, y, button, action, ctrl=ctrl, alt=alt, shift=shift)
            
        except:
            self.reset()
            return None


class ANSIInput(InputHandler):
    """
    ANSI terminal input handler.
    
    Handles:
    - Keyboard input with modifiers
    - Mouse events (X11, SGR protocols)
    - Non-blocking input with timeouts
    - UTF-8 character input
    """
    
    def __init__(self):
        """Initialize ANSI input handler."""
        super().__init__()
        self.stdin = sys.stdin
        self.stdin_fd = None
        self.parser = ANSIEscapeParser()
        self.input_buffer = bytearray()
        self.event_queue = []
        self.utf8_buffer = bytearray()
        self.original_termios = None
        
    def initialize(self) -> bool:
        """Initialize input handler."""
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
                # Set terminal to raw mode to prevent echo
                tty.setraw(self.stdin_fd)
            except:
                self.original_termios = None
            
            # Set non-blocking mode
            import fcntl
            flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            self._initialized = True
            return True
            
        except:
            return False
    
    def shutdown(self) -> None:
        """Shutdown input handler."""
        if not self._initialized:
            return
        
        try:
            # Restore original terminal settings
            if hasattr(self, 'original_termios') and self.original_termios and self.stdin_fd is not None:
                import termios
                termios.tcsetattr(self.stdin_fd, termios.TCSADRAIN, self.original_termios)
            
            # Restore blocking mode
            if self.stdin_fd is not None:
                import fcntl
                flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
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
    
    def has_events(self) -> bool:
        """Check if events are available."""
        if self.event_queue:
            return True
        
        # Check for available input
        if self.stdin_fd:
            ready, _, _ = select.select([self.stdin_fd], [], [], 0)
            return bool(ready)
        
        return False
    
    def enable_mouse(self, enable: bool = True) -> bool:
        """Enable or disable mouse events."""
        # Mouse enabling is handled by the display backend
        self._mouse_enabled = enable
        return True
    
    def supports_mouse(self) -> bool:
        """Check if mouse is supported."""
        return True
    
    def flush_input(self) -> None:
        """Flush input buffer."""
        self.event_queue.clear()
        self.input_buffer.clear()
        self.utf8_buffer.clear()
        self.parser.reset()
        
        # Flush stdin
        if self.stdin_fd:
            try:
                while True:
                    ready, _, _ = select.select([self.stdin_fd], [], [], 0)
                    if not ready:
                        break
                    os.read(self.stdin_fd, 4096)
            except:
                pass
    
    def _convert_to_event(self, parsed: object) -> Optional[object]:
        """
        Convert parsed input to Vindauga event.
        
        This would normally create proper Event objects from vindauga.events,
        but for now we'll return the parsed objects directly.
        """
        # In a full implementation, this would create proper Event objects
        # For now, return the parsed object
        return parsed