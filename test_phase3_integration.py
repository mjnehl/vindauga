#!/usr/bin/env python3
"""
Phase 3 Integration Test Application

Tests the new I/O system integration with Vindauga's existing framework.
Allows switching between old curses implementation and new I/O system.
"""

import sys
import time
import logging
from vindauga.widgets.application import Application
from vindauga.widgets.window import Window
from vindauga.widgets.static_text import StaticText
from vindauga.widgets.button import Button
from vindauga.types.rect import Rect
from vindauga.constants.command_codes import cmQuit, cmOK, wnNoNumber
from vindauga.constants.event_codes import evCommand
from vindauga.constants.buttons import bfDefault, bfNormal
from vindauga.events.event import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWindow(Window):
    """Test window with some basic widgets."""
    
    def __init__(self):
        super().__init__(
            Rect(10, 5, 70, 15),
            "Phase 3 Integration Test",
            wnNoNumber
        )
        
        # Add static text
        self.insert(StaticText(
            Rect(2, 2, 58, 3),
            "Testing new I/O system integration with Vindauga"
        ))
        
        # Add buttons
        self.insert(Button(
            Rect(10, 6, 25, 8),
            "~T~est Input",
            cmOK,
            bfDefault
        ))
        
        self.insert(Button(
            Rect(35, 6, 50, 8),
            "~Q~uit",
            cmQuit,
            bfNormal
        ))
        
        # Add status text
        self.status_text = StaticText(
            Rect(2, 9, 58, 10),
            "Status: Ready"
        )
        self.insert(self.status_text)
    
    def handleEvent(self, event):
        """Handle events for testing."""
        super().handleEvent(event)
        
        if event.what == evCommand:
            if event.message.command == cmOK:
                # Update status when Test button is clicked
                self.status_text.text = f"Status: Button clicked at {time.strftime('%H:%M:%S')}"
                self.drawView()
                self.clearEvent(event)


class TestApp(Application):
    """Test application for Phase 3 integration."""
    
    def __init__(self, use_new_io=False, io_backend='auto'):
        logger.info(f"Initializing TestApp with use_new_io={use_new_io}, backend={io_backend}")
        super().__init__(use_new_io=use_new_io, io_backend=io_backend)
        
        # Create and insert test window
        self.test_window = TestWindow()
        self.desktop.insert(self.test_window)
        
        # Store configuration for display
        self.use_new_io = use_new_io
        self.io_backend = io_backend
    
    def initStatusLine(self, bounds):
        """Create custom status line showing I/O mode."""
        from vindauga.widgets.status_line import StatusLine
        from vindauga.widgets.status_def import StatusDef
        from vindauga.widgets.status_item import StatusItem
        from vindauga.constants.keys import kbF10, kbAltX
        
        io_mode = "NEW I/O" if self.use_new_io else "LEGACY"
        backend = self.io_backend if self.use_new_io else "curses"
        
        bounds = self.getExtent()
        bounds.topLeft.y = bounds.bottomRight.y - 1
        
        self.statusLine = StatusLine(
            bounds,
            StatusDef(0, 0xFFFF) +
            StatusItem(f" Mode: {io_mode} ({backend}) ", kbF10) +
            StatusItem(" ~Alt-X~ Exit", kbAltX)
        )


def main():
    """Main entry point for test application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Phase 3 I/O Integration")
    parser.add_argument(
        '--new-io',
        action='store_true',
        help='Use new I/O system instead of legacy curses'
    )
    parser.add_argument(
        '--backend',
        choices=['auto', 'ansi', 'termio', 'curses'],
        default='auto',
        help='I/O backend to use (only with --new-io)'
    )
    parser.add_argument(
        '--features',
        nargs='*',
        help='Feature flags for new I/O (e.g., damage_tracking=false)'
    )
    
    args = parser.parse_args()
    
    # Parse feature flags
    features = {}
    if args.features:
        for feature in args.features:
            if '=' in feature:
                key, value = feature.split('=', 1)
                # Convert string values to appropriate types
                if value.lower() in ('true', 'false'):
                    features[key] = value.lower() == 'true'
                elif value.isdigit():
                    features[key] = int(value)
                else:
                    features[key] = value
    
    # Print configuration
    print(f"Phase 3 Integration Test")
    print(f"========================")
    print(f"Mode: {'New I/O System' if args.new_io else 'Legacy Curses'}")
    if args.new_io:
        print(f"Backend: {args.backend}")
        if features:
            print(f"Features: {features}")
    print()
    print("Controls:")
    print("  - Tab: Navigate between buttons")
    print("  - Enter/Space: Activate button")
    print("  - Alt-X or Quit button: Exit")
    print("  - Mouse: Click on buttons (if supported)")
    print()
    input("Press Enter to start...")
    
    try:
        # Create and run application
        app = TestApp(use_new_io=args.new_io, io_backend=args.backend)
        app.run()
        
        print("\nApplication exited successfully!")
        if args.new_io:
            print("New I/O system integration test completed.")
        else:
            print("Legacy curses mode test completed.")
            
    except Exception as e:
        logger.exception("Error running test application")
        print(f"\nError: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())