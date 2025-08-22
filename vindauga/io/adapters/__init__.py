"""
Adapter layer for integrating new I/O system with existing Vindauga code.

This package provides adapters that bridge the new I/O subsystem with
the existing Vindauga API, enabling backward compatibility while allowing
gradual migration to the new system.
"""

from .screen_adapter import ScreenAdapter
from .buffer_adapter import BufferAdapter
from .event_adapter import EventAdapter

__all__ = [
    'ScreenAdapter',
    'BufferAdapter',
    'EventAdapter',
]