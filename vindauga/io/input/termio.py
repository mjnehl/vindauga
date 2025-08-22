# -*- coding: utf-8 -*-
"""
TermIO input handler for Unix/Linux systems.

This module provides high-performance input handling using direct
termios control for Unix-like systems.
"""

import sys
import os
import select
import fcntl
import termios
from typing import Optional, List
from .base import InputHandler
from .ansi import ANSIEscapeParser, ParsedKey, ParsedMouse


class TermIOInput(InputHandler):
    """
    TermIO input handler for Unix/Linux.
    
    Uses select() for efficient non-blocking I/O and provides
    high-performance event processing with minimal latency.
    """
    
    def __init__(self):
        """Initialize TermIO input handler."""
        super().__init__()
        self.stdin_fd = None
        self.parser = ANSIEscapeParser()
        self.input_buffer = bytearray(4096)
        self.event_queue = []
        self.partial_sequence = bytearray()
        
    def initialize(self) -> bool:
        """Initialize input handler."""
        if self._initialized:
            return True
        
        try:
            # Get stdin file descriptor
            if hasattr(sys.stdin, 'fileno'):
                self.stdin_fd = sys.stdin.fileno()
            else:
                return False
            
            # Check if stdin is a TTY
            if not os.isatty(self.stdin_fd):
                return False
            
            # Set non-blocking mode
            flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            self._initialized = True
            return True
            
        except:
            return False
    
    def shutdown(self) -> None:
        """Shutdown input handler."""
        if not self._initialized:
            return
        
        try:
            # Restore blocking mode
            if self.stdin_fd is not None:
                flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
        except:
            pass
        
        self._initialized = False
    
    def get_event(self, timeout: float = 0.0) -> Optional[object]:
        """
        Get next event with optional timeout.
        
        Uses select() for efficient waiting and handles partial
        escape sequences across reads.
        
        Args:
            timeout: Timeout in seconds (0 = non-blocking, -1 = blocking)
            
        Returns:
            Event object or None
        """
        if not self._initialized:
            return None
        
        # Check queued events first
        if self.event_queue:
            return self.event_queue.pop(0)
        
        # Process any partial sequence first
        if self.partial_sequence:
            for byte in self.partial_sequence:
                result = self.parser.parse_byte(byte)
                if result:
                    self.partial_sequence.clear()
                    return result
            # If we still have partial sequence, continue reading
        
        # Wait for input using select
        if timeout < 0:
            # Blocking wait
            ready, _, _ = select.select([self.stdin_fd], [], [])
        elif timeout == 0:
            # Non-blocking check
            ready, _, _ = select.select([self.stdin_fd], [], [], 0)
        else:
            # Timed wait
            ready, _, _ = select.select([self.stdin_fd], [], [], timeout)
        
        if not ready:
            return None
        
        # Read available input
        try:
            # Use larger buffer for better performance
            nbytes = os.readv(self.stdin_fd, [self.input_buffer])
            if nbytes <= 0:
                return None
            
            # Process bytes through parser
            for i in range(nbytes):
                byte = self.input_buffer[i]
                result = self.parser.parse_byte(byte)
                if result:
                    # Save remaining bytes as partial sequence
                    if i + 1 < nbytes:
                        self.partial_sequence = bytearray(self.input_buffer[i+1:nbytes])
                    return result
            
            # All bytes processed but no complete sequence
            # This might be a partial escape sequence
            self.partial_sequence.extend(self.input_buffer[:nbytes])
            
        except (OSError, IOError):
            return None
        
        return None
    
    def has_events(self) -> bool:
        """Check if events are available."""
        if self.event_queue:
            return True
        
        if self.partial_sequence:
            return True
        
        # Use select with 0 timeout to check for available input
        if self.stdin_fd:
            ready, _, _ = select.select([self.stdin_fd], [], [], 0)
            return bool(ready)
        
        return False
    
    def enable_mouse(self, enable: bool = True) -> bool:
        """Enable or disable mouse events."""
        # Mouse enabling is typically handled by the display backend
        # which sends the appropriate escape sequences
        self._mouse_enabled = enable
        return True
    
    def supports_mouse(self) -> bool:
        """Check if mouse is supported."""
        # TermIO on Unix systems generally supports mouse
        return True
    
    def flush_input(self) -> None:
        """Flush input buffer."""
        self.event_queue.clear()
        self.partial_sequence.clear()
        self.parser.reset()
        
        # Drain stdin
        if self.stdin_fd:
            try:
                # Set to non-blocking temporarily
                flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                # Read and discard all available input
                while True:
                    ready, _, _ = select.select([self.stdin_fd], [], [], 0)
                    if not ready:
                        break
                    try:
                        os.read(self.stdin_fd, 4096)
                    except:
                        break
                
                # Restore original flags
                fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags)
                
            except:
                pass
    
    def get_events(self, max_count: int = 10) -> List[object]:
        """
        Get multiple events at once.
        
        Optimized to read all available input in one go and
        process multiple events efficiently.
        """
        events = []
        
        # First get any queued events
        while self.event_queue and len(events) < max_count:
            events.append(self.event_queue.pop(0))
        
        # Then try to read more
        while len(events) < max_count:
            event = self.get_event(0.0)  # Non-blocking
            if event:
                events.append(event)
            else:
                break
        
        return events