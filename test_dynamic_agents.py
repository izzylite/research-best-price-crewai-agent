#!/usr/bin/env python3
"""Test script for dynamic multi-agent scraping."""

import sys
import threading
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from ecommerce_scraper.dynamic.dynamic_scraper import DynamicMultiAgentScraper


def test_dynamic_scraping():
    """Test the dynamic multi-agent scraping approach."""
    print("🧪 Testing Dynamic Multi-Agent Scraping")
    print("=" * 50)
    
    # Check if we're in main thread
    if threading.current_thread() is not threading.main_thread():
        print("❌ Error: Not in main thread!")
        return False
    
    print("✅ Running in main thread")
    
    # Test with a simple category URL
    test_category_url = "https://demo.vercel.store"
    test_vendor = "demo"
    test_category_name = "all_products"
    
    print(f"🎯 Test Target:")
    print(f"   Vendor: {test_vendor}")
    print(f"   Category: {test_category_name}")
    print(f"   URL: {test_category_url}")
    print()
    
    try:
        # Create dynamic scraper
        scraper = DynamicMultiAgentScraper(max_concurrent_agents=2)
        print("🤖 Created DynamicMultiAgentScraper")
        
        # Test the direct scraping (no discovery needed!)
        print("🚀 Starting direct dynamic scraping...")
        result = scraper.scrape_category_directly(
            category_url=test_category_url,
            vendor=test_vendor,
            category_name=test_category_name
        )
        
        # Display results
        print("\n📊 Results:")
        print("-" * 30)
        
        if result.success:
            print(f"✅ Success!")
            print(f"📦 Products found: {result.total_products}")
            print(f"🤖 Agent results: {len(result.agent_results)}")
            
            if result.agent_results:
                print("\n🤖 Agent Breakdown:")
                for agent_result in result.agent_results:
                    status = "✅" if agent_result['success'] else "❌"
                    print(f"   {status} Agent {agent_result['agent_id']}: {agent_result['subcategory']} ({agent_result['products_found']} products)")
            
            print(f"\n⏰ Completed at: {result.timestamp}")
            return True
        else:
            print(f"❌ Failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_threading_compatibility():
    """Test that the approach doesn't have threading issues."""
    print("\n🧪 Testing Threading Compatibility")
    print("=" * 40)
    
    # This should work without the "signal only works in main thread" error
    try:
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        
        print("🔧 Testing Stagehand tool creation...")
        with EcommerceStagehandTool.create_with_context() as tool:
            print("✅ Stagehand tool created successfully")
            
            # Test a simple operation
            print("🌐 Testing navigation...")
            result = tool._run(
                instruction="Navigate to the homepage",
                url="https://demo.vercel.store",
                command_type="act"
            )
            
            if "Error" not in result:
                print("✅ Navigation test passed")
                return True
            else:
                print(f"❌ Navigation failed: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Threading compatibility test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Dynamic Agent Tests")
    print("=" * 50)
    
    # Test 1: Threading compatibility
    threading_ok = test_threading_compatibility()
    
    if not threading_ok:
        print("\n❌ Threading compatibility failed, skipping dynamic test")
        return False
    
    # Test 2: Dynamic scraping
    dynamic_ok = test_dynamic_scraping()
    
    # Final result
    if threading_ok and dynamic_ok:
        print("\n🎉 All tests passed!")
        print("💡 Dynamic multi-agent approach works correctly")
        print("🔧 CrewAI orchestration avoids threading issues")
        return True
    else:
        print("\n❌ Some tests failed")
        print("🔧 Check the errors above and fix any issues")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
