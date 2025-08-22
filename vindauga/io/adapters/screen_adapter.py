"""
Screen adapter that bridges the new I/O system with Vindauga's Screen class.

This adapter provides a compatible interface for the Screen class to use
the new display and input backends while maintaining backward compatibility.
"""

import sys
import logging
from typing import Optional, Tuple, Any, Dict
from ..platform_factory_fixed import PlatformIO, PlatformType
from ..display_buffer import DisplayBuffer
from ..screen_cell import ScreenCell

logger = logging.getLogger(__name__)


class ScreenAdapter:
    """Adapts new I/O system for use with Vindauga Screen class."""
    
    def __init__(self, io_backend: str = 'auto', io_features: Optional[Dict] = None):
        """
        Initialize the screen adapter.
        
        Args:
            io_backend: Backend to use ('auto', 'ansi', 'termio', 'curses')
            io_features: Feature flags for performance tuning
        """
        self.io_backend = io_backend
        self.io_features = io_features or {}
        
        # Set default features
        self.damage_tracking = self.io_features.get('damage_tracking', True)
        self.event_coalescing = self.io_features.get('event_coalescing', True)
        self.cursor_optimization = self.io_features.get('cursor_optimization', True)
        self.fps_limiting = self.io_features.get('fps_limiting', 60)
        self.buffer_pooling = self.io_features.get('buffer_pooling', True)
        
        # Initialize platform I/O
        self._init_platform_io()
        
        # Initialize display buffer
        width, height = self.display.get_size()
        self.buffer = DisplayBuffer(width, height)
        
        # Track cursor state
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_visible = True
        
        # Performance metrics
        self.metrics = {
            'frame_count': 0,
            'total_frame_time': 0,
            'input_events': 0,
        }
    
    def _init_platform_io(self):
        """Initialize the platform I/O backends."""
        # Map backend strings to platform types
        backend_map = {
            'auto': None,
            'ansi': PlatformType.ANSI,
            'termio': PlatformType.TERMIO,
            'curses': PlatformType.CURSES,
        }
        
        platform = backend_map.get(self.io_backend)
        
        try:
            # Create platform I/O with specified backend
            self.display, self.input_handler = PlatformIO.create(platform)
            
            # Initialize backends
            self.display.initialize()
            self.input_handler.initialize()
            
            # Apply feature settings
            if hasattr(self.input_handler, 'enable_event_coalescing'):
                self.input_handler.enable_event_coalescing(self.event_coalescing)
            
            logger.info(f"Initialized {self.display.__class__.__name__} display backend")
            
        except Exception as e:
            logger.error(f"Failed to initialize I/O backend: {e}")
            raise
    
    def get_size(self) -> Tuple[int, int]:
        """Get terminal size."""
        return self.display.get_size()
    
    def clear_screen(self):
        """Clear the screen."""
        self.display.clear_screen()
        self.buffer.clear()
    
    def set_cursor_position(self, x: int, y: int):
        """Set cursor position."""
        self.cursor_x = x
        self.cursor_y = y
        self.display.set_cursor_position(x, y)
    
    def set_cursor_visibility(self, visible: bool):
        """Set cursor visibility."""
        self.cursor_visible = visible
        self.display.set_cursor_visibility(visible)
    
    def put_char(self, x: int, y: int, ch: str, fg: int = 7, bg: int = 0):
        """
        Put a character at the specified position.
        
        Args:
            x: X coordinate
            y: Y coordinate
            ch: Character to display
            fg: Foreground color (0-255)
            bg: Background color (0-255)
        """
        if self.damage_tracking:
            # Use buffer with damage tracking
            cell = ScreenCell(ch, fg, bg)
            self.buffer.put_cell(x, y, cell)
        else:
            # Direct write without damage tracking
            self.display.put_char(x, y, ch, fg, bg)
    
    def put_text(self, x: int, y: int, text: str, fg: int = 7, bg: int = 0):
        """
        Put text at the specified position.
        
        Args:
            x: Starting X coordinate
            y: Y coordinate
            text: Text to display
            fg: Foreground color (0-255)
            bg: Background color (0-255)
        """
        if self.damage_tracking:
            # Use buffer with damage tracking
            self.buffer.put_text(x, y, text, fg, bg)
        else:
            # Direct write without damage tracking
            for i, ch in enumerate(text):
                self.display.put_char(x + i, y, ch, fg, bg)
    
    def flush(self):
        """Flush pending changes to display."""
        import time
        start_time = time.time()
        
        if self.damage_tracking:
            # Get dirty regions and update only changed areas
            dirty_regions = self.buffer.get_dirty_regions()
            
            for region in dirty_regions:
                for y in range(region.y, region.y + region.height):
                    for x in range(region.x, region.x + region.width):
                        cell = self.buffer.get_cell(x, y)
                        if cell:
                            self.display.put_char(x, y, cell.char, cell.fg, cell.bg)
            
            # Clear dirty state
            self.buffer.clear_dirty()
        
        # Apply FPS limiting if enabled
        if self.fps_limiting > 0:
            frame_time = 1.0 / self.fps_limiting
            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
        
        # Flush display
        self.display.flush()
        
        # Update metrics
        self.metrics['frame_count'] += 1
        self.metrics['total_frame_time'] += time.time() - start_time
    
    def get_char(self) -> Optional[Tuple[int, Any]]:
        """
        Get next input event.
        
        Returns:
            Tuple of (event_type, event_data) or None if no input
        """
        event = self.input_handler.get_event(timeout=0)
        
        if event:
            self.metrics['input_events'] += 1
            
            # Convert to Vindauga event format
            if hasattr(event, 'key'):
                # Keyboard event
                return ('key', event.key)
            elif hasattr(event, 'x'):
                # Mouse event
                return ('mouse', event)
            elif hasattr(event, 'width'):
                # Resize event
                return ('resize', (event.width, event.height))
        
        return None
    
    def enable_mouse(self, enable: bool = True):
        """Enable or disable mouse support."""
        if hasattr(self.display, 'enable_mouse'):
            self.display.enable_mouse(enable)
    
    def shutdown(self):
        """Shutdown the adapter and cleanup."""
        try:
            # Log performance metrics
            if self.metrics['frame_count'] > 0:
                avg_frame_time = self.metrics['total_frame_time'] / self.metrics['frame_count']
                logger.info(f"Performance: {avg_frame_time*1000:.2f}ms avg frame time")
                logger.info(f"Processed {self.metrics['input_events']} input events")
            
            # Shutdown backends
            if hasattr(self, 'input_handler'):
                self.input_handler.shutdown()
            if hasattr(self, 'display'):
                self.display.shutdown()
                
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def resize(self, width: int, height: int):
        """Handle terminal resize."""
        # Resize buffer
        if self.buffer_pooling:
            # Preserve buffer contents during resize
            old_buffer = self.buffer
            self.buffer = DisplayBuffer(width, height)
            
            # Copy old content
            for y in range(min(old_buffer.height, height)):
                for x in range(min(old_buffer.width, width)):
                    cell = old_buffer.get_cell(x, y)
                    if cell:
                        self.buffer.put_cell(x, y, cell)
        else:
            # Create new buffer
            self.buffer = DisplayBuffer(width, height)
    
    def get_metrics(self) -> Dict:
        """Get performance metrics."""
        metrics = self.metrics.copy()
        if metrics['frame_count'] > 0:
            metrics['avg_frame_time_ms'] = (metrics['total_frame_time'] / metrics['frame_count']) * 1000
        return metrics