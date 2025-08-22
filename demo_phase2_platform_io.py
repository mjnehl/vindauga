#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 Platform I/O Demonstration

This demo showcases the multi-platform terminal I/O system with:
- Automatic platform detection
- Display buffer rendering
- Input event handling
- Color support
"""

import sys
import time
import signal
from vindauga.io import (
    PlatformIO, PlatformDetector, PlatformType,
    DisplayBuffer, ScreenCell
)


def cleanup(display, input_handler):
    """Clean up terminal state."""
    try:
        # Disable mouse first
        if display and hasattr(display, 'enable_mouse'):
            display.enable_mouse(False)
    except:
        pass
    
    if input_handler:
        try:
            input_handler.shutdown()
        except:
            pass
    if display:
        try:
            display.shutdown()
        except:
            pass


def demo_platform_detection():
    """Demonstrate platform detection."""
    print("=" * 60)
    print("PHASE 2: PLATFORM DETECTION")
    print("=" * 60)
    
    detector = PlatformDetector()
    info = detector.get_platform_info()
    
    print(f"\nSystem: {info['system']}")
    print(f"Is TTY: {info['is_tty']}")
    print(f"Terminal: {info['term']}")
    
    print("\nAvailable Platforms:")
    for platform_name, caps in info['platform_capabilities'].items():
        if caps['available']:
            print(f"  ✓ {platform_name}: Score={caps['score']}, Colors={caps['colors']}")
        else:
            print(f"  ✗ {platform_name}: Not available")
    
    best_platform = detector.select_best_platform()
    if best_platform:
        print(f"\n🎯 Best Platform: {best_platform.name}")
    
    return best_platform


def demo_display_output(display, buffer):
    """Demonstrate display output with colors and attributes."""
    # Title bar
    title = " Phase 2 Demo - Terminal I/O "
    x = (buffer.width - len(title)) // 2
    buffer.put_text(x, 0, title, fg=0, bg=4, attrs=ScreenCell.ATTR_BOLD)
    
    # Color palette demo
    y = 2
    buffer.put_text(2, y, "16-Color Palette:", fg=7, bg=0)
    y += 2
    
    # Show 16 colors
    for color in range(16):
        x = 2 + (color % 8) * 9
        if color == 8:
            y += 2
        label = f"Color {color:2}"
        buffer.put_text(x, y, label, fg=color, bg=0)
    
    # Text attributes demo
    y += 4
    buffer.put_text(2, y, "Text Attributes:", fg=7, bg=0)
    y += 2
    
    buffer.put_text(2, y, "Normal text", fg=7, bg=0)
    y += 1
    buffer.put_text(2, y, "Bold text", fg=7, bg=0, attrs=ScreenCell.ATTR_BOLD)
    y += 1
    buffer.put_text(2, y, "Underlined text", fg=7, bg=0, attrs=ScreenCell.ATTR_UNDERLINE)
    y += 1
    buffer.put_text(2, y, "Reverse video", fg=7, bg=0, attrs=ScreenCell.ATTR_REVERSE)
    
    # Wide character support
    y += 3
    buffer.put_text(2, y, "Wide Characters:", fg=7, bg=0)
    y += 2
    buffer.put_text(2, y, "English: Hello, World!", fg=2, bg=0)
    y += 1
    buffer.put_text(2, y, "中文: 你好，世界！", fg=3, bg=0)
    y += 1
    buffer.put_text(2, y, "日本語: こんにちは", fg=6, bg=0)
    y += 1
    buffer.put_text(2, y, "Emoji: 🎉 🚀 ⭐ 💻", fg=5, bg=0)
    
    # Instructions
    y = buffer.height - 3
    buffer.put_text(2, y, "Press 'q' to quit, arrow keys to test input", 
                   fg=7, bg=0, attrs=ScreenCell.ATTR_BOLD)
    
    # Flush to display
    display.flush_buffer(buffer)


def demo_input_handling(input_handler, display, buffer):
    """Demonstrate input event handling."""
    # Status line position
    status_y = buffer.height - 1
    
    print_status = lambda msg: (
        buffer.clear_rect(0, status_y, buffer.width, 1),
        buffer.put_text(2, status_y, msg, fg=0, bg=7),
        display.flush_buffer(buffer)
    )
    
    print_status("Ready for input... (Press 'q' to quit)")
    
    while True:
        # Get input event
        event = input_handler.get_event(0.1)  # 100ms timeout
        
        if event:
            # Check event type
            if hasattr(event, 'key'):
                # Keyboard event
                key = event.key
                
                # Build status message
                msg = f"Key: {key}"
                if event.ctrl:
                    msg += " [Ctrl]"
                if event.alt:
                    msg += " [Alt]"
                if event.shift:
                    msg += " [Shift]"
                
                print_status(msg)
                
                # Check for quit
                if key.lower() == 'q':
                    break
                    
            elif hasattr(event, 'x'):
                # Mouse event
                msg = f"Mouse: ({event.x}, {event.y}) Button={event.button} Action={event.action}"
                print_status(msg)


def main():
    """Run the Phase 2 platform I/O demo."""
    display = None
    input_handler = None
    
    # Set up signal handler for cleanup
    def signal_handler(signum, frame):
        cleanup(display, input_handler)
        import sys as sys_module
        sys_module.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Detect platforms
        best_platform = demo_platform_detection()
        
        if not best_platform:
            print("\n❌ No suitable platform available!")
            return 1
        
        print("\n" + "=" * 60)
        print("INITIALIZING PLATFORM I/O")
        print("=" * 60)
        
        # Create platform I/O
        display, input_handler = PlatformIO.create(best_platform)
        
        # Initialize backends
        if not display.initialize():
            print("❌ Failed to initialize display")
            return 1
        
        if not input_handler.initialize():
            print("❌ Failed to initialize input")
            return 1
        
        # Don't print after display is initialized (it interferes with alternate screen)
        # These values can be shown in the display itself
        
        # Enable mouse if supported
        mouse_enabled = False
        if input_handler.supports_mouse() and hasattr(display, 'enable_mouse'):
            mouse_enabled = display.enable_mouse(True)
        
        # Create display buffer
        buffer = DisplayBuffer(display.width, display.height)
        
        # Demo display output
        demo_display_output(display, buffer)
        
        # Demo input handling
        demo_input_handling(input_handler, display, buffer)
        
        print("\n✓ Demo completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Clean up - ensure mouse is disabled
        if display:
            try:
                # Explicitly disable mouse
                display.enable_mouse(False)
                # Force a flush to ensure mouse disable sequence is sent
                import sys
                sys.stdout.write('\x1b[?1000l\x1b[?1006l')  # Disable X11 and SGR mouse
                sys.stdout.flush()
            except:
                pass
        
        # Clean up display and input
        cleanup(display, input_handler)


if __name__ == '__main__':
    sys.exit(main())