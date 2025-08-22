# -*- coding: utf-8 -*-
"""
Terminal capability detection and querying.

This module provides comprehensive terminal capability detection using
escape sequences, environment variables, and runtime queries.
"""

import sys
import os
import select
import time
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum


class TerminalCapability(Enum):
    """Terminal capabilities."""
    # Display capabilities
    COLOR_16 = "color_16"
    COLOR_256 = "color_256"
    COLOR_24BIT = "color_24bit"
    UNICODE = "unicode"
    WIDE_CHARS = "wide_chars"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    
    # Control capabilities
    ALTERNATE_SCREEN = "alternate_screen"
    CURSOR_SHAPE = "cursor_shape"
    CURSOR_COLOR = "cursor_color"
    TITLE = "title"
    
    # Input capabilities
    MOUSE_X11 = "mouse_x11"
    MOUSE_SGR = "mouse_sgr"
    MOUSE_URXVT = "mouse_urxvt"
    BRACKETED_PASTE = "bracketed_paste"
    FOCUS_EVENTS = "focus_events"
    
    # Advanced capabilities
    SIXEL_GRAPHICS = "sixel_graphics"
    KITTY_GRAPHICS = "kitty_graphics"
    SYNCHRONIZED_UPDATE = "synchronized_update"


@dataclass
class TerminalInfo:
    """Terminal information."""
    name: str = "unknown"
    version: str = "unknown"
    type: str = "unknown"
    capabilities: Dict[TerminalCapability, bool] = None
    color_count: int = 16
    size: Tuple[int, int] = (80, 24)
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = {}


class TerminalCapabilityDetector:
    """
    Comprehensive terminal capability detector.
    
    Uses multiple methods to detect capabilities:
    - Environment variables (fast, static)
    - DA (Device Attributes) queries (accurate, dynamic)
    - CSI queries (specific features)
    - terminfo database (fallback)
    """
    
    # ANSI escape sequences for queries
    DA1_QUERY = "\x1b[c"          # Primary device attributes
    DA2_QUERY = "\x1b[>c"         # Secondary device attributes
    DA3_QUERY = "\x1b[=c"         # Tertiary device attributes
    DSR_QUERY = "\x1b[6n"         # Device status report (cursor position)
    DECRQSS_QUERY = "\x1b[?2026$p" # Request presentation state
    
    # Response patterns
    DA1_PATTERN = re.compile(r'\x1b\[([?;0-9]+)c')
    DA2_PATTERN = re.compile(r'\x1b\[>([0-9;]+)c')
    DA3_PATTERN = re.compile(r'\x1b\[=([0-9;]+)c')
    DSR_PATTERN = re.compile(r'\x1b\[(\d+);(\d+)R')
    
    def __init__(self, timeout: float = 0.1):
        """
        Initialize capability detector.
        
        Args:
            timeout: Timeout for terminal queries
        """
        self.timeout = timeout
        self.terminal_info = TerminalInfo()
        self._stdin_fd = None
        self._original_termios = None
        
        # Terminal type database
        self.terminal_database = {
            'xterm': {
                TerminalCapability.COLOR_256: True,
                TerminalCapability.MOUSE_X11: True,
                TerminalCapability.MOUSE_SGR: True,
                TerminalCapability.ALTERNATE_SCREEN: True,
            },
            'xterm-256color': {
                TerminalCapability.COLOR_256: True,
                TerminalCapability.COLOR_24BIT: True,
                TerminalCapability.MOUSE_X11: True,
                TerminalCapability.MOUSE_SGR: True,
                TerminalCapability.ALTERNATE_SCREEN: True,
            },
            'screen': {
                TerminalCapability.COLOR_256: True,
                TerminalCapability.ALTERNATE_SCREEN: True,
            },
            'tmux': {
                TerminalCapability.COLOR_256: True,
                TerminalCapability.COLOR_24BIT: True,
                TerminalCapability.ALTERNATE_SCREEN: True,
            },
            'kitty': {
                TerminalCapability.COLOR_24BIT: True,
                TerminalCapability.KITTY_GRAPHICS: True,
                TerminalCapability.UNICODE: True,
                TerminalCapability.WIDE_CHARS: True,
            },
            'iterm2': {
                TerminalCapability.COLOR_24BIT: True,
                TerminalCapability.SIXEL_GRAPHICS: True,
                TerminalCapability.UNICODE: True,
                TerminalCapability.WIDE_CHARS: True,
            },
        }
    
    def detect_all(self) -> TerminalInfo:
        """
        Detect all terminal capabilities using multiple methods.
        
        Returns:
            TerminalInfo with detected capabilities
        """
        # Start with environment detection (fast)
        self._detect_from_environment()
        
        # Try runtime queries if we have a TTY
        if self._setup_terminal():
            try:
                self._query_device_attributes()
                self._query_specific_features()
            finally:
                self._restore_terminal()
        
        # Fill in from database
        self._detect_from_database()
        
        # Final adjustments
        self._finalize_detection()
        
        return self.terminal_info
    
    def _detect_from_environment(self):
        """Detect capabilities from environment variables."""
        # Terminal type
        term = os.environ.get('TERM', 'unknown')
        self.terminal_info.type = term
        
        # Color support from TERM
        if '256color' in term:
            self.terminal_info.capabilities[TerminalCapability.COLOR_256] = True
            self.terminal_info.color_count = 256
        elif 'color' in term:
            self.terminal_info.capabilities[TerminalCapability.COLOR_16] = True
            self.terminal_info.color_count = 16
        
        # 24-bit color from COLORTERM
        colorterm = os.environ.get('COLORTERM', '')
        if colorterm in ['truecolor', '24bit']:
            self.terminal_info.capabilities[TerminalCapability.COLOR_24BIT] = True
            self.terminal_info.color_count = 16777216
        
        # Terminal emulator detection
        term_program = os.environ.get('TERM_PROGRAM', '')
        if term_program:
            self.terminal_info.name = term_program
            
            # Program-specific capabilities
            if 'iTerm' in term_program:
                self.terminal_info.capabilities[TerminalCapability.COLOR_24BIT] = True
                self.terminal_info.capabilities[TerminalCapability.SIXEL_GRAPHICS] = True
            elif term_program == 'Apple_Terminal':
                self.terminal_info.capabilities[TerminalCapability.COLOR_256] = True
            elif term_program == 'vscode':
                self.terminal_info.capabilities[TerminalCapability.COLOR_24BIT] = True
        
        # Kitty detection
        if 'KITTY_WINDOW_ID' in os.environ:
            self.terminal_info.name = 'kitty'
            self.terminal_info.capabilities[TerminalCapability.KITTY_GRAPHICS] = True
            self.terminal_info.capabilities[TerminalCapability.COLOR_24BIT] = True
        
        # Unicode support
        lang = os.environ.get('LANG', '')
        if 'UTF-8' in lang or 'utf8' in lang.lower():
            self.terminal_info.capabilities[TerminalCapability.UNICODE] = True
    
    def _setup_terminal(self) -> bool:
        """Set up terminal for queries."""
        try:
            if not sys.stdin.isatty():
                return False
            
            import termios
            import tty
            
            self._stdin_fd = sys.stdin.fileno()
            self._original_termios = termios.tcgetattr(self._stdin_fd)
            
            # Set to raw mode for queries
            tty.setraw(self._stdin_fd)
            
            # Make non-blocking
            import fcntl
            flags = fcntl.fcntl(self._stdin_fd, fcntl.F_GETFL)
            fcntl.fcntl(self._stdin_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            return True
            
        except:
            return False
    
    def _restore_terminal(self):
        """Restore terminal settings."""
        if self._original_termios and self._stdin_fd is not None:
            try:
                import termios
                termios.tcsetattr(self._stdin_fd, termios.TCSANOW, 
                                self._original_termios)
            except:
                pass
    
    def _send_query(self, query: str) -> Optional[str]:
        """
        Send query and get response.
        
        Args:
            query: Query sequence to send
            
        Returns:
            Response string or None
        """
        if self._stdin_fd is None:
            return None
        
        try:
            # Send query
            sys.stdout.write(query)
            sys.stdout.flush()
            
            # Wait for response
            response = b''
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                ready, _, _ = select.select([self._stdin_fd], [], [], 0.01)
                if ready:
                    try:
                        data = os.read(self._stdin_fd, 1024)
                        if data:
                            response += data
                            # Check if we have a complete response
                            if b'c' in data or b'R' in data:
                                break
                    except:
                        break
                        
            return response.decode('ascii', errors='ignore') if response else None
            
        except:
            return None
    
    def _query_device_attributes(self):
        """Query device attributes."""
        # Primary device attributes (DA1)
        response = self._send_query(self.DA1_QUERY)
        if response:
            match = self.DA1_PATTERN.search(response)
            if match:
                params = match.group(1).split(';')
                self._parse_da1_response(params)
        
        # Secondary device attributes (DA2)
        response = self._send_query(self.DA2_QUERY)
        if response:
            match = self.DA2_PATTERN.search(response)
            if match:
                params = match.group(1).split(';')
                self._parse_da2_response(params)
    
    def _parse_da1_response(self, params: List[str]):
        """Parse DA1 response parameters."""
        # Common DA1 parameters indicate capabilities
        param_set = set(params)
        
        # Check for specific capabilities
        if '1' in param_set:  # 132 column mode
            pass
        if '4' in param_set:  # Sixel graphics
            self.terminal_info.capabilities[TerminalCapability.SIXEL_GRAPHICS] = True
        if '6' in param_set:  # Selective erase
            pass
        if '22' in param_set:  # ANSI color
            self.terminal_info.capabilities[TerminalCapability.COLOR_16] = True
    
    def _parse_da2_response(self, params: List[str]):
        """Parse DA2 response parameters."""
        if len(params) >= 1:
            terminal_id = params[0]
            
            # Terminal identification
            terminal_types = {
                '0': 'VT100',
                '1': 'VT220',
                '2': 'VT240',
                '18': 'VT330',
                '19': 'VT340',
                '24': 'VT320',
                '41': 'VT420',
                '61': 'VT510',
                '64': 'VT520',
                '65': 'VT525',
            }
            
            if terminal_id in terminal_types:
                self.terminal_info.type = terminal_types[terminal_id]
        
        if len(params) >= 2:
            # Firmware version
            self.terminal_info.version = params[1]
    
    def _query_specific_features(self):
        """Query for specific features."""
        # Check cursor position reporting (basic test)
        response = self._send_query(self.DSR_QUERY)
        if response and self.DSR_PATTERN.search(response):
            # Terminal responds to DSR
            self.terminal_info.capabilities[TerminalCapability.CURSOR_SHAPE] = True
    
    def _detect_from_database(self):
        """Fill in capabilities from terminal database."""
        term_type = self.terminal_info.type.lower()
        
        # Check direct match
        if term_type in self.terminal_database:
            for cap, value in self.terminal_database[term_type].items():
                if cap not in self.terminal_info.capabilities:
                    self.terminal_info.capabilities[cap] = value
        
        # Check partial matches
        for known_term, caps in self.terminal_database.items():
            if known_term in term_type:
                for cap, value in caps.items():
                    if cap not in self.terminal_info.capabilities:
                        self.terminal_info.capabilities[cap] = value
    
    def _finalize_detection(self):
        """Final adjustments to detected capabilities."""
        caps = self.terminal_info.capabilities
        
        # If we have 24-bit color, we also have 256 and 16
        if caps.get(TerminalCapability.COLOR_24BIT):
            caps[TerminalCapability.COLOR_256] = True
            caps[TerminalCapability.COLOR_16] = True
            self.terminal_info.color_count = 16777216
        elif caps.get(TerminalCapability.COLOR_256):
            caps[TerminalCapability.COLOR_16] = True
            if self.terminal_info.color_count < 256:
                self.terminal_info.color_count = 256
        
        # Wide chars require Unicode
        if caps.get(TerminalCapability.WIDE_CHARS):
            caps[TerminalCapability.UNICODE] = True
        
        # Get terminal size
        try:
            import shutil
            cols, rows = shutil.get_terminal_size()
            self.terminal_info.size = (cols, rows)
        except:
            pass


def detect_terminal_capabilities(timeout: float = 0.1) -> TerminalInfo:
    """
    Convenience function to detect terminal capabilities.
    
    Args:
        timeout: Timeout for queries
        
    Returns:
        TerminalInfo with detected capabilities
    """
    detector = TerminalCapabilityDetector(timeout=timeout)
    return detector.detect_all()