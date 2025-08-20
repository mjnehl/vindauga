#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVision-Style Performance Analysis for Vindauga Python Implementation

This script analyzes the performance implications of implementing TVision-style
improvements in Vindauga, focusing on key bottlenecks and optimization opportunities.
"""

import time
import sys
import os
import gc
import threading
import array
import pickle
import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from functools import wraps
import cProfile
import pstats
import io
import tracemalloc
from contextlib import contextmanager

# Add vindauga to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

@dataclass
class PerformanceMetrics:
    """Performance measurement container"""
    operation: str
    execution_time: float
    memory_before: int
    memory_after: int
    memory_peak: int
    cpu_time: float
    iterations: int = 1
    
    @property
    def memory_delta(self) -> int:
        return self.memory_after - self.memory_before
    
    @property
    def avg_time_per_iteration(self) -> float:
        return self.execution_time / self.iterations if self.iterations > 0 else 0

class PerformanceProfiler:
    """Comprehensive performance profiler for Vindauga components"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.profiler = None
        
    @contextmanager
    def profile_block(self, operation_name: str, iterations: int = 1):
        """Context manager for profiling code blocks"""
        # Start memory tracking
        tracemalloc.start()
        gc.collect()
        
        # Record initial state
        memory_before = tracemalloc.get_traced_memory()[0]
        start_time = time.perf_counter()
        
        # Start CPU profiling
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        
        try:
            yield
        finally:
            # Stop profiling
            self.profiler.disable()
            
            # Record final state
            end_time = time.perf_counter()
            memory_current, memory_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # Calculate CPU time from profiler
            stats = pstats.Stats(self.profiler)
            cpu_time = stats.total_tt
            
            # Create metrics
            metrics = PerformanceMetrics(
                operation=operation_name,
                execution_time=end_time - start_time,
                memory_before=memory_before,
                memory_after=memory_current,
                memory_peak=memory_peak,
                cpu_time=cpu_time,
                iterations=iterations
            )
            
            self.metrics.append(metrics)
            
    def get_profiler_stats(self) -> str:
        """Get detailed profiler statistics"""
        if not self.profiler:
            return "No profiler data available"
            
        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions
        return stream.getvalue()

class DrawBufferBenchmark:
    """Benchmark draw buffer operations with different allocation strategies"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
        
    def benchmark_fixed_width_buffer(self, iterations: int = 1000) -> PerformanceMetrics:
        """Benchmark current fixed-width buffer implementation"""
        from vindauga.types.draw_buffer import DrawBuffer, LINE_WIDTH
        
        with self.profiler.profile_block("Fixed Width Buffer Operations", iterations):
            buffers = []
            for i in range(iterations):
                buffer = DrawBuffer(filled=True)
                # Simulate typical operations
                buffer.moveStr(0, "Hello World" * 20, 0x07)
                buffer.moveChar(100, 'X', 0x0F, 50)
                buffer.moveCStr(200, "~Highlighted~ Text", 0x0F07)
                buffers.append(buffer)
                
                # Simulate some manipulation
                for j in range(0, min(LINE_WIDTH - 10, 500), 10):
                    buffer.putChar(j, chr(65 + (j % 26)))
                    
        return self.profiler.metrics[-1]
    
    def benchmark_dynamic_width_buffer(self, iterations: int = 1000, max_width: int = 2048) -> PerformanceMetrics:
        """Benchmark dynamic width buffer simulation"""
        
        class DynamicDrawBuffer:
            """Simulated dynamic width buffer"""
            def __init__(self, initial_width: int = 80):
                self.width = initial_width
                self._data = array.array('L', [0] * initial_width)
                
            def ensure_width(self, required_width: int):
                if required_width > self.width:
                    # Resize with growth factor
                    new_width = max(required_width, int(self.width * 1.5))
                    old_data = self._data
                    self._data = array.array('L', [0] * new_width)
                    self._data[:len(old_data)] = old_data
                    self.width = new_width
                    
            def moveStr(self, indent: int, text: str, attr: int):
                required_width = indent + len(text)
                self.ensure_width(required_width)
                attr = (attr & 0xFF) << 16
                for i, c in enumerate(text):
                    self._data[indent + i] = ord(c) | attr
                    
            def moveChar(self, indent: int, c: str, attr: int, count: int):
                required_width = indent + count
                self.ensure_width(required_width)
                attr = (attr & 0xFF) << 16
                char_val = ord(c) | attr
                for i in range(count):
                    self._data[indent + i] = char_val
                    
        with self.profiler.profile_block("Dynamic Width Buffer Operations", iterations):
            buffers = []
            for i in range(iterations):
                buffer = DynamicDrawBuffer(80)
                # Simulate operations that trigger resizing
                buffer.moveStr(0, "Hello World" * 20, 0x07)
                buffer.moveChar(100, 'X', 0x0F, 50)
                buffer.moveStr(500, "Extended text that triggers resize", 0x0E)
                buffer.moveChar(1000, 'Y', 0x0C, 100)
                buffers.append(buffer)
                
        return self.profiler.metrics[-1]

class EventQueueBenchmark:
    """Benchmark event queue operations and thread safety"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
        
    def benchmark_simple_queue(self, iterations: int = 10000) -> PerformanceMetrics:
        """Benchmark simple list-based event queue"""
        from vindauga.events.event import Event
        from vindauga.constants.event_codes import evNothing
        
        with self.profiler.profile_block("Simple Event Queue", iterations):
            queue = []
            for i in range(iterations):
                event = Event(evNothing)
                queue.append(event)
                
                # Simulate processing
                if len(queue) > 100:
                    # Process some events
                    for _ in range(50):
                        if queue:
                            queue.pop(0)
                            
        return self.profiler.metrics[-1]
    
    def benchmark_thread_safe_queue(self, iterations: int = 10000) -> PerformanceMetrics:
        """Benchmark thread-safe event queue with locks"""
        import queue
        import threading
        from vindauga.events.event import Event
        from vindauga.constants.event_codes import evNothing
        
        with self.profiler.profile_block("Thread-Safe Event Queue", iterations):
            event_queue = queue.Queue()
            lock = threading.Lock()
            
            def producer():
                for i in range(iterations // 2):
                    event = Event(evNothing)
                    with lock:
                        event_queue.put(event)
                        
            def consumer():
                processed = 0
                while processed < iterations // 2:
                    try:
                        with lock:
                            event = event_queue.get_nowait()
                            processed += 1
                    except queue.Empty:
                        time.sleep(0.001)  # Small delay
                        
            # Run producer and consumer in parallel
            producer_thread = threading.Thread(target=producer)
            consumer_thread = threading.Thread(target=consumer)
            
            producer_thread.start()
            consumer_thread.start()
            
            producer_thread.join()
            consumer_thread.join()
            
        return self.profiler.metrics[-1]

class UnicodeProcessingBenchmark:
    """Benchmark Unicode processing performance"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
        
    def benchmark_basic_string_ops(self, iterations: int = 10000) -> PerformanceMetrics:
        """Benchmark basic string operations"""
        test_strings = [
            "Hello World",
            "Héllo Wörld",
            "Привет мир",
            "こんにちは世界",
            "🌍🌎🌏 Unicode",
            "Mixed: ASCII + Ñoño + 中文 + 🎉"
        ]
        
        with self.profiler.profile_block("Unicode String Operations", iterations):
            results = []
            for i in range(iterations):
                for text in test_strings:
                    # Simulate common operations
                    length = len(text)
                    encoded = text.encode('utf-8')
                    decoded = encoded.decode('utf-8')
                    width = sum(1 + (ord(c) > 127) for c in text)  # Simplified width calc
                    results.append((length, len(encoded), width))
                    
        return self.profiler.metrics[-1]
    
    def benchmark_wcwidth_calculation(self, iterations: int = 5000) -> PerformanceMetrics:
        """Benchmark character width calculations"""
        import unicodedata
        
        test_chars = [
            'A', 'á', 'Ñ', 'π', '中', '🌍', '\t', '\n'
        ]
        
        def simple_wcwidth(char):
            """Simplified width calculation"""
            code = ord(char)
            if code < 32 or code == 127:
                return 0
            elif code < 127:
                return 1
            elif unicodedata.east_asian_width(char) in ('F', 'W'):
                return 2
            else:
                return 1
                
        with self.profiler.profile_block("Character Width Calculations", iterations):
            widths = []
            for i in range(iterations):
                for char in test_chars:
                    width = simple_wcwidth(char)
                    widths.append(width)
                    
        return self.profiler.metrics[-1]

class TimerSystemBenchmark:
    """Benchmark timer system performance"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
        
    def benchmark_timer_operations(self, iterations: int = 1000) -> PerformanceMetrics:
        """Benchmark timer creation and management"""
        from vindauga.types.timer import Timer
        
        with self.profiler.profile_block("Timer Operations", iterations):
            timers = []
            for i in range(iterations):
                timer = Timer()
                timer.start()
                timer.stop()
                timers.append(timer)
                
                # Simulate timer checking
                for t in timers[-10:]:  # Check last 10 timers
                    expired = t.expired()
                    
        return self.profiler.metrics[-1]
    
    def benchmark_polling_overhead(self, duration_ms: int = 100) -> PerformanceMetrics:
        """Benchmark polling overhead simulation"""
        
        class MockEventLoop:
            def __init__(self, timeout_ms: int = 20):
                self.timeout_ms = timeout_ms
                self.running = False
                
            def run_with_polling(self, duration_ms: int):
                self.running = True
                start_time = time.time()
                polls = 0
                
                while (time.time() - start_time) * 1000 < duration_ms and self.running:
                    # Simulate polling
                    time.sleep(self.timeout_ms / 1000.0)
                    polls += 1
                    
                    # Simulate some work
                    dummy = sum(range(100))
                    
                return polls
                
        with self.profiler.profile_block("Polling Overhead Simulation"):
            event_loop = MockEventLoop(20)  # 20ms timeout like TVision
            polls = event_loop.run_with_polling(duration_ms)
            
        return self.profiler.metrics[-1]

class SerializationBenchmark:
    """Benchmark serialization performance"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
        
    def create_test_data(self, size: int = 1000) -> Dict[str, Any]:
        """Create test data structure"""
        return {
            'widgets': [
                {
                    'type': 'button',
                    'id': i,
                    'text': f'Button {i}',
                    'bounds': {'x': i % 100, 'y': i // 100, 'w': 80, 'h': 20},
                    'attributes': {'color': i % 16, 'enabled': True}
                }
                for i in range(size)
            ],
            'metadata': {
                'version': '1.0',
                'created': time.time(),
                'platform': sys.platform
            }
        }
    
    def benchmark_pickle_serialization(self, iterations: int = 100) -> PerformanceMetrics:
        """Benchmark Python pickle serialization"""
        test_data = self.create_test_data(1000)
        
        with self.profiler.profile_block("Pickle Serialization", iterations):
            for i in range(iterations):
                # Serialize
                serialized = pickle.dumps(test_data, protocol=pickle.HIGHEST_PROTOCOL)
                
                # Deserialize
                deserialized = pickle.loads(serialized)
                
        return self.profiler.metrics[-1]
    
    def benchmark_json_serialization(self, iterations: int = 100) -> PerformanceMetrics:
        """Benchmark JSON serialization"""
        test_data = self.create_test_data(1000)
        
        with self.profiler.profile_block("JSON Serialization", iterations):
            for i in range(iterations):
                # Serialize
                serialized = json.dumps(test_data)
                
                # Deserialize  
                deserialized = json.loads(serialized)
                
        return self.profiler.metrics[-1]

class PythonVsCppAnalysis:
    """Analyze Python vs C++ performance characteristics"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
        
    def benchmark_gil_impact(self, iterations: int = 1000) -> PerformanceMetrics:
        """Simulate GIL impact on performance"""
        import threading
        
        def cpu_intensive_task(n: int):
            """CPU-intensive task that holds GIL"""
            result = 0
            for i in range(n):
                result += i * i
            return result
            
        with self.profiler.profile_block("GIL Impact Simulation", iterations):
            # Single-threaded execution
            single_start = time.perf_counter()
            single_result = cpu_intensive_task(iterations)
            single_time = time.perf_counter() - single_start
            
            # Multi-threaded execution (should show GIL impact)
            results = []
            threads = []
            multi_start = time.perf_counter()
            
            for i in range(4):  # 4 threads
                thread = threading.Thread(
                    target=lambda: results.append(cpu_intensive_task(iterations // 4))
                )
                threads.append(thread)
                thread.start()
                
            for thread in threads:
                thread.join()
                
            multi_time = time.perf_counter() - multi_start
            
            # The ratio should show GIL impact
            gil_overhead = multi_time / single_time
            
        return self.profiler.metrics[-1]

def run_comprehensive_analysis():
    """Run comprehensive performance analysis"""
    profiler = PerformanceProfiler()
    
    print("🔍 Starting TVision-Style Performance Analysis for Vindauga")
    print("=" * 60)
    
    # 1. Dynamic Buffer Allocation Analysis
    print("\n📊 1. Draw Buffer Performance Analysis")
    buffer_bench = DrawBufferBenchmark(profiler)
    
    fixed_metrics = buffer_bench.benchmark_fixed_width_buffer(1000)
    print(f"   Fixed Width (1024): {fixed_metrics.execution_time:.4f}s, "
          f"Memory: {fixed_metrics.memory_delta / 1024:.1f}KB")
    
    dynamic_metrics = buffer_bench.benchmark_dynamic_width_buffer(1000)
    print(f"   Dynamic Width:      {dynamic_metrics.execution_time:.4f}s, "
          f"Memory: {dynamic_metrics.memory_delta / 1024:.1f}KB")
    
    # 2. Event Queue Analysis
    print("\n📊 2. Event Queue Performance Analysis")
    queue_bench = EventQueueBenchmark(profiler)
    
    simple_metrics = queue_bench.benchmark_simple_queue(10000)
    print(f"   Simple Queue:       {simple_metrics.execution_time:.4f}s, "
          f"Memory: {simple_metrics.memory_delta / 1024:.1f}KB")
    
    threadsafe_metrics = queue_bench.benchmark_thread_safe_queue(10000)
    print(f"   Thread-Safe Queue:  {threadsafe_metrics.execution_time:.4f}s, "
          f"Memory: {threadsafe_metrics.memory_delta / 1024:.1f}KB")
    
    # 3. Unicode Processing Analysis
    print("\n📊 3. Unicode Processing Performance Analysis")
    unicode_bench = UnicodeProcessingBenchmark(profiler)
    
    string_metrics = unicode_bench.benchmark_basic_string_ops(10000)
    print(f"   String Operations:  {string_metrics.execution_time:.4f}s, "
          f"Memory: {string_metrics.memory_delta / 1024:.1f}KB")
    
    width_metrics = unicode_bench.benchmark_wcwidth_calculation(5000)
    print(f"   Width Calculations: {width_metrics.execution_time:.4f}s, "
          f"Memory: {width_metrics.memory_delta / 1024:.1f}KB")
    
    # 4. Timer System Analysis
    print("\n📊 4. Timer System Performance Analysis")
    timer_bench = TimerSystemBenchmark(profiler)
    
    timer_metrics = timer_bench.benchmark_timer_operations(1000)
    print(f"   Timer Operations:   {timer_metrics.execution_time:.4f}s, "
          f"Memory: {timer_metrics.memory_delta / 1024:.1f}KB")
    
    polling_metrics = timer_bench.benchmark_polling_overhead(1000)
    print(f"   Polling Overhead:   {polling_metrics.execution_time:.4f}s, "
          f"Memory: {polling_metrics.memory_delta / 1024:.1f}KB")
    
    # 5. Serialization Analysis
    print("\n📊 5. Serialization Performance Analysis")
    serial_bench = SerializationBenchmark(profiler)
    
    pickle_metrics = serial_bench.benchmark_pickle_serialization(100)
    print(f"   Pickle:             {pickle_metrics.execution_time:.4f}s, "
          f"Memory: {pickle_metrics.memory_delta / 1024:.1f}KB")
    
    json_metrics = serial_bench.benchmark_json_serialization(100)
    print(f"   JSON:               {json_metrics.execution_time:.4f}s, "
          f"Memory: {json_metrics.memory_delta / 1024:.1f}KB")
    
    # 6. Python vs C++ Analysis
    print("\n📊 6. Python vs C++ Performance Characteristics")
    cpp_analysis = PythonVsCppAnalysis(profiler)
    
    gil_metrics = cpp_analysis.benchmark_gil_impact(10000)
    print(f"   GIL Impact:         {gil_metrics.execution_time:.4f}s, "
          f"Memory: {gil_metrics.memory_delta / 1024:.1f}KB")
    
    # Summary
    print("\n📈 Performance Summary")
    print("=" * 60)
    total_time = sum(m.execution_time for m in profiler.metrics)
    total_memory = sum(m.memory_delta for m in profiler.metrics)
    
    print(f"Total Analysis Time: {total_time:.4f}s")
    print(f"Total Memory Delta:  {total_memory / 1024:.1f}KB")
    print(f"Operations Analyzed: {len(profiler.metrics)}")
    
    return profiler.metrics

if __name__ == "__main__":
    metrics = run_comprehensive_analysis()