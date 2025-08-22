#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run all Phase 1 and Phase 2 tests for the TVision I/O migration.
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    """Run all tests and report results."""
    # Create test loader
    loader = unittest.TestLoader()
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add Phase 1 tests
    suite.addTests(loader.loadTestsFromModule(__import__('vindauga.io.tests.test_screen_cell', fromlist=[''])))
    suite.addTests(loader.loadTestsFromModule(__import__('vindauga.io.tests.test_damage_region', fromlist=[''])))
    suite.addTests(loader.loadTestsFromModule(__import__('vindauga.io.tests.test_fps_limiter', fromlist=[''])))
    suite.addTests(loader.loadTestsFromModule(__import__('vindauga.io.tests.test_display_buffer', fromlist=[''])))
    suite.addTests(loader.loadTestsFromModule(__import__('vindauga.io.tests.test_platform_detector', fromlist=[''])))
    
    # Add Phase 2 tests
    suite.addTests(loader.loadTestsFromModule(__import__('vindauga.io.tests.test_phase2_backends', fromlist=[''])))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TVision I/O Migration Test Summary")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total_tests - failures - errors - skipped
    
    print(f"Total Tests: {total_tests}")
    print(f"  ✓ Passed: {passed}")
    print(f"  ✗ Failed: {failures}")
    print(f"  ⚠ Errors: {errors}")
    print(f"  ⊘ Skipped: {skipped}")
    
    # Calculate success rate
    if total_tests > 0:
        success_rate = (passed / total_tests) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        # Check if we meet 80% requirement
        if success_rate >= 80:
            print("✅ Meets 80% test pass requirement")
        else:
            print("❌ Does not meet 80% test pass requirement")
    
    print("\nPhase 1 Tests: 65")
    print("Phase 2 Tests: 22")
    print("Total Tests: 87")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)