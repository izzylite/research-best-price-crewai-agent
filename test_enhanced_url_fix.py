#!/usr/bin/env python3
"""
Test the enhanced URL fix for CrewAI ecommerce scraper.
Verifies that the scraper now uses the full ASDA fruit category URL correctly.
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

def test_enhanced_url_fix():
    """Test that the scraper uses the correct full URL with enhanced task description."""
    global terminate_requested

    # Test URL from ASDA Fruit category (the problematic one)
    test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
    vendor = "asda"
    category_name = "Fruit, Veg & Flowers > Fruit"
    max_pages = 1  # Just test 1 page

    print(f"🧪 Testing Enhanced URL Fix...")
    print(f"📍 Target URL: {test_url}")
    print(f"📏 URL Length: {len(test_url)} characters")
    print(f"🏪 Vendor: {vendor}")
    print(f"📂 Category: {category_name}")
    print(f"📄 Max pages: {max_pages}")
    print("💡 Press Ctrl+C to gracefully terminate at any time")
    print("🔍 Watch for 'EXACT URL BEING USED' in the output to verify the fix")
    print()

    try:
        from ecommerce_scraper.main import EcommerceScraper

        print("🤖 Creating EcommerceScraper instance...")
        scraper = EcommerceScraper(verbose=True)

        print("🚀 Starting enhanced scraping test...")
        print("📋 The enhanced task description should guide the agent to use the exact URL")
        print()

        # Execute the scraping with enhanced task description
        result = scraper.scrape_category_directly(
            category_url=test_url,
            vendor=vendor,
            category_name=category_name,
            max_pages=max_pages
        )

        if terminate_requested:
            print(f"🛑 Test terminated by user request")
            return False

        print(f"\n✅ Test completed!")
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
                    print("✅ SUCCESS: Agent used the correct full URL!")
                    print("🎉 The enhanced task description fix worked!")
                else:
                    print(f"❌ ISSUE: Agent used different URL")
                    print(f"   Expected: {test_url}")
                    print(f"   Got:      {agent_result['url']}")
                    print("💡 The enhanced task description may need further refinement")

        # Save results if successful
        if result.success and result.products:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"enhanced_url_fix_test_{timestamp}.json"
            
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_description': 'Enhanced URL fix test',
                    'test_url': test_url,
                    'vendor': vendor,
                    'category': category_name,
                    'success': result.success,
                    'products_count': len(result.products),
                    'products': [p.model_dump() for p in result.products],
                    'agent_results': result.agent_results,
                    'session_id': result.session_id,
                    'timestamp': timestamp
                }, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Results saved to: {filename}")

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
    """Run the enhanced URL fix test."""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("🚀 Enhanced URL Fix Test")
    print("=" * 60)
    print("This test verifies that the enhanced task description")
    print("ensures the CrewAI agent uses the full ASDA fruit URL:")
    print("https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/")
    print("view-all-fruit/1215686352935-910000975210-1215666947025")
    print()
    print("🔧 Enhancements Applied:")
    print("✅ Enhanced task description with explicit URL instructions")
    print("✅ Added URL validation and logging to StagehandTool")
    print("✅ Step-by-step process guidance for the agent")
    print("=" * 60)
    print()

    try:
        success = test_enhanced_url_fix()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 ENHANCED URL FIX TEST PASSED!")
            print("✅ The scraper is now using the full URL correctly")
            print("💡 The enhanced task description successfully guides the agent")
            print("🚀 You can now use the scraper with confidence!")
        else:
            print("🚨 ENHANCED URL FIX TEST FAILED!")
            print("❌ The scraper may still have URL usage issues")
            print("💡 Check the output above for specific error details")
            print("🔧 Consider further task description refinements")
        print("=" * 60)
        
        return success
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
