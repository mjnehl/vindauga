# -*- coding: utf-8 -*-
"""
Event coalescing for improved performance.

This module provides event coalescing to reduce the number of events
processed, especially for rapid mouse movements and key repeats.
"""

import time
from typing import Optional, List, Any
from dataclasses import dataclass
from collections import deque


@dataclass
class MouseMoveEvent:
    """Mouse movement event."""
    x: int
    y: int
    timestamp: float
    
    def can_coalesce_with(self, other: 'MouseMoveEvent', max_time_diff: float = 0.05) -> bool:
        """Check if this event can be coalesced with another."""
        if not isinstance(other, MouseMoveEvent):
            return False
        # Coalesce if within time window
        return abs(self.timestamp - other.timestamp) <= max_time_diff


@dataclass
class KeyEvent:
    """Keyboard event."""
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    timestamp: float = 0.0
    repeat_count: int = 1
    
    def can_coalesce_with(self, other: 'KeyEvent', max_time_diff: float = 0.05) -> bool:
        """Check if this event can be coalesced with another."""
        if not isinstance(other, KeyEvent):
            return False
        # Only coalesce identical key events (for key repeat)
        return (self.key == other.key and 
                self.ctrl == other.ctrl and
                self.alt == other.alt and
                self.shift == other.shift and
                abs(self.timestamp - other.timestamp) <= max_time_diff)


@dataclass
class ResizeEvent:
    """Terminal resize event."""
    width: int
    height: int
    timestamp: float
    
    def can_coalesce_with(self, other: 'ResizeEvent', max_time_diff: float = 0.1) -> bool:
        """Check if this event can be coalesced with another."""
        if not isinstance(other, ResizeEvent):
            return False
        # Coalesce rapid resize events
        return abs(self.timestamp - other.timestamp) <= max_time_diff


class EventCoalescer:
    """
    Event coalescer for reducing event processing overhead.
    
    Features:
    - Coalesces rapid mouse movements into single events
    - Combines repeated key events
    - Merges rapid resize events
    - Configurable time windows and thresholds
    """
    
    def __init__(self,
                 mouse_coalesce_time: float = 0.016,  # ~60 FPS
                 key_coalesce_time: float = 0.05,     # 50ms for key repeat
                 resize_coalesce_time: float = 0.1,   # 100ms for resize
                 max_queue_size: int = 100):
        """
        Initialize event coalescer.
        
        Args:
            mouse_coalesce_time: Time window for mouse event coalescing
            key_coalesce_time: Time window for key event coalescing
            resize_coalesce_time: Time window for resize event coalescing
            max_queue_size: Maximum pending events before forced flush
        """
        self.mouse_coalesce_time = mouse_coalesce_time
        self.key_coalesce_time = key_coalesce_time
        self.resize_coalesce_time = resize_coalesce_time
        self.max_queue_size = max_queue_size
        
        # Event queues
        self.pending_events = deque(maxlen=max_queue_size)
        self.last_mouse_event: Optional[MouseMoveEvent] = None
        self.last_key_event: Optional[KeyEvent] = None
        self.last_resize_event: Optional[ResizeEvent] = None
        
        # Statistics
        self.events_received = 0
        self.events_coalesced = 0
        self.events_output = 0
    
    def add_event(self, event: Any) -> Optional[Any]:
        """
        Add an event for potential coalescing.
        
        Args:
            event: Input event
            
        Returns:
            Coalesced event if ready, None if holding for more
        """
        self.events_received += 1
        current_time = time.time()
        
        # Handle mouse movement events
        if isinstance(event, MouseMoveEvent):
            return self._handle_mouse_event(event, current_time)
        
        # Handle keyboard events
        elif isinstance(event, KeyEvent):
            return self._handle_key_event(event, current_time)
        
        # Handle resize events
        elif isinstance(event, ResizeEvent):
            return self._handle_resize_event(event, current_time)
        
        # Pass through other events immediately
        else:
            self.events_output += 1
            return event
    
    def _handle_mouse_event(self, event: MouseMoveEvent, current_time: float) -> Optional[MouseMoveEvent]:
        """Handle mouse movement event coalescing."""
        event.timestamp = current_time
        
        if self.last_mouse_event is None:
            # First mouse event, hold it
            self.last_mouse_event = event
            return None
        
        # Check if we can coalesce
        if self.last_mouse_event.can_coalesce_with(event, self.mouse_coalesce_time):
            # Coalesce: keep the latest position
            self.events_coalesced += 1
            self.last_mouse_event = event
            return None
        else:
            # Can't coalesce, output the previous event
            output = self.last_mouse_event
            self.last_mouse_event = event
            self.events_output += 1
            return output
    
    def _handle_key_event(self, event: KeyEvent, current_time: float) -> Optional[KeyEvent]:
        """Handle keyboard event coalescing."""
        event.timestamp = current_time
        
        if self.last_key_event is None:
            # First key event
            self.last_key_event = event
            return None
        
        # Check if we can coalesce (same key in rapid succession)
        if self.last_key_event.can_coalesce_with(event, self.key_coalesce_time):
            # Coalesce: increment repeat count
            self.events_coalesced += 1
            self.last_key_event.repeat_count += 1
            self.last_key_event.timestamp = current_time
            return None
        else:
            # Different key or too much time passed
            output = self.last_key_event
            self.last_key_event = event
            self.events_output += 1
            return output
    
    def _handle_resize_event(self, event: ResizeEvent, current_time: float) -> Optional[ResizeEvent]:
        """Handle resize event coalescing."""
        event.timestamp = current_time
        
        if self.last_resize_event is None:
            # First resize event
            self.last_resize_event = event
            return None
        
        # Check if we can coalesce
        if self.last_resize_event.can_coalesce_with(event, self.resize_coalesce_time):
            # Coalesce: keep the latest size
            self.events_coalesced += 1
            self.last_resize_event = event
            return None
        else:
            # Too much time passed
            output = self.last_resize_event
            self.last_resize_event = event
            self.events_output += 1
            return output
    
    def flush(self) -> List[Any]:
        """
        Flush all pending events.
        
        Returns:
            List of pending events
        """
        output = []
        
        # Flush held events in order
        if self.last_mouse_event:
            output.append(self.last_mouse_event)
            self.events_output += 1
            self.last_mouse_event = None
        
        if self.last_key_event:
            output.append(self.last_key_event)
            self.events_output += 1
            self.last_key_event = None
        
        if self.last_resize_event:
            output.append(self.last_resize_event)
            self.events_output += 1
            self.last_resize_event = None
        
        return output
    
    def get_pending_event(self, max_wait: float = 0.0) -> Optional[Any]:
        """
        Get next pending event with timeout.
        
        Args:
            max_wait: Maximum time to wait for coalescing
            
        Returns:
            Next event or None
        """
        current_time = time.time()
        
        # Check if any held events have aged out
        if self.last_mouse_event:
            if current_time - self.last_mouse_event.timestamp > self.mouse_coalesce_time:
                event = self.last_mouse_event
                self.last_mouse_event = None
                self.events_output += 1
                return event
        
        if self.last_key_event:
            if current_time - self.last_key_event.timestamp > self.key_coalesce_time:
                event = self.last_key_event
                self.last_key_event = None
                self.events_output += 1
                return event
        
        if self.last_resize_event:
            if current_time - self.last_resize_event.timestamp > self.resize_coalesce_time:
                event = self.last_resize_event
                self.last_resize_event = None
                self.events_output += 1
                return event
        
        return None
    
    def get_stats(self) -> dict:
        """Get coalescing statistics."""
        return {
            'events_received': self.events_received,
            'events_coalesced': self.events_coalesced,
            'events_output': self.events_output,
            'coalesce_ratio': self.events_coalesced / max(1, self.events_received),
            'reduction_ratio': 1.0 - (self.events_output / max(1, self.events_received))
        }
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.events_received = 0
        self.events_coalesced = 0
        self.events_output = 0