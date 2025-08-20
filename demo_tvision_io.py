#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo of the new TVision I/O subsystem (Phase 1)

This demo showcases the new I/O infrastructure without requiring
full platform implementations. It demonstrates:
- DisplayBuffer with damage tracking
- ScreenCell with Unicode/wide character support
- Platform detection capabilities
- FPS limiting and performance optimization
"""

import time
import sys
from vindauga.io import PlatformIO, ScreenCell, DisplayBuffer, DamageRegion
from vindauga.io.platform import PlatformDetector, PlatformType


def demo_screen_cell():
    """Demonstrate ScreenCell capabilities."""
    print("=== ScreenCell Demo ===")
    
    # Basic ASCII character
    cell1 = ScreenCell('A', 0x07)
    print(f"ASCII cell: '{cell1.text}' width={cell1.width} attr=0x{cell1.attr:02x}")
    
    # Unicode wide character
    cell2 = ScreenCell('你', 0x0F)  # Chinese character
    print(f"Wide char:  '{cell2.text}' width={cell2.width} is_wide={cell2.is_wide()}")
    
    # Emoji
    cell3 = ScreenCell('🚀', 0x0E)
    print(f"Emoji:      '{cell3.text}' width={cell3.width}")
    
    # Combining character
    cell4 = ScreenCell('é', 0x0A)  # e with acute accent
    print(f"Combining:  '{cell4.text}' width={cell4.width}")
    
    # Trail cell for wide characters
    trail = cell2.make_trail()
    print(f"Trail cell: '{trail.text}' width={trail.width} is_trail={trail.is_trail()}")
    
    # Memory optimization demonstration
    print(f"ScreenCell memory slots: {ScreenCell.__slots__}")
    
    print()


def demo_display_buffer():
    """Demonstrate DisplayBuffer with damage tracking."""
    print("=== DisplayBuffer Demo ===")
    
    # Create a buffer
    buffer = DisplayBuffer(80, 25)
    print(f"Created buffer: {buffer.width}x{buffer.height}")
    
    # Put some content
    buffer.put_text(10, 5, "Hello, 世界! 🌍", 0x07)
    buffer.put_text(10, 6, "Wide chars: 你好 測試", 0x0F)
    buffer.put_char(10, 8, '🚀', 0x0E)
    
    # Show damage tracking
    print(f"Has damage: {buffer.has_damage()}")
    damaged_rows = buffer.get_damaged_rows()
    print(f"Damaged rows: {damaged_rows}")
    
    # Show buffer stats
    stats = buffer.get_stats()
    print(f"Buffer stats:")
    print(f"  Total cells: {stats['total_cells']}")
    print(f"  Dirty cells: {stats['dirty_cells']}")
    print(f"  Damaged rows: {stats['damaged_rows']}")
    print(f"  Damage ratio: {stats['damage_ratio']:.2%}")
    
    # Demonstrate flush preparation (without actual screen output)
    buffer.set_fps_limit(0)  # Disable for demo
    flush_data = buffer.prepare_flush()
    print(f"Flush data: {len(flush_data)} regions to update")
    for i, (row, start, end, cells) in enumerate(flush_data[:3]):  # Show first 3
        text = ''.join(cell.text for cell in cells)
        print(f"  Region {i+1}: row={row}, cols={start}-{end}, text='{text}'")
    
    # Demonstrate resize
    print(f"Resizing buffer to 120x30...")
    buffer.resize(120, 30)
    print(f"New size: {buffer.width}x{buffer.height}")
    
    print()


def demo_platform_detection():
    """Demonstrate platform detection."""
    print("=== Platform Detection Demo ===")
    
    detector = PlatformDetector()
    
    # Show system info
    info = detector.get_platform_info()
    print(f"System: {info['system']}")
    print(f"Python: {info['python_version'].split()[0]}")
    print(f"Terminal: {info.get('terminal', 'unknown')}")
    print(f"Color term: {info.get('colorterm', 'none')}")
    
    print("\nPlatform capabilities:")
    for platform_name, caps in info['platforms'].items():
        status = "✓ Available" if caps['available'] else "✗ Not available"
        print(f"  {platform_name.upper():8} {status:15} (score: {caps['score']:3d})")
        if caps['available']:
            features = []
            if caps['colors']: features.append(f"{caps['max_colors']} colors")
            if caps['mouse']: features.append("mouse")
            if caps['unicode']: features.append("unicode")
            if caps['true_color']: features.append("24-bit color")
            if features:
                print(f"           Features: {', '.join(features)}")
    
    # Show available platforms
    try:
        available = detector.list_available_platforms()
        print(f"\nAvailable platforms: {[str(p) for p in available]}")
        
        if available:
            best = detector.detect_best_platform()
            print(f"Best platform: {best}")
        else:
            print("No platforms available in this environment")
    except Exception as e:
        print(f"Platform detection limited in this environment: {type(e).__name__}")
    
    print()


def demo_fps_limiting():
    """Demonstrate FPS limiting."""
    print("=== FPS Limiting Demo ===")
    
    buffer = DisplayBuffer(40, 10)
    
    # Test with 30 FPS limit
    buffer.set_fps_limit(30)
    print("Testing 30 FPS limit...")
    
    updates = 0
    start_time = time.time()
    
    # Try to update rapidly for 1 second
    while time.time() - start_time < 1.0:
        buffer.put_char(updates % 40, 0, str(updates % 10), 0x07)
        flush_data = buffer.prepare_flush()
        if flush_data:  # Update was allowed
            buffer.commit_flush()
            updates += 1
    
    elapsed = time.time() - start_time
    actual_fps = updates / elapsed
    print(f"Actual FPS: {actual_fps:.1f} (target: 30.0)")
    
    # Test without FPS limit
    buffer.set_fps_limit(0)  # Disable
    print("Testing without FPS limit...")
    
    updates = 0
    start_time = time.time()
    
    while time.time() - start_time < 0.1:  # Shorter test
        buffer.put_char(updates % 40, 1, str(updates % 10), 0x07)
        flush_data = buffer.prepare_flush()
        if flush_data:
            buffer.commit_flush()
            updates += 1
    
    elapsed = time.time() - start_time
    actual_fps = updates / elapsed
    print(f"Unlimited FPS: {actual_fps:.0f} updates/second")
    
    print()


def demo_damage_tracking():
    """Demonstrate damage tracking optimization."""
    print("=== Damage Tracking Demo ===")
    
    buffer = DisplayBuffer(80, 25)
    
    # Show initial state
    print("Initial state: no damage")
    print(f"Has damage: {buffer.has_damage()}")
    
    # Make some changes
    print("\nMaking changes...")
    buffer.put_text(10, 5, "Line 1", 0x07)
    buffer.put_text(20, 10, "Line 2", 0x0F)
    buffer.put_text(30, 15, "Line 3", 0x0E)
    
    # Show damage
    print(f"Has damage: {buffer.has_damage()}")
    damaged_rows = buffer.get_damaged_rows()
    print(f"Damaged rows: {damaged_rows}")
    
    # Show damage regions
    for row in damaged_rows:
        region = buffer.damage[row]
        print(f"  Row {row}: columns {region.start}-{region.end} ({region.length()} cells)")
    
    # Simulate flush
    print("\nSimulating flush...")
    buffer.set_fps_limit(0)
    flush_data = buffer.prepare_flush()
    buffer.commit_flush()
    
    print(f"After flush - Has damage: {buffer.has_damage()}")
    
    print()


def demo_unicode_edge_cases():
    """Demonstrate Unicode edge case handling."""
    print("=== Unicode Edge Cases Demo ===")
    
    test_cases = [
        ("ASCII", "Hello"),
        ("Latin", "café"),
        ("Chinese", "你好"),
        ("Japanese", "こんにちは"),
        ("Arabic", "مرحبا"),
        ("Emoji", "👋🌍🚀"),
        ("Mixed", "Hello 世界 🌍"),
        ("Combining", "e\u0301"),  # e + combining acute accent
    ]
    
    buffer = DisplayBuffer(50, len(test_cases) + 2)
    
    for i, (name, text) in enumerate(test_cases):
        buffer.put_text(0, i, f"{name:10}: {text}", 0x07)
        
        # Show individual character analysis
        total_width = 0
        for j, char in enumerate(text):
            cell = ScreenCell(char)
            total_width += cell.width
        
        print(f"{name:10}: '{text}' -> display width: {total_width}")
    
    # Show buffer stats
    stats = buffer.get_stats()
    print(f"\nBuffer contains {stats['dirty_cells']} dirty cells across {stats['damaged_rows']} rows")
    
    print()


def main():
    """Run all demos."""
    print("🚀 TVision I/O Subsystem Phase 1 Demo")
    print("=" * 50)
    print()
    
    try:
        demo_screen_cell()
        demo_display_buffer()
        demo_platform_detection()
        demo_fps_limiting()
        demo_damage_tracking()
        demo_unicode_edge_cases()
        
        print("✅ All demos completed successfully!")
        print("\n📋 Phase 1 Features Demonstrated:")
        print("  ✓ ScreenCell with UTF-8 and wide character support")
        print("  ✓ DisplayBuffer with damage tracking")
        print("  ✓ Platform detection and capability scoring")
        print("  ✓ FPS limiting for performance optimization")
        print("  ✓ Memory-efficient design with __slots__")
        print("  ✓ Unicode edge case handling")
        
        print("\n🎯 Ready for Phase 2: Platform Implementations")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())