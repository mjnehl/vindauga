#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner for Phase 1 of the TVision I/O migration.

This script runs all unit tests and calculates code coverage for the
vindauga.io module components.
"""

import sys
import unittest
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run all Phase 1 unit tests."""
    # Discover and run tests
    loader = unittest.TestLoader()
    test_dir = project_root / 'vindauga' / 'io' / 'tests'
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed.")
        
    return result.wasSuccessful()


def calculate_coverage():
    """Calculate test coverage using coverage.py if available."""
    try:
        import coverage
    except ImportError:
        print("\n⚠️  Coverage.py not installed. Install with: pip install coverage")
        print("   Skipping coverage calculation.")
        return
    
    print("\n" + "=" * 70)
    print("CALCULATING COVERAGE")
    print("=" * 70)
    
    # Create coverage instance
    cov = coverage.Coverage(source=['vindauga/io'])
    
    # Start coverage
    cov.start()
    
    # Run tests
    loader = unittest.TestLoader()
    test_dir = project_root / 'vindauga' / 'io' / 'tests'
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=0)
    runner.run(suite)
    
    # Stop coverage
    cov.stop()
    cov.save()
    
    # Generate report
    print("\nCoverage Report:")
    print("-" * 70)
    cov.report()
    
    # Get total coverage
    total = cov.report(show_missing=False)
    
    print("-" * 70)
    if total >= 80:
        print(f"✅ Coverage: {total:.1f}% (Target: 80% - PASSED)")
    else:
        print(f"⚠️  Coverage: {total:.1f}% (Target: 80% - NEEDS IMPROVEMENT)")


def main():
    """Main entry point."""
    print("=" * 70)
    print("PHASE 1 TEST RUNNER")
    print("TVision I/O Migration - Core Infrastructure")
    print("=" * 70)
    
    # Run tests
    success = run_tests()
    
    # Calculate coverage if tests passed
    if success:
        calculate_coverage()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()