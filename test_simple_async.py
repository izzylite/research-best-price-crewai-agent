#!/usr/bin/env python3
"""Simple test for async concurrent Stagehand operations."""

import asyncio
import sys
import threading
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool


async def test_single_stagehand():
    """Test a single Stagehand operation."""
    print("🧪 Testing Single Stagehand Operation")
    print("=" * 40)
    
    # Check if we're in main thread
    if threading.current_thread() is not threading.main_thread():
        print("❌ Error: Not in main thread!")
        return False
    
    print("✅ Running in main thread")
    
    try:
        # Create Stagehand tool
        with EcommerceStagehandTool.create_with_context() as tool:
            print("🔧 Created Stagehand tool")
            
            # Test navigation
            result = tool._run(
                instruction="Navigate to the product page",
                url="https://demo.vercel.store/products/acme-mug",
                command_type="act"
            )
            
            print(f"📄 Navigation result: {result}")
            
            if "Error" in result:
                print("❌ Navigation failed")
                return False
            
            # Test extraction
            result = tool._run(
                instruction="Extract product title and price",
                command_type="extract"
            )
            
            print(f"📦 Extraction result: {result}")
            
            if "Error" in result:
                print("❌ Extraction failed")
                return False
            
            print("✅ Single Stagehand test passed!")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_stagehand_sessions():
    """Test multiple concurrent Stagehand sessions."""
    print("\n🧪 Testing Multiple Concurrent Stagehand Sessions")
    print("=" * 50)
    
    urls = [
        "https://demo.vercel.store/products/acme-mug",
        "https://demo.vercel.store/products/acme-circles-t-shirt",
        "https://demo.vercel.store/products/acme-drawstring-bag"
    ]
    
    async def scrape_single_url(url, session_id):
        """Scrape a single URL with its own Stagehand session."""
        print(f"🔄 Session {session_id}: Starting {url}")
        
        try:
            # Each session gets its own Stagehand tool instance
            with EcommerceStagehandTool.create_with_context() as tool:
                # Navigate
                nav_result = tool._run(
                    instruction="Navigate to the product page",
                    url=url,
                    command_type="act"
                )
                
                if "Error" in nav_result:
                    print(f"❌ Session {session_id}: Navigation failed - {nav_result}")
                    return {"session_id": session_id, "url": url, "success": False, "error": nav_result}
                
                # Extract
                extract_result = tool._run(
                    instruction="Extract product title and price",
                    command_type="extract"
                )
                
                if "Error" in extract_result:
                    print(f"❌ Session {session_id}: Extraction failed - {extract_result}")
                    return {"session_id": session_id, "url": url, "success": False, "error": extract_result}
                
                print(f"✅ Session {session_id}: Success!")
                return {
                    "session_id": session_id, 
                    "url": url, 
                    "success": True, 
                    "data": extract_result
                }
                
        except Exception as e:
            print(f"❌ Session {session_id}: Exception - {e}")
            return {"session_id": session_id, "url": url, "success": False, "error": str(e)}
    
    # Run sessions concurrently
    print(f"🚀 Starting {len(urls)} concurrent sessions...")
    
    tasks = [scrape_single_url(url, i+1) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful = 0
    failed = 0
    
    print("\n📊 Results:")
    print("-" * 30)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Exception: {result}")
            failed += 1
        elif result["success"]:
            print(f"✅ Session {result['session_id']}: {result['url']}")
            successful += 1
        else:
            print(f"❌ Session {result['session_id']}: {result['url']} - {result['error']}")
            failed += 1
    
    print(f"\n📈 Summary: {successful} successful, {failed} failed")
    
    return successful > 0 and failed == 0


async def main():
    """Run all tests."""
    print("🚀 Starting Async Stagehand Tests")
    print("=" * 50)
    
    # Check main thread
    if threading.current_thread() is not threading.main_thread():
        print("❌ Error: Tests must run in main thread")
        return False
    
    # Test 1: Single operation
    test1_success = await test_single_stagehand()
    
    if not test1_success:
        print("\n❌ Single test failed, skipping concurrent test")
        return False
    
    # Test 2: Multiple concurrent sessions
    test2_success = await test_multiple_stagehand_sessions()
    
    # Final result
    if test1_success and test2_success:
        print("\n🎉 All tests passed!")
        print("💡 Async concurrent Stagehand operations work correctly")
        print("🔧 You can safely replace BatchProcessor with async approach")
        return True
    else:
        print("\n❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
