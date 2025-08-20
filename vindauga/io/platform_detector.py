# -*- coding: utf-8 -*-
"""
Platform detection for selecting the appropriate I/O backend.

This module provides platform detection capabilities to automatically
select the best available terminal I/O backend for the current environment.
"""

import os
import sys
import platform
from enum import Enum, auto
from typing import Dict, Optional, Any
from dataclasses import dataclass


class PlatformType(Enum):
    """Available platform backend types."""
    ANSI = auto()      # ANSI escape sequences (most modern terminals)
    TERMIO = auto()    # Linux/Unix terminal I/O
    CURSES = auto()    # NCurses library
    WIN32 = auto()     # Windows Console API
    DUMMY = auto()     # Dummy backend for testing


@dataclass
class PlatformCapabilities:
    """
    Capabilities of a specific platform backend.
    
    Attributes:
        name: Platform name
        available: Whether this platform is available
        color_support: Level of color support (0, 16, 256, 16777216)
        mouse_support: Whether mouse input is supported
        unicode_support: Whether Unicode is properly supported
        performance_score: Performance rating (0-100)
    """
    name: str
    available: bool = False
    color_support: int = 0
    mouse_support: bool = False
    unicode_support: bool = False
    performance_score: int = 0
    
    def overall_score(self) -> int:
        """
        Calculate an overall score for platform selection.
        
        Returns:
            Score from 0-100, higher is better
        """
        if not self.available:
            return 0
        
        score = self.performance_score
        
        # Add points for features
        if self.color_support >= 16777216:  # 24-bit color
            score += 20
        elif self.color_support >= 256:
            score += 15
        elif self.color_support >= 16:
            score += 10
        
        if self.mouse_support:
            score += 10
        
        if self.unicode_support:
            score += 10
        
        return min(score, 100)


class PlatformDetector:
    """
    Detects and evaluates available platform backends.
    
    This class examines the system environment to determine which
    terminal I/O backends are available and their capabilities.
    """
    
    def __init__(self):
        """Initialize the platform detector."""
        self.system = platform.system()
        self.is_windows = self.system == 'Windows'
        self.is_linux = self.system == 'Linux'
        self.is_mac = self.system == 'Darwin'
        self.is_unix = self.is_linux or self.is_mac
        
        # Terminal environment
        self.term = os.environ.get('TERM', '')
        self.colorterm = os.environ.get('COLORTERM', '')
        self.term_program = os.environ.get('TERM_PROGRAM', '')
        
        # Check if we're in a real terminal
        self.is_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def detect_ansi_capabilities(self) -> PlatformCapabilities:
        """
        Detect ANSI terminal capabilities.
        
        Returns:
            PlatformCapabilities for ANSI backend
        """
        caps = PlatformCapabilities(name="ANSI")
        
        # ANSI requires a real terminal
        if not self.is_tty:
            caps.available = False
            return caps
        
        # Check for dumb terminal
        if self.term == 'dumb':
            caps.available = False
            return caps
        
        caps.available = True
        caps.unicode_support = True
        caps.mouse_support = True
        caps.performance_score = 70
        
        # Detect color support
        if self.colorterm in ('truecolor', '24bit'):
            caps.color_support = 16777216  # 24-bit
        elif '256color' in self.term:
            caps.color_support = 256
        elif self.term in ('xterm', 'screen', 'vt100', 'linux', 'ansi'):
            caps.color_support = 16
        else:
            caps.color_support = 8
        
        # Adjust performance score based on terminal type
        if 'kitty' in self.term or self.term_program == 'kitty':
            caps.performance_score = 95
        elif 'alacritty' in self.term or self.term_program == 'alacritty':
            caps.performance_score = 90
        elif 'iterm' in self.term_program.lower():
            caps.performance_score = 85
        elif 'xterm' in self.term:
            caps.performance_score = 75
        
        return caps
    
    def detect_termio_capabilities(self) -> PlatformCapabilities:
        """
        Detect TermIO (Unix terminal I/O) capabilities.
        
        Returns:
            PlatformCapabilities for TermIO backend
        """
        caps = PlatformCapabilities(name="TermIO")
        
        # TermIO is Unix-specific
        if not self.is_unix:
            return caps
        
        # Check if we can import required modules
        try:
            import termios
            import tty
            import fcntl
            caps.available = True
        except ImportError:
            return caps
        
        # Check if stdin is a terminal
        if not hasattr(sys.stdin, 'fileno'):
            caps.available = False
            return caps
        
        try:
            # Try to get terminal attributes
            termios.tcgetattr(sys.stdin.fileno())
        except:
            caps.available = False
            return caps
        
        # TermIO has similar capabilities to ANSI
        caps.unicode_support = True
        caps.mouse_support = True
        caps.performance_score = 80  # Generally faster than ANSI
        
        # Color support same as ANSI
        if self.colorterm in ('truecolor', '24bit'):
            caps.color_support = 16777216
        elif '256color' in self.term:
            caps.color_support = 256
        elif self.term not in ('', 'dumb'):
            caps.color_support = 16
        
        return caps
    
    def detect_curses_capabilities(self) -> PlatformCapabilities:
        """
        Detect Curses library capabilities.
        
        Returns:
            PlatformCapabilities for Curses backend
        """
        caps = PlatformCapabilities(name="Curses")
        
        # Try to import curses
        try:
            import curses
            caps.available = True
        except ImportError:
            return caps
        
        # Curses capabilities
        caps.unicode_support = True  # Modern curses supports Unicode
        caps.mouse_support = True
        caps.color_support = 256  # Most curses implementations support 256 colors
        caps.performance_score = 60  # Generally slower than direct terminal I/O
        
        return caps
    
    def detect_win32_capabilities(self) -> PlatformCapabilities:
        """
        Detect Windows Console API capabilities.
        
        Returns:
            PlatformCapabilities for Win32 backend
        """
        caps = PlatformCapabilities(name="Win32")
        
        if not self.is_windows:
            return caps
        
        # Check for Windows-specific modules
        try:
            import msvcrt
            # Would also need pywin32 or ctypes for full implementation
            caps.available = False  # Not implemented yet
        except ImportError:
            return caps
        
        # Windows Terminal supports more features
        if 'WT_SESSION' in os.environ:
            caps.unicode_support = True
            caps.color_support = 16777216
            caps.performance_score = 75
        else:
            # Legacy console
            caps.unicode_support = False
            caps.color_support = 16
            caps.performance_score = 50
        
        caps.mouse_support = True
        
        return caps
    
    def detect_all(self) -> Dict[PlatformType, PlatformCapabilities]:
        """
        Detect capabilities of all platforms.
        
        Returns:
            Dictionary mapping platform types to their capabilities
        """
        return {
            PlatformType.ANSI: self.detect_ansi_capabilities(),
            PlatformType.TERMIO: self.detect_termio_capabilities(),
            PlatformType.CURSES: self.detect_curses_capabilities(),
            PlatformType.WIN32: self.detect_win32_capabilities(),
        }
    
    def select_best_platform(self) -> Optional[PlatformType]:
        """
        Select the best available platform based on capabilities.
        
        Returns:
            The PlatformType with the highest score, or None if none available
        """
        all_caps = self.detect_all()
        
        # Filter to available platforms and sort by score
        available = [
            (platform_type, caps)
            for platform_type, caps in all_caps.items()
            if caps.available
        ]
        
        if not available:
            return None
        
        # Sort by overall score (highest first)
        available.sort(key=lambda x: x[1].overall_score(), reverse=True)
        
        return available[0][0]
    
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the platform environment.
        
        Returns:
            Dictionary with platform information
        """
        return {
            'system': self.system,
            'is_tty': self.is_tty,
            'term': self.term,
            'colorterm': self.colorterm,
            'term_program': self.term_program,
            'python_version': sys.version,
            'platform_capabilities': {
                platform_type.name: {
                    'available': caps.available,
                    'score': caps.overall_score(),
                    'colors': caps.color_support,
                    'mouse': caps.mouse_support,
                    'unicode': caps.unicode_support,
                }
                for platform_type, caps in self.detect_all().items()
            }
        }