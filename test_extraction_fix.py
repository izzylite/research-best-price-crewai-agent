#!/usr/bin/env python3
"""
Test script to verify the extraction agent fixes are working properly.
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
from ecommerce_scraper.agents.extraction_agent import ExtractionAgent
from crewai import Crew

def test_direct_extraction():
    """Test direct extraction using the Stagehand tool."""
    print("🧪 Testing direct extraction with Stagehand tool...")
    
    try:
        # Create tool and navigate to ASDA fruit page
        tool = EcommerceStagehandTool()
        
        # Navigate to the page
        nav_result = tool._run(
            instruction="Navigate to ASDA fruit page",
            url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025",
            command_type="act"
        )
        print(f"✅ Navigation result: {nav_result[:100]}...")
        
        # Extract products using the working instruction
        extract_result = tool._run(
            instruction="Extract all product data including name, price, description, image URL, and weight from all products on the page. Return as a structured list where each product has: name (string), price (number), description (string), image_url (string), weight (string), category (string 'Fruit'), vendor (string 'asda')",
            command_type="extract"
        )
        
        print(f"✅ Extraction completed. Result length: {len(extract_result)} characters")
        
        # Try to parse the result
        try:
            if extract_result.startswith('{"extraction":'):
                # Parse the wrapper format
                parsed = json.loads(extract_result)
                products_json = parsed.get('extraction', '[]')
                if isinstance(products_json, str):
                    products = json.loads(products_json)
                else:
                    products = products_json
            else:
                products = json.loads(extract_result)
            
            print(f"✅ Successfully parsed {len(products)} products")
            
            # Show first few products
            for i, product in enumerate(products[:3]):
                print(f"  Product {i+1}: {product.get('name', 'N/A')} - £{product.get('price', 'N/A')}")
            
            return True, len(products)
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"Raw result: {extract_result[:200]}...")
            return False, 0
            
    except Exception as e:
        print(f"❌ Direct extraction test failed: {e}")
        return False, 0

def test_agent_extraction():
    """Test extraction using the ExtractionAgent."""
    print("\n🤖 Testing extraction with ExtractionAgent...")
    
    try:
        # Create extraction agent
        tool = EcommerceStagehandTool()
        agent = ExtractionAgent(stagehand_tool=tool, verbose=True)
        
        # Create extraction task
        task = agent.create_extraction_task(
            vendor="asda",
            category="Fruit",
            page_number=1
        )
        
        # Create and run crew
        crew = Crew(
            agents=[agent.get_agent()],
            tasks=[task],
            verbose=True
        )
        
        print("🚀 Running extraction crew...")
        result = crew.kickoff()
        
        print(f"✅ Agent extraction completed")
        print(f"Result type: {type(result)}")
        print(f"Result: {str(result)[:200]}...")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Agent extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Run all tests."""
    print("🔧 Testing Extraction Agent Fixes")
    print("=" * 50)
    
    # Test 1: Direct extraction
    direct_success, product_count = test_direct_extraction()
    
    # Test 2: Agent extraction
    agent_success, agent_result = test_agent_extraction()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"Direct extraction: {'✅ PASS' if direct_success else '❌ FAIL'}")
    if direct_success:
        print(f"  Products extracted: {product_count}")
    
    print(f"Agent extraction: {'✅ PASS' if agent_success else '❌ FAIL'}")
    
    if direct_success and agent_success:
        print("\n🎉 All tests passed! Extraction fixes are working.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
