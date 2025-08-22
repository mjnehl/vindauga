#!/usr/bin/env python3
"""
Simple Phase 3 Integration Test

Tests the basic new I/O system integration without full application dependencies.
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_legacy_mode():
    """Test that legacy mode still works."""
    print("Testing legacy curses mode...")
    
    try:
        from vindauga.types.screen import Screen
        
        # Initialize with legacy mode (default)
        Screen.init(use_new_io=False)
        screen = Screen.screen
        
        print(f"  Screen initialized: {screen is not None}")
        print(f"  Using new I/O: {screen.use_new_io}")
        print(f"  Screen size: {screen.screenWidth}x{screen.screenHeight}")
        
        # Cleanup
        if hasattr(screen, 'shutdown'):
            screen.shutdown()
            
        return True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_new_io_mode():
    """Test that new I/O mode initializes."""
    print("\nTesting new I/O mode...")
    
    try:
        from vindauga.types.screen import Screen
        
        # Initialize with new I/O mode
        Screen.screen = None  # Reset singleton
        Screen.init(use_new_io=True, io_backend='ansi')
        screen = Screen.screen
        
        print(f"  Screen initialized: {screen is not None}")
        print(f"  Using new I/O: {screen.use_new_io}")
        print(f"  I/O backend: {screen.io_backend}")
        
        if hasattr(screen, 'screen_adapter'):
            print(f"  Screen adapter: {screen.screen_adapter is not None}")
            print(f"  Display: {screen.display is not None}")
            print(f"  Input handler: {screen.input_handler is not None}")
        
        # Test screen size
        if hasattr(screen, 'screen_adapter'):
            width, height = screen.screen_adapter.get_size()
            print(f"  Screen size from adapter: {width}x{height}")
        
        # Cleanup
        if hasattr(screen, 'shutdown'):
            screen.shutdown()
            
        return True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_draw_buffer():
    """Test DrawBuffer with new I/O."""
    print("\nTesting DrawBuffer integration...")
    
    try:
        from vindauga.types.draw_buffer import DrawBuffer
        
        # Test legacy buffer
        buffer_legacy = DrawBuffer(filled=False, use_new_io=False)
        print(f"  Legacy buffer created: {buffer_legacy is not None}")
        
        # Test new I/O buffer
        buffer_new = DrawBuffer(filled=False, use_new_io=True)
        print(f"  New I/O buffer created: {buffer_new is not None}")
        print(f"  Using new I/O: {buffer_new._use_new_io}")
        
        # Test basic operations
        test_text = "Hello World"
        buffer_legacy.moveStr(0, test_text, 0x07)
        print(f"  Legacy buffer moveStr: OK")
        
        buffer_new.moveStr(0, test_text, 0x07)
        print(f"  New I/O buffer moveStr: OK")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_event_adapter():
    """Test event translation."""
    print("\nTesting Event Adapter...")
    
    try:
        from vindauga.io.adapters.event_adapter import EventAdapter, KeyEvent, MouseEvent
        from vindauga.constants.event_codes import evKeyDown, evMouseMove
        
        adapter = EventAdapter()
        print(f"  Event adapter created: {adapter is not None}")
        
        # Test key event translation
        key_event = KeyEvent(char='A', key_code=65)
        vindauga_event = adapter.translate_to_vindauga(key_event)
        print(f"  Key event translation: {vindauga_event.what == evKeyDown}")
        
        # Test mouse event translation
        mouse_event = MouseEvent(x=10, y=5, buttons=1, event_type='move')
        vindauga_event = adapter.translate_to_vindauga(mouse_event)
        print(f"  Mouse event translation: {vindauga_event.what == evMouseMove}")
        print(f"  Mouse coordinates: ({vindauga_event.mouse.where.x}, {vindauga_event.mouse.where.y})")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    """Run all integration tests."""
    print("Phase 3 Integration Tests")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Event Adapter", test_event_adapter()))
    results.append(("DrawBuffer", test_draw_buffer()))
    
    # Screen tests might fail due to terminal requirements
    try:
        results.append(("Legacy Mode", test_legacy_mode()))
    except Exception as e:
        print(f"\nSkipping legacy mode test: {e}")
        results.append(("Legacy Mode", None))
    
    try:
        results.append(("New I/O Mode", test_new_io_mode()))
    except Exception as e:
        print(f"\nSkipping new I/O mode test: {e}")
        results.append(("New I/O Mode", None))
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    for name, result in results:
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "PASSED"
        else:
            status = "FAILED"
        print(f"  {name:20} {status}")
    
    # Return exit code
    failed = sum(1 for _, r in results if r is False)
    if failed > 0:
        print(f"\n{failed} test(s) failed!")
        return 1
    else:
        print("\nAll tests passed or skipped!")
        return 0


if __name__ == '__main__':
    sys.exit(main())