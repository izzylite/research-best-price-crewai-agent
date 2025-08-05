#!/usr/bin/env python3
"""
Minimal test to isolate the observe parameter issue
"""

import os
import sys
import asyncio
import nest_asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_observe_parameter_flow():
    """Test the exact parameter flow in observe method."""
    print("🔍 Testing Observe Parameter Flow")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        # Test the exact parameter flow
        print("1. Testing direct observe method call...")
        
        # Handle event loop
        try:
            loop = asyncio.get_running_loop()
            nest_asyncio.apply(loop)
            run_async = loop.run_until_complete
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            run_async = loop.run_until_complete
        
        # Test with the exact instruction that's failing
        instruction = "Find cookie banner or modal dialog"
        print(f"2. Calling observe with instruction: '{instruction}' (len: {len(instruction)})")
        
        # Call observe directly
        try:
            result = run_async(tool.observe(instruction, False))
            print(f"3. ✅ Direct observe call succeeded: {result[:100]}...")
        except Exception as e:
            print(f"3. ❌ Direct observe call failed: {e}")
            
        # Test through _run method
        print("\n4. Testing through _run method...")
        try:
            result = tool._run(operation="observe", instruction=instruction, return_action=False)
            print(f"5. ✅ _run observe call succeeded: {result[:100]}...")
        except Exception as e:
            print(f"5. ❌ _run observe call failed: {e}")
            
        # Test parameter extraction
        print("\n6. Testing parameter extraction...")
        kwargs = {"operation": "observe", "instruction": instruction, "return_action": False}
        
        # Extract parameters like _execute_operation does
        operation = kwargs.get("operation", "")
        extracted_instruction = kwargs.get("instruction", "")
        return_action = kwargs.get("return_action", False)
        
        print(f"   operation: '{operation}'")
        print(f"   instruction: '{extracted_instruction}' (len: {len(extracted_instruction)})")
        print(f"   return_action: {return_action}")
        print(f"   instruction empty check: {not extracted_instruction}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the minimal test."""
    print("🚀 Minimal Observe Parameter Test")
    print("=" * 70)
    
    success = test_observe_parameter_flow()
    
    print("\n" + "=" * 70)
    print("📊 TEST RESULT")
    print("=" * 70)
    
    if success:
        print("✅ Test completed - check output for parameter flow details")
    else:
        print("❌ Test failed - parameter flow issue identified")

if __name__ == "__main__":
    main()
