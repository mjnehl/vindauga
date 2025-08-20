#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo: Display Buffer with Damage Tracking

This demo showcases the DisplayBuffer class and its damage tracking capabilities,
which are core components of Phase 1 of the TVision I/O migration.
"""

import time
from vindauga.io.display_buffer import DisplayBuffer
from vindauga.io.screen_cell import ScreenCell


def print_buffer_visualization(buffer: DisplayBuffer, show_damage: bool = True):
    """Visualize the buffer content and damage regions."""
    print("\n" + "=" * 60)
    print("BUFFER VISUALIZATION")
    print("=" * 60)
    
    # Show buffer content
    for y in range(min(buffer.height, 10)):  # Show first 10 rows
        row_text = ""
        for x in range(min(buffer.width, 60)):  # Show first 60 columns
            cell = buffer.get_cell(x, y)
            if cell:
                row_text += cell.char
        print(f"Row {y:2}: {row_text}")
    
    if show_damage:
        print("\nDAMAGE REGIONS:")
        print("-" * 40)
        damage_count = 0
        for y, region in buffer.get_damaged_regions():
            bounds = region.get_bounds()
            print(f"  Row {y:2}: columns {bounds[0]:3} to {bounds[1]:3} (width: {region.width})")
            damage_count += 1
        
        if damage_count == 0:
            print("  No damage (buffer is clean)")
        else:
            print(f"\nTotal damaged rows: {damage_count}")


def demo_basic_operations():
    """Demonstrate basic buffer operations."""
    print("\n" + "=" * 60)
    print("DEMO 1: Basic Buffer Operations")
    print("=" * 60)
    
    # Create a buffer
    buffer = DisplayBuffer(80, 25)
    print(f"\nCreated buffer: {buffer}")
    
    # Put some text
    buffer.put_text(5, 2, "Hello, World!", fg=7, bg=0)
    buffer.put_text(5, 4, "Display Buffer Demo", fg=2, bg=0, 
                   attrs=ScreenCell.ATTR_BOLD)
    
    print("\nAdded text to buffer:")
    print_buffer_visualization(buffer)
    
    # Clear damage to show tracking
    print("\nClearing damage tracking...")
    buffer.clear_damage()
    print_buffer_visualization(buffer)
    
    # Add more text to show new damage
    buffer.put_text(5, 6, "New text creates damage", fg=3)
    print("\nAdded new text (creates damage):")
    print_buffer_visualization(buffer)


def demo_wide_characters():
    """Demonstrate wide character support."""
    print("\n" + "=" * 60)
    print("DEMO 2: Wide Character Support")
    print("=" * 60)
    
    buffer = DisplayBuffer(80, 25)
    
    # Mix ASCII and wide characters
    buffer.put_text(5, 2, "ASCII: Hello", fg=7)
    buffer.put_text(5, 3, "中文: 你好世界", fg=3)
    buffer.put_text(5, 4, "日本語: こんにちは", fg=6)
    buffer.put_text(5, 5, "Emoji: 🎉 🚀 ⭐", fg=5)
    
    print("\nBuffer with wide characters:")
    print_buffer_visualization(buffer)
    
    # Show cell details
    print("\nCell details at row 3:")
    for x in range(5, 20):
        cell = buffer.get_cell(x, 3)
        if cell and cell.char.strip():
            print(f"  Col {x:2}: '{cell.char}' (width: {cell.width}, wide: {cell.is_wide})")


def demo_scrolling():
    """Demonstrate scrolling operations."""
    print("\n" + "=" * 60)
    print("DEMO 3: Scrolling Operations")
    print("=" * 60)
    
    buffer = DisplayBuffer(40, 10)
    
    # Fill with numbered lines
    for y in range(10):
        buffer.put_text(0, y, f"Line {y:2}: Original content here")
    
    print("\nInitial buffer:")
    print_buffer_visualization(buffer, show_damage=False)
    
    # Scroll up
    print("\nScrolling up by 2 lines...")
    buffer.scroll_up(2)
    print_buffer_visualization(buffer, show_damage=False)
    
    # Scroll down
    print("\nScrolling down by 1 line...")
    buffer.scroll_down(1)
    print_buffer_visualization(buffer, show_damage=False)


def demo_damage_optimization():
    """Demonstrate damage tracking optimization."""
    print("\n" + "=" * 60)
    print("DEMO 4: Damage Tracking Optimization")
    print("=" * 60)
    
    buffer = DisplayBuffer(80, 25)
    
    # Scenario 1: Multiple changes on same row
    print("\nScenario 1: Multiple changes on same row")
    buffer.put_text(5, 5, "First")
    buffer.put_text(20, 5, "Second")
    buffer.put_text(40, 5, "Third")
    
    # Show coalesced damage
    print("Multiple writes coalesce into single damage region:")
    for y, region in buffer.get_damaged_regions():
        bounds = region.get_bounds()
        print(f"  Row {y}: columns {bounds[0]} to {bounds[1]} (single region)")
    
    buffer.clear_damage()
    
    # Scenario 2: Scattered changes
    print("\nScenario 2: Scattered changes across rows")
    buffer.put_char(10, 5, 'A')
    buffer.put_char(20, 10, 'B')
    buffer.put_char(30, 15, 'C')
    
    damage_count = sum(1 for _ in buffer.get_damaged_regions())
    print(f"Scattered changes create {damage_count} separate damage regions")
    
    for y, region in buffer.get_damaged_regions():
        bounds = region.get_bounds()
        print(f"  Row {y:2}: column {bounds[0]} (width: {region.width})")


def demo_fps_limiting():
    """Demonstrate FPS limiting functionality."""
    print("\n" + "=" * 60)
    print("DEMO 5: FPS Limiting")
    print("=" * 60)
    
    # Create buffer with 10 FPS limit
    buffer = DisplayBuffer(80, 25, fps=10)
    print(f"\nBuffer with FPS limit: {buffer.fps_limiter}")
    
    # Simulate rapid updates
    print("\nSimulating rapid updates (should be limited to 10 FPS):")
    update_count = 0
    allowed_count = 0
    start_time = time.time()
    
    while time.time() - start_time < 1.0:  # Run for 1 second
        if buffer.should_update():
            allowed_count += 1
            print(f"  Update {allowed_count} allowed at {time.time() - start_time:.3f}s")
        update_count += 1
        time.sleep(0.01)  # Try to update every 10ms (100 FPS)
    
    print(f"\nAttempted updates: {update_count}")
    print(f"Allowed updates: {allowed_count} (target: ~10)")


def demo_buffer_statistics():
    """Demonstrate buffer statistics."""
    print("\n" + "=" * 60)
    print("DEMO 6: Buffer Statistics")
    print("=" * 60)
    
    buffer = DisplayBuffer(80, 25)
    
    # Add various content
    buffer.put_text(10, 5, "Sample text here")
    buffer.put_text(10, 10, "Another line of text")
    buffer.clear_rect(20, 8, 10, 3)
    
    # Show statistics
    print(f"\nBuffer: {buffer}")
    print("\nDamage summary:")
    
    damaged_rows = list(buffer.get_damaged_regions())
    total_damage = sum(region.width for _, region in damaged_rows)
    total_cells = buffer.width * buffer.height
    
    print(f"  Total cells: {total_cells}")
    print(f"  Damaged rows: {len(damaged_rows)}")
    print(f"  Damaged cells: {total_damage}")
    print(f"  Damage percentage: {(total_damage / total_cells) * 100:.1f}%")


def main():
    """Run all demos."""
    print("=" * 60)
    print("PHASE 1 DISPLAY BUFFER DEMONSTRATION")
    print("TVision I/O Migration - Core Infrastructure")
    print("=" * 60)
    
    demos = [
        ("Basic Operations", demo_basic_operations),
        ("Wide Characters", demo_wide_characters),
        ("Scrolling", demo_scrolling),
        ("Damage Optimization", demo_damage_optimization),
        ("FPS Limiting", demo_fps_limiting),
        ("Buffer Statistics", demo_buffer_statistics)
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n[{i}/{len(demos)}] Running: {name}")
        demo_func()
        
        if i < len(demos):
            input("\nPress Enter to continue to next demo...")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\nPhase 1 components demonstrated:")
    print("  ✅ DisplayBuffer with 2D cell grid")
    print("  ✅ ScreenCell with Unicode support")
    print("  ✅ DamageRegion tracking for efficiency")
    print("  ✅ FPS limiting for controlled updates")
    print("  ✅ Wide character support")
    print("  ✅ Scrolling operations")
    print("\nThese components form the foundation for the TVision I/O subsystem.")


if __name__ == '__main__':
    main()