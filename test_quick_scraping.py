#!/usr/bin/env python3
"""Quick test of the scraping execution with minimal setup."""

import sys
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_interactive_scraper import extract_urls_from_selections, execute_scraping_plan, create_scraping_plan

def test_quick_scraping():
    """Test a quick scraping execution."""
    print("🧪 Testing quick scraping execution...")
    
    # Test data: select ASDA with one category for quick testing
    vendors = ["asda"]
    vendor_categories = {
        "asda": [1]  # Just Rollback category
    }
    
    print(f"Test vendors: {vendors}")
    print(f"Test categories: {vendor_categories}")
    
    try:
        # Step 1: Create scraping plan
        print("\n📋 Creating scraping plan...")
        plan = create_scraping_plan(vendors, vendor_categories, "recent")
        
        print(f"✅ Plan created with session ID: {plan['session_id']}")
        print(f"   Total URLs: {plan['total_urls']}")
        print(f"   Estimated products: {plan['total_estimated_products']}")
        
        # Step 2: Extract URLs
        print("\n🔗 Extracting URLs...")
        scraping_urls = extract_urls_from_selections(vendors, vendor_categories)
        
        print(f"✅ Extracted {len(scraping_urls)} URLs:")
        for url_info in scraping_urls:
            print(f"   • {url_info['category_name']}: {url_info['url']}")
        
        # Step 3: Execute scraping (this will test the actual execution)
        print("\n🚀 Starting scraping execution...")
        execute_scraping_plan(plan, scraping_urls, "recent")
        
        print("\n🎉 Scraping execution completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in quick scraping test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting quick scraping execution test...\n")
    
    success = test_quick_scraping()
    
    print("\n" + "="*60 + "\n")
    
    if success:
        print("🎉 Quick scraping test completed successfully!")
    else:
        print("❌ Quick scraping test failed. Check the output above for details.")
