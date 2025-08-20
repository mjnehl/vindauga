# -*- coding: utf-8 -*-
"""
Platform detection and I/O system factory.

Detects available terminal I/O platforms and selects the best one based on
capabilities and performance characteristics.
"""

import os
import sys
import platform
from enum import Enum
from typing import Optional, Dict, List, Any


class PlatformType(Enum):
    """Available I/O platform types."""
    ANSI = 'ansi'
    TERMIO = 'termio'
    CURSES = 'curses'
    WIN32 = 'win32'
    
    @classmethod
    def from_string(cls, value: str) -> 'PlatformType':
        """Convert string to PlatformType."""
        value = value.lower()
        for platform_type in cls:
            if platform_type.value == value:
                return platform_type
        raise ValueError(f"Unknown platform type: {value}")
    
    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class PlatformCapabilities:
    """Capabilities of a specific platform."""
    
    def __init__(self,
                 has_colors: bool = False,
                 has_mouse: bool = False,
                 has_unicode: bool = False,
                 has_24bit_color: bool = False,
                 max_colors: int = 0,
                 is_available: bool = False):
        """Initialize platform capabilities."""
        self.has_colors = has_colors
        self.has_mouse = has_mouse
        self.has_unicode = has_unicode
        self.has_24bit_color = has_24bit_color
        self.max_colors = max_colors
        self.is_available = is_available
    
    def score(self) -> int:
        """Calculate capability score for platform selection."""
        if not self.is_available:
            return 0
        
        score = 0
        if self.has_colors:
            score += 10
        if self.has_mouse:
            score += 10
        if self.has_unicode:
            score += 10
        if self.has_24bit_color:
            score += 50
        
        # Add score based on color count
        if self.max_colors >= 16777216:
            score += 100
        elif self.max_colors >= 256:
            score += 50
        elif self.max_colors >= 16:
            score += 20
        
        return score


class PlatformDetector:
    """Detect available I/O platforms and their capabilities."""
    
    def __init__(self):
        """Initialize platform detector."""
        self._capabilities_cache: Dict[PlatformType, PlatformCapabilities] = {}
    
    def get_ansi_capabilities(self) -> PlatformCapabilities:
        """Detect ANSI terminal capabilities."""
        if PlatformType.ANSI in self._capabilities_cache:
            return self._capabilities_cache[PlatformType.ANSI]
        
        caps = PlatformCapabilities()
        
        # Check if we're in a terminal
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            caps.is_available = False
            self._capabilities_cache[PlatformType.ANSI] = caps
            return caps
        
        # Check terminal type
        term = os.environ.get('TERM', '')
        if term in ['dumb', '']:
            caps.is_available = False
            self._capabilities_cache[PlatformType.ANSI] = caps
            return caps
        
        caps.is_available = True
        caps.has_unicode = True
        caps.has_mouse = True
        
        # Check color support
        colorterm = os.environ.get('COLORTERM', '')
        if colorterm in ['truecolor', '24bit']:
            caps.has_24bit_color = True
            caps.has_colors = True
            caps.max_colors = 16777216
        elif '256color' in term:
            caps.has_colors = True
            caps.max_colors = 256
        elif term in ['xterm', 'screen', 'vt100', 'linux']:
            caps.has_colors = True
            caps.max_colors = 16
        
        self._capabilities_cache[PlatformType.ANSI] = caps
        return caps
    
    def get_termio_capabilities(self) -> PlatformCapabilities:
        """Detect TermIO capabilities."""
        if PlatformType.TERMIO in self._capabilities_cache:
            return self._capabilities_cache[PlatformType.TERMIO]
        
        caps = PlatformCapabilities()
        
        # TermIO is Linux/Unix specific
        if platform.system() == 'Windows':
            caps.is_available = False
            self._capabilities_cache[PlatformType.TERMIO] = caps
            return caps
        
        # Try to import termios
        try:
            import termios
            import tty
            import fcntl
            
            # Check if stdin is a terminal
            if hasattr(sys.stdin, 'fileno'):
                termios.tcgetattr(sys.stdin.fileno())
                caps.is_available = True
        except (ImportError, OSError, ValueError):
            caps.is_available = False
            self._capabilities_cache[PlatformType.TERMIO] = caps
            return caps
        
        if caps.is_available:
            caps.has_unicode = True
            caps.has_mouse = True
            
            # Check color support from TERM
            term = os.environ.get('TERM', '')
            colorterm = os.environ.get('COLORTERM', '')
            
            if colorterm in ['truecolor', '24bit']:
                caps.has_24bit_color = True
                caps.has_colors = True
                caps.max_colors = 16777216
            elif '256color' in term:
                caps.has_colors = True
                caps.max_colors = 256
            elif term not in ['dumb', '']:
                caps.has_colors = True
                caps.max_colors = 16
        
        self._capabilities_cache[PlatformType.TERMIO] = caps
        return caps
    
    def get_curses_capabilities(self) -> PlatformCapabilities:
        """Detect Curses capabilities."""
        if PlatformType.CURSES in self._capabilities_cache:
            return self._capabilities_cache[PlatformType.CURSES]
        
        caps = PlatformCapabilities()
        
        # Try to import curses
        try:
            import curses
            caps.is_available = True
            caps.has_colors = True
            caps.has_mouse = True
            caps.has_unicode = True
            caps.max_colors = 256  # Typical curses limitation
        except ImportError:
            caps.is_available = False
        
        self._capabilities_cache[PlatformType.CURSES] = caps
        return caps
    
    def get_win32_capabilities(self) -> PlatformCapabilities:
        """Detect Win32 console capabilities."""
        if PlatformType.WIN32 in self._capabilities_cache:
            return self._capabilities_cache[PlatformType.WIN32]
        
        caps = PlatformCapabilities()
        caps.is_available = False  # Not implemented yet
        
        self._capabilities_cache[PlatformType.WIN32] = caps
        return caps
    
    def get_platform_capabilities(self, platform_type: PlatformType) -> PlatformCapabilities:
        """Get capabilities for a specific platform type."""
        if platform_type == PlatformType.ANSI:
            return self.get_ansi_capabilities()
        elif platform_type == PlatformType.TERMIO:
            return self.get_termio_capabilities()
        elif platform_type == PlatformType.CURSES:
            return self.get_curses_capabilities()
        elif platform_type == PlatformType.WIN32:
            return self.get_win32_capabilities()
        else:
            raise ValueError(f"Unknown platform type: {platform_type}")
    
    def detect_best_platform(self) -> PlatformType:
        """Detect and return the best available platform."""
        platforms = [
            (PlatformType.ANSI, self.get_ansi_capabilities()),
            (PlatformType.TERMIO, self.get_termio_capabilities()),
            (PlatformType.CURSES, self.get_curses_capabilities()),
            (PlatformType.WIN32, self.get_win32_capabilities())
        ]
        
        # Filter available platforms and sort by score
        available = [(p, c) for p, c in platforms if c.is_available]
        if not available:
            raise RuntimeError("No terminal I/O platform available")
        
        available.sort(key=lambda x: x[1].score(), reverse=True)
        return available[0][0]
    
    def list_available_platforms(self) -> List[PlatformType]:
        """List all available platforms."""
        available = []
        for platform_type in PlatformType:
            caps = self.get_platform_capabilities(platform_type)
            if caps.is_available:
                available.append(platform_type)
        return available
    
    def get_platform_info(self) -> Dict[str, Any]:
        """Get detailed platform information."""
        info = {
            'system': platform.system(),
            'python_version': sys.version,
            'terminal': os.environ.get('TERM', 'unknown'),
            'colorterm': os.environ.get('COLORTERM', 'unknown'),
            'platforms': {}
        }
        
        for platform_type in PlatformType:
            caps = self.get_platform_capabilities(platform_type)
            info['platforms'][platform_type.value] = {
                'available': caps.is_available,
                'score': caps.score(),
                'has_colors': caps.has_colors,
                'has_mouse': caps.has_mouse,
                'has_unicode': caps.has_unicode,
                'has_24bit_color': caps.has_24bit_color,
                'max_colors': caps.max_colors
            }
        
        return info


class PlatformIO:
    """Platform I/O system combining display and input handlers."""
    
    def __init__(self, display, input_handler, platform_type: PlatformType):
        """Initialize platform I/O system."""
        self.display = display
        self.input = input_handler
        self.platform_type = platform_type
        self._initialized = False
    
    @classmethod
    def create(cls, platform_name: Optional[str] = None) -> 'PlatformIO':
        """Create platform I/O system."""
        if platform_name:
            platform_type = PlatformType.from_string(platform_name)
        else:
            detector = PlatformDetector()
            platform_type = detector.detect_best_platform()
        
        # Import and create appropriate backends
        if platform_type == PlatformType.ANSI:
            from .display.ansi import ANSIDisplay
            from .input.ansi import ANSIInput
            display = ANSIDisplay()
            input_handler = ANSIInput()
        elif platform_type == PlatformType.TERMIO:
            from .display.termio import TermIODisplay
            from .input.termio import TermIOInput
            display = TermIODisplay()
            input_handler = TermIOInput()
        elif platform_type == PlatformType.CURSES:
            from .display.curses import CursesDisplay
            from .input.curses import CursesInput
            display = CursesDisplay()
            input_handler = CursesInput()
        else:
            raise ValueError(f"Unsupported platform: {platform_type}")
        
        return cls(display, input_handler, platform_type)
    
    def initialize(self) -> bool:
        """Initialize the I/O system."""
        if self._initialized:
            return True
        
        # Initialize display
        if not self.display.initialize():
            self.shutdown()
            return False
        
        # Initialize input
        if not self.input.initialize():
            self.shutdown()
            return False
        
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        """Shutdown the I/O system."""
        if self.display:
            self.display.shutdown()
        if self.input:
            self.input.shutdown()
        self._initialized = False
    
    def __enter__(self):
        """Context manager entry."""
        if not self.initialize():
            raise RuntimeError("Failed to initialize I/O system")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()