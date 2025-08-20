# -*- coding: utf-8 -*-
"""
I/O subsystem for Vindauga TUI library.

Provides platform-independent display and input handling through various backends:
- ANSI: Direct ANSI escape sequence handling for modern terminals
- TermIO: Linux/Unix terminal I/O using termios
- Curses: Cross-platform terminal handling using curses library
- Win32: Windows console API (future implementation)

The module automatically detects the best available platform and provides
a unified interface for terminal operations.
"""

from .platform import (
    PlatformType,
    PlatformCapabilities,
    PlatformDetector,
    PlatformIO
)

from .display.buffer import (
    ScreenCell,
    DisplayBuffer,
    DamageRegion,
    FPSLimiter
)

__all__ = [
    'PlatformType',
    'PlatformCapabilities',
    'PlatformDetector',
    'PlatformIO',
    'ScreenCell',
    'DisplayBuffer',
    'DamageRegion',
    'FPSLimiter'
]