#!/usr/bin/env python3
"""
Test keyboard input in Codespaces environment
"""

import sys
import os
import select
import termios
import tty

def test_stdin():
    """Test if stdin is available and connected to a terminal."""
    print("Testing stdin availability...")
    
    # Check if stdin is a terminal
    if sys.stdin.isatty():
        print("✓ stdin is connected to a terminal")
    else:
        print("✗ stdin is NOT connected to a terminal")
        print("  This is likely the issue in Codespaces")
    
    # Check file descriptor
    try:
        fd = sys.stdin.fileno()
        print(f"✓ stdin file descriptor: {fd}")
    except Exception as e:
        print(f"✗ Cannot get stdin file descriptor: {e}")
        return False
    
    # Try to get terminal settings
    try:
        old_settings = termios.tcgetattr(fd)
        print("✓ Can read terminal settings")
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("✓ Can write terminal settings")
    except Exception as e:
        print(f"✗ Cannot access terminal settings: {e}")
        print("  This is the main issue preventing keyboard input")
        return False
    
    return True

def test_simple_input():
    """Test simple Python input."""
    print("\nTesting Python input() function...")
    try:
        user_input = input("Type something and press Enter: ")
        print(f"✓ Received: '{user_input}'")
        return True
    except Exception as e:
        print(f"✗ input() failed: {e}")
        return False

def test_getch():
    """Test raw character input (if possible)."""
    print("\nTesting raw character input...")
    
    if not sys.stdin.isatty():
        print("✗ Cannot test raw input - stdin is not a TTY")
        return False
    
    try:
        import termios, tty
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        print("Press any key (or Ctrl+C to skip)...")
        
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            print(f"\r✓ Received character: '{ch}' (ord: {ord(ch)})")
            return True
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
    except KeyboardInterrupt:
        print("\r✗ Skipped by user")
        return False
    except Exception as e:
        print(f"✗ Raw input failed: {e}")
        return False

def suggest_solutions():
    """Suggest solutions for Codespaces."""
    print("\n" + "="*60)
    print("SOLUTIONS FOR CODESPACES:")
    print("="*60)
    
    if not sys.stdin.isatty():
        print("""
1. Run demos in the VS Code integrated terminal:
   - Open VS Code terminal (Ctrl+`)
   - Run: python examples/phase2_demo.py

2. Use the Codespaces web terminal:
   - Click on the Terminal tab in browser
   - Run the demos there

3. For automated testing without keyboard input:
   - The display-only demos (demo_simple.py, etc.) work fine
   - They demonstrate the display buffer functionality
        """)
    else:
        print("""
The terminal appears to be working! Try:
   python examples/phase2_demo.py --platform ansi
   
If it still doesn't work, the issue may be with the specific
platform initialization code.
        """)

def main():
    print("Keyboard Input Diagnostic for Codespaces")
    print("="*60)
    
    # Run tests
    stdin_ok = test_stdin()
    input_ok = test_simple_input() if stdin_ok else False
    
    if stdin_ok and input_ok:
        test_getch()
    
    # Provide solutions
    suggest_solutions()

if __name__ == "__main__":
    main()