#!/usr/bin/env python3
"""
Apply fixes to the input handlers to make them work in Codespaces.
"""

import os
import shutil

def fix_ansi_input():
    """Fix the ANSI input handler."""
    original = "/workspaces/vindauga/vindauga/io/input/ansi.py"
    backup = "/workspaces/vindauga/vindauga/io/input/ansi.py.bak"
    fixed = "/workspaces/vindauga/vindauga/io/input/ansi_fixed.py"
    
    if os.path.exists(original):
        # Backup original
        shutil.copy2(original, backup)
        print(f"Backed up {original} to {backup}")
        
        # Copy fixed version
        shutil.copy2(fixed, original)
        print(f"Applied fix to {original}")
        return True
    return False

def fix_termio_input():
    """Fix the TermIO input handler - add better error handling."""
    filepath = "/workspaces/vindauga/vindauga/io/input/termio.py"
    
    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Add import for fcntl if not present
    if 'import fcntl' not in content:
        content = content.replace('import os', 'import os\nimport fcntl')
    
    # Fix the initialize method to check for TTY
    fixed_init = '''    def initialize(self) -> bool:
        """
        Initialize the TermIO input subsystem.
        
        Returns:
            True if initialization was successful.
        """
        try:
            # Check if stdin is a TTY
            if not sys.stdin.isatty():
                return False
            
            self.stdin_fd = sys.stdin.fileno()
            
            # Save terminal state
            try:
                self._original_termios = termios.tcgetattr(self.stdin_fd)
            except:
                return False
            
            # Set to raw mode with non-blocking
            new_termios = termios.tcgetattr(self.stdin_fd)
            new_termios[3] = new_termios[3] & ~(termios.ECHO | termios.ICANON)
            new_termios[6][termios.VMIN] = 0
            new_termios[6][termios.VTIME] = 0
            termios.tcsetattr(self.stdin_fd, termios.TCSADRAIN, new_termios)
            
            # Set non-blocking
            flags = fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)'''
    
    # Check if we need to fix it
    if 'if not sys.stdin.isatty():' not in content:
        print(f"Fixing {filepath}")
        
        # Backup
        shutil.copy2(filepath, filepath + '.bak')
        
        # Simple patch - just add TTY check at beginning of initialize
        content = content.replace(
            '        """\n        try:',
            '        """\n        try:\n            # Check if stdin is a TTY\n            if not sys.stdin.isatty():\n                return False\n'
        )
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"Fixed {filepath}")
        return True
    
    return False

def main():
    print("Applying input handler fixes for Codespaces compatibility...")
    print("="*60)
    
    # Fix ANSI input
    if fix_ansi_input():
        print("✓ Fixed ANSI input handler")
    else:
        print("✗ Could not fix ANSI input handler")
    
    # Fix TermIO input
    if fix_termio_input():
        print("✓ Fixed TermIO input handler")
    else:
        print("✗ TermIO input handler already fixed or not found")
    
    print("="*60)
    print("\nFixes applied! Now try running:")
    print("  python examples/phase2_demo.py")
    print("\nNote: You must run this in a real terminal (VS Code terminal or web terminal)")
    print("      It won't work through Claude Code's command interface.")

if __name__ == "__main__":
    main()