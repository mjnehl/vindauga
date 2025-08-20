#!/usr/bin/env python3
"""
Working demo that handles keyboard input properly in Codespaces.
"""

import sys
import time
import select
import curses
from vindauga.io import DisplayBuffer, ScreenCell

def run_display_demo():
    """Run the display-only demo (no input needed)."""
    print("Running display demo...")
    
    buffer = DisplayBuffer(80, 25)
    
    # Draw a simple scene
    buffer.put_text(10, 5, "╔════════════════════════╗", 0x1F)
    buffer.put_text(10, 6, "║  Vindauga Demo Works!  ║", 0x1F)
    buffer.put_text(10, 7, "║  Unicode: 你好 🌍      ║", 0x1F)
    buffer.put_text(10, 8, "╚════════════════════════╝", 0x1F)
    
    stats = buffer.get_stats()
    print(f"Buffer stats: {stats}")
    
    # Show the content
    for row in buffer.get_damaged_rows():
        print(f"Row {row} has changes")
    
    print("Display demo completed!")

def run_curses_demo(stdscr):
    """Run interactive demo using curses."""
    # Setup curses
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking
    stdscr.clear()
    
    # Initialize colors if available
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    
    # Create display buffer for our content
    height, width = stdscr.getmaxyx()
    buffer = DisplayBuffer(width, height)
    
    # Main loop
    frame = 0
    running = True
    last_key = "None"
    
    while running:
        # Clear and prepare buffer
        buffer.clear()
        
        # Draw header
        title = "Vindauga Curses Demo - Press 'q' to quit"
        buffer.put_text(0, 0, title, 0x1F)
        
        # Draw info
        buffer.put_text(2, 2, f"Frame: {frame:04d}", 0x07)
        buffer.put_text(2, 3, f"Size: {width}x{height}", 0x07)
        buffer.put_text(2, 4, f"Last key: {last_key}", 0x07)
        
        # Draw Unicode examples
        buffer.put_text(2, 6, "Unicode support:", 0x0F)
        buffer.put_text(4, 7, "English: Hello World!", 0x07)
        buffer.put_text(4, 8, "Chinese: 你好世界", 0x07)
        buffer.put_text(4, 9, "Emoji: 🚀 🌍 ❤️", 0x07)
        
        # Update screen from buffer
        for y in range(min(height, buffer.height)):
            for x in range(min(width, buffer.width)):
                cell = buffer.get_cell(x, y)
                if cell and cell.text and cell.text != ' ':
                    try:
                        # Use color pair if available
                        attr = curses.color_pair(1) if curses.has_colors() else 0
                        stdscr.addstr(y, x, cell.text, attr)
                    except:
                        pass  # Ignore cells that can't be displayed
        
        # Check for input
        ch = stdscr.getch()
        if ch != -1:
            if ch == ord('q'):
                running = False
            elif 32 <= ch <= 126:
                last_key = chr(ch)
            else:
                last_key = f"0x{ch:02X}"
        
        # Update screen
        stdscr.refresh()
        
        # Update frame counter
        frame += 1
        
        # Small delay
        time.sleep(0.05)

def main():
    """Main entry point."""
    print("Vindauga Working Demo")
    print("=" * 60)
    
    # First run display-only demo
    run_display_demo()
    
    print("\n" + "=" * 60)
    print("Interactive Demo Options:")
    print("1. Run with curses (recommended for Codespaces)")
    print("2. Skip interactive demo")
    print("=" * 60)
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        try:
            curses.wrapper(run_curses_demo)
            print("\nInteractive demo completed!")
        except Exception as e:
            print(f"\nCurses demo failed: {e}")
            print("This might happen in some environments.")
    else:
        print("Skipping interactive demo")
    
    print("\nDemo finished!")

if __name__ == "__main__":
    main()
