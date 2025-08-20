#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner for Phase 1 components only.

This script runs unit tests specifically for the Phase 1 components
we've created, avoiding the existing test files that have dependencies
on components we haven't built yet.
"""

import sys
import unittest
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_phase1_tests():
    """Run only Phase 1 component tests."""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Load only our Phase 1 test modules
    loader = unittest.TestLoader()
    
    # Import and add our test modules
    from vindauga.io.tests import test_screen_cell
    from vindauga.io.tests import test_damage_region
    from vindauga.io.tests import test_fps_limiter
    from vindauga.io.tests import test_display_buffer
    from vindauga.io.tests import test_platform_detector
    
    # Add tests to suite
    suite.addTests(loader.loadTestsFromModule(test_screen_cell))
    suite.addTests(loader.loadTestsFromModule(test_damage_region))
    suite.addTests(loader.loadTestsFromModule(test_fps_limiter))
    suite.addTests(loader.loadTestsFromModule(test_display_buffer))
    suite.addTests(loader.loadTestsFromModule(test_platform_detector))
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PHASE 1 TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All Phase 1 tests passed!")
    else:
        print("\n❌ Some tests failed.")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    return result.wasSuccessful()


def calculate_phase1_coverage():
    """Calculate test coverage for Phase 1 components."""
    try:
        import coverage
    except ImportError:
        print("\n⚠️  Coverage.py not installed. Install with: pip install coverage")
        return
    
    print("\n" + "=" * 70)
    print("PHASE 1 COVERAGE ANALYSIS")
    print("=" * 70)
    
    # Create coverage instance
    cov = coverage.Coverage(source_pkgs=['vindauga.io'])
    
    # Start coverage
    cov.start()
    
    # Run tests again with coverage
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    from vindauga.io.tests import test_screen_cell
    from vindauga.io.tests import test_damage_region
    from vindauga.io.tests import test_fps_limiter
    from vindauga.io.tests import test_display_buffer
    from vindauga.io.tests import test_platform_detector
    
    suite.addTests(loader.loadTestsFromModule(test_screen_cell))
    suite.addTests(loader.loadTestsFromModule(test_damage_region))
    suite.addTests(loader.loadTestsFromModule(test_fps_limiter))
    suite.addTests(loader.loadTestsFromModule(test_display_buffer))
    suite.addTests(loader.loadTestsFromModule(test_platform_detector))
    
    runner = unittest.TextTestRunner(verbosity=0)
    runner.run(suite)
    
    # Stop coverage
    cov.stop()
    cov.save()
    
    # Generate report for Phase 1 files only
    print("\nCoverage Report for Phase 1 Components:")
    print("-" * 70)
    
    phase1_files = [
        'vindauga/io/screen_cell.py',
        'vindauga/io/damage_region.py',
        'vindauga/io/fps_limiter.py',
        'vindauga/io/display_buffer.py',
        'vindauga/io/platform_detector.py'
    ]
    
    # Show coverage for each file
    for file in phase1_files:
        try:
            cov.report(include=[file], show_missing=False)
        except:
            pass
    
    print("-" * 70)
    
    # Get total coverage
    try:
        total = cov.report(include=phase1_files, show_missing=False)
        if total >= 80:
            print(f"✅ Phase 1 Coverage: {total:.1f}% (Target: 80% - PASSED)")
        else:
            print(f"⚠️  Phase 1 Coverage: {total:.1f}% (Target: 80% - NEEDS IMPROVEMENT)")
    except:
        print("Unable to calculate total coverage.")


def main():
    """Main entry point."""
    print("=" * 70)
    print("PHASE 1 COMPONENT TEST RUNNER")
    print("TVision I/O Migration - Core Infrastructure")
    print("=" * 70)
    print("\nTesting Phase 1 components:")
    print("  - ScreenCell")
    print("  - DamageRegion")
    print("  - FPSLimiter")
    print("  - DisplayBuffer")
    print("  - PlatformDetector")
    print()
    
    # Run tests
    success = run_phase1_tests()
    
    # Calculate coverage if tests passed
    if success:
        calculate_phase1_coverage()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()