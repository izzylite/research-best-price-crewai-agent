#!/usr/bin/env python3
"""
Test script to verify that the AI agent uses the correct starting URL.
"""

import os
import sys
import json
import signal
import threading
from pathlib import Path
from datetime import datetime
from ecommerce_scraper.main import EcommerceScraper

def save_results_to_directory(result, vendor, category_name):
    """Save scraped results to organized directory structure."""
    if not result.products:
        print("📭 No products to save")
        return None

    # Create directory structure: scrapped-result/vendor/category/
    base_dir = Path("scrapped-result")
    vendor_dir = base_dir / vendor.lower()

    # Clean category name for directory (remove special characters)
    clean_category = category_name.replace(" > ", "_").replace(" ", "_").replace(",", "").replace("&", "and")
    category_dir = vendor_dir / clean_category

    # Create directories if they don't exist
    category_dir.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"products_{timestamp}.json"
    filepath = category_dir / filename

    # Convert products to dictionaries and save
    products_data = {
        "scraping_info": {
            "vendor": vendor,
            "category": category_name,
            "scraped_at": datetime.now().isoformat(),
            "session_id": result.session_id,
            "total_products": len(result.products),
            "success": result.success
        },
        "products": [product.to_dict() for product in result.products]
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(products_data, f, indent=2, ensure_ascii=False)

    print(f"📁 Results saved to: {filepath}")
    print(f"📊 Saved {len(result.products)} products")
    return filepath


def test_url_fix():
    """Test that the scraper uses the correct category URL."""

    # Test URL from ASDA Fruit category
    test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/raw-nuts-seeds-dried-fruit/view-all-raw-nuts-seeds-dried-fruit/1215686352935-1215686353950-1215686355742"
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

            # Save results to organized directory structure
            if result.success and result.products:
                save_results_to_directory(result, vendor, category_name)

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
