# -*- coding: utf-8 -*-
"""
Error recovery and resilience mechanisms for terminal I/O.

This module provides comprehensive error recovery to ensure the I/O
system can gracefully handle and recover from various failure modes.
"""

import sys
import os
import time
import logging
import termios
import fcntl
from typing import Optional, Callable, Any, Dict, List
from enum import Enum
from dataclasses import dataclass


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"              # Retry the operation
    FALLBACK = "fallback"         # Fall back to simpler mode
    RESET = "reset"              # Reset terminal state
    REINITIALIZE = "reinitialize" # Reinitialize subsystem
    IGNORE = "ignore"            # Ignore and continue
    FATAL = "fatal"              # Cannot recover


@dataclass
class ErrorContext:
    """Context information for error recovery."""
    error_type: type
    error_message: str
    component: str
    operation: str
    retry_count: int = 0
    max_retries: int = 3
    timestamp: float = 0.0


class ErrorRecoveryManager:
    """
    Comprehensive error recovery manager for terminal I/O.
    
    Features:
    - Automatic retry with exponential backoff
    - Graceful degradation to simpler modes
    - Terminal state recovery
    - Error pattern detection
    - Fallback strategies
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize error recovery manager.
        
        Args:
            logger: Optional logger for error reporting
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_history: List[ErrorContext] = []
        self.recovery_strategies: Dict[type, RecoveryStrategy] = {
            # I/O errors - usually transient
            BlockingIOError: RecoveryStrategy.RETRY,
            IOError: RecoveryStrategy.RETRY,
            OSError: RecoveryStrategy.RETRY,
            
            # Terminal errors - need reset
            termios.error: RecoveryStrategy.RESET,
            
            # Input errors - can ignore
            UnicodeDecodeError: RecoveryStrategy.IGNORE,
            
            # Serious errors - need reinitialization
            BrokenPipeError: RecoveryStrategy.REINITIALIZE,
            ConnectionResetError: RecoveryStrategy.REINITIALIZE,
            
            # Default
            Exception: RecoveryStrategy.FALLBACK,
        }
        
        # Fallback handlers
        self.fallback_handlers: Dict[str, Callable] = {}
        
        # Terminal state for recovery
        self.saved_termios = None
        self.saved_fcntl_flags = None
        self._save_terminal_state()
    
    def _save_terminal_state(self):
        """Save current terminal state for recovery."""
        try:
            if hasattr(sys.stdin, 'fileno'):
                fd = sys.stdin.fileno()
                self.saved_termios = termios.tcgetattr(fd)
                self.saved_fcntl_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        except:
            pass
    
    def register_fallback(self, component: str, handler: Callable):
        """
        Register a fallback handler for a component.
        
        Args:
            component: Component name
            handler: Fallback handler function
        """
        self.fallback_handlers[component] = handler
    
    def handle_error(self, error: Exception, component: str, operation: str) -> Any:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            error: The exception that occurred
            component: Component where error occurred
            operation: Operation being performed
            
        Returns:
            Recovery result or raises exception if unrecoverable
        """
        # Create error context
        context = ErrorContext(
            error_type=type(error),
            error_message=str(error),
            component=component,
            operation=operation,
            timestamp=time.time()
        )
        
        # Add to history
        self.error_history.append(context)
        
        # Get recovery strategy
        strategy = self.recovery_strategies.get(type(error), RecoveryStrategy.FALLBACK)
        
        self.logger.debug(f"Error in {component}.{operation}: {error} - Strategy: {strategy}")
        
        # Execute recovery strategy
        if strategy == RecoveryStrategy.RETRY:
            return self._retry_operation(context, operation)
        elif strategy == RecoveryStrategy.FALLBACK:
            return self._fallback_operation(context)
        elif strategy == RecoveryStrategy.RESET:
            return self._reset_terminal(context)
        elif strategy == RecoveryStrategy.REINITIALIZE:
            return self._reinitialize_component(context)
        elif strategy == RecoveryStrategy.IGNORE:
            self.logger.debug(f"Ignoring error: {error}")
            return None
        else:  # FATAL
            self.logger.error(f"Fatal error in {component}: {error}")
            raise error
    
    def _retry_operation(self, context: ErrorContext, operation: Callable) -> Any:
        """
        Retry an operation with exponential backoff.
        
        Args:
            context: Error context
            operation: Operation to retry
            
        Returns:
            Operation result or None
        """
        if context.retry_count >= context.max_retries:
            self.logger.warning(f"Max retries exceeded for {context.operation}")
            return self._fallback_operation(context)
        
        # Exponential backoff
        delay = 0.1 * (2 ** context.retry_count)
        time.sleep(delay)
        
        context.retry_count += 1
        
        try:
            # Retry the operation
            return operation()
        except Exception as e:
            # Recursive retry
            return self.handle_error(e, context.component, context.operation)
    
    def _fallback_operation(self, context: ErrorContext) -> Any:
        """
        Execute fallback handler for component.
        
        Args:
            context: Error context
            
        Returns:
            Fallback result or None
        """
        handler = self.fallback_handlers.get(context.component)
        if handler:
            self.logger.info(f"Executing fallback for {context.component}")
            try:
                return handler()
            except Exception as e:
                self.logger.error(f"Fallback failed: {e}")
                return None
        return None
    
    def _reset_terminal(self, context: ErrorContext) -> bool:
        """
        Reset terminal to known good state.
        
        Args:
            context: Error context
            
        Returns:
            True if successful
        """
        self.logger.info("Resetting terminal state")
        
        try:
            # Restore saved termios
            if self.saved_termios and hasattr(sys.stdin, 'fileno'):
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSANOW, self.saved_termios)
            
            # Restore fcntl flags
            if self.saved_fcntl_flags and hasattr(sys.stdin, 'fileno'):
                fd = sys.stdin.fileno()
                fcntl.fcntl(fd, fcntl.F_SETFL, self.saved_fcntl_flags)
            
            # Send reset sequences
            reset_sequences = [
                '\033c',        # Full reset
                '\033[?1049l',  # Exit alternate screen
                '\033[?25h',    # Show cursor
                '\033[0m',      # Reset attributes
                '\033[?1000l',  # Disable mouse
                '\033[?1006l',  # Disable SGR mouse
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
            
            return True
            
        except Exception as e:
            self.logger.error(f"Terminal reset failed: {e}")
            return False
    
    def _reinitialize_component(self, context: ErrorContext) -> bool:
        """
        Reinitialize a component.
        
        Args:
            context: Error context
            
        Returns:
            True if successful
        """
        self.logger.info(f"Reinitializing {context.component}")
        
        # First reset terminal
        self._reset_terminal(context)
        
        # Then try fallback
        return self._fallback_operation(context) is not None
    
    def detect_error_patterns(self) -> List[str]:
        """
        Detect patterns in error history.
        
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Check for repeated errors
        if len(self.error_history) >= 5:
            recent_errors = self.error_history[-5:]
            error_types = [e.error_type for e in recent_errors]
            
            # All same type?
            if len(set(error_types)) == 1:
                patterns.append(f"Repeated {error_types[0].__name__} errors")
            
            # Rapid errors?
            time_span = recent_errors[-1].timestamp - recent_errors[0].timestamp
            if time_span < 1.0:
                patterns.append("Rapid error rate detected")
        
        return patterns
    
    def should_degrade_mode(self) -> bool:
        """
        Check if we should degrade to simpler mode.
        
        Returns:
            True if too many errors
        """
        if len(self.error_history) < 10:
            return False
        
        # Check error rate in last minute
        current_time = time.time()
        recent_errors = [e for e in self.error_history 
                        if current_time - e.timestamp < 60]
        
        # More than 10 errors per minute suggests problems
        return len(recent_errors) > 10
    
    def clear_history(self):
        """Clear error history."""
        self.error_history.clear()


class ResilientIO:
    """
    Wrapper for I/O operations with automatic error recovery.
    """
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        """
        Initialize resilient I/O wrapper.
        
        Args:
            recovery_manager: Error recovery manager
        """
        self.recovery = recovery_manager
    
    def safe_write(self, fd: int, data: bytes, component: str = "output") -> bool:
        """
        Write with error recovery.
        
        Args:
            fd: File descriptor
            data: Data to write
            component: Component name
            
        Returns:
            True if successful
        """
        try:
            os.write(fd, data)
            return True
        except Exception as e:
            result = self.recovery.handle_error(e, component, "write")
            return result is not None
    
    def safe_read(self, fd: int, size: int, component: str = "input") -> Optional[bytes]:
        """
        Read with error recovery.
        
        Args:
            fd: File descriptor
            size: Bytes to read
            component: Component name
            
        Returns:
            Data or None
        """
        try:
            return os.read(fd, size)
        except Exception as e:
            return self.recovery.handle_error(e, component, "read")
    
    def safe_flush(self, file_obj: Any, component: str = "output") -> bool:
        """
        Flush with error recovery.
        
        Args:
            file_obj: File object
            component: Component name
            
        Returns:
            True if successful
        """
        try:
            file_obj.flush()
            return True
        except BlockingIOError:
            # Ignore blocking errors on flush
            return True
        except Exception as e:
            result = self.recovery.handle_error(e, component, "flush")
            return result is not None