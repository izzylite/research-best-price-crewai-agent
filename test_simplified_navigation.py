#!/usr/bin/env python3
"""
Test the simplified Navigation Agent
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simplified_navigation():
    """Test that the Navigation Agent instructions are now simplified"""
    print("🧪 Testing Simplified Navigation Agent")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        from ecommerce_scraper.agents.navigation_agent import NavigationAgent
        
        print("1. Creating SimplifiedStagehandTool...")
        tool = SimplifiedStagehandTool()
        print("   ✅ Tool created")
        
        print("2. Creating NavigationAgent...")
        nav_agent = NavigationAgent(stagehand_tool=tool, verbose=True)
        print("   ✅ Agent created")
        
        print("3. Creating navigation task...")
        task = nav_agent.create_page_navigation_task(
            vendor='asda',
            category='fruit',
            category_url='https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025',
            page_number=1
        )
        
        print("4. Checking task description length...")
        description_length = len(task.description)
        print(f"   📏 Task description: {description_length} characters")
        
        # Show first part of description
        print("5. Task description preview:")
        print(f"   📄 {task.description[:200]}...")
        
        # Check if it's simplified
        if description_length < 1000:  # Much shorter than before
            print("   ✅ SUCCESS: Instructions are simplified!")
            return True
        else:
            print("   ⚠️ WARNING: Instructions are still quite long")
            return False
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test the simplified navigation agent"""
    print("🚀 Simplified Navigation Agent Test")
    print("=" * 60)
    
    success = test_simplified_navigation()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 NAVIGATION AGENT SIMPLIFIED!")
        print("   The agent should no longer get stuck on complex instructions.")
        print("   Try running the scraper again - it should work now.")
    else:
        print("🔧 NAVIGATION AGENT STILL COMPLEX")
        print("   The agent may still get stuck on instruction overload.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
