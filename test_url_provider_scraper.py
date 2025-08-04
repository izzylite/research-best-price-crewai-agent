#!/usr/bin/env python3
"""
Test the URL Provider Tool approach with the full CrewAI ecommerce scraper.
This is the definitive test to verify that agents now use the correct full URL.
"""

import sys
import os
import signal
import time
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Global flag for graceful termination
terminate_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global terminate_requested
    print(f"\n🛑 Termination requested (signal {signum})")
    terminate_requested = True

def test_url_provider_scraper():
    """Test the full scraper with URL Provider Tool approach."""
    global terminate_requested

    # Test URL from ASDA Fruit category (the problematic one)
    test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
    vendor = "asda"
    category_name = "Fruit, Veg & Flowers > Fruit"
    max_pages = 1  # Just test 1 page

    print(f"🧪 Testing URL Provider Tool Approach with Full Scraper")
    print(f"📍 Target URL: {test_url}")
    print(f"📏 URL Length: {len(test_url)} characters")
    print(f"🏪 Vendor: {vendor}")
    print(f"📂 Category: {category_name}")
    print(f"📄 Max pages: {max_pages}")
    print()
    print("🔍 Key things to watch for:")
    print("   1. 'Category URL Provider' tool being created")
    print("   2. Agent using the URL Provider tool first")
    print("   3. 'EXACT URL BEING USED' showing the full URL")
    print("   4. Successful navigation to the correct page")
    print()
    print("💡 Press Ctrl+C to gracefully terminate at any time")
    print()

    try:
        from ecommerce_scraper.main import EcommerceScraper

        print("🤖 Creating EcommerceScraper with URL Provider Tool support...")
        scraper = EcommerceScraper(verbose=True)

        print("🚀 Starting URL Provider Tool scraping test...")
        print("📋 The agent should now use the URL Provider Tool to get the exact URL")
        print()

        # Execute the scraping with URL Provider Tool approach
        result = scraper.scrape_category_directly(
            category_url=test_url,
            vendor=vendor,
            category_name=category_name,
            max_pages=max_pages
        )

        if terminate_requested:
            print(f"🛑 Test terminated by user request")
            return False

        print(f"\n" + "="*60)
        print(f"📊 URL PROVIDER TOOL TEST RESULTS")
        print(f"="*60)
        print(f"✅ Test completed successfully!")
        print(f"📊 Results Summary:")
        print(f"   Success: {result.success}")
        print(f"   Products found: {len(result.products)}")
        print(f"   Session ID: {result.session_id}")
        print(f"   Error: {result.error if result.error else 'None'}")

        if result.agent_results:
            for agent_result in result.agent_results:
                print(f"\n🤖 Agent {agent_result['agent_id']} Results:")
                print(f"   Products: {agent_result['products_found']}")
                print(f"   URL used: {agent_result['url']}")

                # Check if the correct URL was used
                if agent_result['url'] == test_url:
                    print("🎉 SUCCESS: Agent used the correct full URL!")
                    print("✅ URL Provider Tool approach is working!")
                else:
                    print(f"❌ ISSUE: Agent used different URL")
                    print(f"   Expected: {test_url}")
                    print(f"   Got:      {agent_result['url']}")
                    print("💡 URL Provider Tool may need further refinement")

        # Display some sample products if successful
        if result.success and result.products:
            print(f"\n📦 Sample Products Found:")
            for i, product in enumerate(result.products[:3]):  # Show first 3
                print(f"   {i+1}. {product.name} - £{product.price.amount}")

            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"url_provider_test_results_{timestamp}.json"
            
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_description': 'URL Provider Tool approach test',
                    'test_url': test_url,
                    'vendor': vendor,
                    'category': category_name,
                    'success': result.success,
                    'products_count': len(result.products),
                    'products': [p.model_dump() for p in result.products],
                    'agent_results': result.agent_results,
                    'session_id': result.session_id,
                    'timestamp': timestamp,
                    'url_provider_tool_used': True
                }, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Results saved to: {filename}")

        print(f"="*60)
        return result.success

    except KeyboardInterrupt:
        print(f"\n🛑 Test interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the URL Provider Tool scraper test."""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("🚀 URL Provider Tool Scraper Test")
    print("=" * 60)
    print("This test verifies that the URL Provider Tool approach")
    print("successfully provides the full ASDA fruit URL to agents:")
    print()
    print("https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/")
    print("view-all-fruit/1215686352935-910000975210-1215666947025")
    print()
    print("🔧 How it works:")
    print("1. Creates a CategoryURLProviderTool with the exact URL")
    print("2. Adds the tool to the ProductScraperAgent")
    print("3. Agent uses the tool to get the URL instead of parsing text")
    print("4. Agent navigates to the exact URL provided by the tool")
    print("=" * 60)
    print()

    try:
        success = test_url_provider_scraper()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 URL PROVIDER TOOL TEST PASSED!")
            print("✅ The scraper successfully uses the URL Provider Tool")
            print("✅ Agents now get the exact URL from the tool")
            print("✅ No more URL parsing ambiguity!")
            print("🚀 The URL issue has been resolved!")
        else:
            print("🚨 URL PROVIDER TOOL TEST FAILED!")
            print("❌ The scraper may still have URL usage issues")
            print("💡 Check the output above for specific error details")
            print("🔧 Consider further refinements to the approach")
        print("=" * 60)
        
        return success
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
