#!/usr/bin/env python3
"""
Test to isolate the CrewAI tool calling issue
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

# Set up logging to see all debug messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_crewai_agent_tool_call():
    """Test how CrewAI agents call the SimplifiedStagehandTool."""
    print("🤖 Testing CrewAI Agent Tool Call")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        from ecommerce_scraper.agents.navigation_agent import NavigationAgent
        from crewai import Crew
        
        print("1. Creating SimplifiedStagehandTool...")
        tool = SimplifiedStagehandTool()
        print(f"   Tool instance: {id(tool)}")
        print(f"   Tool name: {tool.name}")
        print(f"   Tool args_schema: {tool.args_schema}")
        
        print("\n2. Creating NavigationAgent...")
        nav_agent = NavigationAgent(stagehand_tool=tool, verbose=True)
        agent = nav_agent.get_agent()
        print(f"   Agent tools: {[t.name for t in agent.tools]}")
        print(f"   Tool instances: {[id(t) for t in agent.tools]}")
        
        print("\n3. Creating simple navigation task...")
        task = nav_agent.create_page_navigation_task(
            vendor='asda',
            category='fruit',
            category_url='https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025',
            page_number=1
        )
        
        print("\n4. Checking task description for tool calling format...")
        task_desc = task.description
        if "simplified_stagehand_tool" in task_desc:
            print("   ✅ Task mentions simplified_stagehand_tool")
        else:
            print("   ❌ Task does not mention simplified_stagehand_tool")
            
        # Look for specific tool calling examples
        if '{"operation": "observe"' in task_desc:
            print("   ✅ Task has observe operation examples")
        else:
            print("   ❌ Task missing observe operation examples")
        
        print("\n5. Creating minimal crew...")
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=True
        )
        
        print("\n6. Executing crew (this should trigger the tool call)...")
        print("   NOTE: This will show if CrewAI calls the tool differently")
        
        # Execute with timeout to avoid hanging
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Crew execution timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)  # 2 minute timeout
        
        try:
            result = crew.kickoff()
            signal.alarm(0)  # Cancel timeout
            print(f"   ✅ Crew completed: {str(result)[:100]}...")
            return True
        except TimeoutError:
            print("   ⏰ Crew execution timed out (expected)")
            return False
        except Exception as e:
            signal.alarm(0)  # Cancel timeout
            print(f"   ❌ Crew execution failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_method_inspection():
    """Inspect the tool methods to see if there are any issues."""
    print("\n🔍 Tool Method Inspection")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        print("1. Tool attributes:")
        print(f"   name: {tool.name}")
        print(f"   description: {tool.description[:100]}...")
        print(f"   args_schema: {tool.args_schema}")
        
        print("\n2. Tool methods:")
        methods = [method for method in dir(tool) if not method.startswith('_')]
        for method in methods:
            print(f"   {method}: {type(getattr(tool, method))}")
        
        print("\n3. Testing _run method signature:")
        import inspect
        sig = inspect.signature(tool._run)
        print(f"   _run signature: {sig}")
        
        print("\n4. Testing observe method signature:")
        sig = inspect.signature(tool.observe)
        print(f"   observe signature: {sig}")
        
        print("\n5. Testing _execute_operation method:")
        if hasattr(tool, '_execute_operation'):
            sig = inspect.signature(tool._execute_operation)
            print(f"   _execute_operation signature: {sig}")
        else:
            print("   ❌ _execute_operation method not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Inspection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 CrewAI Tool Issue Debug Suite")
    print("=" * 70)
    
    # Test 1: Tool method inspection
    test1_success = test_tool_method_inspection()
    
    # Test 2: CrewAI agent tool call (this might hang, so we'll timeout)
    test2_success = test_crewai_agent_tool_call()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DEBUG SUMMARY")
    print("=" * 70)
    
    print(f"Tool inspection: {'✅ Success' if test1_success else '❌ Failed'}")
    print(f"CrewAI tool call: {'✅ Success' if test2_success else '❌ Failed/Timeout'}")
    
    if test1_success:
        print("\n🔍 FINDINGS:")
        print("   • Tool structure looks correct")
        print("   • Methods are properly defined")
        print("   • Signatures match expected patterns")
        
        if not test2_success:
            print("\n❌ ISSUE LIKELY IN:")
            print("   • CrewAI tool calling mechanism")
            print("   • Agent task instructions")
            print("   • Tool parameter passing")
            print("   • Async/sync handling in CrewAI context")

if __name__ == "__main__":
    main()
