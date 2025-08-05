#!/usr/bin/env python3
"""
Test the threading fix for SimplifiedStagehandTool
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

def test_threading_fix():
    """Test that the SimplifiedStagehandTool now works in non-main threads"""
    print("🧪 Testing Threading Fix")
    print("=" * 50)
    
    def run_in_thread():
        """Run tool operations in a separate thread"""
        try:
            from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
            
            print("   1. Creating tool in worker thread...")
            tool = SimplifiedStagehandTool()
            
            print("   2. Testing navigation in worker thread...")
            start_time = time.time()
            nav_result = tool._run(
                operation="navigate",
                url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
            )
            nav_duration = time.time() - start_time
            
            if "Error:" in nav_result:
                print(f"   ❌ Navigation failed: {nav_result}")
                return False
            else:
                print(f"   ✅ Navigation succeeded in {nav_duration:.2f}s")
            
            print("   3. Testing observe in worker thread...")
            start_time = time.time()
            observe_result = tool._run(
                operation="observe",
                instruction="Find any popup dialogs",
                return_action=False
            )
            observe_duration = time.time() - start_time
            
            if "Error:" in observe_result:
                print(f"   ❌ Observe failed: {observe_result}")
                return False
            else:
                print(f"   ✅ Observe succeeded in {observe_duration:.2f}s")
            
            tool.close()
            return True
            
        except Exception as e:
            print(f"   ❌ Thread test failed: {e}")
            return False
    
    # Test in worker thread
    result = None
    exception = None
    
    def thread_wrapper():
        nonlocal result, exception
        try:
            result = run_in_thread()
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=thread_wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout=120)  # 2 minute timeout
    
    if thread.is_alive():
        print("   ❌ THREAD TEST TIMED OUT")
        print("   🔍 Threading fix didn't resolve the hanging issue")
        return False
    elif exception:
        print(f"   ❌ Thread test failed with exception: {exception}")
        return False
    elif result:
        print("   ✅ THREAD TEST SUCCEEDED")
        print("   🎉 SimplifiedStagehandTool now works in worker threads!")
        return True
    else:
        print("   ❌ Thread test returned False")
        return False

def test_crewai_integration():
    """Test that the fix works with CrewAI"""
    print("\n🤖 Testing CrewAI Integration")
    print("=" * 50)
    
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
        
        print("3. Creating crew...")
        crew = Crew(
            agents=[nav_agent.get_agent()],
            tasks=[task],
            verbose=True
        )
        
        print("4. Testing crew execution with timeout...")
        
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
        thread.join(timeout=90)  # 90 second timeout
        
        if thread.is_alive():
            print("   ❌ CREWAI EXECUTION STILL TIMES OUT")
            return False
        elif exception:
            print(f"   ❌ CrewAI execution failed: {exception}")
            return False
        elif result and "Error:" not in str(result):
            print(f"   ✅ CrewAI execution succeeded: {result}")
            return True
        else:
            print(f"   ⚠️ CrewAI execution completed but with issues: {result}")
            return False
        
    except Exception as e:
        print(f"   ❌ CrewAI integration test failed: {e}")
        return False

def main():
    """Test the threading fix"""
    print("🚀 Threading Fix Test")
    print("=" * 60)
    
    # Test threading fix
    threading_success = test_threading_fix()
    
    # Test CrewAI integration (only if threading works)
    crewai_success = False
    if threading_success:
        crewai_success = test_crewai_integration()
    else:
        print("\n⏭️ Skipping CrewAI test - threading fix failed")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 THREADING FIX RESULTS")
    print("=" * 60)
    
    print(f"Threading Fix: {'✅ Working' if threading_success else '❌ Failed'}")
    print(f"CrewAI Integration: {'✅ Working' if crewai_success else '❌ Failed/Skipped'}")
    
    if threading_success and crewai_success:
        print("\n🎉 THREADING ISSUE COMPLETELY FIXED!")
        print("   The Navigation Agent should no longer get stuck!")
        print("   Try running the scraper again - it should work now!")
    elif threading_success:
        print("\n🔧 THREADING PARTIALLY FIXED")
        print("   Tool works in threads, but CrewAI integration still has issues")
    else:
        print("\n🔧 THREADING FIX FAILED")
        print("   The tool still has threading/signal issues")
    
    return threading_success and crewai_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
