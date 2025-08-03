#!/usr/bin/env python3
"""
Test the actual scraping functionality with our fixed EcommerceStagehandTool.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_scraping():
    """Test actual product scraping with our fixed implementation."""
    print("🛍️ Testing Product Scraping with Fixed StagehandTool")
    print("=" * 60)
    
    try:
        # Import the scraper
        print("🔧 Importing EcommerceScraper...")
        from ecommerce_scraper.main import EcommerceScraper
        print("✅ Import successful")
        
        # Create scraper instance
        print("\n🔧 Creating scraper instance...")
        scraper = EcommerceScraper(verbose=True)
        print("✅ Scraper created successfully")
        
        # Test with a simple demo site
        test_url = "https://demo.vercel.store/products/acme-circles-t-shirt"
        print(f"\n🌐 Testing scraping with URL: {test_url}")
        
        # Perform the scraping
        result = scraper.scrape_product(test_url)
        
        # Check results
        print(f"\n📊 Scraping Results:")
        print(f"Success: {result.get('success', False)}")
        print(f"URL: {result.get('product_url', 'N/A')}")
        print(f"Site Type: {result.get('site_type', 'N/A')}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        if result.get('data'):
            data_str = str(result['data'])
            print(f"Data preview: {data_str[:300]}...")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"\n❌ Scraping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Product Scraping Test")
    print("=" * 60)
    
    success = test_scraping()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SCRAPING TEST PASSED! The fixed StagehandTool is working!")
    else:
        print("⚠️ SCRAPING TEST FAILED. Check the output above for details.")
    
    sys.exit(0 if success else 1)
