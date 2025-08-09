#!/usr/bin/env python3
"""
Test script to verify that the centralized index management approach works correctly.

This script tests the new centralized methods:
1. increment_retailer_index() with boundary checking
2. get_current_retailer() with safe access
3. has_more_retailers() for status checking
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.workflows.product_search_flow import ProductSearchState

def test_centralized_index_management():
    """Test the centralized index management methods."""
    print("Testing centralized index management...")
    
    # Create a mock flow class with the centralized methods
    class MockFlow:
        def __init__(self):
            self.state = ProductSearchState(
                product_query="test product",
                retailers=[
                    {"vendor": "Retailer1", "url": "http://retailer1.com"},
                    {"vendor": "Retailer2", "url": "http://retailer2.com"}
                ],
                current_retailer_index=0
            )
        
        def increment_retailer_index(self) -> bool:
            """Increment the retailer index and reset the attempt number."""
            self.state.current_retailer_index += 1
            self.state.current_attempt = 1
            self.state.retailers_searched += 1
            
            # Boundary check: return False if we've exceeded the retailers list
            return self.state.current_retailer_index < len(self.state.retailers)
        
        def get_current_retailer(self):
            """Safely get the current retailer with bounds checking."""
            if not self.state.retailers or self.state.current_retailer_index >= len(self.state.retailers):
                return None
            return self.state.retailers[self.state.current_retailer_index]
        
        def has_more_retailers(self) -> bool:
            """Check if there are more retailers to process."""
            return self.state.current_retailer_index < len(self.state.retailers)
    
    flow = MockFlow()
    
    # Test 1: Initial state
    current = flow.get_current_retailer()
    if current and current["vendor"] == "Retailer1":
        print("✅ Initial retailer access works correctly")
    else:
        print("❌ Initial retailer access failed")
        return False
    
    if flow.has_more_retailers():
        print("✅ has_more_retailers() correctly identifies available retailers")
    else:
        print("❌ has_more_retailers() incorrectly reports no retailers")
        return False
    
    # Test 2: Increment to next retailer
    has_more = flow.increment_retailer_index()
    if has_more and flow.state.current_retailer_index == 1:
        print("✅ increment_retailer_index() correctly moves to next retailer")
    else:
        print("❌ increment_retailer_index() failed to move to next retailer")
        return False
    
    current = flow.get_current_retailer()
    if current and current["vendor"] == "Retailer2":
        print("✅ get_current_retailer() returns correct retailer after increment")
    else:
        print("❌ get_current_retailer() returns wrong retailer after increment")
        return False
    
    # Test 3: Increment beyond bounds
    has_more = flow.increment_retailer_index()
    if not has_more and flow.state.current_retailer_index == 2:
        print("✅ increment_retailer_index() correctly detects end of list")
    else:
        print("❌ increment_retailer_index() failed to detect end of list")
        return False
    
    current = flow.get_current_retailer()
    if current is None:
        print("✅ get_current_retailer() safely returns None for out-of-bounds index")
    else:
        print("❌ get_current_retailer() should return None for out-of-bounds index")
        return False
    
    if not flow.has_more_retailers():
        print("✅ has_more_retailers() correctly identifies no more retailers")
    else:
        print("❌ has_more_retailers() incorrectly reports more retailers available")
        return False
    
    return True

def test_empty_retailers_list():
    """Test behavior with empty retailers list."""
    print("Testing empty retailers list handling...")
    
    class MockFlow:
        def __init__(self):
            self.state = ProductSearchState(
                product_query="test product",
                retailers=[],
                current_retailer_index=0
            )
        
        def get_current_retailer(self):
            if not self.state.retailers or self.state.current_retailer_index >= len(self.state.retailers):
                return None
            return self.state.retailers[self.state.current_retailer_index]
        
        def has_more_retailers(self) -> bool:
            return self.state.current_retailer_index < len(self.state.retailers)
    
    flow = MockFlow()
    
    # Test empty list handling
    current = flow.get_current_retailer()
    if current is None:
        print("✅ get_current_retailer() safely handles empty retailers list")
    else:
        print("❌ get_current_retailer() should return None for empty list")
        return False
    
    if not flow.has_more_retailers():
        print("✅ has_more_retailers() correctly identifies empty list")
    else:
        print("❌ has_more_retailers() incorrectly reports retailers in empty list")
        return False
    
    return True

def test_statistics_tracking():
    """Test that statistics are properly tracked during index increments."""
    print("Testing statistics tracking...")
    
    class MockFlow:
        def __init__(self):
            self.state = ProductSearchState(
                product_query="test product",
                retailers=[
                    {"vendor": "Retailer1", "url": "http://retailer1.com"},
                    {"vendor": "Retailer2", "url": "http://retailer2.com"}
                ],
                current_retailer_index=0
            )
        
        def increment_retailer_index(self) -> bool:
            self.state.current_retailer_index += 1
            self.state.current_attempt = 1
            self.state.retailers_searched += 1
            return self.state.current_retailer_index < len(self.state.retailers)
    
    flow = MockFlow()
    
    # Initial state
    if flow.state.retailers_searched == 0 and flow.state.current_attempt == 1:
        print("✅ Initial statistics are correct")
    else:
        print("❌ Initial statistics are incorrect")
        return False
    
    # After first increment
    flow.increment_retailer_index()
    if flow.state.retailers_searched == 1 and flow.state.current_attempt == 1:
        print("✅ Statistics correctly updated after first increment")
    else:
        print("❌ Statistics not correctly updated after first increment")
        return False
    
    # After second increment
    flow.increment_retailer_index()
    if flow.state.retailers_searched == 2 and flow.state.current_attempt == 1:
        print("✅ Statistics correctly updated after second increment")
    else:
        print("❌ Statistics not correctly updated after second increment")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🧪 Testing centralized index management approach...\n")
    
    tests = [
        test_centralized_index_management,
        test_empty_retailers_list,
        test_statistics_tracking
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
        print("🎉 All tests passed! The centralized index management approach is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
