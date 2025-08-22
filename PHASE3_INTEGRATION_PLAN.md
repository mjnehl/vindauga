# Phase 3 Integration Plan - What Will Be Modified

## Overview
Phase 3 will create a **facade/adapter layer** to connect the new I/O system with existing Vindauga code. The goal is to **minimize changes** to existing application code while routing I/O through our new system.

## Proposed Modifications Outside io/

### 1. Screen Class (vindauga/types/screen.py) - MAIN INTEGRATION POINT

**Current State:**
- Directly uses curses for terminal I/O
- Hardcoded to curses initialization
- Fixed buffer width (1024)
- Direct terminal manipulation

**Proposed Changes:**
```python
class Screen:
    def __init__(self, use_new_io=True, platform=None):
        if use_new_io:
            # Use new I/O system
            from vindauga.io import PlatformIO
            self.display, self.input_handler = PlatformIO.create(platform)
            self.display.initialize()
            self.input_handler.initialize()
        else:
            # Fall back to old curses implementation
            self.stdscr = self.initialiseScreen()
```

**Methods to Modify:**
- `initialiseScreen()` - Route to new display backend
- `getChar()` - Use new input handler
- `putChar()` - Use new display buffer
- `drawView()` - Use new DisplayBuffer instead of curses
- `flushScreen()` - Use new display.flush_buffer()
- `clearScreen()` - Use new display.clear_screen()
- `setCursor()` - Use new display.set_cursor_position()
- `resize()` - Use new display.get_size()

### 2. DrawBuffer Class (vindauga/types/draw_buffer.py)

**Current State:**
- Fixed 1024 width array
- Direct character/attribute manipulation

**Proposed Changes:**
```python
class DrawBuffer:
    def __init__(self, use_new_io=True):
        if use_new_io:
            # Use dynamic DisplayBuffer from new I/O
            from vindauga.io import DisplayBuffer
            self._buffer = DisplayBuffer(width, height)
        else:
            # Use old fixed buffer
            self._data = BufferArray()
```

**Methods to Modify:**
- `moveChar()` - Delegate to DisplayBuffer.put_char()
- `moveBuf()` - Delegate to DisplayBuffer.put_text()
- `putAttribute()` - Use new attribute system
- `putChar()` - Delegate to DisplayBuffer.put_char()

### 3. Event Handling (vindauga/events/)

**Files to Modify:**
- `vindauga/events/event.py` - Add translation from new event types
- `vindauga/events/event_queue.py` - Integrate with new input handler

**Proposed Event Adapter:**
```python
class EventAdapter:
    @staticmethod
    def translate_new_to_old(new_event):
        """Convert new I/O event to old Vindauga event."""
        if hasattr(new_event, 'key'):
            # Keyboard event
            return Event(evKeyDown, new_event.key)
        elif hasattr(new_event, 'x'):
            # Mouse event
            return Event(evMouseMove, ...)
```

### 4. Application Base (vindauga/app.py)

**Minor Changes:**
- Add parameter to select I/O backend
- Pass through to Screen initialization

```python
class Application:
    def __init__(self, use_new_io=True, io_platform=None):
        Screen.init(use_new_io=use_new_io, platform=io_platform)
```

## Files That Will NOT Be Modified

These files will continue to work unchanged:
- All widget classes (views/*.py)
- All dialog classes (dialogs/*.py)
- All menu classes (menus/*.py)
- All utility classes (utilities/*.py)
- Constants and enums (constants/*.py)

## Integration Strategy

### Step 1: Create Adapter Layer (No modifications yet)
```
vindauga/io/adapters/
├── screen_adapter.py     # Adapts Screen to use new I/O
├── buffer_adapter.py     # Adapts DrawBuffer to use DisplayBuffer
└── event_adapter.py      # Translates events
```

### Step 2: Add Feature Flags
- Add `use_new_io` parameter to Screen.__init__()
- Default to False initially (no breaking changes)
- Allow opt-in testing

### Step 3: Gradual Migration
1. Test with simple apps first
2. Fix compatibility issues
3. Switch default to True when stable
4. Eventually remove old code

## Example Usage After Integration

```python
# Old way (still works)
from vindauga.app import Application
app = Application()  # Uses curses

# New way (opt-in)
from vindauga.app import Application
from vindauga.io import PlatformType

# Use new I/O with auto-detection
app = Application(use_new_io=True)

# Use specific backend
app = Application(use_new_io=True, io_platform=PlatformType.ANSI)
```

## Summary of Changes

### Files to Modify (4-5 files):
1. `vindauga/types/screen.py` - Main integration point
2. `vindauga/types/draw_buffer.py` - Buffer adapter
3. `vindauga/events/event.py` - Event translation
4. `vindauga/events/event_queue.py` - Event integration
5. `vindauga/app.py` - Add initialization parameters

### New Files to Create (3-4 files):
1. `vindauga/io/adapters/screen_adapter.py`
2. `vindauga/io/adapters/buffer_adapter.py`
3. `vindauga/io/adapters/event_adapter.py`

### Lines of Code to Change:
- Estimated 200-300 lines modified
- Mostly adding if/else branches for backward compatibility
- No breaking changes to existing API

## Questions for You

1. **Do you want backward compatibility?** 
   - Keep old curses code as fallback?
   - Or fully replace with new I/O?

2. **Feature flag approach OK?**
   - Start with opt-in via parameter?
   - Or switch everything at once?

3. **Any specific widgets/apps to test first?**
   - Simple dialogs?
   - File viewers?
   - Menus?

4. **Performance requirements?**
   - Any specific benchmarks to meet?
   - Areas of concern?

Let me know your preferences before I start modifying code outside io/!