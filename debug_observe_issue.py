#!/usr/bin/env python3
"""
Debug the observe operation parameter passing issue
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_parameter_passing():
    """Debug how parameters are passed to the observe operation"""
    print("🔍 Debugging Observe Operation Parameter Passing")
    print("=" * 60)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        print("1. Testing direct parameter passing...")
        
        # Test 1: Direct kwargs
        print("   Test 1a: Direct kwargs")
        try:
            result = tool._run(
                operation="observe",
                instruction="Find any popup dialogs",
                return_action=False
            )
            print(f"   ✅ Direct kwargs worked: {result[:100]}...")
        except Exception as e:
            print(f"   ❌ Direct kwargs failed: {e}")
        
        # Test 2: Simulate CrewAI JSON string format
        print("   Test 1b: CrewAI JSON string format")
        import json
        json_params = json.dumps({
            "operation": "observe",
            "instruction": "Find any popup dialogs",
            "return_action": False
        })
        
        try:
            result = tool._run(json_params)
            print(f"   ✅ JSON string worked: {result[:100]}...")
        except Exception as e:
            print(f"   ❌ JSON string failed: {e}")
        
        # Test 3: Check what parameters are actually received
        print("\n2. Debugging parameter extraction...")
        
        # Monkey patch the _run method to see what parameters it receives
        original_run = tool._run
        
        def debug_run(*args, **kwargs):
            print(f"   📥 Received args: {args}")
            print(f"   📥 Received kwargs: {kwargs}")
            
            # Check if args contains JSON
            if args and len(args) == 1 and isinstance(args[0], str):
                try:
                    parsed = json.loads(args[0])
                    print(f"   📥 Parsed JSON: {parsed}")
                except:
                    print(f"   📥 Not JSON: {args[0][:100]}...")
            
            return original_run(*args, **kwargs)
        
        tool._run = debug_run
        
        print("   Test 2a: Debug direct call")
        try:
            tool._run(operation="observe", instruction="Test instruction", return_action=False)
        except Exception as e:
            print(f"   ❌ Debug direct call failed: {e}")
        
        print("   Test 2b: Debug JSON call")
        try:
            tool._run('{"operation": "observe", "instruction": "Test instruction", "return_action": false}')
        except Exception as e:
            print(f"   ❌ Debug JSON call failed: {e}")
        
        # Restore original method
        tool._run = original_run
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_observe_method_directly():
    """Test the observe method directly to see if it works"""
    print("\n🎯 Testing Observe Method Directly")
    print("=" * 60)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        # Navigate first
        print("1. Navigating to ASDA...")
        tool._run(operation="navigate", url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        
        print("2. Testing _observe_sync method directly...")
        try:
            result = tool._observe_sync("Find any popup dialogs or modal windows", False)
            print(f"   ✅ Direct _observe_sync worked: {result[:100]}...")
        except Exception as e:
            print(f"   ❌ Direct _observe_sync failed: {e}")
        
        print("3. Testing legacy observe method...")
        try:
            result = tool.observe("Find any popup dialogs or modal windows", False)
            print(f"   ✅ Legacy observe worked: {result[:100]}...")
        except Exception as e:
            print(f"   ❌ Legacy observe failed: {e}")
        
        tool.close()
        return True
        
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run debug tests"""
    print("🚀 SimplifiedStagehandTool Observe Debug")
    print("=" * 70)
    
    # Debug parameter passing
    param_success = debug_parameter_passing()
    
    # Test direct method calls
    direct_success = test_observe_method_directly()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DEBUG SUMMARY")
    print("=" * 70)
    
    print(f"Parameter Passing: {'✅ Success' if param_success else '❌ Failed'}")
    print(f"Direct Method Calls: {'✅ Success' if direct_success else '❌ Failed'}")
    
    if not param_success:
        print("\n🔧 PARAMETER PASSING ISSUE DETECTED")
        print("   The observe operation is not receiving the instruction parameter correctly.")
        print("   This explains why the Navigation Agent is stuck.")
    
    return param_success and direct_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
