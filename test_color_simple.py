#!/usr/bin/env python3
"""Simple color test that allows Ctrl+C to work."""

import sys
import time
import os
import signal
from vindauga.io import PlatformIO, PlatformType, DisplayBuffer

def test_color_support():
    """Test different color modes without input handling."""
    print("Simple Color Test")
    print("="*60)
    
    # Check environment
    term = os.environ.get('TERM', 'unknown')
    colorterm = os.environ.get('COLORTERM', 'unknown')
    
    print(f"TERM={term}")
    print(f"COLORTERM={colorterm}")
    
    # Create ANSI backend (display only, no input)
    display, _ = PlatformIO.create(PlatformType.ANSI)
    
    # Set up signal handler for clean exit
    cleanup_done = False
    
    def cleanup():
        nonlocal cleanup_done
        if cleanup_done:
            return
        cleanup_done = True
        try:
            display.enable_mouse(False)
            display.clear_screen()
            display.shutdown()
        except:
            pass
        # Force reset terminal
        sys.stdout.write('\033[?1000l\033[?1006l\033[?25h\033[0m\033[?1049l')
        sys.stdout.flush()
    
    def signal_handler(signum, frame):
        print("\n\nExiting...")
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize display only (no input handler)
        display.initialize()
        
        # Check detected color support
        detected_colors = display.get_color_count()
        print(f"\nDetected: {detected_colors:,} colors")
        print("\nPress Ctrl+C to exit\n")
        time.sleep(1)
        
        # Create buffer
        buffer = DisplayBuffer(display.width, display.height)
        y = 1
        
        # Title
        buffer.put_text(2, y, f"Color Test - {detected_colors:,} colors (Ctrl+C to exit)", fg=7, bg=0)
        y += 2
        
        # Test 16 colors
        buffer.put_text(2, y, "16 colors:", fg=7, bg=0)
        y += 1
        for i in range(16):
            x = 2 + (i % 8) * 5
            if i == 8:
                y += 1
            buffer.put_text(x, y, f"█{i:2}", fg=i, bg=0)
        y += 2
        
        # Test 256 colors if available
        if detected_colors >= 256:
            buffer.put_text(2, y, "256-color grayscale:", fg=7, bg=0)
            y += 1
            for i in range(24):
                color = 232 + i
                buffer.put_char(2 + i*2, y, '█', fg=color, bg=0)
            y += 2
        
        # Test 24-bit color if available
        if detected_colors >= 16777216:
            buffer.put_text(2, y, "24-bit gradients:", fg=7, bg=0)
            y += 1
            
            # Red gradient
            buffer.put_text(2, y, "R: ", fg=7, bg=0)
            for i in range(40):
                color = (int(255 * i/39) << 16)
                buffer.put_char(5 + i, y, '█', fg=color, bg=0)
            y += 1
            
            # Green gradient
            buffer.put_text(2, y, "G: ", fg=7, bg=0)
            for i in range(40):
                color = (int(255 * i/39) << 8)
                buffer.put_char(5 + i, y, '█', fg=color, bg=0)
            y += 1
            
            # Blue gradient
            buffer.put_text(2, y, "B: ", fg=7, bg=0)
            for i in range(40):
                color = int(255 * i/39)
                buffer.put_char(5 + i, y, '█', fg=color, bg=0)
            y += 1
            
            # Rainbow
            buffer.put_text(2, y, "🌈: ", fg=7, bg=0)
            for i in range(40):
                hue = i / 40.0 * 360
                # Simple HSV to RGB (S=1, V=1)
                h = hue / 60.0
                c = 1.0
                x = c * (1 - abs(h % 2 - 1))
                if h < 1:
                    r, g, b = c, x, 0
                elif h < 2:
                    r, g, b = x, c, 0
                elif h < 3:
                    r, g, b = 0, c, x
                elif h < 4:
                    r, g, b = 0, x, c
                elif h < 5:
                    r, g, b = x, 0, c
                else:
                    r, g, b = c, 0, x
                color = (int(r*255) << 16) | (int(g*255) << 8) | int(b*255)
                buffer.put_char(5 + i, y, '█', fg=color, bg=0)
            y += 2
        
        # Render
        display.flush_buffer(buffer)
        
        # Keep displaying (Ctrl+C will work)
        print("Color test displayed. Press Ctrl+C to exit.")
        while True:
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
    
    return 0

if __name__ == '__main__':
    sys.exit(test_color_support())