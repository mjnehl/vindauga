# -*- coding: utf-8 -*-
"""
Unit tests for platform detection system.

Tests for PlatformDetector, PlatformType, and PlatformCapabilities classes.
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from vindauga.io.platform import PlatformDetector, PlatformType, PlatformCapabilities


class TestPlatformType(unittest.TestCase):
    """Test cases for PlatformType enum."""
    
    def test_from_string(self):
        """Test PlatformType.from_string method."""
        self.assertEqual(PlatformType.from_string('ansi'), PlatformType.ANSI)
        self.assertEqual(PlatformType.from_string('ANSI'), PlatformType.ANSI)
        self.assertEqual(PlatformType.from_string('termio'), PlatformType.TERMIO)
        self.assertEqual(PlatformType.from_string('curses'), PlatformType.CURSES)
        
        with self.assertRaises(ValueError):
            PlatformType.from_string('unknown')
    
    def test_string_conversion(self):
        """Test string conversion."""
        self.assertEqual(str(PlatformType.ANSI), 'ansi')
        self.assertEqual(str(PlatformType.TERMIO), 'termio')
        self.assertEqual(str(PlatformType.CURSES), 'curses')


class TestPlatformCapabilities(unittest.TestCase):
    """Test cases for PlatformCapabilities class."""
    
    def test_basic_capabilities(self):
        """Test basic capability creation."""
        caps = PlatformCapabilities(
            has_colors=True,
            has_mouse=True,
            has_unicode=True,
            max_colors=256,
            is_available=True
        )
        
        self.assertTrue(caps.has_colors)
        self.assertTrue(caps.has_mouse)
        self.assertTrue(caps.has_unicode)
        self.assertEqual(caps.max_colors, 256)
        self.assertTrue(caps.is_available)
    
    def test_scoring(self):
        """Test capability scoring."""
        # High capability platform
        high_caps = PlatformCapabilities(
            has_colors=True,
            has_mouse=True,
            has_unicode=True,
            has_24bit_color=True,
            max_colors=16777216,
            is_available=True
        )
        
        # Low capability platform
        low_caps = PlatformCapabilities(
            has_colors=False,
            has_mouse=False,
            has_unicode=False,
            max_colors=0,
            is_available=True
        )
        
        # Unavailable platform
        unavailable_caps = PlatformCapabilities(is_available=False)
        
        self.assertGreater(high_caps.score(), low_caps.score())
        self.assertGreater(low_caps.score(), unavailable_caps.score())
        self.assertEqual(unavailable_caps.score(), 0)  # Unavailable = 0 score


class TestPlatformDetector(unittest.TestCase):
    """Test cases for PlatformDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = PlatformDetector()
    
    def test_ansi_detection(self):
        """Test ANSI terminal detection."""
        # Mock terminal environment
        with patch.dict(os.environ, {'TERM': 'xterm-256color', 'COLORTERM': 'truecolor'}):
            with patch('sys.stdout') as mock_stdout:
                mock_stdout.isatty.return_value = True
                
                caps = self.detector.get_ansi_capabilities()
                
                self.assertTrue(caps.is_available)
                self.assertTrue(caps.has_colors)
                self.assertTrue(caps.has_mouse)
                self.assertTrue(caps.has_unicode)
                self.assertTrue(caps.has_24bit_color)
                self.assertEqual(caps.max_colors, 16777216)
    
    def test_ansi_detection_no_terminal(self):
        """Test ANSI detection when not in a terminal."""
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = False
            
            caps = self.detector.get_ansi_capabilities()
            self.assertFalse(caps.is_available)
    
    def test_ansi_detection_basic_term(self):
        """Test ANSI detection with basic terminal."""
        with patch.dict(os.environ, {'TERM': 'screen', 'COLORTERM': ''}):
            with patch('sys.stdout') as mock_stdout:
                mock_stdout.isatty.return_value = True
                
                caps = self.detector.get_ansi_capabilities()
                
                self.assertTrue(caps.is_available)
                self.assertTrue(caps.has_colors)
                self.assertFalse(caps.has_24bit_color)
                self.assertEqual(caps.max_colors, 256)
    
    @patch('platform.system')
    def test_termio_detection_linux(self, mock_system):
        """Test TermIO detection on Linux."""
        mock_system.return_value = 'Linux'
        
        # Mock termios import and stdin
        with patch.dict('sys.modules', {'termios': MagicMock(), 'tty': MagicMock()}):
            with patch('sys.stdin') as mock_stdin:
                mock_stdin.fileno.return_value = 0
                
                # Mock successful termios.tcgetattr call
                import sys
                termios_mock = sys.modules['termios']
                termios_mock.tcgetattr.return_value = {}
                
                caps = self.detector.get_termio_capabilities()
                
                self.assertTrue(caps.is_available)
                self.assertTrue(caps.has_colors)  # Depends on TERM
                self.assertTrue(caps.has_mouse)
                self.assertTrue(caps.has_unicode)
    
    @patch('platform.system')
    def test_termio_detection_windows(self, mock_system):
        """Test TermIO detection on Windows (should be unavailable)."""
        mock_system.return_value = 'Windows'
        
        caps = self.detector.get_termio_capabilities()
        self.assertFalse(caps.is_available)
    
    def test_curses_detection_available(self):
        """Test Curses detection when available."""
        # Mock successful curses import
        with patch.dict('sys.modules', {'curses': MagicMock()}):
            caps = self.detector.get_curses_capabilities()
            
            self.assertTrue(caps.is_available)
            self.assertTrue(caps.has_colors)
            self.assertTrue(caps.has_mouse)
            self.assertTrue(caps.has_unicode)
            self.assertFalse(caps.has_24bit_color)
            self.assertEqual(caps.max_colors, 256)
    
    def test_curses_detection_unavailable(self):
        """Test Curses detection when unavailable."""
        # Mock failed curses import
        with patch('builtins.__import__') as mock_import:
            def import_side_effect(name, *args, **kwargs):
                if name == 'curses':
                    raise ImportError("No module named 'curses'")
                return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = import_side_effect
            
            # Clear cache to force re-detection
            self.detector._capabilities_cache.clear()
            
            caps = self.detector.get_curses_capabilities()
            self.assertFalse(caps.is_available)
    
    def test_win32_detection(self):
        """Test Win32 detection (future implementation)."""
        caps = self.detector.get_win32_capabilities()
        self.assertFalse(caps.is_available)  # Not implemented yet
    
    def test_best_platform_detection(self):
        """Test best platform detection."""
        # Mock all platforms as available with different scores
        with patch.object(self.detector, 'get_ansi_capabilities') as mock_ansi:
            with patch.object(self.detector, 'get_termio_capabilities') as mock_termio:
                with patch.object(self.detector, 'get_curses_capabilities') as mock_curses:
                    
                    # ANSI with highest score
                    mock_ansi.return_value = PlatformCapabilities(
                        has_colors=True, has_mouse=True, has_unicode=True, 
                        has_24bit_color=True, max_colors=16777216, is_available=True
                    )
                    
                    # TermIO with medium score
                    mock_termio.return_value = PlatformCapabilities(
                        has_colors=True, has_mouse=True, has_unicode=True,
                        max_colors=256, is_available=True
                    )
                    
                    # Curses with lower score
                    mock_curses.return_value = PlatformCapabilities(
                        has_colors=True, has_mouse=True, has_unicode=True,
                        max_colors=256, is_available=True
                    )
                    
                    best_platform = self.detector.detect_best_platform()
                    self.assertEqual(best_platform, PlatformType.ANSI)
    
    def test_no_platforms_available(self):
        """Test behavior when no platforms are available."""
        # Mock all platforms as unavailable
        with patch.object(self.detector, 'get_ansi_capabilities') as mock_ansi:
            with patch.object(self.detector, 'get_termio_capabilities') as mock_termio:
                with patch.object(self.detector, 'get_curses_capabilities') as mock_curses:
                    
                    mock_ansi.return_value = PlatformCapabilities(is_available=False)
                    mock_termio.return_value = PlatformCapabilities(is_available=False)
                    mock_curses.return_value = PlatformCapabilities(is_available=False)
                    
                    with self.assertRaises(RuntimeError):
                        self.detector.detect_best_platform()
    
    def test_list_available_platforms(self):
        """Test listing available platforms."""
        # Mock some platforms as available
        with patch.object(self.detector, 'get_platform_capabilities') as mock_caps:
            def caps_side_effect(platform_type):
                if platform_type == PlatformType.ANSI:
                    return PlatformCapabilities(is_available=True)
                elif platform_type == PlatformType.CURSES:
                    return PlatformCapabilities(is_available=True)
                else:
                    return PlatformCapabilities(is_available=False)
            
            mock_caps.side_effect = caps_side_effect
            
            available = self.detector.list_available_platforms()
            self.assertIn(PlatformType.ANSI, available)
            self.assertIn(PlatformType.CURSES, available)
            self.assertNotIn(PlatformType.TERMIO, available)
            self.assertNotIn(PlatformType.WIN32, available)
    
    def test_platform_info(self):
        """Test platform information gathering."""
        info = self.detector.get_platform_info()
        
        self.assertIn('system', info)
        self.assertIn('python_version', info)
        self.assertIn('terminal', info)
        self.assertIn('colorterm', info)
        self.assertIn('platforms', info)
        
        # Check that all platform types are included
        for platform_type in PlatformType:
            self.assertIn(platform_type.value, info['platforms'])
    
    def test_capabilities_caching(self):
        """Test that capabilities are cached."""
        # First call
        caps1 = self.detector.get_ansi_capabilities()
        
        # Second call should return same object (cached)
        caps2 = self.detector.get_ansi_capabilities()
        
        self.assertIs(caps1, caps2)


if __name__ == '__main__':
    unittest.main()