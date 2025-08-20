# -*- coding: utf-8 -*-
"""
Display backend modules for Vindauga.

Provides various display backends for different platforms:
- base: Abstract base class for display backends
- buffer: Display buffer and damage tracking
- ansi: ANSI escape sequence display backend
- termio: Linux/Unix terminal I/O display backend
- curses: Curses-based display backend
"""

from .base import Display
from .buffer import ScreenCell, DisplayBuffer, DamageRegion, FPSLimiter

__all__ = [
    'Display',
    'ScreenCell',
    'DisplayBuffer',
    'DamageRegion',
    'FPSLimiter'
]