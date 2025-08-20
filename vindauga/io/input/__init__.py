# -*- coding: utf-8 -*-
"""
Input backend modules for Vindauga.

Provides various input backends for different platforms:
- base: Abstract base class for input backends
- ansi: ANSI escape sequence input backend
- ansi_parser: ANSI escape sequence parser
- termio: Linux/Unix terminal I/O input backend
- curses: Curses-based input backend
"""

from .base import InputHandler

__all__ = [
    'InputHandler'
]