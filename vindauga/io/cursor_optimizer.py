# -*- coding: utf-8 -*-
"""
Cursor movement optimization for terminal output.

This module provides optimized cursor movement to reduce the number of
bytes sent to the terminal.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class MoveType(Enum):
    """Types of cursor movements."""
    ABSOLUTE = "absolute"      # ESC[row;colH
    UP = "up"                  # ESC[nA
    DOWN = "down"              # ESC[nB
    RIGHT = "right"            # ESC[nC
    LEFT = "left"              # ESC[nD
    HOME = "home"              # ESC[H
    CARRIAGE_RETURN = "cr"     # \r
    NEWLINE = "newline"        # \n
    TAB = "tab"                # \t
    BACKSPACE = "backspace"    # \b


@dataclass
class CursorMove:
    """Represents a cursor movement."""
    move_type: MoveType
    distance: int = 0
    row: int = 0
    col: int = 0
    
    def to_sequence(self) -> str:
        """Convert to ANSI escape sequence."""
        if self.move_type == MoveType.ABSOLUTE:
            return f"\x1b[{self.row};{self.col}H"
        elif self.move_type == MoveType.UP:
            if self.distance == 1:
                return "\x1b[A"
            return f"\x1b[{self.distance}A"
        elif self.move_type == MoveType.DOWN:
            if self.distance == 1:
                return "\x1b[B"
            return f"\x1b[{self.distance}B"
        elif self.move_type == MoveType.RIGHT:
            if self.distance == 1:
                return "\x1b[C"
            return f"\x1b[{self.distance}C"
        elif self.move_type == MoveType.LEFT:
            if self.distance == 1:
                return "\x1b[D"
            return f"\x1b[{self.distance}D"
        elif self.move_type == MoveType.HOME:
            return "\x1b[H"
        elif self.move_type == MoveType.CARRIAGE_RETURN:
            return "\r"
        elif self.move_type == MoveType.NEWLINE:
            return "\n" * self.distance if self.distance > 1 else "\n"
        elif self.move_type == MoveType.TAB:
            return "\t" * self.distance if self.distance > 1 else "\t"
        elif self.move_type == MoveType.BACKSPACE:
            return "\b" * self.distance if self.distance > 1 else "\b"
        return ""
    
    def byte_count(self) -> int:
        """Get byte count for this movement."""
        return len(self.to_sequence())


class CursorOptimizer:
    """
    Optimizes cursor movements to minimize bytes sent.
    
    Chooses the most efficient movement method:
    - Absolute positioning
    - Relative movements (up/down/left/right)
    - Special characters (CR, LF, tab, backspace)
    - Home position
    """
    
    def __init__(self, terminal_width: int = 80, terminal_height: int = 24):
        """
        Initialize cursor optimizer.
        
        Args:
            terminal_width: Terminal width in columns
            terminal_height: Terminal height in rows
        """
        self.width = terminal_width
        self.height = terminal_height
        self.current_row = 1
        self.current_col = 1
        
        # Statistics
        self.moves_optimized = 0
        self.bytes_saved = 0
        self.total_moves = 0
    
    def optimize_move(self, target_row: int, target_col: int) -> CursorMove:
        """
        Find optimal movement to target position.
        
        Args:
            target_row: Target row (1-based)
            target_col: Target column (1-based)
            
        Returns:
            Optimal cursor movement
        """
        self.total_moves += 1
        
        # Validate bounds
        target_row = max(1, min(target_row, self.height))
        target_col = max(1, min(target_col, self.width))
        
        # If already at position, no move needed
        if self.current_row == target_row and self.current_col == target_col:
            return CursorMove(MoveType.ABSOLUTE, row=target_row, col=target_col)
        
        # Calculate all possible movements
        candidates = []
        
        # Absolute positioning (always possible)
        absolute_move = CursorMove(MoveType.ABSOLUTE, row=target_row, col=target_col)
        candidates.append(absolute_move)
        
        # Home position (1,1)
        if target_row == 1 and target_col == 1:
            candidates.append(CursorMove(MoveType.HOME))
        
        # Relative movements
        row_diff = target_row - self.current_row
        col_diff = target_col - self.current_col
        
        # Vertical movement
        if row_diff != 0:
            if row_diff > 0:
                # Moving down
                if col_diff == 0:
                    # Pure down movement
                    candidates.append(CursorMove(MoveType.DOWN, distance=row_diff))
                elif self.current_col == 1 and target_col == 1:
                    # Down with newlines (stays at column 1)
                    candidates.append(CursorMove(MoveType.NEWLINE, distance=row_diff))
            else:
                # Moving up
                if col_diff == 0:
                    # Pure up movement
                    candidates.append(CursorMove(MoveType.UP, distance=-row_diff))
        
        # Horizontal movement
        if col_diff != 0:
            if row_diff == 0:
                # Same row
                if col_diff > 0:
                    # Moving right
                    candidates.append(CursorMove(MoveType.RIGHT, distance=col_diff))
                    
                    # Check if tabs would be efficient
                    if self.current_col % 8 != 0:
                        tabs_needed = self._calculate_tabs(self.current_col, target_col)
                        if tabs_needed > 0:
                            candidates.append(CursorMove(MoveType.TAB, distance=tabs_needed))
                else:
                    # Moving left
                    candidates.append(CursorMove(MoveType.LEFT, distance=-col_diff))
                    
                    # Check if backspace would work
                    if -col_diff < 8:
                        candidates.append(CursorMove(MoveType.BACKSPACE, distance=-col_diff))
            
            # Carriage return to column 1
            if target_col == 1 and row_diff == 0:
                candidates.append(CursorMove(MoveType.CARRIAGE_RETURN))
        
        # Combination movements (CR + down, etc.)
        if target_col == 1 and row_diff > 0:
            # CR + down
            combined = [
                CursorMove(MoveType.CARRIAGE_RETURN),
                CursorMove(MoveType.DOWN, distance=row_diff)
            ]
            # Create a pseudo-move for comparison
            combined_bytes = sum(m.byte_count() for m in combined)
            if combined_bytes < absolute_move.byte_count():
                # Use the first move, caller can detect pattern
                candidates.append(CursorMove(MoveType.CARRIAGE_RETURN))
        
        # Find the most efficient movement
        best_move = min(candidates, key=lambda m: m.byte_count())
        
        # Track statistics
        naive_bytes = absolute_move.byte_count()
        optimal_bytes = best_move.byte_count()
        if optimal_bytes < naive_bytes:
            self.moves_optimized += 1
            self.bytes_saved += naive_bytes - optimal_bytes
        
        # Update position
        self.current_row = target_row
        self.current_col = target_col
        
        return best_move
    
    def _calculate_tabs(self, from_col: int, to_col: int) -> int:
        """Calculate number of tabs needed."""
        # Tabs move to next multiple of 8
        tabs = 0
        current = from_col
        while current < to_col:
            next_tab = ((current - 1) // 8 + 1) * 8 + 1
            if next_tab <= to_col:
                tabs += 1
                current = next_tab
            else:
                break
        
        # Only use tabs if they get us close
        if tabs > 0 and to_col - current < 8:
            return tabs
        return 0
    
    def optimize_path(self, positions: List[Tuple[int, int]]) -> List[CursorMove]:
        """
        Optimize a sequence of cursor positions.
        
        Args:
            positions: List of (row, col) positions
            
        Returns:
            Optimized movement sequence
        """
        moves = []
        for row, col in positions:
            move = self.optimize_move(row, col)
            moves.append(move)
        return moves
    
    def reset_position(self, row: int = 1, col: int = 1):
        """Reset current cursor position."""
        self.current_row = row
        self.current_col = col
    
    def get_statistics(self) -> dict:
        """Get optimization statistics."""
        return {
            'total_moves': self.total_moves,
            'moves_optimized': self.moves_optimized,
            'bytes_saved': self.bytes_saved,
            'optimization_rate': self.moves_optimized / max(1, self.total_moves),
            'average_savings': self.bytes_saved / max(1, self.moves_optimized)
        }
    
    def reset_statistics(self):
        """Reset statistics."""
        self.moves_optimized = 0
        self.bytes_saved = 0
        self.total_moves = 0


class CursorTracker:
    """
    Tracks cursor position across output operations.
    
    Useful for maintaining cursor state when outputting
    text and escape sequences.
    """
    
    def __init__(self, width: int = 80, height: int = 24):
        """Initialize cursor tracker."""
        self.width = width
        self.height = height
        self.row = 1
        self.col = 1
    
    def write_text(self, text: str):
        """Update position after writing text."""
        for char in text:
            if char == '\n':
                self.row = min(self.row + 1, self.height)
                self.col = 1
            elif char == '\r':
                self.col = 1
            elif char == '\t':
                # Tab moves to next multiple of 8
                self.col = ((self.col - 1) // 8 + 1) * 8 + 1
                if self.col > self.width:
                    self.col = 1
                    self.row = min(self.row + 1, self.height)
            elif char == '\b':
                self.col = max(1, self.col - 1)
            elif ord(char) >= 32:  # Printable character
                self.col += 1
                if self.col > self.width:
                    self.col = 1
                    self.row = min(self.row + 1, self.height)
    
    def move_to(self, row: int, col: int):
        """Update position after cursor movement."""
        self.row = max(1, min(row, self.height))
        self.col = max(1, min(col, self.width))
    
    def get_position(self) -> Tuple[int, int]:
        """Get current cursor position."""
        return (self.row, self.col)