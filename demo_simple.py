#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple demo of TVision I/O Phase 1 - Core functionality only
"""

from vindauga.io import ScreenCell, DisplayBuffer

def main():
    print("🚀 TVision I/O Phase 1 - Simple Demo")
    print("=" * 40)
    
    # 1. ScreenCell demo
    print("\n1. ScreenCell Examples:")
    cells = [
        ScreenCell('A', 0x07),           # ASCII
        ScreenCell('你', 0x0F),          # Chinese (wide)
        ScreenCell('🚀', 0x0E),          # Emoji (wide)
    ]
    
    for i, cell in enumerate(cells, 1):
        print(f"   {i}. '{cell.text}' -> width={cell.width}, wide={cell.is_wide()}")
    
    # 2. DisplayBuffer demo
    print("\n2. DisplayBuffer Example:")
    buffer = DisplayBuffer(80, 25)
    buffer.put_text(10, 5, "Hello, World! 你好 🌍", 0x07)
    
    print(f"   Buffer: {buffer.width}x{buffer.height}")
    print(f"   Has damage: {buffer.has_damage()}")
    print(f"   Damaged rows: {buffer.get_damaged_rows()}")
    
    # Get some cells back
    cell = buffer.get_cell(10, 5)  # 'H'
    wide_cell = buffer.get_cell(21, 5)  # '你'
    print(f"   Cell at (10,5): '{cell.text}'")
    print(f"   Cell at (21,5): '{wide_cell.text}' (width={wide_cell.width})")
    
    # 3. Stats
    stats = buffer.get_stats()
    print(f"\n3. Buffer Stats:")
    print(f"   Dirty cells: {stats['dirty_cells']}")
    print(f"   Damage ratio: {stats['damage_ratio']:.1%}")
    
    print("\n✅ Phase 1 core functionality working!")
    return 0

if __name__ == "__main__":
    main()