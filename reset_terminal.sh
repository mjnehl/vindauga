#!/bin/bash
# Reset terminal after TVision I/O tests

echo "Resetting terminal..."

# Clear screen and reset cursor
printf '\033c'

# Exit alternate screen buffer
printf '\033[?1049l'

# Show cursor
printf '\033[?25h'

# Reset all text attributes
printf '\033[0m'

# Disable mouse modes
printf '\033[?1000l'  # X11 mouse
printf '\033[?1006l'  # SGR mouse
printf '\033[?1002l'  # Cell motion tracking
printf '\033[?1003l'  # All motion tracking

# Reset terminal modes
stty sane 2>/dev/null

# Clear screen again
clear

echo "Terminal reset complete!"
echo ""
echo "If terminal is still not working correctly, try:"
echo "  - Close and reopen terminal tab/window"
echo "  - Run: reset"
echo "  - Run: stty sane"