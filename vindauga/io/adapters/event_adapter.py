"""
Event adapter for translating between new I/O system events and Vindauga events.

This adapter provides bidirectional translation between the new I/O system's
event format and Vindauga's existing event system, ensuring backward compatibility.
"""

import logging
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass

# Import Vindauga event system
from vindauga.events.event import Event
from vindauga.events.key_down_event import KeyDownEvent
from vindauga.events.mouse_event import MouseEvent
from vindauga.constants.event_codes import (
    evKeyDown, evMouseDown, evMouseUp, evMouseMove,
    evNothing, evCommand
)
from vindauga.constants.keys import *
from vindauga.constants.mouse_button_state_masks import *

logger = logging.getLogger(__name__)


@dataclass
class NewIOEvent:
    """Base class for new I/O system events."""
    timestamp: float = 0.0


@dataclass
class KeyEvent(NewIOEvent):
    """Keyboard event from new I/O system."""
    key_code: int = 0
    scan_code: int = 0
    modifiers: int = 0
    char: str = ''
    is_special: bool = False


@dataclass
class MouseEvent(NewIOEvent):
    """Mouse event from new I/O system."""
    x: int = 0
    y: int = 0
    buttons: int = 0
    event_type: str = 'move'  # 'move', 'down', 'up', 'wheel'
    wheel_delta: int = 0


@dataclass
class ResizeEvent(NewIOEvent):
    """Terminal resize event from new I/O system."""
    width: int = 0
    height: int = 0


class EventAdapter:
    """
    Translates between new I/O system events and Vindauga events.
    
    This adapter ensures that the new I/O system can work seamlessly
    with existing Vindauga code without requiring changes to event handling.
    """
    
    # Key mapping from new I/O to Vindauga key codes
    KEY_MAP = {
        # Special keys
        '\x1b': kbEsc,
        '\r': kbEnter,
        '\n': kbEnter,
        '\t': kbTab,
        '\x7f': kbBack,
        '\x08': kbBack,
        
        # Function keys (ANSI sequences will be mapped)
        'F1': kbF1,
        'F2': kbF2,
        'F3': kbF3,
        'F4': kbF4,
        'F5': kbF5,
        'F6': kbF6,
        'F7': kbF7,
        'F8': kbF8,
        'F9': kbF9,
        'F10': kbF10,
        'F11': kbF11,
        'F12': kbF12,
        
        # Navigation keys
        'UP': kbUp,
        'DOWN': kbDown,
        'LEFT': kbLeft,
        'RIGHT': kbRight,
        'HOME': kbHome,
        'END': kbEnd,
        'PGUP': kbPgUp,
        'PGDN': kbPgDn,
        'INS': kbIns,
        'DEL': kbDel,
    }
    
    # Modifier key mapping
    MODIFIER_MAP = {
        'shift': kbShift,
        'ctrl': kbCtrlShift,
        'alt': kbAltShift,
    }
    
    def __init__(self):
        """Initialize the event adapter."""
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.last_mouse_buttons = 0
        
    def translate_to_vindauga(self, new_event: Union[KeyEvent, MouseEvent, ResizeEvent, Any]) -> Optional[Event]:
        """
        Translate a new I/O system event to a Vindauga event.
        
        Args:
            new_event: Event from the new I/O system
            
        Returns:
            Vindauga Event object or None if translation not possible
        """
        if new_event is None:
            return None
            
        # Handle different event types
        if isinstance(new_event, KeyEvent) or (hasattr(new_event, 'key_code') or hasattr(new_event, 'char')):
            return self._translate_key_event(new_event)
        elif isinstance(new_event, MouseEvent) or (hasattr(new_event, 'x') and hasattr(new_event, 'y')):
            return self._translate_mouse_event(new_event)
        elif isinstance(new_event, ResizeEvent) or (hasattr(new_event, 'width') and hasattr(new_event, 'height')):
            return self._translate_resize_event(new_event)
        elif hasattr(new_event, 'what'):
            # Already a Vindauga event, pass through
            return new_event
        else:
            logger.debug(f"Unknown event type: {type(new_event)}")
            return None
    
    def _translate_key_event(self, key_event: Union[KeyEvent, Any]) -> Event:
        """Translate a keyboard event."""
        event = Event(evKeyDown)
        
        # Get key code
        if hasattr(key_event, 'key_code'):
            key_code = key_event.key_code
        elif hasattr(key_event, 'char'):
            if key_event.char in self.KEY_MAP:
                key_code = self.KEY_MAP[key_event.char]
            elif len(key_event.char) == 1:
                key_code = ord(key_event.char)
            else:
                key_code = 0
        else:
            key_code = 0
        
        # Handle special keys
        if hasattr(key_event, 'is_special') and key_event.is_special:
            if hasattr(key_event, 'name') and key_event.name in self.KEY_MAP:
                key_code = self.KEY_MAP[key_event.name]
        
        # Apply modifiers
        if hasattr(key_event, 'modifiers'):
            if key_event.modifiers & 1:  # Shift
                key_code |= kbShift
            if key_event.modifiers & 2:  # Ctrl
                key_code |= kbCtrlShift
            if key_event.modifiers & 4:  # Alt
                key_code |= kbAltShift
        
        # Handle Ctrl+letter combinations
        if hasattr(key_event, 'char') and len(key_event.char) == 1:
            char_code = ord(key_event.char)
            if 1 <= char_code <= 26:  # Ctrl+A through Ctrl+Z
                key_code = kbCtrlA + (char_code - 1)
        
        event.keyDown.keyCode = key_code
        event.keyDown.charScan.charCode = key_code & 0xFF
        event.keyDown.charScan.scanCode = (key_code >> 8) & 0xFF
        
        return event
    
    def _translate_mouse_event(self, mouse_event: Union[MouseEvent, Any]) -> Event:
        """Translate a mouse event."""
        # Determine event type
        if hasattr(mouse_event, 'event_type'):
            if mouse_event.event_type == 'down':
                what = evMouseDown
            elif mouse_event.event_type == 'up':
                what = evMouseUp
            elif mouse_event.event_type == 'move':
                what = evMouseMove
            else:
                what = evMouseMove
        else:
            # Try to infer from button state changes
            if hasattr(mouse_event, 'buttons'):
                if mouse_event.buttons > self.last_mouse_buttons:
                    what = evMouseDown
                elif mouse_event.buttons < self.last_mouse_buttons:
                    what = evMouseUp
                else:
                    what = evMouseMove
            else:
                what = evMouseMove
        
        event = Event(what)
        
        # Set mouse coordinates
        if hasattr(mouse_event, 'x'):
            event.mouse.where.x = mouse_event.x
            self.last_mouse_x = mouse_event.x
        else:
            event.mouse.where.x = self.last_mouse_x
            
        if hasattr(mouse_event, 'y'):
            event.mouse.where.y = mouse_event.y
            self.last_mouse_y = mouse_event.y
        else:
            event.mouse.where.y = self.last_mouse_y
        
        # Set button state
        buttons = 0
        if hasattr(mouse_event, 'buttons'):
            mouse_buttons = mouse_event.buttons
            if mouse_buttons & 1:  # Left button
                buttons |= mbLeftButton
            if mouse_buttons & 2:  # Right button
                buttons |= mbRightButton
            if mouse_buttons & 4:  # Middle button
                buttons |= mbMiddleButton
            self.last_mouse_buttons = mouse_buttons
        else:
            buttons = self.last_mouse_buttons
            
        event.mouse.buttons = buttons
        event.mouse.eventFlags = 0
        event.mouse.controlKeyState = 0
        
        # Handle wheel events
        if hasattr(mouse_event, 'wheel_delta') and mouse_event.wheel_delta != 0:
            event.mouse.wheel = mouse_event.wheel_delta
        else:
            event.mouse.wheel = 0
        
        return event
    
    def _translate_resize_event(self, resize_event: Union[ResizeEvent, Any]) -> Event:
        """
        Translate a terminal resize event.
        
        Note: Vindauga doesn't have a specific resize event type,
        so we return a command event that can be handled specially.
        """
        event = Event(evCommand)
        event.message.command = 0xFFFF  # Special resize command
        
        if hasattr(resize_event, 'width') and hasattr(resize_event, 'height'):
            # Store dimensions in the message
            event.message.infoInt = (resize_event.height << 16) | resize_event.width
        
        return event
    
    def translate_from_vindauga(self, vindauga_event: Event) -> Optional[Union[KeyEvent, MouseEvent]]:
        """
        Translate a Vindauga event to new I/O system event.
        
        This is used when Vindauga code generates events that need
        to be processed by the new I/O system.
        
        Args:
            vindauga_event: Vindauga Event object
            
        Returns:
            New I/O system event or None
        """
        if vindauga_event.what == evKeyDown:
            return self._translate_vindauga_key_event(vindauga_event)
        elif vindauga_event.what in (evMouseDown, evMouseUp, evMouseMove):
            return self._translate_vindauga_mouse_event(vindauga_event)
        else:
            return None
    
    def _translate_vindauga_key_event(self, event: Event) -> KeyEvent:
        """Translate a Vindauga keyboard event to new I/O format."""
        key_event = KeyEvent()
        
        key_code = event.keyDown.keyCode
        key_event.key_code = key_code
        
        # Extract modifiers
        modifiers = 0
        if key_code & kbShift:
            modifiers |= 1
        if key_code & kbCtrlShift:
            modifiers |= 2
        if key_code & kbAltShift:
            modifiers |= 4
        key_event.modifiers = modifiers
        
        # Get base key
        base_key = key_code & 0xFF
        if 32 <= base_key <= 126:
            key_event.char = chr(base_key)
        
        # Check for special keys
        for name, code in self.KEY_MAP.items():
            if (key_code & ~(kbShift | kbCtrlShift | kbAltShift)) == code:
                key_event.is_special = True
                break
        
        return key_event
    
    def _translate_vindauga_mouse_event(self, event: Event) -> MouseEvent:
        """Translate a Vindauga mouse event to new I/O format."""
        mouse_event = MouseEvent()
        
        mouse_event.x = event.mouse.where.x
        mouse_event.y = event.mouse.where.y
        
        # Translate button state
        buttons = 0
        if event.mouse.buttons & mbLeftButton:
            buttons |= 1
        if event.mouse.buttons & mbRightButton:
            buttons |= 2
        if event.mouse.buttons & mbMiddleButton:
            buttons |= 4
        mouse_event.buttons = buttons
        
        # Determine event type
        if event.what == evMouseDown:
            mouse_event.event_type = 'down'
        elif event.what == evMouseUp:
            mouse_event.event_type = 'up'
        else:
            mouse_event.event_type = 'move'
        
        # Handle wheel
        if hasattr(event.mouse, 'wheel'):
            mouse_event.wheel_delta = event.mouse.wheel
        
        return mouse_event
    
    def reset(self):
        """Reset adapter state."""
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.last_mouse_buttons = 0