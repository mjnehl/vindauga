# -*- coding: utf-8 -*-
"""Unit tests for FPSLimiter class."""

import unittest
import time
from vindauga.io.fps_limiter import FPSLimiter


class TestFPSLimiter(unittest.TestCase):
    """Test cases for FPSLimiter class."""
    
    def test_initialization(self):
        """Test FPS limiter initialization."""
        limiter = FPSLimiter(60)
        self.assertEqual(limiter.target_fps, 60)
        self.assertAlmostEqual(limiter.frame_time, 1.0/60, places=6)
        self.assertTrue(limiter.enabled)
        self.assertIsNone(limiter.last_frame_time)
    
    def test_unlimited_fps(self):
        """Test unlimited FPS (disabled limiter)."""
        limiter = FPSLimiter(0)
        self.assertEqual(limiter.target_fps, 0)
        self.assertEqual(limiter.frame_time, 0.0)
        self.assertFalse(limiter.enabled)
        
        # Should always allow updates
        self.assertTrue(limiter.should_update())
        self.assertTrue(limiter.should_update())
        self.assertTrue(limiter.should_update())
    
    def test_should_update_first_frame(self):
        """Test that first frame always proceeds."""
        limiter = FPSLimiter(60)
        self.assertTrue(limiter.should_update())
        self.assertIsNotNone(limiter.last_frame_time)
    
    def test_should_update_timing(self):
        """Test frame timing enforcement."""
        limiter = FPSLimiter(100)  # 100 FPS = 10ms per frame
        
        # First frame
        self.assertTrue(limiter.should_update())
        
        # Immediate second call should be rejected
        self.assertFalse(limiter.should_update())
        
        # Wait enough time and try again
        time.sleep(0.011)  # Wait 11ms
        self.assertTrue(limiter.should_update())
    
    def test_wait_until_ready(self):
        """Test blocking wait behavior."""
        limiter = FPSLimiter(100)  # 100 FPS = 10ms per frame
        
        start_time = time.monotonic()
        limiter.wait_until_ready()
        first_frame_time = time.monotonic()
        
        limiter.wait_until_ready()
        second_frame_time = time.monotonic()
        
        # Should have waited approximately 10ms
        elapsed = second_frame_time - first_frame_time
        self.assertGreaterEqual(elapsed, 0.009)  # At least 9ms
        self.assertLess(elapsed, 0.020)  # Less than 20ms
    
    def test_set_fps(self):
        """Test changing FPS target."""
        limiter = FPSLimiter(60)
        self.assertEqual(limiter.target_fps, 60)
        self.assertTrue(limiter.enabled)
        
        limiter.set_fps(30)
        self.assertEqual(limiter.target_fps, 30)
        self.assertAlmostEqual(limiter.frame_time, 1.0/30, places=6)
        self.assertTrue(limiter.enabled)
        
        # Disable limiting
        limiter.set_fps(0)
        self.assertEqual(limiter.target_fps, 0)
        self.assertFalse(limiter.enabled)
    
    def test_reset(self):
        """Test resetting the frame timer."""
        limiter = FPSLimiter(60)
        limiter.should_update()  # Initialize timer
        
        # Immediate update should be rejected
        self.assertFalse(limiter.should_update())
        
        # Reset and try again
        limiter.reset()
        self.assertTrue(limiter.should_update())
    
    def test_get_current_fps(self):
        """Test FPS calculation."""
        limiter = FPSLimiter(60)
        
        # No frames yet
        self.assertEqual(limiter.get_current_fps(), 0.0)
        
        # After first frame
        limiter.should_update()
        time.sleep(0.01)  # Wait 10ms
        
        fps = limiter.get_current_fps()
        # Should be approximately 100 FPS (1/0.01)
        self.assertGreater(fps, 50)
        self.assertLess(fps, 150)
    
    def test_get_frame_time(self):
        """Test frame time measurement."""
        limiter = FPSLimiter(60)
        
        # No frames yet
        self.assertEqual(limiter.get_frame_time(), 0.0)
        
        # After first frame
        limiter.should_update()
        time.sleep(0.01)  # Wait 10ms
        
        frame_time = limiter.get_frame_time()
        self.assertGreaterEqual(frame_time, 0.009)
        self.assertLess(frame_time, 0.020)
    
    def test_invalid_fps(self):
        """Test error handling for invalid FPS values."""
        with self.assertRaises(ValueError):
            FPSLimiter(-1)
        
        limiter = FPSLimiter(60)
        with self.assertRaises(ValueError):
            limiter.set_fps(-10)
    
    def test_repr(self):
        """Test string representation."""
        limiter = FPSLimiter(60)
        self.assertIn("60", repr(limiter))
        self.assertIn("0.0167", repr(limiter))  # ~1/60
        
        limiter = FPSLimiter(0)
        self.assertEqual(repr(limiter), "FPSLimiter(unlimited)")


if __name__ == '__main__':
    unittest.main()