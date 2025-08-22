#!/usr/bin/env python3
"""Automated test of Phase 2 functionality - no user interaction needed."""

import sys
import time
import threading
from vindauga.io import PlatformIO, PlatformType, DisplayBuffer

def run_test():
    """Run automated test."""
    display, input_handler = PlatformIO.create(PlatformType.ANSI)
    
    try:
        # Initialize
        print("Testing Phase 2 initialization...")
        assert display.initialize(), "Display initialization failed"
        assert input_handler.initialize(), "Input initialization failed"
        print("✓ Initialization successful")
        
        # Test display
        print("Testing display output...")
        buffer = DisplayBuffer(display.width, display.height)
        
        # Test text rendering
        buffer.put_text(5, 2, "Phase 2 Automated Test", fg=7, bg=0)
        
        # Test colors
        for i in range(16):
            buffer.put_char(5 + i*2, 4, '█', fg=i, bg=0)
        
        # Test attributes
        buffer.put_text(5, 6, "Bold", fg=7, bg=0, attrs=1)  # ATTR_BOLD
        buffer.put_text(15, 6, "Underline", fg=7, bg=0, attrs=4)  # ATTR_UNDERLINE
        buffer.put_text(30, 6, "Reverse", fg=7, bg=0, attrs=8)  # ATTR_REVERSE
        
        # Test wide characters
        buffer.put_text(5, 8, "UTF-8: 你好 世界 🚀", fg=3, bg=0)
        
        display.flush_buffer(buffer)
        print("✓ Display output successful")
        
        # Test input capabilities
        print("Testing input capabilities...")
        assert input_handler.supports_mouse(), "Mouse support check failed"
        print("✓ Input capabilities verified")
        
        # Test display properties
        print("Testing display properties...")
        assert display.width > 0, "Invalid display width"
        assert display.height > 0, "Invalid display height"
        assert display.supports_colors(), "Color support check failed"
        print(f"✓ Display: {display.width}x{display.height}, colors: {display.get_color_count()}")
        
        # Brief display
        time.sleep(1)
        
        print("\n✅ All Phase 2 automated tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            display.enable_mouse(False)
            display.clear_screen()
            input_handler.shutdown()
            display.shutdown()
            sys.stdout.write('\x1b[?1000l\x1b[?1006l')
            sys.stdout.flush()
        except:
            pass

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)