#!/usr/bin/env python3
"""
Test the session sharing fix for SimplifiedStagehandTool
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_session_sharing_fix():
    """Test that the SimplifiedStagehandTool properly uses session_id parameter"""
    
    print("🧪 Testing SimplifiedStagehandTool Session Sharing Fix")
    print("=" * 60)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        # Test 1: Create tool without session_id (should create new session)
        print("\n1. Testing tool creation without session_id...")
        tool1 = SimplifiedStagehandTool()
        print(f"   Tool1 session_id: {tool1.session_id}")
        
        # Test 2: Create tool with session_id (should reuse session)
        print("\n2. Testing tool creation with session_id...")
        test_session_id = "test-session-123"
        tool2 = SimplifiedStagehandTool(session_id=test_session_id)
        print(f"   Tool2 session_id: {tool2.session_id}")
        print(f"   Expected: {test_session_id}")
        print(f"   Match: {tool2.session_id == test_session_id}")
        
        # Test 3: Check that the session_id is passed to Stagehand config
        print("\n3. Testing Stagehand initialization with session_id...")
        
        # Mock the Stagehand initialization to see if session_id is passed
        original_stagehand = None
        stagehand_config_used = None
        
        # Monkey patch Stagehand to capture config
        def mock_stagehand(**config):
            nonlocal stagehand_config_used
            stagehand_config_used = config
            print(f"   Stagehand called with config keys: {list(config.keys())}")
            if 'browserbase_session_id' in config:
                print(f"   ✅ browserbase_session_id found: {config['browserbase_session_id']}")
            else:
                print(f"   ❌ browserbase_session_id NOT found in config")
            
            # Return a mock object
            class MockStagehand:
                async def init(self):
                    pass
                @property
                def session_id(self):
                    return config.get('browserbase_session_id', 'new-session-456')
            
            return MockStagehand()
        
        # Apply monkey patch
        import ecommerce_scraper.tools.simplified_stagehand_tool as tool_module
        if hasattr(tool_module, 'Stagehand'):
            original_stagehand = tool_module.Stagehand
        
        # Import and patch Stagehand
        from stagehand import Stagehand
        original_stagehand = Stagehand
        tool_module.Stagehand = mock_stagehand
        
        # Test with session_id
        tool3 = SimplifiedStagehandTool(session_id="test-session-456")
        await tool3._get_stagehand()
        
        # Restore original
        if original_stagehand:
            tool_module.Stagehand = original_stagehand
        
        print("\n✅ Session sharing fix test completed!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_session_sharing_fix())
