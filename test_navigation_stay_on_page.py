#!/usr/bin/env python3
"""Test that the Navigation Agent stays on the product page and doesn't navigate away."""

import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_navigation_stay_on_page():
    """Test that the Navigation Agent stays on the product page."""
    print("🔍 Testing Navigation Agent - Stay on Product Page...")
    
    try:
        from ecommerce_scraper.agents.navigation_agent import NavigationAgent
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        from crewai import Crew
        
        # Create Navigation Agent with taller viewport
        print("1. Creating Navigation Agent with improved popup handling...")
        nav_stagehand_tool = EcommerceStagehandTool(viewport_width=1920, viewport_height=1080)
        nav_agent = NavigationAgent(stagehand_tool=nav_stagehand_tool)
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        
        nav_task = nav_agent.create_navigation_task(
            vendor="ASDA",
            category_url=asda_url,
            page_number=1
        )
        
        nav_crew = Crew(
            agents=[nav_agent.get_agent()],
            tasks=[nav_task],
            verbose=True
        )
        
        print("2. Executing navigation with improved popup handling...")
        nav_result = nav_crew.kickoff()
        
        # Parse navigation result
        try:
            if hasattr(nav_result, 'raw'):
                nav_data = json.loads(nav_result.raw)
            else:
                nav_data = json.loads(str(nav_result))
            
            print(f"\n📊 NAVIGATION RESULTS:")
            print(f"   Navigation Status: {nav_data.get('navigation_status', 'Unknown')}")
            print(f"   Products Visible: {nav_data.get('page_info', {}).get('products_visible', 0)}")
            print(f"   Popups Handled: {nav_data.get('page_info', {}).get('popups_handled', 0)}")
            
            # Check if we stayed on the product page
            products_visible = nav_data.get('page_info', {}).get('products_visible', 0)
            if products_visible > 0:
                print(f"   ✅ SUCCESS: Found {products_visible} products - stayed on product page!")
                print(f"   🎯 Navigation Agent correctly avoided clicking navigation links")
            else:
                print(f"   ❌ ISSUE: Found 0 products - may have navigated away from product page")
                print(f"   🔧 Navigation Agent may have clicked wrong elements")
            
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"\n📊 RAW NAVIGATION RESULT: {nav_result}")
        
        print("\n🎉 Navigation stay-on-page test completed!")
        
    except Exception as e:
        print(f"\n❌ Navigation stay-on-page test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Navigation Agent Stay-on-Page Test\n")
    test_navigation_stay_on_page()
