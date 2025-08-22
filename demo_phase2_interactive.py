#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Phase 2 Demo

A working demonstration of the Phase 2 platform I/O system.
"""

import sys
import os
import time
from vindauga.io import (
    PlatformIO, PlatformDetector, PlatformType,
    DisplayBuffer, ScreenCell
)


def main():
    """Run interactive demo."""
    display = None
    input_handler = None
    
    print("=" * 60)
    print("PHASE 2 INTERACTIVE DEMO")
    print("=" * 60)
    
    try:
        # Detect best platform
        detector = PlatformDetector()
        best = detector.select_best_platform()
        
        if not best:
            print("No suitable platform available!")
            return 1
        
        print(f"\nUsing platform: {best.name}")
        
        # Create platform I/O
        display, input_handler = PlatformIO.create(best)
        
        # Initialize display
        if not display.initialize():
            print("Failed to initialize display")
            return 1
        
        # Initialize input
        if not input_handler.initialize():
            print("Failed to initialize input")  
            return 1
        
        print(f"Display size: {display.width}x{display.height}")
        print("\nStarting interactive mode...")
        time.sleep(1)
        
        # Create display buffer
        buffer = DisplayBuffer(display.width, display.height)
        
        # Draw UI
        draw_ui(buffer, display)
        
        # Event loop
        cursor_x = 10
        cursor_y = 10
        message = "Ready"
        
        while True:
            # Update status
            update_status(buffer, display, message)
            
            # Get input
            event = input_handler.get_event(0.05)  # 50ms timeout
            
            if event:
                if hasattr(event, 'key'):
                    # Keyboard event
                    key = event.key
                    
                    # Exit on 'q'
                    if key.lower() == 'q':
                        break
                    
                    # Handle arrow keys
                    elif key == 'Up' and cursor_y > 5:
                        cursor_y -= 1
                    elif key == 'Down' and cursor_y < display.height - 5:
                        cursor_y += 1
                    elif key == 'Left' and cursor_x > 2:
                        cursor_x -= 1
                    elif key == 'Right' and cursor_x < display.width - 2:
                        cursor_x += 1
                    
                    # Update cursor position
                    buffer.put_char(cursor_x, cursor_y, '█', fg=15, bg=0)
                    display.flush_buffer(buffer)
                    
                    # Update message
                    modifiers = []
                    if event.ctrl:
                        modifiers.append("Ctrl")
                    if event.alt:
                        modifiers.append("Alt")
                    if event.shift:
                        modifiers.append("Shift")
                    
                    if modifiers:
                        message = f"Key: {key} [{'+'.join(modifiers)}]"
                    else:
                        message = f"Key: {key}"
                
                elif hasattr(event, 'x'):
                    # Mouse event
                    message = f"Mouse: ({event.x},{event.y}) B{event.button} {event.action}"
                    
                    # Move cursor to mouse position
                    if event.action in ('press', 'click'):
                        if 2 <= event.x < display.width - 2 and 5 <= event.y < display.height - 5:
                            # Clear old cursor
                            buffer.put_char(cursor_x, cursor_y, ' ', fg=7, bg=0)
                            # Update position
                            cursor_x = event.x
                            cursor_y = event.y
                            # Draw new cursor
                            buffer.put_char(cursor_x, cursor_y, '█', fg=15, bg=0)
                            display.flush_buffer(buffer)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Clean up
        if display:
            try:
                # Disable mouse
                display.enable_mouse(False)
                # Clear screen
                display.clear_screen()
                # Shutdown
                display.shutdown()
            except:
                pass
        
        if input_handler:
            try:
                input_handler.shutdown()
            except:
                pass
        
        # Force disable mouse as fallback
        try:
            sys.stdout.write('\x1b[?1000l\x1b[?1006l')
            sys.stdout.flush()
        except:
            pass
        
        print("\nDemo ended.")


def draw_ui(buffer, display):
    """Draw the user interface."""
    # Clear buffer
    buffer.clear()
    
    # Title bar
    title = " Phase 2 Interactive Demo "
    x = (buffer.width - len(title)) // 2
    buffer.put_text(x, 0, title, fg=0, bg=7, attrs=ScreenCell.ATTR_BOLD)
    
    # Instructions
    buffer.put_text(2, 2, "Instructions:", fg=15, bg=0, attrs=ScreenCell.ATTR_BOLD)
    buffer.put_text(4, 3, "• Use arrow keys to move cursor", fg=7, bg=0)
    buffer.put_text(4, 4, "• Click mouse to position cursor", fg=7, bg=0)
    buffer.put_text(4, 5, "• Press 'q' to quit", fg=7, bg=0)
    
    # Draw border
    for x in range(buffer.width):
        buffer.put_char(x, 7, '─', fg=8, bg=0)
        buffer.put_char(x, buffer.height - 3, '─', fg=8, bg=0)
    
    # Initial cursor
    buffer.put_char(10, 10, '█', fg=15, bg=0)
    
    # Status line at bottom
    buffer.put_text(2, buffer.height - 2, "Status:", fg=15, bg=0, attrs=ScreenCell.ATTR_BOLD)
    
    # Flush to display
    display.flush_buffer(buffer)


def update_status(buffer, display, message):
    """Update status line."""
    # Clear status area
    buffer.clear_rect(10, buffer.height - 2, buffer.width - 12, 1)
    # Write status
    buffer.put_text(10, buffer.height - 2, message, fg=10, bg=0)
    # Flush changes
    display.flush_buffer(buffer)


if __name__ == '__main__':
    sys.exit(main())