#!/usr/bin/env python3
"""
Test script to verify phase2 demos are fixed.
"""

import sys
import os

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        from vindauga.io import PlatformIO, PlatformType, DisplayBuffer, ScreenCell
        print("✓ Core imports work")
    except ImportError as e:
        print(f"✗ Core import failed: {e}")
        return False
    
    try:
        from vindauga.io.input.ansi import ANSIInput
        print("✓ ANSIInput import works")
    except ImportError as e:
        print(f"✗ ANSIInput import failed: {e}")
        return False
    
    try:
        from vindauga.io.input.termio import TermIOInput
        print("✓ TermIOInput import works")
    except ImportError as e:
        print(f"✗ TermIOInput import failed: {e}")
        return False
    
    try:
        from vindauga.io.input.curses import CursesInput
        print("✓ CursesInput import works")
    except ImportError as e:
        print(f"✗ CursesInput import failed: {e}")
        return False
    
    return True

def test_initialization():
    """Test that platform initialization handles non-TTY gracefully."""
    print("\nTesting platform initialization...")
    
    from vindauga.io import PlatformIO
    
    # Test ANSI platform
    try:
        io_system = PlatformIO.create('ansi')
        result = io_system.initialize()
        if sys.stdin.isatty():
            if result:
                print("✓ ANSI platform initialized (TTY mode)")
                io_system.shutdown()
            else:
                print("✗ ANSI platform failed to initialize in TTY")
        else:
            if not result:
                print("✓ ANSI platform correctly refused non-TTY")
            else:
                print("✗ ANSI platform should not initialize in non-TTY")
                io_system.shutdown()
    except Exception as e:
        print(f"✗ ANSI platform error: {e}")
    
    # Test TermIO platform
    try:
        io_system = PlatformIO.create('termio')
        result = io_system.initialize()
        if sys.stdin.isatty():
            if result:
                print("✓ TermIO platform initialized (TTY mode)")
                io_system.shutdown()
            else:
                print("✗ TermIO platform failed to initialize in TTY")
        else:
            if not result:
                print("✓ TermIO platform correctly refused non-TTY")
            else:
                print("✗ TermIO platform should not initialize in non-TTY")
                io_system.shutdown()
    except Exception as e:
        print(f"✗ TermIO platform error: {e}")

def test_display_buffer():
    """Test that display buffer works regardless of TTY."""
    print("\nTesting display buffer...")
    
    from vindauga.io import DisplayBuffer, ScreenCell
    
    try:
        buffer = DisplayBuffer(80, 25)
        buffer.put_text(10, 5, "Hello World", 0x07)
        buffer.put_text(10, 6, "Unicode: 你好 🌍", 0x0F)
        
        stats = buffer.get_stats()
        print(f"✓ Display buffer works: {stats['dirty_cells']} dirty cells")
        
        # Test cell retrieval
        cell = buffer.get_cell(10, 5)
        if cell and cell.text == 'H':
            print("✓ Cell retrieval works")
        else:
            print("✗ Cell retrieval failed")
            
    except Exception as e:
        print(f"✗ Display buffer error: {e}")

def main():
    """Run all tests."""
    print("Phase 2 Demo Test Suite")
    print("="*60)
    print(f"Running in TTY: {sys.stdin.isatty()}")
    print("="*60)
    
    # Run tests
    imports_ok = test_imports()
    
    if imports_ok:
        test_initialization()
        test_display_buffer()
    
    print("\n" + "="*60)
    print("Test Summary:")
    print("="*60)
    
    if sys.stdin.isatty():
        print("""
✓ You're in a TTY - the demos should work!
  Try running:
    python examples/phase2_demo.py
    python examples/phase2_advanced_demo.py
        """)
    else:
        print("""
⚠ Not in a TTY (running through Claude Code)
  The demos need a real terminal to work.
  
  To test them:
  1. Open VS Code integrated terminal (Ctrl+`)
  2. Run: python examples/phase2_demo.py
  
  Or use the display-only demos which work anywhere:
    python demo_simple.py
    python demo_tvision_io.py
        """)

if __name__ == "__main__":
    main()