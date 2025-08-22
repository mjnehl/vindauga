# -*- coding: utf-8 -*-
"""
Vindauga I/O subsystem.

This module provides a multi-platform terminal I/O system with support for:
- ANSI escape sequences
- Unix/Linux TermIO
- Curses library
- Automatic platform detection
"""

from typing import Tuple, Optional
from .platform_detector import PlatformDetector, PlatformType, PlatformCapabilities
from .display.base import Display
from .input.base import InputHandler

# Import display backends
from .display.ansi import ANSIDisplay
from .display.termio import TermIODisplay
from .display.curses import CursesDisplay

# Import input backends
from .input.ansi import ANSIInput
from .input.termio import TermIOInput
from .input.curses import CursesInput

# Import core components
from .screen_cell import ScreenCell
from .display_buffer import DisplayBuffer
from .damage_region import DamageRegion
from .fps_limiter import FPSLimiter


class PlatformIO:
    """
    Platform I/O factory for creating display and input backends.
    
    Automatically detects the best available platform and creates
    appropriate display and input handlers.
    """
    
    @staticmethod
    def create(platform_type: Optional[PlatformType] = None) -> Tuple[Display, InputHandler]:
        """
        Create display and input backends for the specified platform.
        
        Args:
            platform_type: Specific platform to use, or None for auto-detection
            
        Returns:
            Tuple of (Display, InputHandler) objects
            
        Raises:
            RuntimeError: If no suitable platform is available
        """
        # Auto-detect if not specified
        if platform_type is None:
            detector = PlatformDetector()
            platform_type = detector.select_best_platform()
            
            if platform_type is None:
                raise RuntimeError("No suitable platform available")
        
        # Create backends based on platform
        if platform_type == PlatformType.ANSI:
            return ANSIDisplay(), ANSIInput()
            
        elif platform_type == PlatformType.TERMIO:
            return TermIODisplay(), TermIOInput()
            
        elif platform_type == PlatformType.CURSES:
            # Curses requires special initialization
            import curses
            display = CursesDisplay()
            # Initialize curses through the display
            if not display.initialize():
                raise RuntimeError("Failed to initialize curses")
            # Create input handler with the curses screen
            input_handler = CursesInput(display.stdscr)
            input_handler.initialize()
            return display, input_handler
            
        else:
            raise RuntimeError(f"Unsupported platform: {platform_type}")
    
    @staticmethod
    def detect_platforms():
        """
        Detect available platforms and their capabilities.
        
        Returns:
            Dictionary of platform information
        """
        detector = PlatformDetector()
        return detector.get_platform_info()


__all__ = [
    # Factory
    'PlatformIO',
    
    # Platform detection
    'PlatformDetector',
    'PlatformType',
    'PlatformCapabilities',
    
    # Base classes
    'Display',
    'InputHandler',
    
    # Display backends
    'ANSIDisplay',
    'TermIODisplay',
    'CursesDisplay',
    
    # Input backends
    'ANSIInput',
    'TermIOInput',
    'CursesInput',
    
    # Core components
    'ScreenCell',
    'DisplayBuffer',
    'DamageRegion',
    'FPSLimiter',
]