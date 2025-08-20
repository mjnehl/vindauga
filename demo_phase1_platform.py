#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo: Platform Detection System

This demo showcases the platform detection capabilities of Phase 1,
which will automatically select the best available terminal I/O backend.
"""

import json
from vindauga.io.platform_detector import (
    PlatformDetector, PlatformType, PlatformCapabilities
)


def print_separator(title: str = ""):
    """Print a formatted separator."""
    if title:
        print(f"\n{'=' * 20} {title} {'=' * 20}")
    else:
        print("=" * 60)


def demo_platform_detection():
    """Demonstrate automatic platform detection."""
    print_separator("Platform Detection")
    
    detector = PlatformDetector()
    
    # Show system information
    print("\nSystem Information:")
    print(f"  Operating System: {detector.system}")
    print(f"  Is Windows: {detector.is_windows}")
    print(f"  Is Linux: {detector.is_linux}")
    print(f"  Is macOS: {detector.is_mac}")
    print(f"  Is Unix-like: {detector.is_unix}")
    
    print("\nTerminal Environment:")
    print(f"  TERM: {detector.term or '(not set)'}")
    print(f"  COLORTERM: {detector.colorterm or '(not set)'}")
    print(f"  TERM_PROGRAM: {detector.term_program or '(not set)'}")
    print(f"  Is TTY: {detector.is_tty}")


def demo_capability_detection():
    """Demonstrate capability detection for each platform."""
    print_separator("Platform Capabilities")
    
    detector = PlatformDetector()
    all_caps = detector.detect_all()
    
    for platform_type, caps in all_caps.items():
        print(f"\n{platform_type.name} Backend:")
        print(f"  Available: {'✅' if caps.available else '❌'}")
        
        if caps.available or platform_type == PlatformType.WIN32:
            print(f"  Color Support: {format_color_support(caps.color_support)}")
            print(f"  Mouse Support: {'✅' if caps.mouse_support else '❌'}")
            print(f"  Unicode Support: {'✅' if caps.unicode_support else '❌'}")
            print(f"  Performance Score: {caps.performance_score}/100")
            print(f"  Overall Score: {caps.overall_score()}/100")


def format_color_support(colors: int) -> str:
    """Format color support for display."""
    if colors >= 16777216:
        return f"24-bit RGB ({colors:,} colors)"
    elif colors >= 256:
        return f"8-bit palette ({colors} colors)"
    elif colors >= 16:
        return f"4-bit ANSI ({colors} colors)"
    elif colors > 0:
        return f"Basic ({colors} colors)"
    else:
        return "No color support"


def demo_best_platform_selection():
    """Demonstrate automatic best platform selection."""
    print_separator("Best Platform Selection")
    
    detector = PlatformDetector()
    best = detector.select_best_platform()
    
    if best:
        print(f"\n🎯 Selected Platform: {best.name}")
        
        # Get capabilities of selected platform
        all_caps = detector.detect_all()
        caps = all_caps[best]
        
        print("\nSelected Platform Details:")
        print(f"  Score: {caps.overall_score()}/100")
        print(f"  Colors: {format_color_support(caps.color_support)}")
        print(f"  Features:")
        features = []
        if caps.mouse_support:
            features.append("Mouse")
        if caps.unicode_support:
            features.append("Unicode")
        if caps.color_support >= 16777216:
            features.append("True Color")
        print(f"    {', '.join(features) if features else 'Basic'}")
    else:
        print("\n⚠️  No suitable platform found!")
        print("This might happen in non-terminal environments.")


def demo_platform_scoring():
    """Demonstrate how platform scoring works."""
    print_separator("Platform Scoring System")
    
    print("\nScoring Breakdown:")
    print("-" * 40)
    
    # Create example capabilities
    examples = [
        ("Minimal Terminal", PlatformCapabilities(
            name="Example1",
            available=True,
            color_support=0,
            mouse_support=False,
            unicode_support=False,
            performance_score=50
        )),
        ("Basic Terminal", PlatformCapabilities(
            name="Example2",
            available=True,
            color_support=16,
            mouse_support=False,
            unicode_support=True,
            performance_score=60
        )),
        ("Modern Terminal", PlatformCapabilities(
            name="Example3",
            available=True,
            color_support=256,
            mouse_support=True,
            unicode_support=True,
            performance_score=70
        )),
        ("Advanced Terminal", PlatformCapabilities(
            name="Example4",
            available=True,
            color_support=16777216,
            mouse_support=True,
            unicode_support=True,
            performance_score=80
        ))
    ]
    
    for name, caps in examples:
        score = caps.overall_score()
        print(f"\n{name}:")
        print(f"  Base Performance: {caps.performance_score}")
        
        bonuses = []
        if caps.color_support >= 16777216:
            bonuses.append("+20 (24-bit color)")
        elif caps.color_support >= 256:
            bonuses.append("+15 (256 colors)")
        elif caps.color_support >= 16:
            bonuses.append("+10 (16 colors)")
        
        if caps.mouse_support:
            bonuses.append("+10 (mouse)")
        if caps.unicode_support:
            bonuses.append("+10 (Unicode)")
        
        if bonuses:
            print(f"  Bonuses: {', '.join(bonuses)}")
        print(f"  Total Score: {score}/100")


def demo_json_export():
    """Demonstrate exporting platform info as JSON."""
    print_separator("Platform Information Export")
    
    detector = PlatformDetector()
    info = detector.get_platform_info()
    
    print("\nPlatform information (JSON format):")
    print("-" * 40)
    
    # Pretty print with limited depth
    simplified = {
        'system': info['system'],
        'is_tty': info['is_tty'],
        'terminal': {
            'TERM': info['term'],
            'COLORTERM': info['colorterm']
        },
        'available_platforms': []
    }
    
    for platform_name, caps_info in info['platform_capabilities'].items():
        if caps_info['available']:
            simplified['available_platforms'].append({
                'name': platform_name,
                'score': caps_info['score'],
                'colors': caps_info['colors']
            })
    
    print(json.dumps(simplified, indent=2))


def demo_fallback_behavior():
    """Demonstrate fallback behavior when platforms aren't available."""
    print_separator("Fallback Behavior")
    
    print("\nPlatform Priority Order:")
    print("1. ANSI (best for modern terminals)")
    print("2. TermIO (Unix/Linux native)")
    print("3. Curses (universal fallback)")
    print("4. Win32 (Windows-specific, not yet implemented)")
    
    print("\nFallback Scenarios:")
    
    # Simulate different scenarios
    scenarios = [
        ("SSH session", "Usually selects ANSI or TermIO"),
        ("Local terminal", "Selects best available (often ANSI)"),
        ("IDE terminal", "May select Curses if ANSI not detected"),
        ("Pipe/redirect", "No platform available (not a TTY)"),
        ("Windows Terminal", "Would select Win32 when implemented")
    ]
    
    for scenario, result in scenarios:
        print(f"  • {scenario}: {result}")


def main():
    """Run all platform detection demos."""
    print("=" * 60)
    print("PHASE 1 PLATFORM DETECTION DEMONSTRATION")
    print("TVision I/O Migration - Platform Detection System")
    print("=" * 60)
    
    demos = [
        ("Platform Detection", demo_platform_detection),
        ("Capability Detection", demo_capability_detection),
        ("Best Platform Selection", demo_best_platform_selection),
        ("Scoring System", demo_platform_scoring),
        ("Information Export", demo_json_export),
        ("Fallback Behavior", demo_fallback_behavior)
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        if i > 1:
            input("\nPress Enter to continue...")
        print(f"\n[{i}/{len(demos)}] {name}")
        demo_func()
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\nPhase 1 Platform Detection Features:")
    print("  ✅ Automatic OS detection")
    print("  ✅ Terminal capability detection")
    print("  ✅ Color support detection (4/8/24-bit)")
    print("  ✅ Mouse and Unicode detection")
    print("  ✅ Performance scoring system")
    print("  ✅ Automatic best platform selection")
    print("\nThis system will automatically choose the best")
    print("available backend for the current environment.")


if __name__ == '__main__':
    main()