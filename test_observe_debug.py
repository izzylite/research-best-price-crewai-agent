#!/usr/bin/env python3
"""
Debug the observe operation issue by testing different calling patterns
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_direct_tool_call():
    """Test calling the tool directly with different parameter formats."""
    print("🔍 Testing Direct Tool Call Patterns")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        print("1. Testing navigation first...")
        nav_result = tool._run(operation="navigate", url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        print(f"   Navigation result: {nav_result[:100]}...")
        
        print("\n2. Testing observe with kwargs...")
        observe_result = tool._run(
            operation="observe",
            instruction="Find cookie banner or modal dialog",
            return_action=False
        )
        print(f"   Observe result: {observe_result[:100]}...")
        
        print("\n3. Testing observe with dict format (like CrewAI)...")
        # Simulate how CrewAI might call the tool
        kwargs = {
            "operation": "observe",
            "instruction": "Find cookie banner or modal dialog",
            "return_action": False
        }
        observe_result2 = tool._run(**kwargs)
        print(f"   Observe result 2: {observe_result2[:100]}...")
        
        print("\n4. Testing observe method directly...")
        import asyncio
        import nest_asyncio
        
        # Handle event loop
        try:
            loop = asyncio.get_running_loop()
            nest_asyncio.apply(loop)
            run_async = loop.run_until_complete
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            run_async = loop.run_until_complete
        
        direct_result = run_async(tool.observe("Find cookie banner or modal dialog", False))
        print(f"   Direct observe result: {direct_result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_crewai_simulation():
    """Simulate how CrewAI calls the tool."""
    print("\n🤖 Testing CrewAI Simulation")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        # Navigate first
        print("1. Navigation...")
        tool._run(operation="navigate", url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        
        # Simulate CrewAI tool call format
        print("2. Simulating CrewAI tool call...")
        
        # This is how CrewAI calls tools based on the logs
        tool_input = '{"operation": "observe", "instruction": "Find cookie banner or modal dialog"}'
        parsed_input = json.loads(tool_input)
        
        print(f"   Parsed input: {parsed_input}")
        print(f"   Input type: {type(parsed_input)}")
        print(f"   Instruction: '{parsed_input.get('instruction', 'NOT_FOUND')}'")
        print(f"   Instruction type: {type(parsed_input.get('instruction', 'NOT_FOUND'))}")
        
        # Call tool with parsed input
        result = tool._run(**parsed_input)
        print(f"   Result: {result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ CrewAI simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_extraction():
    """Test parameter extraction in _execute_operation."""
    print("\n🔧 Testing Parameter Extraction")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        # Test different kwargs formats
        test_cases = [
            {"operation": "observe", "instruction": "Find cookie banner"},
            {"operation": "observe", "instruction": "Find cookie banner", "return_action": False},
            {"operation": "observe", "instruction": "Find cookie banner", "return_action": True},
        ]
        
        for i, kwargs in enumerate(test_cases, 1):
            print(f"{i}. Testing kwargs: {kwargs}")
            
            # Extract parameters like _execute_operation does
            operation = kwargs.get("operation", "")
            instruction = kwargs.get("instruction", "")
            return_action = kwargs.get("return_action", False)
            
            print(f"   operation: '{operation}' (type: {type(operation)})")
            print(f"   instruction: '{instruction}' (type: {type(instruction)}, len: {len(instruction)})")
            print(f"   return_action: {return_action} (type: {type(return_action)})")
            print(f"   instruction empty check: {not instruction}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Parameter extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all debug tests."""
    print("🚀 Observe Operation Debug Suite")
    print("=" * 70)
    
    # Test 1: Direct tool calls
    test1_success = test_direct_tool_call()
    
    # Test 2: CrewAI simulation
    test2_success = test_crewai_simulation()
    
    # Test 3: Parameter extraction
    test3_success = test_parameter_extraction()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DEBUG SUMMARY")
    print("=" * 70)
    
    print(f"Direct tool call: {'✅ Success' if test1_success else '❌ Failed'}")
    print(f"CrewAI simulation: {'✅ Success' if test2_success else '❌ Failed'}")
    print(f"Parameter extraction: {'✅ Success' if test3_success else '❌ Failed'}")
    
    if all([test1_success, test2_success, test3_success]):
        print("\n🎉 ALL TESTS PASSED - Observe operation should work correctly")
    else:
        print("\n❌ SOME TESTS FAILED - Issue identified for debugging")

if __name__ == "__main__":
    main()
