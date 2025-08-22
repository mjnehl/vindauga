# -*- coding: utf-8 -*-
"""
Improved ANSI input handler with event coalescing and error recovery.

This module combines the fixed ANSI input handler with event coalescing
and error recovery for a production-ready implementation.
"""

import sys
import os
import select
import time
import logging
from typing import Optional, List, Any
from .ansi_fixed import ANSIInput as BaseANSIInput
from ..event_coalescer import EventCoalescer, MouseMoveEvent, KeyEvent
from ..error_recovery import ErrorRecoveryManager, ResilientIO


class ImprovedANSIInput(BaseANSIInput):
    """
    Production-ready ANSI input handler with:
    - Event coalescing for performance
    - Error recovery for reliability
    - Configurable Ctrl+C handling
    - Comprehensive cleanup
    """
    
    def __init__(self, 
                 allow_ctrl_c: bool = True,
                 enable_coalescing: bool = True,
                 enable_error_recovery: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize improved ANSI input handler.
        
        Args:
            allow_ctrl_c: If True, Ctrl+C triggers SIGINT
            enable_coalescing: Enable event coalescing
            enable_error_recovery: Enable error recovery
            logger: Optional logger
        """
        super().__init__(allow_ctrl_c=allow_ctrl_c)
        
        self.enable_coalescing = enable_coalescing
        self.enable_error_recovery = enable_error_recovery
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize subsystems
        if enable_coalescing:
            self.coalescer = EventCoalescer()
        else:
            self.coalescer = None
        
        if enable_error_recovery:
            self.error_recovery = ErrorRecoveryManager(logger=self.logger)
            self.resilient_io = ResilientIO(self.error_recovery)
            
            # Register fallback handlers
            self.error_recovery.register_fallback("input", self._fallback_to_basic_input)
        else:
            self.error_recovery = None
            self.resilient_io = None
        
        # Statistics
        self.total_events = 0
        self.coalesced_events = 0
        self.error_count = 0
    
    def _fallback_to_basic_input(self) -> Optional[Any]:
        """Fallback to basic input mode on errors."""
        self.logger.warning("Falling back to basic input mode")
        
        # Disable advanced features
        self.enable_coalescing = False
        
        # Try to read a single character
        try:
            if self.stdin_fd is not None:
                data = os.read(self.stdin_fd, 1)
                if data:
                    # Return basic key event
                    from .ansi_fixed import ParsedKey
                    return ParsedKey(chr(data[0]))
        except:
            pass
        
        return None
    
    def get_event(self, timeout: float = 0.0) -> Optional[object]:
        """
        Get next event with coalescing and error recovery.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Event object or None
        """
        if not self._initialized:
            return None
        
        # Check for coalesced events first
        if self.coalescer:
            event = self.coalescer.get_pending_event()
            if event:
                return event
        
        # Try to get raw event with error recovery
        if self.enable_error_recovery and self.resilient_io:
            try:
                raw_event = self._get_raw_event_safe(timeout)
            except Exception as e:
                self.error_count += 1
                raw_event = self.error_recovery.handle_error(
                    e, "input", "get_event"
                )
        else:
            raw_event = super().get_event(timeout)
        
        if raw_event is None:
            return None
        
        self.total_events += 1
        
        # Apply coalescing if enabled
        if self.coalescer:
            # Convert to coalesceable event type if possible
            coalesced = self._to_coalesceable(raw_event)
            if coalesced:
                result = self.coalescer.add_event(coalesced)
                if result:
                    self.coalesced_events += 1
                    return result
                # Event held for coalescing
                return None
            else:
                # Pass through non-coalesceable events
                return raw_event
        
        return raw_event
    
    def _get_raw_event_safe(self, timeout: float) -> Optional[object]:
        """Get raw event with error recovery."""
        # Check queued events first
        if self.event_queue:
            return self.event_queue.pop(0)
        
        # Read available input with error recovery
        if timeout < 0:
            ready = True
        elif timeout == 0:
            ready, _, _ = select.select([self.stdin_fd], [], [], 0)
        else:
            ready, _, _ = select.select([self.stdin_fd], [], [], timeout)
        
        if not ready:
            return None
        
        # Read with error recovery
        data = self.resilient_io.safe_read(self.stdin_fd, 4096, "input")
        if not data:
            return None
        
        # Parse input bytes
        for byte in data:
            result = self.parser.parse_byte(byte)
            if result:
                event = self._convert_to_event(result)
                if event:
                    self.event_queue.append(event)
        
        # Return first event if available
        if self.event_queue:
            return self.event_queue.pop(0)
        
        return None
    
    def _to_coalesceable(self, event: Any) -> Optional[Any]:
        """Convert event to coalesceable type if possible."""
        # Check if it's a parsed key event
        if hasattr(event, 'key'):
            return KeyEvent(
                key=event.key,
                ctrl=getattr(event, 'ctrl', False),
                alt=getattr(event, 'alt', False),
                shift=getattr(event, 'shift', False),
                timestamp=time.time()
            )
        
        # Check if it's a mouse event
        elif hasattr(event, 'x') and hasattr(event, 'y'):
            if getattr(event, 'action', '') == 'move':
                return MouseMoveEvent(
                    x=event.x,
                    y=event.y,
                    timestamp=time.time()
                )
        
        # Not coalesceable
        return None
    
    def flush_events(self) -> List[Any]:
        """
        Flush all pending coalesced events.
        
        Returns:
            List of pending events
        """
        if self.coalescer:
            return self.coalescer.flush()
        return []
    
    def get_statistics(self) -> dict:
        """Get input handler statistics."""
        stats = {
            'total_events': self.total_events,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.total_events)
        }
        
        if self.coalescer:
            coalesce_stats = self.coalescer.get_stats()
            stats.update(coalesce_stats)
        
        if self.error_recovery:
            stats['error_patterns'] = self.error_recovery.detect_error_patterns()
            stats['should_degrade'] = self.error_recovery.should_degrade_mode()
        
        return stats
    
    def reset_statistics(self):
        """Reset all statistics."""
        self.total_events = 0
        self.coalesced_events = 0
        self.error_count = 0
        
        if self.coalescer:
            self.coalescer.reset_stats()
        
        if self.error_recovery:
            self.error_recovery.clear_history()
    
    def shutdown(self) -> None:
        """Enhanced shutdown with statistics reporting."""
        if self._initialized:
            # Log final statistics
            stats = self.get_statistics()
            if stats['total_events'] > 0:
                self.logger.info(f"Input handler statistics: {stats}")
        
        # Flush any pending events
        if self.coalescer:
            pending = self.flush_events()
            if pending:
                self.logger.debug(f"Flushed {len(pending)} pending events on shutdown")
        
        # Call parent shutdown
        super().shutdown()