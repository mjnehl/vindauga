# -*- coding: utf-8 -*-
"""
Abstract base class for input backends.
"""

from abc import ABC, abstractmethod
from typing import Optional, List


class InputHandler(ABC):
    """Abstract base class for input handlers."""
    
    def __init__(self):
        """Initialize input handler."""
        self._initialized = False
        self._mouse_enabled = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if input handler is initialized."""
        return self._initialized
    
    @property
    def mouse_enabled(self) -> bool:
        """Check if mouse is enabled."""
        return self._mouse_enabled
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the input handler."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the input handler."""
        pass
    
    @abstractmethod
    def get_event(self, timeout: float = 0.0):
        """Get next event with optional timeout."""
        pass
    
    @abstractmethod
    def has_events(self) -> bool:
        """Check if events are available."""
        pass
    
    @abstractmethod
    def enable_mouse(self, enable: bool = True) -> bool:
        """Enable or disable mouse events."""
        pass
    
    @abstractmethod
    def supports_mouse(self) -> bool:
        """Check if mouse is supported."""
        pass
    
    @abstractmethod
    def flush_input(self) -> None:
        """Flush input buffer."""
        pass
    
    def peek_event(self):
        """Peek at next event without consuming it."""
        # Default implementation using get_event
        # Subclasses should override for better implementation
        event = self.get_event(0.0)
        return event
    
    def wait_for_event(self, timeout: float = -1.0):
        """Wait for event with timeout."""
        return self.get_event(timeout)
    
    def get_events(self, max_count: int = 10) -> List:
        """Get multiple events at once."""
        events = []
        for _ in range(max_count):
            event = self.get_event(0.0)
            if event:
                events.append(event)
            else:
                break
        return events
    
    def __enter__(self):
        """Context manager entry."""
        if not self.initialize():
            raise RuntimeError("Failed to initialize input handler")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()