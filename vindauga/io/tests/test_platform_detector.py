# -*- coding: utf-8 -*-
"""Unit tests for PlatformDetector class."""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from vindauga.io.platform_detector import (
    PlatformType, PlatformCapabilities, PlatformDetector
)


class TestPlatformType(unittest.TestCase):
    """Test cases for PlatformType enum."""
    
    def test_platform_types(self):
        """Test platform type enum values."""
        self.assertIsNotNone(PlatformType.ANSI)
        self.assertIsNotNone(PlatformType.TERMIO)
        self.assertIsNotNone(PlatformType.CURSES)
        self.assertIsNotNone(PlatformType.WIN32)
        self.assertIsNotNone(PlatformType.DUMMY)


class TestPlatformCapabilities(unittest.TestCase):
    """Test cases for PlatformCapabilities class."""
    
    def test_initialization(self):
        """Test capabilities initialization."""
        caps = PlatformCapabilities(
            name="Test",
            available=True,
            color_support=256,
            mouse_support=True,
            unicode_support=True,
            performance_score=75
        )
        
        self.assertEqual(caps.name, "Test")
        self.assertTrue(caps.available)
        self.assertEqual(caps.color_support, 256)
        self.assertTrue(caps.mouse_support)
        self.assertTrue(caps.unicode_support)
        self.assertEqual(caps.performance_score, 75)
    
    def test_overall_score_unavailable(self):
        """Test score for unavailable platform."""
        caps = PlatformCapabilities(name="Test", available=False)
        self.assertEqual(caps.overall_score(), 0)
    
    def test_overall_score_calculation(self):
        """Test score calculation."""
        # Basic platform
        caps = PlatformCapabilities(
            name="Test",
            available=True,
            performance_score=50
        )
        self.assertEqual(caps.overall_score(), 50)
        
        # With 16 colors
        caps.color_support = 16
        self.assertEqual(caps.overall_score(), 60)
        
        # With 256 colors
        caps.color_support = 256
        self.assertEqual(caps.overall_score(), 65)
        
        # With 24-bit color
        caps.color_support = 16777216
        self.assertEqual(caps.overall_score(), 70)
        
        # With mouse support
        caps.mouse_support = True
        self.assertEqual(caps.overall_score(), 80)
        
        # With Unicode support
        caps.unicode_support = True
        self.assertEqual(caps.overall_score(), 90)
        
        # Score capped at 100
        caps.performance_score = 100
        self.assertEqual(caps.overall_score(), 100)


class TestPlatformDetector(unittest.TestCase):
    """Test cases for PlatformDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = PlatformDetector()
    
    @patch('platform.system')
    def test_system_detection(self, mock_system):
        """Test OS detection."""
        # Linux
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()
        self.assertTrue(detector.is_linux)
        self.assertTrue(detector.is_unix)
        self.assertFalse(detector.is_windows)
        self.assertFalse(detector.is_mac)
        
        # Windows
        mock_system.return_value = 'Windows'
        detector = PlatformDetector()
        self.assertTrue(detector.is_windows)
        self.assertFalse(detector.is_unix)
        self.assertFalse(detector.is_linux)
        self.assertFalse(detector.is_mac)
        
        # macOS
        mock_system.return_value = 'Darwin'
        detector = PlatformDetector()
        self.assertTrue(detector.is_mac)
        self.assertTrue(detector.is_unix)
        self.assertFalse(detector.is_windows)
        self.assertFalse(detector.is_linux)
    
    @patch.dict(os.environ, {'TERM': 'xterm-256color', 'COLORTERM': 'truecolor'})
    def test_detect_ansi_capabilities(self):
        """Test ANSI capability detection."""
        with patch('sys.stdout.isatty', return_value=True):
            # Create new detector with patched environment
            detector = PlatformDetector()
            caps = detector.detect_ansi_capabilities()
            self.assertTrue(caps.available)
            self.assertEqual(caps.color_support, 16777216)  # 24-bit
            self.assertTrue(caps.mouse_support)
            self.assertTrue(caps.unicode_support)
    
    @patch.dict(os.environ, {'TERM': 'dumb'})
    @patch('sys.stdout')
    def test_detect_ansi_dumb_terminal(self, mock_stdout):
        """Test ANSI detection with dumb terminal."""
        mock_stdout.isatty.return_value = True
        
        caps = self.detector.detect_ansi_capabilities()
        self.assertFalse(caps.available)
    
    @patch('sys.stdout')
    def test_detect_ansi_not_tty(self, mock_stdout):
        """Test ANSI detection when not a TTY."""
        mock_stdout.isatty.return_value = False
        
        caps = self.detector.detect_ansi_capabilities()
        self.assertFalse(caps.available)
    
    @patch('platform.system')
    def test_detect_termio_capabilities(self, mock_system):
        """Test TermIO capability detection."""
        # On Unix
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()
        
        # Mock termios module
        with patch.dict('sys.modules', {'termios': MagicMock(), 
                                        'tty': MagicMock(),
                                        'fcntl': MagicMock()}):
            with patch('sys.stdin.fileno', return_value=0):
                sys.modules['termios'].tcgetattr = MagicMock()
                
                caps = detector.detect_termio_capabilities()
                self.assertTrue(caps.available)
                self.assertTrue(caps.unicode_support)
                self.assertTrue(caps.mouse_support)
        
        # On Windows
        mock_system.return_value = 'Windows'
        detector = PlatformDetector()
        caps = detector.detect_termio_capabilities()
        self.assertFalse(caps.available)
    
    def test_detect_curses_capabilities(self):
        """Test Curses capability detection."""
        # Mock curses module
        with patch.dict('sys.modules', {'curses': MagicMock()}):
            caps = self.detector.detect_curses_capabilities()
            self.assertTrue(caps.available)
            self.assertTrue(caps.unicode_support)
            self.assertTrue(caps.mouse_support)
            self.assertEqual(caps.color_support, 256)
        
        # Without curses
        with patch('builtins.__import__', side_effect=ImportError):
            caps = self.detector.detect_curses_capabilities()
            self.assertFalse(caps.available)
    
    @patch('platform.system')
    def test_detect_win32_capabilities(self, mock_system):
        """Test Win32 capability detection."""
        # On Windows
        mock_system.return_value = 'Windows'
        detector = PlatformDetector()
        caps = detector.detect_win32_capabilities()
        # Currently not implemented
        self.assertFalse(caps.available)
        
        # On non-Windows
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()
        caps = detector.detect_win32_capabilities()
        self.assertFalse(caps.available)
    
    def test_detect_all(self):
        """Test detecting all platforms."""
        all_caps = self.detector.detect_all()
        
        self.assertIn(PlatformType.ANSI, all_caps)
        self.assertIn(PlatformType.TERMIO, all_caps)
        self.assertIn(PlatformType.CURSES, all_caps)
        self.assertIn(PlatformType.WIN32, all_caps)
        
        for platform_type, caps in all_caps.items():
            self.assertIsInstance(caps, PlatformCapabilities)
    
    @patch('sys.stdout')
    def test_select_best_platform(self, mock_stdout):
        """Test best platform selection."""
        mock_stdout.isatty.return_value = True
        
        # Mock all platforms with different scores
        with patch.object(self.detector, 'detect_all') as mock_detect:
            mock_detect.return_value = {
                PlatformType.ANSI: PlatformCapabilities(
                    name="ANSI", available=True, performance_score=70
                ),
                PlatformType.TERMIO: PlatformCapabilities(
                    name="TermIO", available=True, performance_score=80
                ),
                PlatformType.CURSES: PlatformCapabilities(
                    name="Curses", available=True, performance_score=60
                ),
                PlatformType.WIN32: PlatformCapabilities(
                    name="Win32", available=False
                ),
            }
            
            # Should select TermIO (highest score)
            best = self.detector.select_best_platform()
            self.assertEqual(best, PlatformType.TERMIO)
    
    def test_select_best_platform_none_available(self):
        """Test when no platforms are available."""
        with patch.object(self.detector, 'detect_all') as mock_detect:
            mock_detect.return_value = {
                PlatformType.ANSI: PlatformCapabilities(name="ANSI", available=False),
                PlatformType.TERMIO: PlatformCapabilities(name="TermIO", available=False),
                PlatformType.CURSES: PlatformCapabilities(name="Curses", available=False),
                PlatformType.WIN32: PlatformCapabilities(name="Win32", available=False),
            }
            
            best = self.detector.select_best_platform()
            self.assertIsNone(best)
    
    def test_get_platform_info(self):
        """Test getting platform information."""
        info = self.detector.get_platform_info()
        
        self.assertIn('system', info)
        self.assertIn('is_tty', info)
        self.assertIn('term', info)
        self.assertIn('colorterm', info)
        self.assertIn('term_program', info)
        self.assertIn('python_version', info)
        self.assertIn('platform_capabilities', info)
        
        # Check all platforms are included
        caps = info['platform_capabilities']
        self.assertIn('ANSI', caps)
        self.assertIn('TERMIO', caps)
        self.assertIn('CURSES', caps)
        self.assertIn('WIN32', caps)


if __name__ == '__main__':
    unittest.main()