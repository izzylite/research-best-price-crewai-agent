#!/usr/bin/env python3
"""Test script for the new dynamic category scraping functionality."""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.main import EcommerceScraper, DynamicScrapingResult

def test_dynamic_scraper_creation():
    """Test that we can create an EcommerceScraper instance."""
    print("🧪 Testing EcommerceScraper creation...")
    
    try:
        scraper = EcommerceScraper(verbose=True)
        print("✅ EcommerceScraper created successfully")
        
        # Test context manager
        with EcommerceScraper(verbose=False) as scraper_cm:
            print("✅ Context manager works")
            
        print("✅ Context manager cleanup completed")
        return True
        
    except Exception as e:
        print(f"❌ Error creating EcommerceScraper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dynamic_scraping_result():
    """Test DynamicScrapingResult creation."""
    print("\n🧪 Testing DynamicScrapingResult creation...")
    
    try:
        # Test successful result
        result = DynamicScrapingResult(
            success=True,
            products=[],
            agent_results=[{
                'agent_id': 1,
                'subcategory': 'test',
                'success': True,
                'products_found': 0,
                'url': 'https://example.com'
            }],
            vendor='test_vendor',
            category='test_category'
        )
        
        print(f"✅ DynamicScrapingResult created: {result.success}")
        print(f"   - Vendor: {result.vendor}")
        print(f"   - Category: {result.category}")
        print(f"   - Products: {result.total_products}")
        print(f"   - Timestamp: {result.timestamp}")
        
        # Test failed result
        failed_result = DynamicScrapingResult(
            success=False,
            error="Test error",
            vendor='test_vendor',
            category='test_category'
        )
        
        print(f"✅ Failed result created: {failed_result.success}")
        print(f"   - Error: {failed_result.error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating DynamicScrapingResult: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scrape_category_directly_interface():
    """Test that the scrape_category_directly method exists and has correct signature."""
    print("\n🧪 Testing scrape_category_directly interface...")
    
    try:
        scraper = EcommerceScraper(verbose=False)
        
        # Check if method exists
        if hasattr(scraper, 'scrape_category_directly'):
            print("✅ scrape_category_directly method exists")
            
            # Check method signature
            import inspect
            sig = inspect.signature(scraper.scrape_category_directly)
            params = list(sig.parameters.keys())
            
            expected_params = ['category_url', 'vendor', 'category_name', 'max_pages']
            
            for param in expected_params:
                if param in params:
                    print(f"✅ Parameter '{param}' found")
                else:
                    print(f"❌ Parameter '{param}' missing")
                    return False
            
            print("✅ Method signature is correct")
            return True
        else:
            print("❌ scrape_category_directly method not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing interface: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Dynamic Category Scraping Implementation")
    print("=" * 60)
    
    tests = [
        test_dynamic_scraper_creation,
        test_dynamic_scraping_result,
        test_scrape_category_directly_interface
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dynamic scraping implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
