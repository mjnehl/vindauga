# Backend Testing Guide

## Overview
Phase 2 implements three different terminal I/O backends. Your Mac Terminal auto-selects ANSI because it has the best capabilities, but all three backends should work.

## How to Test Each Backend

### 1. Manual Backend Selection
```bash
python3 demo_backend_selector.py
```
This interactive demo lets you choose which backend to test:
- Option 1: ANSI (uses escape sequences)
- Option 2: TermIO (Unix terminal I/O)
- Option 3: Curses (ncurses wrapper)
- Option 4: Auto-detect (will pick best available)

### 2. Test Color Support
```bash
python3 test_color_modes.py
```
This shows:
- Your terminal's claimed color support (TERM and COLORTERM variables)
- What the backend actually detects
- Visual test patterns for 16, 256, and 24-bit colors

### 3. Run All Backend Tests
```bash
python3 test_all_backends.py
```
This automatically tests all three backends and reports which ones work.

## Expected Results

### On macOS Terminal

#### ANSI Backend ✅
- **Status**: Should work perfectly
- **Colors**: 16,777,216 (24-bit) if Terminal.app or iTerm2
- **Why selected**: Best color support, most features
- **Test**: Colors, mouse, keyboard all work

#### TermIO Backend ⚠️
- **Status**: May fail initialization on macOS
- **Reason**: macOS doesn't fully support Linux-style termios raw mode
- **Note**: This is expected - TermIO is optimized for Linux

#### Curses Backend ⚠️
- **Status**: May fail if ncurses not properly installed
- **Fix**: `brew install ncurses` (but may still have issues)
- **Note**: Curses is a fallback option

### Why ANSI is Auto-Selected on Mac

The PlatformDetector scores each backend based on capabilities:

1. **ANSI scores highest** on modern terminals because:
   - Supports 24-bit color (detected via COLORTERM=truecolor)
   - Works on all Unix-like systems
   - No dependencies required
   - Most efficient for modern terminals

2. **TermIO scores lower** because:
   - Limited to what termios provides
   - More complex setup
   - Platform-specific quirks

3. **Curses scores lowest** because:
   - Limited to curses capabilities
   - Adds dependency
   - Less efficient than direct escape sequences

## How to Verify Color Support

### Check Your Terminal's Capabilities
```bash
echo "TERM=$TERM"
echo "COLORTERM=$COLORTERM"
```

Expected on macOS:
- `TERM=xterm-256color` (256 colors minimum)
- `COLORTERM=truecolor` (24-bit color support)

### Visual Test
Run `python3 test_color_modes.py` and you should see:
- **16 colors**: Basic colors (always work)
- **256 colors**: Color cube + grayscale (if TERM includes "256color")
- **24-bit colors**: Smooth gradients (if COLORTERM=truecolor)

### What the Numbers Mean
- **16 colors**: Basic terminal colors (3-bit + bright)
- **256 colors**: 216 color cube + 24 grayscales + 16 basic
- **16,777,216 colors**: Full 24-bit RGB (8 bits per channel)

## Forcing a Specific Backend

If you want to force a backend for testing:

```python
from vindauga.io import PlatformIO, PlatformType

# Force ANSI
display, input_handler = PlatformIO.create(PlatformType.ANSI)

# Force TermIO (may fail on Mac)
display, input_handler = PlatformIO.create(PlatformType.TERMIO)

# Force Curses (needs ncurses)
display, input_handler = PlatformIO.create(PlatformType.CURSES)
```

## Troubleshooting

### TermIO Fails on Mac
**Expected**: macOS has different termios behavior than Linux.
**Solution**: Use ANSI backend (auto-selected anyway).

### Curses Fails
**Cause**: ncurses not installed or incompatible.
**Solution**: 
```bash
brew install ncurses
# May need to set LDFLAGS/CPPFLAGS for Python to find it
```
But ANSI works better anyway on modern terminals.

### Colors Look Wrong
**Check**:
1. Terminal preferences - ensure 256 or millions of colors selected
2. Run `echo $COLORTERM` - should show "truecolor" for best results
3. Try different terminal app (iTerm2, Terminal.app, etc.)

### Mouse Doesn't Work
**Check**:
1. Terminal must support mouse reporting
2. Some terminals need mouse mode enabled in preferences
3. SSH connections may not forward mouse events

## Summary

- **ANSI backend**: Primary backend for modern terminals, auto-selected on Mac
- **TermIO backend**: Linux-optimized, may not work on Mac
- **Curses backend**: Compatibility fallback, limited features

The fact that ANSI is auto-selected and works with 24-bit color on your Mac is the **expected and optimal behavior**. The other backends are alternatives for different scenarios (Linux servers, legacy systems, etc.).