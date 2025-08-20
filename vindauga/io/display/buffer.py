# -*- coding: utf-8 -*-
"""
Display buffer and damage tracking system.
"""

import time
import unicodedata
from typing import Optional, List, Tuple, Dict, Any


class ScreenCell:
    """Represents a single character cell on the screen."""
    
    FLAG_DIRTY = 0x01
    FLAG_WIDE = 0x02
    FLAG_TRAIL = 0x04
    
    def __init__(self, text: str = ' ', attr: int = 0, flags: int = 0):
        """Initialize a screen cell."""
        # Truncate text to max 15 UTF-8 bytes
        if text:
            encoded = text.encode('utf-8')
            if len(encoded) > 15:
                # Truncate at valid UTF-8 boundary
                encoded = encoded[:15]
                while encoded:
                    try:
                        text = encoded.decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        encoded = encoded[:-1]
            self.text = text
        else:
            self.text = ' '
        
        self.attr = attr
        self.flags = flags | FLAG_DIRTY
        
        # Calculate display width
        if self.text:
            width = unicodedata.east_asian_width(self.text[0])
            if width in ('W', 'F'):
                self.width = 2
                self.flags |= FLAG_WIDE
            else:
                self.width = 1
        else:
            self.width = 1 if not (flags & FLAG_TRAIL) else 0
    
    def is_dirty(self) -> bool:
        """Check if cell is dirty."""
        return bool(self.flags & self.FLAG_DIRTY)
    
    def mark_dirty(self) -> None:
        """Mark cell as dirty."""
        self.flags |= self.FLAG_DIRTY
    
    def clear_dirty(self) -> None:
        """Clear dirty flag."""
        self.flags &= ~self.FLAG_DIRTY
    
    def is_wide(self) -> bool:
        """Check if cell contains wide character."""
        return bool(self.flags & self.FLAG_WIDE)
    
    def is_trail(self) -> bool:
        """Check if cell is trailing part of wide character."""
        return bool(self.flags & self.FLAG_TRAIL)
    
    def make_trail(self) -> 'ScreenCell':
        """Create trailing cell for wide character."""
        return ScreenCell('', self.attr, self.FLAG_TRAIL | self.FLAG_DIRTY)
    
    def equals(self, other: 'ScreenCell') -> bool:
        """Check if cells are equal (ignoring dirty flag)."""
        if not isinstance(other, ScreenCell):
            return False
        return (self.text == other.text and 
                self.attr == other.attr and
                (self.flags & ~self.FLAG_DIRTY) == (other.flags & ~self.FLAG_DIRTY))
    
    def __eq__(self, other) -> bool:
        """Check equality including all flags."""
        if not isinstance(other, ScreenCell):
            return False
        return (self.text == other.text and 
                self.attr == other.attr and
                self.flags == other.flags)
    
    def copy(self) -> 'ScreenCell':
        """Create a copy of this cell."""
        return ScreenCell(self.text, self.attr, self.flags)


class DamageRegion:
    """Tracks damaged region in a row."""
    
    def __init__(self):
        """Initialize damage region."""
        self.is_dirty = False
        self.start = 0
        self.end = 0
    
    def expand(self, start: int, end: int) -> None:
        """Expand damage region."""
        if not self.is_dirty:
            self.start = start
            self.end = end
            self.is_dirty = True
        else:
            self.start = min(self.start, start)
            self.end = max(self.end, end)
    
    def contains(self, col: int) -> bool:
        """Check if column is in damage region."""
        return self.is_dirty and self.start <= col < self.end
    
    def clear(self) -> None:
        """Clear damage region."""
        self.is_dirty = False
        self.start = 0
        self.end = 0
    
    def length(self) -> int:
        """Get length of damage region."""
        return self.end - self.start if self.is_dirty else 0


class FPSLimiter:
    """Frame rate limiter for display updates."""
    
    def __init__(self, target_fps: int = 60):
        """Initialize FPS limiter."""
        self.set_fps(target_fps)
        self.last_update = 0.0
    
    def set_fps(self, target_fps: int) -> None:
        """Set target FPS."""
        self.target_fps = target_fps
        if target_fps > 0:
            self.frame_time = 1.0 / target_fps
            self.enabled = True
        else:
            self.frame_time = 0.0
            self.enabled = False
    
    def should_update(self) -> bool:
        """Check if update should be performed."""
        if not self.enabled:
            return True
        
        current_time = time.monotonic()
        if current_time - self.last_update >= self.frame_time:
            self.last_update = current_time
            return True
        
        return False


class DisplayBuffer:
    """Double-buffered display with damage tracking."""
    
    def __init__(self, width: int, height: int):
        """Initialize display buffer."""
        self.width = width
        self.height = height
        
        # Create primary buffer
        self.primary_buffer = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(ScreenCell())
            self.primary_buffer.append(row)
        
        # Create damage tracking
        self.damage = [DamageRegion() for _ in range(height)]
        
        # FPS limiter
        self.fps_limiter = FPSLimiter(0)  # Disabled by default
    
    def get_cell(self, x: int, y: int) -> Optional[ScreenCell]:
        """Get cell at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.primary_buffer[y][x]
        return None
    
    def put_char(self, x: int, y: int, char: str, attr: int = 0) -> None:
        """Put character at position."""
        if 0 <= y < self.height and 0 <= x < self.width:
            cell = ScreenCell(char, attr)
            self.primary_buffer[y][x] = cell
            
            # Handle wide characters
            if cell.is_wide() and x + 1 < self.width:
                self.primary_buffer[y][x + 1] = cell.make_trail()
                self.damage[y].expand(x, x + 2)
            else:
                self.damage[y].expand(x, x + 1)
    
    def put_text(self, x: int, y: int, text: str, attr: int = 0) -> None:
        """Put text at position."""
        if y < 0 or y >= self.height:
            return
        
        pos = x
        for char in text:
            if pos >= self.width:
                break
            if pos >= 0:
                self.put_char(pos, y, char, attr)
                cell = self.get_cell(pos, y)
                if cell and cell.is_wide():
                    pos += 2
                else:
                    pos += 1
            else:
                pos += 1
    
    def fill_rect(self, x: int, y: int, width: int, height: int, 
                  char: str = ' ', attr: int = 0) -> None:
        """Fill rectangle with character."""
        for row in range(y, min(y + height, self.height)):
            for col in range(x, min(x + width, self.width)):
                if row >= 0 and col >= 0:
                    self.put_char(col, row, char, attr)
    
    def clear(self, attr: int = 0) -> None:
        """Clear buffer."""
        for y in range(self.height):
            for x in range(self.width):
                self.primary_buffer[y][x] = ScreenCell(' ', attr)
            self.damage[y].expand(0, self.width)
    
    def has_damage(self) -> bool:
        """Check if buffer has damage."""
        return any(region.is_dirty for region in self.damage)
    
    def get_damage(self, row: int) -> Optional[Tuple[int, int]]:
        """Get damage region for row."""
        if 0 <= row < self.height and self.damage[row].is_dirty:
            return (self.damage[row].start, self.damage[row].end)
        return None
    
    def clear_damage(self, row: int) -> None:
        """Clear damage for row."""
        if 0 <= row < self.height:
            self.damage[row].clear()
    
    def get_damaged_rows(self) -> List[int]:
        """Get list of damaged rows."""
        return [i for i, region in enumerate(self.damage) if region.is_dirty]
    
    def prepare_flush(self) -> List[Tuple[int, int, int, List[ScreenCell]]]:
        """Prepare data for flushing."""
        if not self.fps_limiter.should_update():
            return []
        
        flush_data = []
        for row in self.get_damaged_rows():
            damage = self.get_damage(row)
            if damage:
                start, end = damage
                cells = [self.primary_buffer[row][i].copy() for i in range(start, end)]
                flush_data.append((row, start, end, cells))
        
        return flush_data
    
    def commit_flush(self) -> None:
        """Commit flush by clearing damage."""
        for row in range(self.height):
            if self.damage[row].is_dirty:
                # Clear dirty flags on cells
                for x in range(self.damage[row].start, self.damage[row].end):
                    if x < self.width:
                        self.primary_buffer[row][x].clear_dirty()
                # Clear damage region
                self.damage[row].clear()
    
    def resize(self, width: int, height: int) -> None:
        """Resize buffer."""
        # Create new buffer
        new_buffer = []
        for y in range(height):
            row = []
            for x in range(width):
                if y < self.height and x < self.width:
                    row.append(self.primary_buffer[y][x].copy())
                else:
                    row.append(ScreenCell())
            new_buffer.append(row)
        
        self.primary_buffer = new_buffer
        self.width = width
        self.height = height
        self.damage = [DamageRegion() for _ in range(height)]
    
    def set_fps_limit(self, fps: int) -> None:
        """Set FPS limit."""
        self.fps_limiter.set_fps(fps)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        dirty_cells = 0
        damaged_rows = 0
        
        for y in range(self.height):
            if self.damage[y].is_dirty:
                damaged_rows += 1
                for x in range(self.damage[y].start, self.damage[y].end):
                    if x < self.width and self.primary_buffer[y][x].is_dirty():
                        dirty_cells += 1
        
        total_cells = self.width * self.height
        damage_ratio = dirty_cells / total_cells if total_cells > 0 else 0
        
        return {
            'width': self.width,
            'height': self.height,
            'total_cells': total_cells,
            'dirty_cells': dirty_cells,
            'damaged_rows': damaged_rows,
            'damage_ratio': damage_ratio
        }