# -*- coding: utf-8 -*-
"""
Fixed platform factory with better error handling and initialization.

This version properly handles backend initialization failures and
provides better fallback mechanisms.
"""

import sys
import platform
from typing import Tuple, Optional
from enum import Enum

from .display.base import Display
from .input.base import InputHandler
from .platform_detector import PlatformDetector, PlatformType

# Import display backends
from .display.ansi import ANSIDisplay
from .display.termio_fixed import FixedTermIODisplay
from .display.curses import CursesDisplay

# Import input backends  
from .input.ansi_improved import ImprovedANSIInput
from .input.termio import TermIOInput
from .input.curses import CursesInput


class FixedPlatformIO:
    """
    Fixed factory for creating platform-specific I/O backends.
    
    Improvements:
    - Better error handling
    - Proper initialization sequence
    - Automatic fallback on failure
    - Uses improved backends
    """
    
    @staticmethod
    def create(platform_type: Optional[PlatformType] = None,
              allow_fallback: bool = True) -> Tuple[Display, InputHandler]:
        """
        Create display and input handlers for specified platform.
        
        Args:
            platform_type: Specific platform or None for auto-detect
            allow_fallback: If True, fall back to simpler platform on failure
            
        Returns:
            Tuple of (Display, InputHandler)
            
        Raises:
            RuntimeError: If no suitable platform available
        """
        # Auto-detect if not specified
        if platform_type is None:
            detector = PlatformDetector()
            platform_type = detector.select_best_platform()
            
            if platform_type is None:
                raise RuntimeError("No suitable platform available")
        
        # Try to create backends with fallback
        fallback_order = FixedPlatformIO._get_fallback_order(platform_type)
        
        last_error = None
        for platform in fallback_order:
            try:
                display, input_handler = FixedPlatformIO._create_backend(platform)
                
                # Try to initialize
                if display and input_handler:
                    if display.initialize() and input_handler.initialize():
                        return display, input_handler
                    else:
                        # Cleanup failed initialization
                        try:
                            display.shutdown()
                            input_handler.shutdown()
                        except:
                            pass
                        
                        if not allow_fallback:
                            raise RuntimeError(f"Failed to initialize {platform.name} backend")
                        
            except Exception as e:
                last_error = e
                if not allow_fallback:
                    raise
                continue
        
        # All platforms failed
        if last_error:
            raise RuntimeError(f"No platforms could be initialized: {last_error}")
        else:
            raise RuntimeError("No platforms could be initialized")
    
    @staticmethod
    def _create_backend(platform_type: PlatformType) -> Tuple[Optional[Display], Optional[InputHandler]]:
        """
        Create backend for specific platform.
        
        Args:
            platform_type: Platform type
            
        Returns:
            Tuple of (Display, InputHandler) or (None, None) on failure
        """
        try:
            if platform_type == PlatformType.ANSI:
                # Use improved ANSI backend
                display = ANSIDisplay()
                input_handler = ImprovedANSIInput(
                    allow_ctrl_c=True,
                    enable_coalescing=True,
                    enable_error_recovery=True
                )
                return display, input_handler
                
            elif platform_type == PlatformType.TERMIO:
                # Use fixed TermIO backend
                display = FixedTermIODisplay()
                input_handler = TermIOInput()
                return display, input_handler
                
            elif platform_type == PlatformType.CURSES:
                # Curses with better initialization
                return FixedPlatformIO._create_curses_backend()
                
            else:
                return None, None
                
        except Exception:
            return None, None
    
    @staticmethod
    def _create_curses_backend() -> Tuple[Optional[Display], Optional[InputHandler]]:
        """
        Create Curses backend with proper error handling.
        
        Returns:
            Tuple of (Display, InputHandler) or (None, None) on failure
        """
        try:
            import curses
            
            # Check if curses is actually available
            # Some systems have the module but not the functionality
            if not hasattr(curses, 'initscr'):
                return None, None
            
            # Check if we're in a real terminal
            if not sys.stdout.isatty():
                return None, None
            
            # Try to create display
            display = CursesDisplay()
            
            # Don't initialize here - let the factory do it
            # This allows proper cleanup on failure
            
            # Create input handler (will get stdscr after init)
            input_handler = CursesInput(None)
            
            # Special handling for curses initialization
            # We need to initialize display first, then update input
            def curses_init_sequence():
                if display.initialize():
                    # Update input handler with screen
                    input_handler.stdscr = display.stdscr
                    return input_handler.initialize()
                return False
            
            # Monkey patch for coordinated initialization
            original_display_init = display.initialize
            display.initialize = curses_init_sequence
            
            return display, input_handler
            
        except ImportError:
            # Curses not available
            return None, None
        except Exception:
            # Any other error
            return None, None
    
    @staticmethod
    def _get_fallback_order(preferred: PlatformType) -> list:
        """
        Get fallback order for platforms.
        
        Args:
            preferred: Preferred platform
            
        Returns:
            List of platforms to try in order
        """
        all_platforms = [
            PlatformType.ANSI,
            PlatformType.TERMIO,
            PlatformType.CURSES
        ]
        
        # Start with preferred
        order = [preferred]
        
        # Add others based on system
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            # Prefer ANSI on macOS
            if PlatformType.ANSI not in order:
                order.append(PlatformType.ANSI)
            # TermIO might work with fixes
            if PlatformType.TERMIO not in order:
                order.append(PlatformType.TERMIO)
            # Curses as last resort
            if PlatformType.CURSES not in order:
                order.append(PlatformType.CURSES)
                
        elif system == 'Linux':
            # Linux supports all backends well
            for p in [PlatformType.TERMIO, PlatformType.ANSI, PlatformType.CURSES]:
                if p not in order:
                    order.append(p)
                    
        elif system == 'Windows':
            # Windows typically only supports ANSI (with Windows Terminal)
            if PlatformType.ANSI not in order:
                order.append(PlatformType.ANSI)
            # Curses might work with windows-curses
            if PlatformType.CURSES not in order:
                order.append(PlatformType.CURSES)
        
        else:
            # Unknown system - try all
            for p in all_platforms:
                if p not in order:
                    order.append(p)
        
        return order
    
    @staticmethod
    def test_all_backends() -> dict:
        """
        Test all available backends.
        
        Returns:
            Dictionary of platform -> success status
        """
        results = {}
        
        for platform in [PlatformType.ANSI, PlatformType.TERMIO, PlatformType.CURSES]:
            try:
                display, input_handler = FixedPlatformIO.create(
                    platform, 
                    allow_fallback=False
                )
                
                # Test worked
                display.shutdown()
                input_handler.shutdown()
                results[platform.name] = True
                
            except Exception as e:
                results[platform.name] = False
        
        return results


# Alias for compatibility with adapters
PlatformIO = FixedPlatformIO