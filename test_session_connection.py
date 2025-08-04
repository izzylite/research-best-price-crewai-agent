#!/usr/bin/env python3
"""
Test script to verify that Stagehand session connections remain stable.
This tests the root cause fix for the "'NoneType' object has no attribute 'send'" error.
"""

import sys
import os
import time
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
from ecommerce_scraper.config.settings import settings

def test_session_stability():
    """Test that the session connection remains stable across multiple operations."""
    print("🧪 Testing Stagehand Session Connection Stability")
    print("=" * 60)
    
    # Setup logging to see detailed output
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Create tool instance
        print("\n1. Creating Stagehand tool...")
        tool = EcommerceStagehandTool()
        
        # Test 1: Initial navigation
        print("\n2. Testing initial navigation...")
        result = tool._run(
            instruction="Navigate to the demo store",
            url="https://demo.vercel.store",
            command_type="act"
        )
        print(f"   ✅ Navigation result: {result[:100]}...")
        
        # Test 2: Multiple operations on the same session
        print("\n3. Testing multiple operations on same session...")
        
        # Operation 1: Extract page title
        result1 = tool._run(
            instruction="Extract the page title",
            command_type="extract"
        )
        print(f"   ✅ Extract 1: {result1[:50]}...")
        
        # Operation 2: Observe elements
        result2 = tool._run(
            instruction="Find product links on the page",
            command_type="observe"
        )
        print(f"   ✅ Observe: {result2[:50]}...")
        
        # Operation 3: Another extraction
        result3 = tool._run(
            instruction="Extract product information",
            command_type="extract"
        )
        print(f"   ✅ Extract 2: {result3[:50]}...")
        
        # Test 3: Navigation to different page
        print("\n4. Testing navigation to different page...")
        result = tool._run(
            instruction="Navigate to products page",
            url="https://demo.vercel.store/products",
            command_type="act"
        )
        print(f"   ✅ Navigation result: {result[:100]}...")
        
        # Test 4: More operations after navigation
        print("\n5. Testing operations after navigation...")
        
        result4 = tool._run(
            instruction="Extract product listings",
            command_type="extract"
        )
        print(f"   ✅ Extract after nav: {result4[:50]}...")
        
        # Test 5: Check session info
        print("\n6. Checking final session info...")
        session_info = tool.get_session_info()
        print(f"   - Has active session: {session_info['has_active_session']}")
        print(f"   - Current URL: {session_info['current_url']}")
        print(f"   - Cache size: {session_info['cache_size']}")
        
        print("\n✅ Session stability test completed successfully!")
        print("🎉 No session disconnection errors occurred!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Session stability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        try:
            tool.close()
            print("\n🧹 Cleanup completed")
        except:
            pass

def test_event_loop_consistency():
    """Test that the same event loop is used across operations."""
    print("\n" + "=" * 60)
    print("🔬 Testing Event Loop Consistency")
    print("=" * 60)
    
    import asyncio
    
    # Track event loop IDs
    loop_ids = []
    
    def track_loop():
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
            loop_ids.append(loop_id)
            print(f"   Event loop ID: {loop_id}")
            return loop_id
        except RuntimeError:
            print("   No running event loop")
            return None
    
    try:
        tool = EcommerceStagehandTool()
        
        print("\n1. Checking event loop before operations...")
        initial_loop = track_loop()
        
        print("\n2. Performing operations and tracking event loops...")
        
        # Override the run_async_safely to track loops
        original_run_async = tool.run_async_safely
        
        def tracking_run_async(coro):
            print(f"   Before async call:")
            track_loop()
            result = original_run_async(coro)
            print(f"   After async call:")
            track_loop()
            return result
        
        # Monkey patch for testing
        import ecommerce_scraper.tools.stagehand_tool as stagehand_module
        stagehand_module.run_async_safely = tracking_run_async
        
        # Test operations
        tool._run(
            instruction="Navigate to demo store",
            url="https://demo.vercel.store",
            command_type="act"
        )
        
        print(f"\n3. Event loop analysis:")
        unique_loops = set(loop_ids)
        print(f"   Total async calls: {len(loop_ids)}")
        print(f"   Unique event loops: {len(unique_loops)}")
        
        if len(unique_loops) == 1:
            print("   ✅ All operations used the same event loop!")
        else:
            print("   ⚠️ Multiple event loops detected - this could cause session issues")
            
        return len(unique_loops) == 1
        
    except Exception as e:
        print(f"❌ Event loop test failed: {e}")
        return False
    finally:
        try:
            tool.close()
        except:
            pass

if __name__ == "__main__":
    success1 = test_session_stability()
    success2 = test_event_loop_consistency()
    
    print("\n" + "=" * 60)
    print("📊 Final Results:")
    print(f"   Session Stability Test: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"   Event Loop Consistency: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! The root cause fix is working!")
    else:
        print("\n⚠️ Some tests failed. Further investigation needed.")
