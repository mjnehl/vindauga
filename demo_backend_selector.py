#!/usr/bin/env python3
"""Demo that allows manual backend selection for testing."""

import sys
from vindauga.io import PlatformIO, PlatformType, DisplayBuffer, ScreenCell

def show_menu():
    """Show backend selection menu."""
    print("\nTVision I/O Backend Selector")
    print("="*40)
    print("1. ANSI (escape sequences)")
    print("2. TermIO (Unix terminal I/O)")
    print("3. Curses (ncurses wrapper)")
    print("4. Auto-detect best")
    print("0. Exit")
    print()
    
    choice = input("Select backend (0-4): ").strip()
    
    if choice == '1':
        return PlatformType.ANSI, "ANSI"
    elif choice == '2':
        return PlatformType.TERMIO, "TermIO"
    elif choice == '3':
        return PlatformType.CURSES, "Curses"
    elif choice == '4':
        return None, "Auto"
    elif choice == '0':
        return 'EXIT', None
    else:
        print("Invalid choice!")
        return None, None

def test_backend(platform_type, name):
    """Test a specific backend."""
    print(f"\nTesting {name} backend...")
    
    try:
        # Create platform
        if platform_type:
            display, input_handler = PlatformIO.create(platform_type)
        else:
            # Auto-detect
            display, input_handler = PlatformIO.create()
            name = f"Auto ({display.__class__.__name__})"
        
        # Initialize
        if not display.initialize():
            print(f"❌ Failed to initialize {name} display")
            return False
        
        if not input_handler.initialize():
            print(f"❌ Failed to initialize {name} input")
            display.shutdown()
            return False
        
        # Reset stdout to blocking mode after display init
        import fcntl
        import os
        if hasattr(sys.stdout, 'fileno'):
            try:
                fd = sys.stdout.fileno()
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
            except:
                pass
        
        print(f"✓ {name} backend initialized")
        print(f"  Size: {display.width}x{display.height}")
        print(f"  Colors: {display.get_color_count():,}")
        print(f"  Mouse: {input_handler.supports_mouse()}")
        
        # Create test display
        buffer = DisplayBuffer(display.width, display.height)
        
        # Title
        title = f" {name} Backend Test "
        x = (display.width - len(title)) // 2
        buffer.put_text(x, 1, title, fg=0, bg=7, attrs=ScreenCell.ATTR_BOLD)
        
        # Backend info
        y = 3
        buffer.put_text(2, y, f"Backend: {display.__class__.__name__}", fg=7, bg=0)
        y += 1
        buffer.put_text(2, y, f"Display: {display.width}x{display.height}", fg=7, bg=0)
        y += 1
        buffer.put_text(2, y, f"Colors: {display.get_color_count():,}", fg=7, bg=0)
        y += 1
        buffer.put_text(2, y, f"Mouse: {'Yes' if input_handler.supports_mouse() else 'No'}", fg=7, bg=0)
        
        # Color test
        y += 2
        buffer.put_text(2, y, "16-Color Test:", fg=7, bg=0)
        y += 1
        for i in range(16):
            x = 2 + (i % 8) * 4
            if i == 8:
                y += 1
            buffer.put_text(x, y, f"█{i:2}", fg=i, bg=0)
        
        # Attributes test
        y += 2
        buffer.put_text(2, y, "Attributes:", fg=7, bg=0)
        y += 1
        buffer.put_text(2, y, "Bold", fg=7, bg=0, attrs=ScreenCell.ATTR_BOLD)
        buffer.put_text(10, y, "Underline", fg=7, bg=0, attrs=ScreenCell.ATTR_UNDERLINE)
        buffer.put_text(22, y, "Reverse", fg=7, bg=0, attrs=ScreenCell.ATTR_REVERSE)
        
        # UTF-8 test
        y += 2
        buffer.put_text(2, y, "UTF-8: Hello 你好 世界 🚀", fg=2, bg=0)
        
        # Extended color test if supported
        if display.get_color_count() >= 256:
            y += 2
            buffer.put_text(2, y, "256-color gradient:", fg=7, bg=0)
            y += 1
            for i in range(32):
                color = 232 + (i * 24 // 32)  # Grayscale gradient
                buffer.put_char(2 + i, y, '█', fg=color, bg=0)
        
        if display.get_color_count() >= 16777216:
            y += 2
            buffer.put_text(2, y, "24-bit color gradient:", fg=7, bg=0)
            y += 1
            for i in range(32):
                # Create smooth red-to-blue gradient
                r = int(255 * (1 - i/31))
                b = int(255 * (i/31))
                color = (r << 16) | b
                buffer.put_char(2 + i, y, '█', fg=color, bg=0)
        
        # Instructions
        buffer.put_text(2, display.height - 3, "Press 'q' to return to menu", fg=7, bg=0)
        buffer.put_text(2, display.height - 2, "Press arrow keys to test input", fg=7, bg=0)
        
        # Status line
        status_y = display.height - 1
        
        # Render
        display.flush_buffer(buffer)
        
        print("\nBackend is running. Press 'q' in the terminal to return to menu.")
        
        # Input loop
        last_key = ""
        while True:
            event = input_handler.get_event(0.1)
            
            if event:
                if hasattr(event, 'key'):
                    last_key = f"Key: {event.key}"
                    if event.ctrl:
                        last_key += " [Ctrl]"
                    if event.alt:
                        last_key += " [Alt]"
                    if event.shift:
                        last_key += " [Shift]"
                    
                    # Update status
                    buffer.clear_rect(0, status_y, display.width, 1)
                    buffer.put_text(2, status_y, last_key, fg=0, bg=7)
                    display.flush_buffer(buffer)
                    
                    if event.key.lower() == 'q':
                        break
                        
                elif hasattr(event, 'x'):
                    # Mouse event
                    mouse_info = f"Mouse: ({event.x},{event.y}) Button={event.button}"
                    buffer.clear_rect(0, status_y, display.width, 1)
                    buffer.put_text(2, status_y, mouse_info, fg=0, bg=7)
                    display.flush_buffer(buffer)
        
        # Cleanup
        try:
            display.enable_mouse(False)
            display.clear_screen()
            display.shutdown()
        except:
            pass
        
        try:
            input_handler.shutdown()
        except:
            pass
        
        # Force reset terminal
        sys.stdout.write('\033[?1000l\033[?1006l\033[?25h\033[0m')
        sys.stdout.flush()
        
        # Reset stdout to blocking mode
        import fcntl
        import os
        if hasattr(sys.stdout, 'fileno'):
            try:
                fd = sys.stdout.fileno()
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
            except:
                pass
        
        print(f"✓ {name} backend test completed")
        return True
        
    except Exception as e:
        # Reset stdout to blocking mode before printing error
        import fcntl
        import os
        if hasattr(sys.stdout, 'fileno'):
            try:
                fd = sys.stdout.fileno()
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
            except:
                pass
        
        print(f"❌ {name} backend failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main program loop."""
    print("\n" + "="*40)
    print("TVision I/O Backend Test Suite")
    print("="*40)
    print("\nThis tool lets you test each backend")
    print("individually to verify they all work.")
    
    while True:
        platform_type, name = show_menu()
        
        if platform_type == 'EXIT':
            print("\nExiting...")
            break
        elif platform_type is not None or name == "Auto":
            test_backend(platform_type, name)
        
        input("\nPress Enter to continue...")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())