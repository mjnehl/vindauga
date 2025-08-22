# -*- coding: utf-8 -*-
"""
Terminal cleanup manager for ensuring proper terminal restoration.

This module provides comprehensive cleanup handling to ensure terminals
are always restored to a sane state, even after crashes.
"""

import sys
import os
import signal
import atexit
import weakref
from typing import Optional, Set, Callable


class TerminalCleanupManager:
    """
    Singleton manager for terminal cleanup operations.
    
    Ensures that terminal state is properly restored on exit,
    even in case of crashes or unexpected termination.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize cleanup manager."""
        if self._initialized:
            return
            
        self._initialized = True
        self._cleanup_handlers: Set[weakref.ref] = set()
        self._signal_handlers_installed = False
        self._original_termios = None
        self._stdin_fd = None
        
        # Save initial terminal state
        self._save_terminal_state()
        
        # Register atexit handler
        atexit.register(self._cleanup_all)
    
    def _save_terminal_state(self):
        """Save original terminal state."""
        try:
            import termios
            if hasattr(sys.stdin, 'fileno'):
                self._stdin_fd = sys.stdin.fileno()
                self._original_termios = termios.tcgetattr(self._stdin_fd)
        except:
            pass
    
    def register_cleanup(self, handler: Callable[[], None]):
        """
        Register a cleanup handler.
        
        Args:
            handler: Cleanup function to call on exit
        """
        # Use weak reference to avoid keeping objects alive
        self._cleanup_handlers.add(weakref.ref(handler))
        
        # Install signal handlers on first registration
        if not self._signal_handlers_installed:
            self._install_signal_handlers()
            self._signal_handlers_installed = True
    
    def unregister_cleanup(self, handler: Callable[[], None]):
        """
        Unregister a cleanup handler.
        
        Args:
            handler: Cleanup function to remove
        """
        # Remove dead references and the specified handler
        dead_refs = set()
        for ref in self._cleanup_handlers:
            obj = ref()
            if obj is None:
                dead_refs.add(ref)
            elif obj == handler:
                dead_refs.add(ref)
        
        self._cleanup_handlers -= dead_refs
    
    def _install_signal_handlers(self):
        """Install signal handlers for cleanup."""
        def signal_handler(signum, frame):
            """Handle signals by cleaning up and re-raising."""
            self._cleanup_all()
            # Re-raise the signal to let default handler run
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
        
        # Install handlers for common termination signals
        for sig in [signal.SIGTERM, signal.SIGHUP]:
            try:
                signal.signal(sig, signal_handler)
            except:
                pass
        
        # Special handling for SIGINT to allow Ctrl+C
        def sigint_handler(signum, frame):
            """Handle SIGINT (Ctrl+C) with cleanup."""
            self._cleanup_all()
            raise KeyboardInterrupt()
        
        try:
            signal.signal(signal.SIGINT, sigint_handler)
        except:
            pass
    
    def _cleanup_all(self):
        """Run all cleanup handlers."""
        # Call registered cleanup handlers
        dead_refs = set()
        for ref in self._cleanup_handlers:
            handler = ref()
            if handler is None:
                dead_refs.add(ref)
            else:
                try:
                    handler()
                except:
                    pass
        
        # Clean up dead references
        self._cleanup_handlers -= dead_refs
        
        # Force terminal restoration
        self._force_terminal_restore()
    
    def _force_terminal_restore(self):
        """Force restore terminal to sane state."""
        try:
            # Send reset sequences directly
            reset_sequences = [
                '\033[?1049l',  # Exit alternate screen
                '\033[?25h',    # Show cursor
                '\033[0m',      # Reset attributes
                '\033[?1000l',  # Disable X11 mouse
                '\033[?1006l',  # Disable SGR mouse
                '\033[?1002l',  # Disable cell motion tracking
                '\033[?1003l',  # Disable all motion tracking
            ]
            
            for seq in reset_sequences:
                try:
                    sys.stdout.write(seq)
                except:
                    pass
            
            try:
                sys.stdout.flush()
            except:
                pass
            
            # Restore terminal settings
            if self._original_termios and self._stdin_fd is not None:
                import termios
                try:
                    termios.tcsetattr(self._stdin_fd, termios.TCSANOW, 
                                    self._original_termios)
                except:
                    pass
            
            # Reset file descriptor flags
            if self._stdin_fd is not None:
                import fcntl
                try:
                    # Clear non-blocking flag
                    flags = fcntl.fcntl(self._stdin_fd, fcntl.F_GETFL)
                    fcntl.fcntl(self._stdin_fd, fcntl.F_SETFL, 
                              flags & ~os.O_NONBLOCK)
                except:
                    pass
                    
            # Reset stdout to blocking
            if hasattr(sys.stdout, 'fileno'):
                import fcntl
                try:
                    fd = sys.stdout.fileno()
                    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
                except:
                    pass
                    
        except:
            pass
    
    def force_cleanup(self):
        """Manually trigger cleanup (for testing/debugging)."""
        self._cleanup_all()


# Global instance
_cleanup_manager = None


def get_cleanup_manager() -> TerminalCleanupManager:
    """Get the global cleanup manager instance."""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = TerminalCleanupManager()
    return _cleanup_manager


def register_cleanup(handler: Callable[[], None]):
    """
    Register a cleanup handler with the global manager.
    
    Args:
        handler: Function to call on cleanup
    """
    get_cleanup_manager().register_cleanup(handler)


def force_terminal_cleanup():
    """Force immediate terminal cleanup (for debugging)."""
    get_cleanup_manager().force_cleanup()