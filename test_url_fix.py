#!/usr/bin/env python3
"""
Test script to verify that the AI agent uses the correct starting URL.
"""

import os
import sys
from ecommerce_scraper.main import EcommerceScraper

def test_url_fix():
    """Test that the scraper uses the correct category URL."""
    
    # Test URL from ASDA Fruit category
    test_url = "https://groceries.asda.com/dept/fruit-veg-salad/fruit/1215686352935-910000975210"
    vendor = "asda"
    category_name = "Fruit, Veg & Flowers > Fruit"
    max_pages = 1  # Just test 1 page
    
    print(f"🧪 Testing URL fix...")
    print(f"📍 Expected starting URL: {test_url}")
    print(f"🏪 Vendor: {vendor}")
    print(f"📂 Category: {category_name}")
    print(f"📄 Max pages: {max_pages}")
    print()
    
    try:
        with EcommerceScraper(verbose=True) as scraper:
            print("🚀 Starting scrape_category_directly test...")
            result = scraper.scrape_category_directly(
                category_url=test_url,
                vendor=vendor,
                category_name=category_name,
                max_pages=max_pages
            )
            
            print(f"✅ Test completed!")
            print(f"📊 Products found: {len(result.products)}")
            print(f"🎯 Success: {result.success}")
            print(f"📋 Session ID: {result.session_id}")
            
            if result.agent_results:
                for agent_result in result.agent_results:
                    print(f"🤖 Agent {agent_result['agent_id']}: {agent_result['products_found']} products")
                    print(f"🔗 URL used: {agent_result['url']}")
                    
                    # Check if the correct URL was used
                    if agent_result['url'] == test_url:
                        print("✅ CORRECT: Agent used the expected category URL!")
                    else:
                        print(f"❌ WRONG: Agent used {agent_result['url']} instead of {test_url}")
            
            return result.success
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_url_fix()
    if success:
        print("\n🎉 URL fix test PASSED!")
        sys.exit(0)
    else:
        print("\n💥 URL fix test FAILED!")
        sys.exit(1)
