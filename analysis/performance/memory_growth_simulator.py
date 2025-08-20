#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Growth Pattern Analysis for Vindauga View Hierarchies

Simulates memory usage patterns with large widget hierarchies and GC behavior.
"""

import gc
import sys
import time
import tracemalloc
from typing import List, Dict, Any
from dataclasses import dataclass
import weakref
import threading

# Add vindauga to path
sys.path.insert(0, '../../')

@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: float
    current_memory: int
    peak_memory: int
    gc_collections: tuple
    object_count: int
    widget_count: int

class MemoryProfiler:
    """Profile memory usage patterns"""
    
    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.tracking = False
        
    def start_tracking(self):
        """Start memory tracking"""
        if not self.tracking:
            tracemalloc.start()
            self.tracking = True
            gc.collect()  # Start with clean slate
            
    def stop_tracking(self):
        """Stop memory tracking"""
        if self.tracking:
            tracemalloc.stop()
            self.tracking = False
            
    def take_snapshot(self, widget_count: int = 0):
        """Take memory snapshot"""
        if not self.tracking:
            return
            
        current, peak = tracemalloc.get_traced_memory()
        gc_stats = gc.get_stats()
        
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            current_memory=current,
            peak_memory=peak,
            gc_collections=tuple(stat['collections'] for stat in gc_stats),
            object_count=len(gc.get_objects()),
            widget_count=widget_count
        )
        
        self.snapshots.append(snapshot)
        return snapshot

class MockWidget:
    """Mock widget for memory testing"""
    
    _instances = weakref.WeakSet()
    
    def __init__(self, widget_type: str = "widget", parent=None):
        self.widget_type = widget_type
        self.parent = parent
        self.children: List['MockWidget'] = []
        self.properties: Dict[str, Any] = {}
        self.event_handlers: Dict[str, callable] = {}
        self.draw_buffer = [0] * 1024  # Simulate draw buffer
        self.visible = True
        self.bounds = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        
        # Add to parent
        if parent:
            parent.add_child(self)
            
        # Track instances
        MockWidget._instances.add(self)
        
    def add_child(self, child: 'MockWidget'):
        """Add child widget"""
        self.children.append(child)
        child.parent = self
        
    def remove_child(self, child: 'MockWidget'):
        """Remove child widget"""
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            
    def destroy(self):
        """Destroy widget and children"""
        # Destroy children first
        for child in self.children[:]:
            child.destroy()
            
        # Remove from parent
        if self.parent:
            self.parent.remove_child(self)
            
        # Clear references
        self.children.clear()
        self.properties.clear()
        self.event_handlers.clear()
        self.draw_buffer = None
        
    @classmethod
    def get_instance_count(cls) -> int:
        """Get number of live instances"""
        return len(cls._instances)

class ViewHierarchySimulator:
    """Simulate large view hierarchies"""
    
    def __init__(self, profiler: MemoryProfiler):
        self.profiler = profiler
        self.root_widgets: List[MockWidget] = []
        
    def create_simple_hierarchy(self, widget_count: int = 1000) -> List[MockWidget]:
        """Create simple flat hierarchy"""
        widgets = []
        
        for i in range(widget_count):
            widget = MockWidget(f"widget_{i}")
            widget.properties = {
                'id': i,
                'text': f'Widget {i}',
                'color': i % 16,
                'enabled': True,
                'data': list(range(10))  # Some data
            }
            widgets.append(widget)
            
        return widgets
        
    def create_deep_hierarchy(self, depth: int = 10, children_per_level: int = 5) -> MockWidget:
        """Create deep nested hierarchy"""
        
        def create_level(parent: MockWidget, current_depth: int, max_depth: int):
            if current_depth >= max_depth:
                return
                
            for i in range(children_per_level):
                child = MockWidget(f"level_{current_depth}_child_{i}", parent)
                child.properties = {
                    'level': current_depth,
                    'index': i,
                    'path': f"{parent.properties.get('path', '')}/{i}" if parent.properties else f"/{i}"
                }
                create_level(child, current_depth + 1, max_depth)
                
        root = MockWidget("root")
        root.properties = {'path': ''}
        create_level(root, 0, depth)
        return root
        
    def create_window_hierarchy(self, window_count: int = 50) -> List[MockWidget]:
        """Create hierarchy simulating multiple windows"""
        windows = []
        
        for w in range(window_count):
            window = MockWidget("window")
            window.properties = {
                'title': f'Window {w}',
                'window_id': w,
                'modal': w % 5 == 0  # Every 5th window is modal
            }
            
            # Add menu bar
            menubar = MockWidget("menubar", window)
            for m in range(5):
                menu = MockWidget("menu", menubar)
                menu.properties = {'title': f'Menu {m}'}
                for item in range(10):
                    menu_item = MockWidget("menu_item", menu)
                    menu_item.properties = {'text': f'Item {item}'}
                    
            # Add toolbar
            toolbar = MockWidget("toolbar", window)
            for b in range(10):
                button = MockWidget("button", toolbar)
                button.properties = {'text': f'Button {b}', 'icon': f'icon_{b}'}
                
            # Add status bar
            statusbar = MockWidget("statusbar", window)
            for p in range(3):
                panel = MockWidget("status_panel", statusbar)
                panel.properties = {'text': f'Panel {p}'}
                
            # Add main content area with nested widgets
            content = MockWidget("content_area", window)
            for r in range(20):  # 20 rows
                row = MockWidget("row", content)
                for c in range(10):  # 10 columns
                    cell = MockWidget("cell", row)
                    cell.properties = {
                        'row': r, 'col': c,
                        'value': f'Cell({r},{c})',
                        'editable': True
                    }
                    
            windows.append(window)
            
        return windows

class GarbageCollectionAnalyzer:
    """Analyze garbage collection behavior"""
    
    def __init__(self, profiler: MemoryProfiler):
        self.profiler = profiler
        
    def test_gc_pressure(self, widget_count: int = 5000):
        """Test GC pressure with widget creation/destruction"""
        print(f"\n🗑️ Testing GC Pressure with {widget_count} widgets")
        
        self.profiler.start_tracking()
        initial_snapshot = self.profiler.take_snapshot(0)
        
        simulator = ViewHierarchySimulator(self.profiler)
        
        # Phase 1: Create widgets
        print("  Creating widgets...")
        widgets = simulator.create_simple_hierarchy(widget_count)
        create_snapshot = self.profiler.take_snapshot(len(widgets))
        
        # Phase 2: Create references and cycles
        print("  Creating circular references...")
        for i in range(0, len(widgets) - 1, 2):
            widgets[i].properties['buddy'] = widgets[i + 1]
            widgets[i + 1].properties['buddy'] = widgets[i]
            
        cycle_snapshot = self.profiler.take_snapshot(len(widgets))
        
        # Phase 3: Force GC
        print("  Forcing garbage collection...")
        collected = gc.collect()
        gc_snapshot = self.profiler.take_snapshot(len(widgets))
        
        # Phase 4: Destroy half
        print("  Destroying half the widgets...")
        for widget in widgets[:len(widgets)//2]:
            widget.destroy()
            
        destroy_snapshot = self.profiler.take_snapshot(MockWidget.get_instance_count())
        
        # Phase 5: Final GC
        print("  Final garbage collection...")
        final_collected = gc.collect()
        final_snapshot = self.profiler.take_snapshot(MockWidget.get_instance_count())
        
        # Analysis
        print(f"\n📊 GC Analysis Results:")
        print(f"  Initial memory: {initial_snapshot.current_memory / 1024:.1f} KB")
        print(f"  After creation: {create_snapshot.current_memory / 1024:.1f} KB")
        print(f"  After cycles:   {cycle_snapshot.current_memory / 1024:.1f} KB")
        print(f"  After GC:       {gc_snapshot.current_memory / 1024:.1f} KB")
        print(f"  After destroy:  {destroy_snapshot.current_memory / 1024:.1f} KB")
        print(f"  Final:          {final_snapshot.current_memory / 1024:.1f} KB")
        print(f"  Objects collected: {collected} + {final_collected}")
        print(f"  Live widgets: {MockWidget.get_instance_count()}")
        
        self.profiler.stop_tracking()

class ThreadSafetyAnalyzer:
    """Analyze thread safety impact on performance"""
    
    def __init__(self, profiler: MemoryProfiler):
        self.profiler = profiler
        self.results = {}
        
    def test_concurrent_widget_access(self, thread_count: int = 4, operations_per_thread: int = 1000):
        """Test concurrent widget access performance"""
        print(f"\n🧵 Testing Thread Safety with {thread_count} threads, {operations_per_thread} ops each")
        
        # Create shared widget hierarchy
        simulator = ViewHierarchySimulator(self.profiler)
        root = simulator.create_deep_hierarchy(5, 3)
        
        # Lock for thread-safe operations
        widget_lock = threading.Lock()
        results = []
        
        def worker_thread(thread_id: int):
            """Worker thread that accesses widgets"""
            thread_results = {
                'thread_id': thread_id,
                'operations': 0,
                'errors': 0,
                'start_time': time.time()
            }
            
            for op in range(operations_per_thread):
                try:
                    # Simulate various operations
                    if op % 4 == 0:
                        # Read operation
                        with widget_lock:
                            value = root.properties.get('path', '')
                            
                    elif op % 4 == 1:
                        # Write operation
                        with widget_lock:
                            root.properties[f'thread_{thread_id}_op_{op}'] = time.time()
                            
                    elif op % 4 == 2:
                        # Tree traversal
                        def visit(widget):
                            widget.properties.get('visited', 0)
                            for child in widget.children:
                                visit(child)
                        with widget_lock:
                            visit(root)
                            
                    else:
                        # Create temporary widget
                        temp = MockWidget(f"temp_{thread_id}_{op}")
                        temp.destroy()
                        
                    thread_results['operations'] += 1
                    
                except Exception as e:
                    thread_results['errors'] += 1
                    
            thread_results['end_time'] = time.time()
            thread_results['duration'] = thread_results['end_time'] - thread_results['start_time']
            results.append(thread_results)
            
        # Start threads
        threads = []
        start_time = time.time()
        
        for i in range(thread_count):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analysis
        total_ops = sum(r['operations'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        avg_thread_time = sum(r['duration'] for r in results) / len(results)
        
        print(f"📊 Thread Safety Results:")
        print(f"  Total time: {total_duration:.3f}s")
        print(f"  Avg thread time: {avg_thread_time:.3f}s")
        print(f"  Total operations: {total_ops}")
        print(f"  Total errors: {total_errors}")
        print(f"  Ops/second: {total_ops / total_duration:.1f}")
        print(f"  Concurrency efficiency: {avg_thread_time / total_duration:.2f}")
        
        # Cleanup
        root.destroy()

def run_memory_analysis():
    """Run comprehensive memory analysis"""
    print("🔍 Memory Growth Pattern Analysis for Vindauga")
    print("=" * 50)
    
    profiler = MemoryProfiler()
    
    # 1. Simple widget creation/destruction
    print("\n1️⃣ Simple Widget Lifecycle")
    profiler.start_tracking()
    
    simulator = ViewHierarchySimulator(profiler)
    widgets = simulator.create_simple_hierarchy(2000)
    after_create = profiler.take_snapshot(len(widgets))
    
    # Destroy widgets
    for widget in widgets:
        widget.destroy()
    gc.collect()
    after_destroy = profiler.take_snapshot(MockWidget.get_instance_count())
    
    print(f"  Created 2000 widgets: {after_create.current_memory / 1024:.1f} KB")
    print(f"  After destruction: {after_destroy.current_memory / 1024:.1f} KB")
    print(f"  Memory reclaimed: {(after_create.current_memory - after_destroy.current_memory) / 1024:.1f} KB")
    
    profiler.stop_tracking()
    
    # 2. Deep hierarchy test
    print("\n2️⃣ Deep Hierarchy Memory Usage")
    profiler.start_tracking()
    
    root = simulator.create_deep_hierarchy(8, 4)  # 8 levels, 4 children each
    after_hierarchy = profiler.take_snapshot(MockWidget.get_instance_count())
    
    print(f"  Deep hierarchy (8 levels): {after_hierarchy.current_memory / 1024:.1f} KB")
    print(f"  Widget instances: {MockWidget.get_instance_count()}")
    
    root.destroy()
    gc.collect()
    after_cleanup = profiler.take_snapshot(MockWidget.get_instance_count())
    
    print(f"  After cleanup: {after_cleanup.current_memory / 1024:.1f} KB")
    
    profiler.stop_tracking()
    
    # 3. Window hierarchy simulation
    print("\n3️⃣ Multiple Windows Simulation")
    profiler.start_tracking()
    
    windows = simulator.create_window_hierarchy(20)
    after_windows = profiler.take_snapshot(MockWidget.get_instance_count())
    
    print(f"  20 windows created: {after_windows.current_memory / 1024:.1f} KB")
    print(f"  Total widgets: {MockWidget.get_instance_count()}")
    
    # Cleanup
    for window in windows:
        window.destroy()
    gc.collect()
    final_cleanup = profiler.take_snapshot(MockWidget.get_instance_count())
    
    print(f"  After cleanup: {final_cleanup.current_memory / 1024:.1f} KB")
    
    profiler.stop_tracking()
    
    # 4. GC Pressure Test
    gc_analyzer = GarbageCollectionAnalyzer(profiler)
    gc_analyzer.test_gc_pressure(3000)
    
    # 5. Thread Safety Test
    thread_analyzer = ThreadSafetyAnalyzer(profiler)
    thread_analyzer.test_concurrent_widget_access(4, 500)
    
    # Summary
    print(f"\n📈 Memory Analysis Summary")
    print("=" * 50)
    print(f"Total snapshots taken: {len(profiler.snapshots)}")
    if profiler.snapshots:
        max_memory = max(s.current_memory for s in profiler.snapshots)
        avg_memory = sum(s.current_memory for s in profiler.snapshots) / len(profiler.snapshots)
        print(f"Peak memory usage: {max_memory / 1024:.1f} KB")
        print(f"Average memory usage: {avg_memory / 1024:.1f} KB")
    
    print(f"Final widget instances: {MockWidget.get_instance_count()}")

if __name__ == "__main__":
    run_memory_analysis()