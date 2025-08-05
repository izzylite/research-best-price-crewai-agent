#!/usr/bin/env python3
"""Test the Navigation Agent fix to ensure it stays in the product area."""

import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_navigation_fix():
    """Test the fixed Navigation Agent."""
    print("🔍 Testing Navigation Agent fix...")
    
    try:
        from ecommerce_scraper.agents.navigation_agent import NavigationAgent
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        from crewai import Crew
        
        # Create navigation agent
        print("1. Creating Navigation Agent...")
        nav_agent = NavigationAgent()
        
        # Test URL from the logs
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        
        print(f"2. Testing URL: {asda_url}")
        
        # Create navigation task
        print("3. Creating navigation task...")
        nav_task = nav_agent.create_navigation_task(
            vendor="ASDA",
            category_url=asda_url,
            page_number=1
        )
        
        print("4. Task created successfully!")
        print(f"   Task description preview: {nav_task.description[:200]}...")
        
        # Create crew and execute
        print("5. Creating and executing navigation crew...")
        crew = Crew(
            agents=[nav_agent.get_agent()],
            tasks=[nav_task],
            verbose=True
        )
        
        print("6. Executing navigation task...")
        result = crew.kickoff()
        
        print("7. Navigation task completed!")
        print(f"   Result: {result}")
        
        # Try to parse the result as JSON
        try:
            if hasattr(result, 'raw'):
                result_data = json.loads(result.raw)
            else:
                result_data = json.loads(str(result))
            
            print("\n📊 NAVIGATION RESULTS:")
            print(f"   Status: {result_data.get('status', 'unknown')}")
            print(f"   Products Visible: {result_data.get('page_info', {}).get('products_visible', 'unknown')}")
            print(f"   Ready for Extraction: {result_data.get('page_info', {}).get('ready_for_extraction', 'unknown')}")
            print(f"   Popups Handled: {result_data.get('page_info', {}).get('popups_handled', [])}")
            
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"\n📊 RAW NAVIGATION RESULT: {result}")
        
        print("\n🎉 Navigation Agent test completed!")
        
    except Exception as e:
        print(f"\n❌ Navigation Agent test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Navigation Agent Fix Test\n")
    test_navigation_fix()
