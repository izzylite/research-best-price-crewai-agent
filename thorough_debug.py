#!/usr/bin/env python3
"""
Thorough debug of the Navigation Agent stuck issue
"""

import os
import sys
import time
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tool_isolation():
    """Test the SimplifiedStagehandTool in complete isolation"""
    print("🔧 Phase 1: Testing SimplifiedStagehandTool Isolation")
    print("=" * 60)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        print("1. Creating tool...")
        tool = SimplifiedStagehandTool()
        
        print("2. Testing navigation...")
        start_time = time.time()
        nav_result = tool._run(
            operation="navigate",
            url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        )
        nav_duration = time.time() - start_time
        print(f"   ✅ Navigation: {nav_duration:.2f}s - {nav_result[:50]}...")
        
        print("3. Testing observe (what likely hangs)...")
        start_time = time.time()
        observe_result = tool._run(
            operation="observe",
            instruction="Find any popup dialogs",
            return_action=False
        )
        observe_duration = time.time() - start_time
        print(f"   ✅ Observe: {observe_duration:.2f}s - {len(observe_result)} chars")
        
        print("4. Testing act...")
        start_time = time.time()
        act_result = tool._run(
            operation="act",
            action="Click any 'Accept' button if visible"
        )
        act_duration = time.time() - start_time
        print(f"   ✅ Act: {act_duration:.2f}s - {act_result}")
        
        tool.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Tool isolation failed: {e}")
        return False

def test_agent_isolation():
    """Test the Navigation Agent without CrewAI Flow"""
    print("\n🤖 Phase 2: Testing Navigation Agent Isolation")
    print("=" * 60)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        from ecommerce_scraper.agents.navigation_agent import NavigationAgent
        from crewai import Crew
        
        print("1. Creating components...")
        tool = SimplifiedStagehandTool()
        nav_agent = NavigationAgent(stagehand_tool=tool, verbose=True)
        
        print("2. Creating simple task...")
        task = nav_agent.create_page_navigation_task(
            vendor='asda',
            category='fruit',
            category_url='https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025',
            page_number=1
        )
        
        print("3. Creating simple crew (not Flow)...")
        crew = Crew(
            agents=[nav_agent.get_agent()],
            tasks=[task],
            verbose=True
        )
        
        print("4. Testing crew execution with timeout...")
        
        # Use threading to implement timeout
        result = None
        exception = None
        
        def run_crew():
            nonlocal result, exception
            try:
                result = crew.kickoff()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=run_crew)
        thread.daemon = True
        thread.start()
        thread.join(timeout=60)  # 60 second timeout
        
        if thread.is_alive():
            print("   ❌ CREW EXECUTION TIMED OUT (60s)")
            print("   🔍 The agent is stuck in CrewAI execution, not tool operations")
            return False
        elif exception:
            print(f"   ❌ Crew execution failed: {exception}")
            return False
        elif result:
            print(f"   ✅ Crew execution succeeded: {result}")
            return True
        else:
            print("   ❌ Crew execution returned no result")
            return False
        
    except Exception as e:
        print(f"   ❌ Agent isolation failed: {e}")
        return False

def test_crewai_basic():
    """Test basic CrewAI functionality"""
    print("\n⚙️ Phase 3: Testing Basic CrewAI Functionality")
    print("=" * 60)
    
    try:
        from crewai import Agent, Task, Crew
        
        print("1. Creating simple agent...")
        simple_agent = Agent(
            role="Test Agent",
            goal="Complete a simple task",
            backstory="A simple test agent",
            verbose=True,
            allow_delegation=False,
            max_iter=2
        )
        
        print("2. Creating simple task...")
        simple_task = Task(
            description="Say 'Hello World' and return success status",
            agent=simple_agent,
            expected_output="A simple greeting message"
        )
        
        print("3. Testing basic crew...")
        crew = Crew(
            agents=[simple_agent],
            tasks=[simple_task],
            verbose=True
        )
        
        # Test with timeout
        result = None
        exception = None
        
        def run_simple_crew():
            nonlocal result, exception
            try:
                result = crew.kickoff()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=run_simple_crew)
        thread.daemon = True
        thread.start()
        thread.join(timeout=30)  # 30 second timeout
        
        if thread.is_alive():
            print("   ❌ BASIC CREWAI TIMED OUT")
            print("   🔍 CrewAI itself has issues")
            return False
        elif exception:
            print(f"   ❌ Basic CrewAI failed: {exception}")
            return False
        else:
            print(f"   ✅ Basic CrewAI works: {result}")
            return True
        
    except Exception as e:
        print(f"   ❌ Basic CrewAI test failed: {e}")
        return False

def main():
    """Run thorough debug"""
    print("🚀 THOROUGH DEBUG: Navigation Agent Stuck Issue")
    print("=" * 70)
    
    # Phase 1: Test tool isolation
    tool_success = test_tool_isolation()
    
    # Phase 2: Test agent isolation (only if tools work)
    agent_success = False
    if tool_success:
        agent_success = test_agent_isolation()
    else:
        print("\n⏭️ Skipping agent test - tool issues detected")
    
    # Phase 3: Test basic CrewAI
    crewai_success = test_crewai_basic()
    
    # Analysis
    print("\n" + "=" * 70)
    print("📊 DEBUG ANALYSIS")
    print("=" * 70)
    
    print(f"Tool Operations: {'✅ Working' if tool_success else '❌ Failed'}")
    print(f"Agent Execution: {'✅ Working' if agent_success else '❌ Failed/Skipped'}")
    print(f"Basic CrewAI: {'✅ Working' if crewai_success else '❌ Failed'}")
    
    # Diagnosis
    if not tool_success:
        print("\n🔧 DIAGNOSIS: SimplifiedStagehandTool has issues")
        print("   The tool operations are failing or hanging")
    elif not crewai_success:
        print("\n🔧 DIAGNOSIS: CrewAI framework has issues")
        print("   Basic CrewAI execution is failing or hanging")
    elif not agent_success:
        print("\n🔧 DIAGNOSIS: Navigation Agent + CrewAI integration issues")
        print("   Tools work, basic CrewAI works, but agent execution hangs")
    else:
        print("\n🎉 DIAGNOSIS: All components work individually")
        print("   The issue is likely in the Flow architecture or complex task setup")
    
    return tool_success and agent_success and crewai_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
