# -*- coding: utf-8 -*-
"""
Curses input handler.

This module provides input handling using the curses library,
which offers a portable interface across different Unix-like systems.
"""

import curses
from typing import Optional, List, Dict
from dataclasses import dataclass
from .base import InputHandler


@dataclass
class CursesKeyEvent:
    """Represents a curses keyboard event."""
    key: str
    code: int
    ctrl: bool = False
    alt: bool = False
    shift: bool = False


@dataclass
class CursesMouseEvent:
    """Represents a curses mouse event."""
    x: int
    y: int
    button: int
    action: str  # 'press', 'release', 'click', 'double', 'triple'


class CursesInput(InputHandler):
    """
    Curses input handler.
    
    Provides keyboard and mouse input handling through the curses library.
    Maps curses key codes to a consistent event format.
    """
    
    def __init__(self, stdscr=None):
        """
        Initialize curses input handler.
        
        Args:
            stdscr: Curses screen object (from curses.initscr())
        """
        super().__init__()
        self.stdscr = stdscr
        self.event_queue = []
        self.key_map = self._build_key_map()
        self._last_mouse_state = 0
        
    def _build_key_map(self) -> Dict[int, str]:
        """Build mapping from curses key codes to key names."""
        return {
            curses.KEY_UP: 'Up',
            curses.KEY_DOWN: 'Down',
            curses.KEY_LEFT: 'Left',
            curses.KEY_RIGHT: 'Right',
            curses.KEY_HOME: 'Home',
            curses.KEY_END: 'End',
            curses.KEY_PPAGE: 'PageUp',
            curses.KEY_NPAGE: 'PageDown',
            curses.KEY_IC: 'Insert',
            curses.KEY_DC: 'Delete',
            curses.KEY_BACKSPACE: 'Backspace',
            curses.KEY_ENTER: 'Enter',
            10: 'Enter',  # Alternative Enter
            13: 'Enter',  # CR
            27: 'Escape',
            9: 'Tab',
            curses.KEY_BTAB: 'BackTab',
            curses.KEY_F1: 'F1',
            curses.KEY_F2: 'F2',
            curses.KEY_F3: 'F3',
            curses.KEY_F4: 'F4',
            curses.KEY_F5: 'F5',
            curses.KEY_F6: 'F6',
            curses.KEY_F7: 'F7',
            curses.KEY_F8: 'F8',
            curses.KEY_F9: 'F9',
            curses.KEY_F10: 'F10',
            curses.KEY_F11: 'F11',
            curses.KEY_F12: 'F12',
        }
    
    def initialize(self) -> bool:
        """Initialize input handler."""
        if self._initialized:
            return True
        
        if not self.stdscr:
            # Curses must be initialized externally
            return False
        
        try:
            # Configure curses for input
            self.stdscr.keypad(True)  # Enable keypad for special keys
            self.stdscr.nodelay(False)  # Blocking mode by default
            self.stdscr.timeout(-1)  # No timeout by default
            
            # Enable mouse if available
            if curses.has_mouse():
                curses.mousemask(
                    curses.ALL_MOUSE_EVENTS | 
                    curses.REPORT_MOUSE_POSITION
                )
                self._mouse_enabled = True
            
            self._initialized = True
            return True
            
        except:
            return False
    
    def shutdown(self) -> None:
        """Shutdown input handler."""
        if not self._initialized:
            return
        
        try:
            if self.stdscr:
                self.stdscr.keypad(False)
                self.stdscr.nodelay(False)
                
            # Disable mouse
            if self._mouse_enabled:
                curses.mousemask(0)
                
        except:
            pass
        
        self._initialized = False
    
    def get_event(self, timeout: float = 0.0) -> Optional[object]:
        """
        Get next event with optional timeout.
        
        Args:
            timeout: Timeout in seconds (0 = non-blocking, -1 = blocking)
            
        Returns:
            Event object or None
        """
        if not self._initialized or not self.stdscr:
            return None
        
        # Check queued events first
        if self.event_queue:
            return self.event_queue.pop(0)
        
        # Set timeout mode
        if timeout < 0:
            # Blocking
            self.stdscr.timeout(-1)
        elif timeout == 0:
            # Non-blocking
            self.stdscr.nodelay(True)
        else:
            # Timed wait (convert to milliseconds)
            self.stdscr.timeout(int(timeout * 1000))
        
        try:
            # Get input from curses
            ch = self.stdscr.getch()
            
            # Check for no input
            if ch == -1:
                return None
            
            # Check for mouse event
            if ch == curses.KEY_MOUSE:
                return self._process_mouse_event()
            
            # Process keyboard event
            return self._process_key_event(ch)
            
        except:
            return None
        finally:
            # Reset to blocking mode
            self.stdscr.nodelay(False)
            self.stdscr.timeout(-1)
    
    def _process_key_event(self, ch: int) -> Optional[CursesKeyEvent]:
        """Process a keyboard event."""
        # Check for special keys
        if ch in self.key_map:
            return CursesKeyEvent(self.key_map[ch], ch)
        
        # Check for control characters
        if 0 < ch < 27:
            # Ctrl+A through Ctrl+Z
            return CursesKeyEvent(chr(ch + 64), ch, ctrl=True)
        
        # Check for Alt combinations (ESC followed by key)
        if ch == 27:  # ESC
            # Try to get next character quickly
            self.stdscr.timeout(50)  # 50ms timeout
            next_ch = self.stdscr.getch()
            self.stdscr.timeout(-1)  # Reset timeout
            
            if next_ch == -1:
                # Just ESC
                return CursesKeyEvent('Escape', 27)
            else:
                # Alt+key
                if next_ch in self.key_map:
                    return CursesKeyEvent(self.key_map[next_ch], next_ch, alt=True)
                elif 32 <= next_ch < 127:
                    return CursesKeyEvent(chr(next_ch), next_ch, alt=True)
        
        # Regular printable character
        if 32 <= ch < 127:
            return CursesKeyEvent(chr(ch), ch)
        
        # Extended ASCII or Unicode
        if ch >= 128:
            try:
                # Try to decode as UTF-8
                char = chr(ch)
                return CursesKeyEvent(char, ch)
            except:
                pass
        
        # Unknown key
        return None
    
    def _process_mouse_event(self) -> Optional[CursesMouseEvent]:
        """Process a mouse event."""
        try:
            mouse_id, x, y, z, bstate = curses.getmouse()
            
            # Determine button and action
            button = 0
            action = 'move'
            
            if bstate & curses.BUTTON1_PRESSED:
                button = 1
                action = 'press'
            elif bstate & curses.BUTTON1_RELEASED:
                button = 1
                action = 'release'
            elif bstate & curses.BUTTON1_CLICKED:
                button = 1
                action = 'click'
            elif bstate & curses.BUTTON1_DOUBLE_CLICKED:
                button = 1
                action = 'double'
            elif bstate & curses.BUTTON1_TRIPLE_CLICKED:
                button = 1
                action = 'triple'
            elif bstate & curses.BUTTON2_PRESSED:
                button = 2
                action = 'press'
            elif bstate & curses.BUTTON2_RELEASED:
                button = 2
                action = 'release'
            elif bstate & curses.BUTTON3_PRESSED:
                button = 3
                action = 'press'
            elif bstate & curses.BUTTON3_RELEASED:
                button = 3
                action = 'release'
            elif bstate & curses.BUTTON4_PRESSED:
                # Scroll up
                button = 4
                action = 'wheel'
            elif bstate & curses.BUTTON5_PRESSED:
                # Scroll down
                button = 5
                action = 'wheel'
            
            return CursesMouseEvent(x, y, button, action)
            
        except:
            return None
    
    def has_events(self) -> bool:
        """Check if events are available."""
        if self.event_queue:
            return True
        
        if self.stdscr:
            # Check for input without blocking
            self.stdscr.nodelay(True)
            ch = self.stdscr.getch()
            self.stdscr.nodelay(False)
            
            if ch != -1:
                # Put it back
                curses.ungetch(ch)
                return True
        
        return False
    
    def enable_mouse(self, enable: bool = True) -> bool:
        """Enable or disable mouse events."""
        if not curses.has_mouse():
            return False
        
        try:
            if enable:
                curses.mousemask(
                    curses.ALL_MOUSE_EVENTS | 
                    curses.REPORT_MOUSE_POSITION
                )
            else:
                curses.mousemask(0)
            
            self._mouse_enabled = enable
            return True
            
        except:
            return False
    
    def supports_mouse(self) -> bool:
        """Check if mouse is supported."""
        try:
            return curses.has_mouse()
        except:
            return False
    
    def flush_input(self) -> None:
        """Flush input buffer."""
        self.event_queue.clear()
        
        if self.stdscr:
            # Flush curses input buffer
            curses.flushinp()
    
    def get_events(self, max_count: int = 10) -> List[object]:
        """Get multiple events at once."""
        events = []
        
        # Get queued events
        while self.event_queue and len(events) < max_count:
            events.append(self.event_queue.pop(0))
        
        # Get more events
        while len(events) < max_count:
            event = self.get_event(0.0)  # Non-blocking
            if event:
                events.append(event)
            else:
                break
        
        return events