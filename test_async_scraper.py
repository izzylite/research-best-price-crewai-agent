#!/usr/bin/env python3
"""Test script for async concurrent scraper."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from ecommerce_scraper.concurrent.async_scraper import scrape_multiple_urls


async def test_concurrent_scraping():
    """Test concurrent scraping with multiple URLs."""
    print("🧪 Testing Async Concurrent Scraper")
    print("=" * 50)
    
    # Test URLs from demo.vercel.store
    test_urls = [
        {
            "url": "https://demo.vercel.store/products/acme-mug",
            "vendor": "demo",
            "category": "mugs"
        },
        {
            "url": "https://demo.vercel.store/products/acme-circles-t-shirt", 
            "vendor": "demo",
            "category": "shirts"
        },
        {
            "url": "https://demo.vercel.store/products/acme-drawstring-bag",
            "vendor": "demo", 
            "category": "bags"
        }
    ]
    
    print(f"📋 Testing {len(test_urls)} URLs concurrently...")
    print(f"🔧 Max concurrent: 2, Max per vendor: 1")
    print()
    
    try:
        # Run concurrent scraping
        results = await scrape_multiple_urls(
            test_urls,
            max_concurrent=2,
            max_per_vendor=1
        )
        
        # Display results
        print("📊 Results:")
        print("-" * 30)
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        total_products = sum(len(r.products) for r in successful)
        
        print(f"✅ Successful: {len(successful)}/{len(results)}")
        print(f"❌ Failed: {len(failed)}")
        print(f"📦 Total products: {total_products}")
        print()
        
        # Show individual results
        for result in results:
            status = "✅" if result.success else "❌"
            duration = f"{result.duration:.1f}s" if result.duration else "N/A"
            products_count = len(result.products) if result.success else 0
            
            print(f"{status} {result.url}")
            print(f"   Vendor: {result.vendor}, Category: {result.category}")
            print(f"   Products: {products_count}, Duration: {duration}")
            
            if not result.success and result.error:
                print(f"   Error: {result.error}")
            print()
        
        # Test summary
        if len(successful) == len(test_urls):
            print("🎉 All tests passed! Async concurrent scraping works correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the errors above.")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test."""
    print("🚀 Starting Async Concurrent Scraper Test")
    print()
    
    # Check if we're in the main thread
    import threading
    if threading.current_thread() is not threading.main_thread():
        print("❌ Error: This test must run in the main thread")
        return False
    
    # Run the async test
    success = asyncio.run(test_concurrent_scraping())
    
    if success:
        print("\n✅ Test completed successfully!")
        print("💡 You can now replace BatchProcessor with AsyncConcurrentScraper")
    else:
        print("\n❌ Test failed!")
        print("🔧 Check the errors above and fix any issues")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
