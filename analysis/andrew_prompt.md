# TVision I/O Subsystem Migration Analysis for Vindauga

## Executive Summary

This analysis examines the feasibility and approach for extracting TVision's I/O subsystem (screen, keyboard, mouse) and converting it to Python to replace Vindauga's current curses-only implementation in `types/screen.py`. The migration would provide Vindauga with multiple platform backends (ANSI, TermIO, Curses) and improved performance through TVision's sophisticated buffer management.

## Current State Analysis

### Vindauga's I/O Architecture
- **Single Implementation**: Curses-only in `types/screen.py` (600+ lines)
- **Monolithic Design**: All I/O handling in one class
- **Limited Platform Support**: Depends on curses availability
- **Basic Buffer Management**: Simple `DrawBuffer` with fixed 1024 width
- **Event Handling**: Direct curses event translation

### TVision's I/O Architecture
- **Multi-Platform**: ANSI, TermIO, Ncurses, Win32 Console
- **Layered Abstraction**: Platform → Adapter → Display/Input
- **Sophisticated Buffering**: Double-buffering with damage tracking
- **Advanced Features**: Unicode, wide characters, 24-bit color

## TVision I/O Subsystem Components

### 1. Display Buffer System

#### TDisplayBuffer Architecture
```
TScreenCell (C++):
- char[15] text     // UTF-8 encoded character
- uint8_t extraWidth // For wide characters
- TColorAttr attr   // Color and attributes
- uint8_t flags     // Cell state flags

TDisplayBuffer:
- TScreenCell* buffer
- damage regions per row
- FPS limiting (60 FPS default)
- atomic flush operations
```

#### Python Equivalent Design
```python
class ScreenCell:
    """Represents a single screen cell with UTF-8 text and attributes"""
    __slots__ = ['text', 'width', 'attr', 'flags']
    
class DisplayBuffer:
    """Double-buffered display with damage tracking"""
    - Primary and shadow buffers
    - Row-based damage regions
    - Atomic buffer swapping
    - FPS limiting capability
```

### 2. Platform Abstraction Layer

#### TVision's Three-Layer Model
```
Application Layer
    ↓
Platform Interface (abstract)
    ↓
Platform Adapter (polymorphic)
    ↓
Platform Implementation (ANSI/TermIO/Curses/Win32)
```

#### Python Module Structure
```
vindauga/io/
├── __init__.py           # Public API
├── platform.py           # Platform detection and selection
├── display/
│   ├── __init__.py
│   ├── base.py          # Abstract display interface
│   ├── buffer.py        # TDisplayBuffer equivalent
│   ├── ansi.py          # ANSI terminal implementation
│   ├── termio.py        # Unix termios implementation
│   ├── curses.py        # Ncurses implementation
│   └── win32.py         # Windows console (future)
├── input/
│   ├── __init__.py
│   ├── base.py          # Abstract input interface
│   ├── keyboard.py      # Keyboard event processing
│   ├── mouse.py         # Mouse event processing
│   ├── ansi_parser.py   # ANSI escape sequence parsing
│   └── event_queue.py   # Event multiplexing
└── palette/
    ├── __init__.py
    ├── base.py          # TPalette interface
    └── color_mapper.py  # Color translation
```

### 3. Key Classes to Port

#### Display Classes
| TVision Class | Purpose | Python Equivalent |
|--------------|---------|------------------|
| TDisplay | Abstract display interface | `Display` base class |
| TDisplayBuffer | Screen buffer management | `DisplayBuffer` class |
| TScreenCell | Individual cell storage | `ScreenCell` dataclass |
| TColorAttr | Color attributes | `ColorAttribute` class |
| ConsoleStrategy | Platform selection | `PlatformStrategy` class |

#### Input Classes
| TVision Class | Purpose | Python Equivalent |
|--------------|---------|------------------|
| InputStrategy | Abstract input interface | `InputHandler` base class |
| NcursesInput | Ncurses input handling | `CursesInput` class |
| LinuxConsoleInput | Linux console input | `LinuxInput` class |
| Win32Input | Windows console input | `Win32Input` class |
| FarInputGetter | Input event retrieval | `EventSource` class |

### 4. Integration Points with Vindauga

#### Minimal Changes Required
```python
# Current Vindauga usage:
from vindauga.types.screen import Screen
Screen.init()
screen.getEvent()
screen.putText(x, y, text, attr)

# After migration (backward compatible):
from vindauga.types.screen import Screen  # Facade over new I/O
Screen.init(platform='auto')  # Auto-detect or specify
# Same API continues to work
```

#### Internal Rewiring
```python
class Screen:  # Existing class becomes facade
    def __init__(self):
        # Delegate to new I/O subsystem
        from vindauga.io import PlatformIO
        self._io = PlatformIO.create()
        self._display = self._io.display
        self._input = self._io.input
    
    def getEvent(self):
        return self._input.getEvent()
    
    def putText(self, x, y, text, attr):
        self._display.putText(x, y, text, attr)
```

### 5. Platform-Specific Considerations

#### ANSI Terminal
- **Escape Sequences**: CSI, OSC, DCS parsing
- **Mouse Protocols**: X10, X11, SGR, URXVT
- **Color Support**: 16, 256, 24-bit RGB
- **Terminal Capabilities**: terminfo/termcap queries

#### TermIO (Unix/Linux)
- **Raw Mode**: `termios` configuration
- **Signal Handling**: SIGWINCH, SIGTSTP, SIGCONT
- **Input Multiplexing**: `select()` or `poll()`
- **TTY Control**: IOCTL operations

#### Curses
- **Compatibility Layer**: Use existing curses as fallback
- **Window Management**: stdscr handling
- **Color Pairs**: Limited to 256 pairs
- **Key Mapping**: curses KEY_* constants

### 6. Buffer Transfer Mechanism

#### TVision's Approach
```cpp
// Damage tracking
void TDisplayBuffer::setDirty(int x, int y, int len) {
    damage[y].expand(x, x + len);
}

// Efficient flush
void TDisplayBuffer::flush() {
    for (row with damage) {
        platform->writeRow(row, damage_start, damage_end);
    }
    clearDamage();
}
```

#### Python Implementation Strategy
```python
class DisplayBuffer:
    def set_dirty(self, x: int, y: int, length: int):
        """Mark region as needing update"""
        self.damage[y].expand(x, x + length)
    
    def flush(self):
        """Efficiently update only changed regions"""
        for y, region in enumerate(self.damage):
            if region.is_dirty:
                self._flush_row(y, region.start, region.end)
        self.clear_damage()
```

### 7. Performance Optimizations

#### Critical Optimizations from TVision
1. **Damage Tracking**: Only update changed screen regions
2. **Buffer Comparison**: Skip identical cells during flush
3. **Batch Operations**: Group escape sequences
4. **FPS Limiting**: Prevent excessive redraws
5. **Wide Character Caching**: Cache wcwidth() results

#### Python-Specific Optimizations
1. **Use `__slots__`**: Reduce memory overhead
2. **Numpy Arrays**: Consider for buffer storage
3. **Cython Critical Paths**: Platform write operations
4. **Lazy Imports**: Platform-specific modules
5. **Thread-Local Storage**: Event processing

### 8. Migration Strategy

#### Phase 1: Core Infrastructure (Week 1-2)
1. Create `vindauga/io/` module structure
2. Implement `DisplayBuffer` with damage tracking
3. Port `ScreenCell` and `ColorAttribute`
4. Create abstract `Display` and `InputHandler` interfaces
5. Implement platform detection logic

#### Phase 2: Platform Implementations (Week 3-4)
1. ANSI terminal display and input
2. TermIO Unix/Linux support
3. Curses compatibility layer
4. Event multiplexing and queue
5. Basic mouse and keyboard handling

#### Phase 3: Integration (Week 5)
1. Create `Screen` facade for backward compatibility
2. Update `DrawBuffer` to use new `DisplayBuffer`
3. Migrate event handling to new system
4. Test with existing Vindauga applications
5. Performance profiling and optimization

#### Phase 4: Advanced Features (Week 6+)
1. Unicode and wide character support
2. 24-bit color implementation
3. Advanced mouse protocols
4. Platform-specific optimizations
5. Documentation and examples

### 9. Risk Analysis

#### Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance regression | High | Profile continuously, optimize hot paths |
| Platform incompatibility | Medium | Maintain curses fallback |
| API breaking changes | Low | Use facade pattern for compatibility |
| Unicode complexity | Medium | Start with ASCII, add Unicode later |
| Memory overhead | Low | Use __slots__, profile memory usage |

#### Implementation Challenges
1. **Escape Sequence Parsing**: Complex state machines needed
2. **Signal Handling**: Platform-specific behavior
3. **Thread Safety**: Python GIL considerations
4. **Testing Coverage**: Multiple platform variants
5. **Documentation**: Complex architecture to explain

### 10. Benefits of Migration

#### Immediate Benefits
- **Multi-platform support**: Not limited to curses availability
- **Better performance**: Damage tracking reduces screen updates
- **Improved compatibility**: Direct ANSI support for modern terminals
- **Clean architecture**: Separation of concerns

#### Future Benefits
- **Easier maintenance**: Modular design
- **Platform extensions**: Easy to add new platforms
- **Advanced features**: 24-bit color, better Unicode
- **Performance path**: Critical sections can be optimized

## Conclusion

Migrating Vindauga to use TVision's I/O architecture is technically feasible and would provide significant benefits. The key to success is:

1. **Maintaining backward compatibility** through the facade pattern
2. **Incremental migration** starting with core abstractions
3. **Platform-specific optimizations** for performance
4. **Comprehensive testing** across platforms
5. **Documentation** of the new architecture

The estimated effort is 5-6 weeks for a complete implementation with all platforms, or 2-3 weeks for a minimal viable implementation with ANSI and Curses support.

### Recommended Approach

1. Start with `DisplayBuffer` and damage tracking (biggest performance win)
2. Implement ANSI terminal support (most modern terminals)
3. Keep curses as fallback (ensure compatibility)
4. Add platform detection (automatic selection)
5. Optimize hot paths (profiling-driven)

This migration would transform Vindauga from a curses-dependent TUI framework to a truly cross-platform solution with professional-grade performance characteristics.