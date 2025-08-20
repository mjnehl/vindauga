#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vindauga Demo - Phase 1 Enhanced Edition

This is an enhanced version of the original vindauga_demo.py that showcases
the new TVision I/O subsystem Phase 1 capabilities. It demonstrates:
- Unicode and wide character support
- Enhanced performance with damage tracking
- International text support
- Modern terminal features

Based on the original vindauga_demo.py but enhanced with Phase 1 features.
"""

import logging
import os
import sys
import time
from typing import Optional

# TVision I/O Phase 1 imports
from vindauga.io import ScreenCell, DisplayBuffer
from vindauga.io.platform import PlatformDetector, PlatformType

# Original Vindauga imports
try:
    from demo.app_commands import AppCommands
    from demo.ascii_table import AsciiChart
    from demo.help_contexts import HelpContexts
    
    from vindauga.constants.buttons import bfDefault, bfNormal
    from vindauga.constants.command_codes import cmMenu, cmQuit, cmClose, hcNoContext, cmNext, cmZoom, cmHelp, cmResize, \
        cmCancel, cmOK, cmCascade, cmTile
    from vindauga.constants.event_codes import evCommand
    from vindauga.constants.keys import kbF10, kbAltX, kbF6, kbF3, kbNoKey, kbF11, kbF5, kbCtrlF5, kbCtrlW
    from vindauga.constants.option_flags import ofCentered, ofTileable
    from vindauga.dialogs.calculator_dialog import CalculatorDialog
    from vindauga.dialogs.calendar import CalendarWindow
    from vindauga.dialogs.change_dir_dialog import ChangeDirDialog, cmChangeDir
    from vindauga.dialogs.color_dialog import ColorDialog
    from vindauga.dialogs.file_dialog import FileDialog, fdOpenButton
    from vindauga.dialogs.mouse_dialog import MouseDialog
    from vindauga.events.event import Event
    from vindauga.events.event_queue import EventQueue
    from vindauga.gadgets.puzzle import PuzzleWindow
    from vindauga.menus.menu_bar import MenuBar
    from vindauga.menus.menu_item import MenuItem
    from vindauga.menus.sub_menu import SubMenu
    from vindauga.misc.message import message
    from vindauga.terminal.terminal_view import TerminalView
    from vindauga.terminal.terminal_window import TerminalWindow
    from vindauga.types.color_group import ColorGroup
    from vindauga.types.color_item import ColorItem
    from vindauga.types.rect import Rect
    from vindauga.types.screen import Screen
    from vindauga.types.status_def import StatusDef
    from vindauga.types.status_item import StatusItem
    from vindauga.types.view import View
    from vindauga.widgets.application import Application
    from vindauga.widgets.button import Button
    from vindauga.widgets.check_boxes import CheckBoxes
    from vindauga.widgets.clock import ClockView
    from vindauga.widgets.dialog import Dialog
    from vindauga.widgets.file_window import FileWindow
    from vindauga.widgets.input_line import InputLine
    from vindauga.widgets.label import Label
    from vindauga.widgets.radio_buttons import RadioButtons
    from vindauga.widgets.static_text import StaticText
    from vindauga.widgets.status_line import StatusLine
    
    VINDAUGA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some Vindauga modules not available: {e}")
    VINDAUGA_AVAILABLE = False

logger = logging.getLogger('vindauga.vindauga_demo_phase1')

# Demo data
checkBoxData = 0
radioButtonData = 0
inputLineData = ''
demoDialogData = list(reversed([checkBoxData, radioButtonData, inputLineData]))


def setupLogging():
    """Set up logging for the demo."""
    logger = logging.getLogger('vindauga')
    logger.propagate = False
    format = '%(name)s\t %(message)s'
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(open('vindauga_phase1.log', 'wt'))
    handler.setFormatter(logging.Formatter(format))
    logger.addHandler(handler)


class Phase1Buffer:
    """
    Enhanced buffer using TVision I/O Phase 1 for demonstration.
    
    This shows how the new I/O system can be integrated into existing
    Vindauga components for better Unicode and performance support.
    """
    
    def __init__(self, width: int = 80, height: int = 25):
        """Initialize the Phase 1 enhanced buffer."""
        self.buffer = DisplayBuffer(width, height)
        self.detector = PlatformDetector()
        self._demo_mode = True
        
        # Get platform info for display
        try:
            self.platform_info = self.detector.get_platform_info()
            available_platforms = self.detector.list_available_platforms()
            self.best_platform = self.detector.detect_best_platform() if available_platforms else None
        except Exception:
            self.platform_info = {'system': 'Unknown', 'platforms': {}}
            self.best_platform = None
    
    def put_enhanced_text(self, x: int, y: int, text: str, attr: int = 0x07) -> None:
        """Put text with enhanced Unicode support."""
        self.buffer.put_text(x, y, text, attr)
    
    def create_unicode_frame(self, x: int, y: int, width: int, height: int, 
                           title: str = "", attr: int = 0x1F) -> None:
        """Create a window frame with Unicode box drawing characters."""
        # Box drawing characters for better visual appeal
        top_left = '┌'
        top_right = '┐' 
        bottom_left = '└'
        bottom_right = '┘'
        horizontal = '─'
        vertical = '│'
        
        # Draw frame
        self.buffer.put_char(x, y, top_left, attr)
        self.buffer.put_char(x + width - 1, y, top_right, attr)
        self.buffer.put_char(x, y + height - 1, bottom_left, attr)
        self.buffer.put_char(x + width - 1, y + height - 1, bottom_right, attr)
        
        # Top and bottom borders
        for i in range(1, width - 1):
            self.buffer.put_char(x + i, y, horizontal, attr)
            self.buffer.put_char(x + i, y + height - 1, horizontal, attr)
        
        # Side borders
        for i in range(1, height - 1):
            self.buffer.put_char(x, y + i, vertical, attr)
            self.buffer.put_char(x + width - 1, y + i, vertical, attr)
        
        # Title
        if title:
            title_text = f" {title} "
            title_x = x + (width - len(title_text)) // 2
            if title_x > x and title_x + len(title_text) < x + width:
                self.buffer.put_text(title_x, y, title_text, attr)
    
    def show_platform_info(self, x: int, y: int) -> None:
        """Show platform detection information."""
        self.put_enhanced_text(x, y, "🔧 Platform Detection:", 0x0E)
        
        system = self.platform_info.get('system', 'Unknown')
        self.put_enhanced_text(x, y + 1, f"System: {system}", 0x07)
        
        if self.best_platform:
            self.put_enhanced_text(x, y + 2, f"Best: {self.best_platform}", 0x0F)
        else:
            self.put_enhanced_text(x, y + 2, "Platform: Limited", 0x08)
        
        # Show platform capabilities
        platforms = self.platform_info.get('platforms', {})
        row = y + 3
        for name, caps in platforms.items():
            if caps.get('available', False):
                score = caps.get('score', 0)
                status = f"✓ {name.upper()}: {score}"
                self.put_enhanced_text(x, row, status, 0x0A)
                row += 1
    
    def demo_unicode_features(self, x: int, y: int) -> None:
        """Demonstrate Unicode and international text features."""
        self.put_enhanced_text(x, y, "🌍 Unicode Features:", 0x0E)
        
        examples = [
            ("English", "Hello, World!", 0x07),
            ("Chinese", "你好，世界！", 0x0F),
            ("Japanese", "こんにちは", 0x0D),
            ("Arabic", "مرحبا", 0x0C),
            ("Emoji", "🚀 ⭐ 🎉 🌈", 0x0B),
            ("Math", "∑ ∞ ≠ ≤ ≥ π", 0x09),
        ]
        
        for i, (name, text, attr) in enumerate(examples):
            row = y + 1 + i
            self.put_enhanced_text(x, row, f"{name:8}: {text}", attr)
    
    def show_performance_stats(self, x: int, y: int) -> None:
        """Show performance statistics."""
        stats = self.buffer.get_stats()
        
        self.put_enhanced_text(x, y, "⚡ Performance:", 0x0E)
        self.put_enhanced_text(x, y + 1, f"Buffer: {stats['width']}×{stats['height']}", 0x07)
        self.put_enhanced_text(x, y + 2, f"Dirty: {stats['dirty_cells']}/{stats['total_cells']}", 0x07)
        self.put_enhanced_text(x, y + 3, f"Damage: {stats['damage_ratio']:.1%}", 0x07)
        self.put_enhanced_text(x, y + 4, f"FPS: {stats['fps_limit']}", 0x07)
    
    def get_buffer_data(self) -> DisplayBuffer:
        """Get the underlying DisplayBuffer for integration."""
        return self.buffer


if VINDAUGA_AVAILABLE:
    class VindaugaDemoPhase1(Application):
        """
        Enhanced Vindauga Demo Application with Phase 1 I/O improvements.
        
        This demonstrates how existing Vindauga applications can be enhanced
        with the new TVision I/O subsystem for better Unicode support and performance.
        """
        
        def __init__(self):
            super().__init__()
            self.helpInUse = False
            self.phase1_buffer = Phase1Buffer()
            
            # Create enhanced clock with Unicode
            r = self.getExtent()
            r.topLeft.x = r.bottomRight.x - 9
            r.topLeft.y = r.bottomRight.y - 1
            self.clock = ClockView(r)
            self.insert(self.clock)
            
            # Process command line files
            for fileSpec in sys.argv[1:]:
                if os.path.isdir(fileSpec):
                    fileSpec = os.path.join(fileSpec, '*')
                
                if '*' in fileSpec or '?' in fileSpec:
                    self.openFile(fileSpec)
                else:
                    w = self.validView(FileWindow(fileSpec))
                    if w:
                        self.desktop.insert(w)
        
        @staticmethod
        def isTileable(view: View, *_args) -> bool:
            return view.options & ofTileable != 0
        
        @staticmethod
        def closeView(view: View, params):
            message(view, evCommand, cmClose, params)
        
        def initStatusLine(self, bounds: Rect) -> StatusLine:
            bounds.topLeft.y = bounds.bottomRight.y - 1
            
            return StatusLine(bounds,
                              StatusDef(0, 50) +
                              StatusItem('~F11~ Help', kbF11, cmHelp) +
                              StatusItem('~Alt+X~ Exit', kbAltX, cmQuit) +
                              StatusItem("", kbCtrlW, cmClose) +
                              StatusItem("", kbF10, cmMenu) +
                              StatusItem("", kbF5, cmZoom) +
                              StatusItem("", kbCtrlF5, cmResize) +
                              StatusDef(50, 0xFFFF) +
                              StatusItem('Phase 1 🚀', kbF11, cmHelp))
        
        def initMenuBar(self, bounds: Rect) -> MenuBar:
            bounds.bottomRight.y = bounds.topLeft.y + 1
            
            # Enhanced menu with Unicode indicators
            subMenu1 = (SubMenu('~≡~', 0, hcNoContext) +
                        MenuItem('~A~bout Phase 1...', AppCommands.cmAboutCmd, kbNoKey, HelpContexts.hcSAbout) +
                        MenuItem.newLine() +
                        MenuItem('🧩 ~P~uzzle', AppCommands.cmPuzzleCmd, kbNoKey, HelpContexts.hcSPuzzle) +
                        MenuItem('📅 Ca~l~endar', AppCommands.cmCalendarCmd, kbNoKey, HelpContexts.hcSCalendar) +
                        MenuItem('📊 Ascii ~T~able', AppCommands.cmAsciiCmd, kbNoKey, HelpContexts.hcSAsciiTable) +
                        MenuItem('🧮 ~C~alculator', AppCommands.cmCalcCmd, kbNoKey, HelpContexts.hcCalculator) +
                        MenuItem.newLine() +
                        MenuItem('🌍 ~U~nicode Demo', AppCommands.cmAboutCmd + 100, kbNoKey, hcNoContext))
            
            subMenu2 = (SubMenu('~F~ile', 0, HelpContexts.hcFile) +
                        MenuItem('~O~pen', AppCommands.cmOpenCmd, kbF3, HelpContexts.hcFOpen, 'F3') +
                        MenuItem('~C~hange Dir...', AppCommands.cmChDirCmd, kbNoKey, HelpContexts.hcFChangeDir) +
                        MenuItem.newLine() +
                        MenuItem('~D~ialog', AppCommands.cmDialogCmd, kbNoKey, hcNoContext) +
                        MenuItem('🖥️ ~S~hell', AppCommands.cmShellCmd, kbNoKey, HelpContexts.hcFDosShell) +
                        MenuItem.newLine() +
                        MenuItem('E~x~it', cmQuit, kbAltX, hcNoContext, 'Alt+X'))
            
            subMenu3 = (SubMenu('~W~indows', 0, HelpContexts.hcWindows) +
                        MenuItem('~R~esize/move', cmResize, kbCtrlF5, HelpContexts.hcWSizeMove, 'Ctrl+F5') +
                        MenuItem('~Z~oom', cmZoom, kbF5, HelpContexts.hcWZoom, 'F5') +
                        MenuItem('~N~ext', cmNext, kbF6, HelpContexts.hcWNext, 'F6') +
                        MenuItem('~C~lose', cmClose, kbCtrlW, HelpContexts.hcWClose, 'Ctrl+W') +
                        MenuItem('~T~ile', cmTile, kbNoKey, HelpContexts.hcWTile) +
                        MenuItem('C~a~scade', cmCascade, kbNoKey, HelpContexts.hcWCascade))
            
            subMenu4 = (SubMenu('~O~ptions', 0, HelpContexts.hcOptions) +
                        MenuItem('🖱️ ~M~ouse...', AppCommands.cmMouseCmd, kbNoKey, HelpContexts.hcOMouse) +
                        MenuItem('🎨 ~C~olors...', AppCommands.cmColorCmd, kbNoKey, HelpContexts.hcOColors) +
                        MenuItem.newLine() +
                        MenuItem('⚡ ~P~erformance Info', AppCommands.cmAboutCmd + 101, kbNoKey, hcNoContext))
            
            subMenu5 = (SubMenu('~R~esolution', 0, hcNoContext) +
                        MenuItem('~1~ 80x25', AppCommands.cmTest80x25, kbNoKey, hcNoContext) +
                        MenuItem('~2~ 80x28', AppCommands.cmTest80x28, kbNoKey, hcNoContext) +
                        MenuItem('~3~ 80x50', AppCommands.cmTest80x50, kbNoKey, hcNoContext) +
                        MenuItem('~4~ 90x30', AppCommands.cmTest90x30, kbNoKey, hcNoContext) +
                        MenuItem('~5~ 94x34', AppCommands.cmTest94x34, kbNoKey, hcNoContext) +
                        MenuItem('~6~ 132x25', AppCommands.cmTest132x25, kbNoKey, hcNoContext) +
                        MenuItem('~7~ 132x50', AppCommands.cmTest132x50, kbNoKey, hcNoContext) +
                        MenuItem('~8~ 132x60', AppCommands.cmTest132x60, kbNoKey, hcNoContext) +
                        MenuItem('~9~ 160x60', AppCommands.cmTest160x60, kbNoKey, hcNoContext))
            
            return MenuBar(bounds, subMenu1 + subMenu2 + subMenu3 + subMenu4 + subMenu5)
        
        def handleEvent(self, event: Event):
            super().handleEvent(event)
            if event.what == evCommand:
                emc = event.message.command
                if emc == cmHelp and not self.helpInUse:
                    self.helpInUse = True
                elif isinstance(emc, AppCommands):
                    self.clearEvent(event)
                    if emc == AppCommands.cmAboutCmd:
                        self.aboutDialogBoxPhase1()
                    elif emc == AppCommands.cmCalendarCmd:
                        self.calendar()
                    elif emc == AppCommands.cmAsciiCmd:
                        self.asciiTable()
                    elif emc == AppCommands.cmCalcCmd:
                        self.calculator()
                    elif emc == AppCommands.cmPuzzleCmd:
                        self.newPuzzle()
                    elif emc == AppCommands.cmOpenCmd:
                        self.openFile('*')
                    elif emc == AppCommands.cmChDirCmd:
                        self.changeDir()
                    elif emc == AppCommands.cmShellCmd:
                        self.doShellWindow()
                    elif emc == AppCommands.cmMouseCmd:
                        self.mouse()
                    elif emc == AppCommands.cmColorCmd:
                        self.colors()
                    elif emc == AppCommands.cmDialogCmd:
                        self.newDialogPhase1()
                    elif AppCommands.cmTest80x25 <= emc <= AppCommands.cmTest160x60:
                        self.testMode(emc)
                elif emc == AppCommands.cmAboutCmd + 100:  # Unicode Demo
                    self.clearEvent(event)
                    self.unicodeDemo()
                elif emc == AppCommands.cmAboutCmd + 101:  # Performance Info
                    self.clearEvent(event)
                    self.performanceInfo()
                elif emc == cmTile:
                    self.clearEvent(event)
                    self.tile()
                elif emc == cmCascade:
                    self.clearEvent(event)
                    self.cascade()
        
        def testMode(self, mode):
            width, height = (int(i) for i in mode.name.replace('cmTest', '').split('x'))
            Screen.screen.setScreenSize(width, height)
            # Resize Phase 1 buffer to match
            self.phase1_buffer = Phase1Buffer(width, height)
        
        def idle(self):
            super().idle()
            self.clock.update()
            TerminalView.updateTerminals()
            if self.desktop.firstThat(self.isTileable, None):
                self.enableCommand(cmTile)
                self.enableCommand(cmCascade)
            else:
                self.disableCommand(cmTile)
                self.disableCommand(cmCascade)
        
        def doShellWindow(self):
            r = Rect(0, 0, 84, 29)
            r.grow(-1, -1)
            t = TerminalWindow(r, '🖥️ Enhanced Terminal', 0)
            self.desktop.insert(t)
        
        def newPuzzle(self):
            p = PuzzleWindow()
            self.desktop.insert(p)
        
        def newDialogPhase1(self):
            """Enhanced dialog with Unicode support."""
            pd = Dialog(Rect(15, 4, 65, 20), '🎛️ Enhanced Demo Dialog')
            
            # Cheese selection with international varieties
            cheese_options = (
                '🧀 ~H~avarti',
                '🫕 ~G~ruyère', 
                '🍕 ~M~ozzarella',
                '💛 ~C~heddar'
            )
            b = CheckBoxes(Rect(3, 3, 22, 7), cheese_options)
            pd.insert(b)
            pd.insert(Label(Rect(2, 2, 12, 3), '🧀 Cheeses', b))
            
            # Consistency with Unicode indicators
            consistency_options = (
                '🟡 ~S~olid',
                '🟠 ~R~unny', 
                '🔴 ~M~elted'
            )
            b = RadioButtons(Rect(25, 3, 40, 6), consistency_options)
            pd.insert(b)
            pd.insert(Label(Rect(24, 2, 36, 3), '🌡️ Consistency', b))
            
            # Enhanced input with Unicode placeholder
            b = InputLine(Rect(3, 9, 47, 10), 128)
            pd.insert(b)
            pd.insert(Label(Rect(2, 8, 28, 9), '📦 Delivery Instructions', b))
            
            # Unicode-enhanced buttons
            pd.insert(Button(Rect(15, 12, 25, 14), '✅ ~O~K', cmOK, bfDefault))
            pd.insert(Button(Rect(30, 12, 42, 14), '❌ ~C~ancel', cmCancel, bfNormal))
            
            # Performance info
            stats = self.phase1_buffer.get_buffer_data().get_stats()
            info_text = f"Buffer: {stats['width']}×{stats['height']} | FPS: {stats['fps_limit']}"
            pd.insert(StaticText(Rect(2, 15, 48, 16), info_text))
            
            pd.setData(demoDialogData)
            
            control = self.desktop.execView(pd)
            data = []
            if control != cmCancel:
                data = pd.getData()
            del pd
            return data
        
        def aboutDialogBoxPhase1(self):
            """Enhanced About dialog showcasing Phase 1 features."""
            aboutBox = Dialog(Rect(0, 0, 50, 18), '🚀 About Vindauga Phase 1')
            
            # Multi-line text with Unicode and performance info
            platform_info = "Limited" if not self.phase1_buffer.best_platform else str(self.phase1_buffer.best_platform)
            stats = self.phase1_buffer.get_buffer_data().get_stats()
            
            about_text = f"""\\003🎯 Vindauga Demo - Phase 1\\n
\\003🌟 Enhanced Edition\\n
\\003━━━━━━━━━━━━━━━━━━━\\n
\\003🌍 Unicode Support: ✅\\n
\\003⚡ Damage Tracking: ✅\\n  
\\003🖥️ Platform: {platform_info}\\n
\\003📊 Buffer: {stats['width']}×{stats['height']}\\n
\\003🎨 Colors: Enhanced\\n
\\003📅 Version: 2024\\n
\\003👥 Borland + Phase 1"""
            
            aboutBox.insert(
                StaticText(Rect(3, 2, 47, 14), about_text)
            )
            aboutBox.insert(
                Button(Rect(19, 15, 31, 17), '✅ OK', cmOK, bfDefault)
            )
            aboutBox.options |= ofCentered
            self.executeDialog(aboutBox, None)
        
        def unicodeDemo(self):
            """Demo window showcasing Unicode capabilities."""
            demo = Dialog(Rect(0, 0, 70, 22), '🌍 Unicode & International Demo')
            
            # Create enhanced buffer display
            buffer = self.phase1_buffer
            
            demo_text = """\\003🌍 International Text Support\\n
\\003━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n
English: Hello, World! 👋\\n
中文: 你好，世界！🇨🇳\\n  
日本語: こんにちは世界 🇯🇵\\n
العربية: مرحبا بالعالم 🇸🇦\\n
Русский: Привет, мир! 🇷🇺\\n
Français: Bonjour le monde! 🇫🇷\\n
Deutsch: Hallo Welt! 🇩🇪\\n
Español: ¡Hola mundo! 🇪🇸\\n
\\003━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n
🚀 Emoji: ⭐ 🎉 🌈 🔥 💎 🎯 ✨\\n
📊 Math: ∑ ∞ ≠ ≤ ≥ π α β γ\\n
🎵 Music: ♪ ♫ ♬ ♭ ♮ ♯\\n
\\003━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n
⚡ Enhanced with TVision I/O Phase 1"""
            
            demo.insert(
                StaticText(Rect(2, 1, 68, 18), demo_text)
            )
            demo.insert(
                Button(Rect(30, 19, 40, 21), '✅ OK', cmOK, bfDefault)
            )
            demo.options |= ofCentered
            self.executeDialog(demo, None)
        
        def performanceInfo(self):
            """Show performance information dialog."""
            info = Dialog(Rect(0, 0, 55, 16), '⚡ Performance Information')
            
            stats = self.phase1_buffer.get_buffer_data().get_stats()
            platform = self.phase1_buffer.best_platform or "Limited"
            
            perf_text = f"""\\003⚡ TVision I/O Phase 1 Performance\\n
\\003━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n
🖥️ Platform: {platform}\\n
📏 Buffer Size: {stats['width']} × {stats['height']}\\n
📊 Total Cells: {stats['total_cells']:,}\\n
🔥 Dirty Cells: {stats['dirty_cells']}\\n
💨 Damage Ratio: {stats['damage_ratio']:.1%}\\n
🎯 FPS Limit: {stats['fps_limit']}\\n
🚀 Full Refresh: {'Yes' if stats['needs_full_refresh'] else 'No'}\\n
\\003━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n
✅ Damage tracking optimizes updates\\n
⚡ Unicode & wide char support\\n  
🌟 Memory-efficient with __slots__"""
            
            info.insert(
                StaticText(Rect(2, 1, 53, 13), perf_text)
            )
            info.insert(
                Button(Rect(22, 14, 32, 16), '✅ OK', cmOK, bfDefault)
            )
            info.options |= ofCentered
            self.executeDialog(info, None)
        
        def tile(self):
            self.desktop.tile(self.desktop.getExtent())
        
        def asciiTable(self):
            chart = self.validView(AsciiChart())
            if chart:
                chart.helpCtx = HelpContexts.hcAsciiTable
                self.desktop.insert(chart)
        
        def calendar(self):
            cal = self.validView(CalendarWindow())
            if cal:
                cal.helpCtx = HelpContexts.hcCalendar
                self.desktop.insert(cal)
        
        def calculator(self):
            calc = self.validView(CalculatorDialog())
            if calc:
                calc.helpCtx = HelpContexts.hcCalculator
                self.desktop.insert(calc)
        
        def cascade(self):
            self.desktop.cascade(self.desktop.getExtent())
        
        def changeDir(self):
            d = self.validView(ChangeDirDialog(0, cmChangeDir))
            if d:
                d.helpCtx = HelpContexts.hcFCChDirDBox
                self.desktop.execView(d)
                self.destroy(d)
        
        def colors(self):
            # Enhanced color groups with Unicode labels
            group1 = (ColorGroup('🖥️ Desktop')
                      + ColorItem('Color', 1)
                      
                      + ColorGroup('📋 Menus')
                      + ColorItem('Normal', 2)
                      + ColorItem('Disabled', 3)
                      + ColorItem('Shortcut', 4)
                      + ColorItem('Selected', 5)
                      + ColorItem('Selected disabled', 6)
                      + ColorItem('Shortcut selected', 7))
            
            group2 = (ColorGroup('💬 Dialogs / Calculator')
                      + ColorItem('Frame/background', 33)
                      + ColorItem('Frame icons', 34)
                      + ColorItem('Scroll bar page', 35)
                      + ColorItem('Scroll bar icons', 36)
                      + ColorItem('Static text', 37)
                      + ColorItem('Label normal', 38)
                      + ColorItem('Label selected', 39)
                      + ColorItem('Label shortcut', 40)
                      + ColorItem('Button normal', 41)
                      + ColorItem('Button default', 42)
                      + ColorItem('Button selected', 43)
                      + ColorItem('Button disabled', 44)
                      + ColorItem('Button shortcut', 45)
                      + ColorItem('Button shadow', 46)
                      + ColorItem('Cluster normal', 47)
                      + ColorItem('Cluster selected', 48)
                      + ColorItem('Cluster shortcut', 49)
                      + ColorItem('Input normal', 50)
                      + ColorItem('Input selected', 51)
                      + ColorItem('Input arrow', 52)
                      + ColorItem('History button', 53)
                      + ColorItem('History sides', 54)
                      + ColorItem('History bar page', 55)
                      + ColorItem('History bar icons', 56)
                      + ColorItem('List normal', 57)
                      + ColorItem('List focused', 58)
                      + ColorItem('List selected', 59)
                      + ColorItem('List divider', 60)
                      + ColorItem('Information pane', 61))
            
            group3 = (ColorGroup('📖 Viewer')
                      + ColorItem('Frame passive', 8)
                      + ColorItem('Frame active', 9)
                      + ColorItem('Frame icons', 10)
                      + ColorItem('Scroll bar page', 11)
                      + ColorItem('Scroll bar icons', 12)
                      + ColorItem('Text', 13)
                      
                      + ColorGroup('🧩 Puzzle')
                      + ColorItem('Frame passive', 8)
                      + ColorItem('Frame active', 9)
                      + ColorItem('Frame icons', 10)
                      + ColorItem('Scroll bar page', 11)
                      + ColorItem('Scroll bar icons', 12)
                      + ColorItem('Normal text', 13)
                      + ColorItem('Highlighted text', 14))
            
            group4 = (ColorGroup('📅 Calendar')
                      + ColorItem('Frame passive', 16)
                      + ColorItem('Frame active', 17)
                      + ColorItem('Frame icons', 18)
                      + ColorItem('Scroll bar page', 19)
                      + ColorItem('Scroll bar icons', 20)
                      + ColorItem('Normal text', 21)
                      + ColorItem('Current day', 22)
                      
                      + ColorGroup('📊 Ascii table')
                      + ColorItem('Frame passive', 24)
                      + ColorItem('Frame active', 25)
                      + ColorItem('Frame icons', 26)
                      + ColorItem('Scroll bar page', 27)
                      + ColorItem('Scroll bar icons', 28)
                      + ColorItem('Text', 29))
            
            group5 = group1 + group2 + group3 + group4
            
            c = ColorDialog(None, group5)
            
            if self.validView(c):
                c.helpCtx = HelpContexts.hcOCColorsDBox
                c.setData(self.getPalette())
                if self.desktop.execView(c) != cmCancel:
                    pal = c.getData()
                    self.setPalette(pal)
                    self.setScreenMode(Screen.screen.screenMode)
            self.destroy(c)
        
        def mouse(self):
            mouseCage = self.validView(MouseDialog())
            if mouseCage:
                mouseCage.helpCtx = HelpContexts.hcOMMouseDBox
                mouseCage.setData([EventQueue.mouseReverse])
                if self.desktop.execView(mouseCage) != cmCancel:
                    data = mouseCage.getData()
                    EventQueue.mouseReverse = data[0].value
                self.destroy(mouseCage)
        
        def openFile(self, fileSpec):
            d = self.validView(FileDialog(fileSpec, '📁 Open a File', '~N~ame', fdOpenButton, 100))
            if d and self.desktop.execView(d) != cmCancel:
                filename = d.getFilename()
                d.helpCtx = HelpContexts.hcFOFileOpenDBox
                w = self.validView(FileWindow(filename))
                if w:
                    self.desktop.insert(w)
                self.destroy(d)


def run_phase1_demo():
    """Run the Phase 1 enhanced Vindauga demo."""
    if not VINDAUGA_AVAILABLE:
        print("❌ Vindauga modules not available")
        print("Running standalone Phase 1 demo instead...")
        run_standalone_demo()
        return
    
    print("🚀 Starting Vindauga Phase 1 Enhanced Demo...")
    myApp = VindaugaDemoPhase1()
    myApp.run()


def run_standalone_demo():
    """Run a standalone demo if Vindauga is not available."""
    print("🚀 TVision I/O Phase 1 - Standalone Demo")
    print("=" * 50)
    
    # Create enhanced buffer
    buffer = Phase1Buffer(80, 25)
    
    # Demo layout
    buffer.create_unicode_frame(2, 2, 76, 21, "TVision I/O Phase 1 Demo", 0x1F)
    
    # Show platform info
    buffer.show_platform_info(5, 4)
    
    # Unicode features
    buffer.demo_unicode_features(5, 10)
    
    # Performance stats
    buffer.show_performance_stats(45, 4)
    
    # Status info
    buffer.put_enhanced_text(5, 20, "🎯 Status: Phase 1 Complete | Ready for Phase 2", 0x0E)
    
    # Get buffer stats
    stats = buffer.get_buffer_data().get_stats()
    
    print(f"✅ Standalone demo created!")
    print(f"📊 Buffer: {stats['width']}×{stats['height']}")
    print(f"💾 Dirty cells: {stats['dirty_cells']}/{stats['total_cells']}")
    print(f"⚡ Damage ratio: {stats['damage_ratio']:.1%}")
    print(f"🎯 FPS limit: {stats['fps_limit']}")
    
    print("\n🌟 Features demonstrated:")
    print("  ✓ Unicode box drawing characters")
    print("  ✓ International text support")
    print("  ✓ Emoji and symbol rendering")
    print("  ✓ Platform detection")
    print("  ✓ Performance optimization")
    print("  ✓ Memory-efficient design")
    
    print("\n🎯 To run full demo: Install Vindauga dependencies")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == '--standalone':
        run_standalone_demo()
    else:
        setupLogging()
        try:
            run_phase1_demo()
        except Exception as e:
            logger.exception('vindauga_demo_phase1 fail')
            print(f"❌ Demo failed: {e}")
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())