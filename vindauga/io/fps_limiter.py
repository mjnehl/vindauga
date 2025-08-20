# -*- coding: utf-8 -*-
"""
Frame rate limiting for controlled display updates.

This module provides the FPSLimiter class which helps control the rate
of screen updates to prevent excessive CPU usage and flickering.
"""

import time
from typing import Optional


class FPSLimiter:
    """
    Limits the frame rate of display updates.
    
    This class helps prevent excessive screen updates by enforcing a maximum
    frames per second (FPS) rate. It's particularly useful for applications
    that might otherwise update the screen too frequently, causing flickering
    or high CPU usage.
    
    Attributes:
        target_fps: The target frames per second (0 = unlimited)
        frame_time: Minimum time between frames in seconds
        last_frame_time: Time of the last frame
    """
    
    def __init__(self, target_fps: int = 60):
        """
        Initialize the FPS limiter.
        
        Args:
            target_fps: Target frames per second (0 for unlimited)
            
        Raises:
            ValueError: If target_fps is negative
        """
        if target_fps < 0:
            raise ValueError(f"FPS cannot be negative: {target_fps}")
        
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps if target_fps > 0 else 0.0
        self.last_frame_time: Optional[float] = None
        self._enabled = target_fps > 0
    
    @property
    def enabled(self) -> bool:
        """Check if FPS limiting is enabled."""
        return self._enabled
    
    def should_update(self) -> bool:
        """
        Check if enough time has passed for the next frame.
        
        This method should be called before each potential screen update.
        If it returns True, the update should proceed. If False, the update
        should be skipped to maintain the target FPS.
        
        Returns:
            True if update should proceed, False to skip this frame
        """
        if not self._enabled:
            return True
        
        current_time = time.monotonic()
        
        # First frame always proceeds
        if self.last_frame_time is None:
            self.last_frame_time = current_time
            return True
        
        # Check if enough time has passed
        time_elapsed = current_time - self.last_frame_time
        if time_elapsed >= self.frame_time:
            self.last_frame_time = current_time
            return True
        
        return False
    
    def wait_until_ready(self) -> None:
        """
        Block until it's time for the next frame.
        
        This method will sleep if necessary to maintain the target FPS.
        It's an alternative to should_update() for applications that
        prefer blocking behavior.
        """
        if not self._enabled:
            return
        
        current_time = time.monotonic()
        
        if self.last_frame_time is not None:
            time_elapsed = current_time - self.last_frame_time
            time_to_wait = self.frame_time - time_elapsed
            
            if time_to_wait > 0:
                time.sleep(time_to_wait)
        
        self.last_frame_time = time.monotonic()
    
    def set_fps(self, target_fps: int) -> None:
        """
        Change the target FPS.
        
        Args:
            target_fps: New target frames per second (0 for unlimited)
            
        Raises:
            ValueError: If target_fps is negative
        """
        if target_fps < 0:
            raise ValueError(f"FPS cannot be negative: {target_fps}")
        
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps if target_fps > 0 else 0.0
        self._enabled = target_fps > 0
        
        # Don't reset last_frame_time to avoid sudden updates
    
    def reset(self) -> None:
        """Reset the frame timer, allowing immediate update."""
        self.last_frame_time = None
    
    def get_current_fps(self) -> float:
        """
        Calculate the actual current FPS based on frame timing.
        
        Returns:
            Current FPS, or 0.0 if no frames have been rendered
        """
        if self.last_frame_time is None:
            return 0.0
        
        current_time = time.monotonic()
        time_elapsed = current_time - self.last_frame_time
        
        if time_elapsed > 0:
            return 1.0 / time_elapsed
        
        return float('inf')  # Instantaneous frame
    
    def get_frame_time(self) -> float:
        """
        Get the time since the last frame.
        
        Returns:
            Seconds since last frame, or 0.0 if no frames yet
        """
        if self.last_frame_time is None:
            return 0.0
        
        return time.monotonic() - self.last_frame_time
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        if not self._enabled:
            return "FPSLimiter(unlimited)"
        return f"FPSLimiter(target_fps={self.target_fps}, frame_time={self.frame_time:.4f}s)"