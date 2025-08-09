#!/usr/bin/env python3
"""
Test script to verify that the SimplifiedStagehandTool fixes are working.

This script tests the main issues that were causing errors:
1. AttributeError: '_Null' object has no attribute 'error'
2. Session management and connection issues
3. Error handling improvements
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool

def test_logger_error_method():
    """Test that the logger error method works without AttributeError."""
    print("Testing logger error method...")
    
    tool = SimplifiedStagehandTool()
    
    # This should not raise AttributeError: '_Null' object has no attribute 'error'
    try:
        tool.logger.error("Test error message")
        print("✅ Logger error method works correctly")
        return True
    except AttributeError as e:
        print(f"❌ Logger error method failed: {e}")
        return False

def test_error_detection():
    """Test that error detection patterns work correctly."""
    print("Testing error detection patterns...")
    
    tool = SimplifiedStagehandTool()
    
    # Test various error patterns that should be detected as session errors
    test_errors = [
        "'NoneType' object has no attribute 'stream'",
        "httpx.ReadError",
        "httpx.ReadTimeout", 
        "httpx.ConnectError",
        "connection broken",
        "session closed",
        "browser has been closed"
    ]
    
    all_passed = True
    for error_msg in test_errors:
        test_error = Exception(error_msg)
        if tool._is_session_closed_error(test_error):
            print(f"✅ Correctly detected session error: {error_msg}")
        else:
            print(f"❌ Failed to detect session error: {error_msg}")
            all_passed = False
    
    return all_passed

def test_tool_initialization():
    """Test that the tool initializes without errors."""
    print("Testing tool initialization...")
    
    try:
        tool = SimplifiedStagehandTool()
        
        # Check that error logger is properly initialized
        if hasattr(tool, '_error_logger') and tool._error_logger:
            print("✅ Error logger properly initialized")
        else:
            print("❌ Error logger not properly initialized")
            return False
            
        # Check that logger property works
        logger = tool.logger
        if logger and hasattr(logger, 'error'):
            print("✅ Logger property works correctly")
        else:
            print("❌ Logger property not working")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Tool initialization failed: {e}")
        return False

def test_operation_error_handling():
    """Test that operation error handling works correctly."""
    print("Testing operation error handling...")
    
    tool = SimplifiedStagehandTool()
    
    # Test with invalid operation
    try:
        result = tool._run(operation="invalid_operation")
        if result.startswith("Error:"):
            print("✅ Invalid operation handled correctly")
            return True
        else:
            print(f"❌ Invalid operation not handled correctly: {result}")
            return False
    except Exception as e:
        print(f"❌ Operation error handling failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing SimplifiedStagehandTool fixes...\n")
    
    tests = [
        test_logger_error_method,
        test_error_detection,
        test_tool_initialization,
        test_operation_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}\n")
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The SimplifiedStagehandTool fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
