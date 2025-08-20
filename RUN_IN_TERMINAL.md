# Running the Phase 2 Demos in Codespaces

## ✅ The demos are now fixed!

The keyboard input issues have been resolved. The demos now properly detect when they're not in a real terminal and handle it gracefully.

## How to Run the Demos

### Option 1: VS Code Integrated Terminal (Recommended)
1. Open the integrated terminal in VS Code: **Ctrl + `** (backtick)
2. Run the demos:
   ```bash
   python examples/phase2_demo.py
   python examples/phase2_advanced_demo.py
   ```

### Option 2: Codespaces Web Terminal
1. In your browser, click on the "Terminal" tab
2. Run the demos there

### Option 3: Use the Working Demo
A special version that uses curses for better compatibility:
```bash
python demo_working.py
```

## What Was Fixed

1. **TTY Detection**: The input handlers now check if stdin is connected to a real terminal
2. **Non-blocking I/O**: Fixed blocking reads that would freeze the application
3. **Error Handling**: Graceful fallback when not in a terminal environment

## Display-Only Demos (Work Anywhere)

These demos don't need keyboard input and work even through Claude Code:
```bash
python demo_simple.py
python demo_tvision_io.py
python demo_enhanced_features.py
```

## Troubleshooting

If you still have issues:

1. **Make sure you're in a real terminal** - The demos won't work through Claude Code's command interface
2. **Try the curses-based demo**: `python demo_working.py`
3. **Check your terminal**: Run `python test_keyboard.py` to diagnose issues

## Controls for Phase 2 Demos

- **q** - Quit
- **c** - Cycle colors
- **Mouse** - Move cursor (if supported)
- **TAB** - Switch platforms (advanced demo)
- **d** - Toggle damage visualization (advanced demo)
- **b** - Benchmark mode (advanced demo)