#!/usr/bin/env python3
"""
Test script to validate Stagehand session recovery functionality.
"""

import sys
import os
import time
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
from ecommerce_scraper.config.settings import settings

def test_session_recovery():
    """Test the session recovery functionality."""
    print("🧪 Testing Stagehand Session Recovery")
    print("=" * 50)
    
    # Setup logging to see detailed output
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Create tool instance
        print("\n1. Creating Stagehand tool...")
        tool = EcommerceStagehandTool()
        
        # Check initial session info
        print("\n2. Initial session info:")
        session_info = tool.get_session_info()
        print(f"   - Has active session: {session_info['has_active_session']}")
        print(f"   - Session working: {session_info.get('session_working', 'Unknown')}")
        print(f"   - Current URL: {session_info['current_url']}")
        
        # Test basic navigation
        print("\n3. Testing basic navigation...")
        result = tool._run(
            instruction="Navigate to the demo store",
            url="https://demo.vercel.store",
            command_type="act"
        )
        print(f"   Navigation result: {result[:100]}...")
        
        # Check session after navigation
        print("\n4. Session info after navigation:")
        session_info = tool.get_session_info()
        print(f"   - Has active session: {session_info['has_active_session']}")
        print(f"   - Session working: {session_info.get('session_working', 'Unknown')}")
        print(f"   - Current URL: {session_info['current_url']}")
        
        # Test session refresh
        print("\n5. Testing manual session refresh...")
        refresh_result = tool.force_session_refresh()
        print(f"   Refresh result: {refresh_result}")
        
        # Check session after refresh
        print("\n6. Session info after refresh:")
        session_info = tool.get_session_info()
        print(f"   - Has active session: {session_info['has_active_session']}")
        print(f"   - Session working: {session_info.get('session_working', 'Unknown')}")
        print(f"   - Current URL: {session_info['current_url']}")
        
        # Test navigation after refresh
        print("\n7. Testing navigation after refresh...")
        result = tool._run(
            instruction="Navigate to the demo store again",
            url="https://demo.vercel.store",
            command_type="act"
        )
        print(f"   Navigation result: {result[:100]}...")
        
        # Test extraction
        print("\n8. Testing product extraction...")
        result = tool._run(
            instruction="Extract product information from the page",
            command_type="extract"
        )
        print(f"   Extraction result: {result[:200]}...")
        
        print("\n✅ Session recovery test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Session recovery test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        try:
            tool.close()
            print("\n🧹 Cleanup completed")
        except:
            pass

if __name__ == "__main__":
    test_session_recovery()
