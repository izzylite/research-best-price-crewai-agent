#!/usr/bin/env python3
"""Test the Extraction Agent's ability to find all products including off-screen ones."""

import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_extraction_scrolling():
    """Test that the Extraction Agent can find all products, not just viewport-visible ones."""
    print("🔍 Testing Extraction Agent scroll-aware extraction...")
    
    try:
        from ecommerce_scraper.agents.extraction_agent import ExtractionAgent
        from ecommerce_scraper.agents.navigation_agent import NavigationAgent
        from crewai import Crew
        
        # First, prepare the page with Navigation Agent using taller viewport
        print("1. Preparing page with Navigation Agent (1920x1080 viewport)...")
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool

        # Create Navigation Stagehand tool with taller viewport (1920x1080)
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
            verbose=False
        )
        
        print("2. Executing navigation...")
        nav_result = nav_crew.kickoff()
        
        # Parse navigation result
        try:
            if hasattr(nav_result, 'raw'):
                nav_data = json.loads(nav_result.raw)
            else:
                nav_data = json.loads(str(nav_result))
            
            products_visible = nav_data.get('page_info', {}).get('products_visible', 0)
            print(f"   Navigation reports: {products_visible} products visible")
            
        except (json.JSONDecodeError, AttributeError):
            print(f"   Navigation result: {nav_result}")
        
        # Now test extraction with session sharing and taller viewport
        print("3. Testing extraction with session sharing and taller viewport...")

        # Get session ID from navigation tool for sharing
        session_id = nav_stagehand_tool.get_session_id()
        print(f"   📋 Navigation session ID: {session_id}")

        # Create extraction tool that reuses the same session
        extraction_stagehand_tool = EcommerceStagehandTool(
            session_id=session_id,
            viewport_width=1920,
            viewport_height=1080
        )

        # Create extraction agent with session-sharing tool
        extraction_agent = ExtractionAgent(stagehand_tool=extraction_stagehand_tool)

        extraction_task = extraction_agent.create_extraction_task(
            vendor="ASDA",
            category="fruit",
            page_number=1
        )
        
        extraction_crew = Crew(
            agents=[extraction_agent.get_agent()],
            tasks=[extraction_task],
            verbose=True
        )
        
        print("4. Executing extraction...")
        extraction_result = extraction_crew.kickoff()
        
        # Parse extraction result
        try:
            if hasattr(extraction_result, 'raw'):
                extraction_data = json.loads(extraction_result.raw)
            else:
                extraction_data = json.loads(str(extraction_result))
            
            products_extracted = len(extraction_data.get('extraction_batch', []))
            print(f"\n📊 EXTRACTION RESULTS:")
            print(f"   Products Extracted: {products_extracted}")
            
            if products_extracted > 10:
                print(f"   ✅ SUCCESS: Found {products_extracted} products (more than viewport-visible)")
                print(f"   🎯 Scroll-aware extraction is working!")
            elif products_extracted > 5:
                print(f"   ⚠️  PARTIAL: Found {products_extracted} products (some improvement)")
                print(f"   🔄 May need further scroll optimization")
            else:
                print(f"   ❌ ISSUE: Only found {products_extracted} products (likely viewport-only)")
                print(f"   🔧 Scroll-aware extraction needs more work")
            
            # Show sample products
            products = extraction_data.get('extraction_batch', [])[:3]
            if products:
                print(f"\n📦 SAMPLE PRODUCTS:")
                for i, product in enumerate(products, 1):
                    print(f"   {i}. {product.get('name', 'Unknown')} - £{product.get('price', {}).get('current', 'N/A')}")
            
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"\n📊 RAW EXTRACTION RESULT: {extraction_result}")
        
        print("\n🎉 Extraction scrolling test completed!")
        
    except Exception as e:
        print(f"\n❌ Extraction scrolling test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Extraction Agent Scroll-Aware Test\n")
    test_extraction_scrolling()
