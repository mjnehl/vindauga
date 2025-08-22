# -*- coding: utf-8 -*-
"""
Curses display backend.
"""

import curses
from typing import Tuple, Dict
from .base import Display
from ..display_buffer import DisplayBuffer
from ..screen_cell import ScreenCell


class CursesDisplay(Display):
    """Curses display backend."""
    
    def __init__(self):
        """Initialize Curses display."""
        super().__init__()
        self.stdscr = None
        self.has_colors = False
        self.color_pairs = {}
        self.next_pair = 1
        self.max_pairs = 64
    
    def initialize(self) -> bool:
        """Initialize Curses display."""
        if self._initialized:
            return True
        
        try:
            # Initialize curses
            self.stdscr = curses.initscr()
            
            # Setup curses
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(True)
            
            # Check color support
            if curses.has_colors():
                curses.start_color()
                try:
                    curses.use_default_colors()
                except:
                    pass
                self.has_colors = True
                self.max_pairs = min(curses.COLOR_PAIRS, 256)
                self._init_color_pairs()
            
            # Hide cursor
            try:
                curses.curs_set(0)
            except:
                pass
            
            # Get size
            self._height, self._width = self.stdscr.getmaxyx()
            
            # Clear screen
            self.stdscr.clear()
            self.stdscr.refresh()
            
            self._initialized = True
            return True
        except Exception:
            return False
    
    def shutdown(self) -> None:
        """Shutdown Curses display."""
        if not self._initialized:
            return
        
        try:
            # Restore cursor
            try:
                curses.curs_set(1)
            except:
                pass
            
            # Clear screen
            if self.stdscr:
                self.stdscr.clear()
                self.stdscr.refresh()
                self.stdscr.keypad(False)
            
            # Restore terminal
            curses.nocbreak()
            curses.echo()
            curses.endwin()
        except:
            pass
        
        self._initialized = False
    
    def get_size(self) -> Tuple[int, int]:
        """Get terminal size."""
        if self.stdscr:
            height, width = self.stdscr.getmaxyx()
            self._width = width
            self._height = height
            return (width, height)
        return (80, 24)
    
    def _init_color_pairs(self) -> None:
        """Initialize color pairs."""
        # Initialize basic 16-color pairs
        pair_num = 1
        for bg in range(8):
            for fg in range(8):
                if pair_num < self.max_pairs:
                    try:
                        curses.init_pair(pair_num, fg, bg)
                        self.color_pairs[(fg, bg)] = pair_num
                        pair_num += 1
                    except:
                        break
        self.next_pair = pair_num
    
    def _get_color_pair(self, fg: int, bg: int) -> int:
        """Get or create color pair."""
        if not self.has_colors:
            return 0
        
        # Map to curses colors (fg and bg are already color values, not packed attributes)
        fg_curses = self._map_color(fg)
        bg_curses = self._map_color(bg)
        
        # Check if pair exists
        if (fg_curses, bg_curses) in self.color_pairs:
            return self.color_pairs[(fg_curses, bg_curses)]
        
        # Create new pair if possible
        if self.next_pair < self.max_pairs:
            try:
                curses.init_pair(self.next_pair, fg_curses, bg_curses)
                self.color_pairs[(fg_curses, bg_curses)] = self.next_pair
                pair_num = self.next_pair
                self.next_pair += 1
                return pair_num
            except:
                pass
        
        return 0
    
    def _map_color(self, color: int) -> int:
        """Map attribute color to curses color."""
        color_map = {
            0: curses.COLOR_BLACK,
            1: curses.COLOR_RED,
            2: curses.COLOR_GREEN,
            3: curses.COLOR_YELLOW,
            4: curses.COLOR_BLUE,
            5: curses.COLOR_MAGENTA,
            6: curses.COLOR_CYAN,
            7: curses.COLOR_WHITE
        }
        return color_map.get(color & 0x07, curses.COLOR_WHITE)
    
    def _get_curses_attr(self, fg: int, bg: int, attrs: int) -> int:
        """Convert attributes to curses format."""
        result = 0
        
        # Get color pair
        if self.has_colors:
            pair = self._get_color_pair(fg, bg)
            if pair > 0:
                result |= curses.color_pair(pair)
        
        # Handle text attributes
        if attrs & ScreenCell.ATTR_BOLD:
            result |= curses.A_BOLD
        if attrs & ScreenCell.ATTR_UNDERLINE:
            result |= curses.A_UNDERLINE
        if attrs & ScreenCell.ATTR_REVERSE:
            result |= curses.A_REVERSE
        
        return result
    
    def flush_buffer(self, buffer: DisplayBuffer) -> None:
        """Flush buffer to screen using curses."""
        if not self._initialized or not self.stdscr:
            return
        
        # Process each damaged row
        for row_idx, damage in buffer.get_damaged_regions():
            if not damage.is_dirty:
                continue
            
            bounds = damage.get_bounds()
            if bounds is None:
                continue
            
            start, end = bounds
            
            # Output cells in damaged region
            for col in range(start, end):
                cell = buffer.get_cell(col, row_idx)
                if not cell:
                    # Clear cell
                    try:
                        self.stdscr.addstr(row_idx, col, ' ')
                    except curses.error:
                        pass
                    continue
                
                # Get curses attributes
                attr = self._get_curses_attr(cell.fg_color, cell.bg_color, cell.attrs)
                
                # Output character
                try:
                    # Skip wide character trailing cells
                    if cell.is_wide and col + 1 < end:
                        # Wide character - curses handles this automatically
                        self.stdscr.addstr(row_idx, col, cell.char, attr)
                    elif not cell.is_wide:
                        # Normal character
                        self.stdscr.addstr(row_idx, col, cell.char, attr)
                except curses.error:
                    # Ignore errors at screen edges
                    pass
        
        # Refresh screen
        self.stdscr.refresh()
        
        # Clear damage tracking
        buffer.clear_damage()
    
    def set_cursor_position(self, x: int, y: int) -> None:
        """Set cursor position."""
        if 0 <= x < self._width and 0 <= y < self._height:
            self._cursor_x = x
            self._cursor_y = y
            try:
                self.stdscr.move(y, x)
            except:
                pass
    
    def set_cursor_visibility(self, visible: bool) -> None:
        """Set cursor visibility."""
        self._cursor_visible = visible
        try:
            if visible:
                curses.curs_set(1)
            else:
                curses.curs_set(0)
        except:
            pass
    
    def clear_screen(self) -> None:
        """Clear screen."""
        if self.stdscr:
            self.stdscr.clear()
            self.stdscr.refresh()
    
    def supports_colors(self) -> bool:
        """Check color support."""
        return self.has_colors
    
    def supports_mouse(self) -> bool:
        """Check mouse support."""
        try:
            return curses.has_mouse()
        except:
            return False
    
    def get_color_count(self) -> int:
        """Get color count."""
        if self.has_colors:
            try:
                return curses.COLORS
            except:
                return 256
        return 0