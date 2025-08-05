#!/usr/bin/env python3
"""
Debug the extract method by calling it directly and comparing with direct Stagehand calls
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def debug_extract_direct():
    """Debug by calling extract directly and comparing with direct Stagehand"""
    
    print("🔍 Debugging Extract Method - Direct Comparison")
    print("=" * 60)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        from stagehand import Stagehand
        
        # Test 1: Direct Stagehand call (we know this works)
        print("\n1. Testing Direct Stagehand Call (Known Working)...")
        
        api_key = os.getenv('BROWSERBASE_API_KEY')
        project_id = os.getenv('BROWSERBASE_PROJECT_ID')
        model_api_key = os.getenv('OPENAI_API_KEY')
        
        direct_stagehand = Stagehand(
            env="BROWSERBASE",
            api_key=api_key,
            project_id=project_id,
            model_name="gpt-4o",
            model_api_key=model_api_key,
        )
        
        await direct_stagehand.init()
        await direct_stagehand.page.goto("https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        
        # Handle popup
        try:
            await direct_stagehand.page.act({"action": "Click the accept or dismiss button on the privacy dialog"})
        except:
            pass
        
        # Extract with direct Stagehand
        instruction = "Extract all product data from the page. For each product, get: name (string), description (string), price (string), image_url (string), weight (string if available). Return valid JSON array."
        
        print(f"   📝 Instruction: {instruction}")
        direct_result = await direct_stagehand.page.extract(instruction)
        print(f"   📊 Direct result type: {type(direct_result)}")
        print(f"   📊 Direct result: {direct_result}")
        
        # Parse direct result
        if hasattr(direct_result, 'model_dump'):
            direct_dict = direct_result.model_dump()
        elif hasattr(direct_result, '__dict__'):
            direct_dict = direct_result.__dict__
        else:
            direct_dict = direct_result
            
        print(f"   📊 Direct dict: {direct_dict}")
        
        # Check for extraction key
        if isinstance(direct_dict, dict) and "extraction" in direct_dict:
            inner = direct_dict["extraction"]
            print(f"   📊 Inner extraction: {inner}")
            if isinstance(inner, str):
                try:
                    parsed_inner = json.loads(inner)
                    print(f"   📊 Parsed inner: {parsed_inner}")
                    if isinstance(parsed_inner, list):
                        print(f"   ✅ Direct Stagehand found {len(parsed_inner)} products")
                except:
                    print(f"   ❌ Failed to parse inner extraction")
        
        # Test 2: SimplifiedStagehandTool call
        print("\n2. Testing SimplifiedStagehandTool Call...")
        
        tool = SimplifiedStagehandTool()
        
        # Navigate and handle popup
        await tool.navigate("https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        try:
            await tool.act("Click the accept or dismiss button on the privacy dialog")
        except:
            pass
        
        # Extract with SimplifiedStagehandTool
        tool_result = await tool.extract(instruction)
        print(f"   📊 Tool result type: {type(tool_result)}")
        print(f"   📊 Tool result: {tool_result}")
        
        # Parse tool result
        try:
            tool_parsed = json.loads(tool_result)
            print(f"   📊 Tool parsed type: {type(tool_parsed)}")
            if isinstance(tool_parsed, list):
                print(f"   📊 Tool found {len(tool_parsed)} products")
            else:
                print(f"   📊 Tool result not a list: {tool_parsed}")
        except json.JSONDecodeError as e:
            print(f"   ❌ Tool result JSON parse error: {e}")
        
        # Test 3: Compare the underlying Stagehand instances
        print("\n3. Comparing Stagehand Instances...")
        
        tool_stagehand = await tool._get_stagehand()
        print(f"   📊 Direct stagehand session: {getattr(direct_stagehand, 'session_id', 'unknown')}")
        print(f"   📊 Tool stagehand session: {getattr(tool_stagehand, 'session_id', 'unknown')}")
        
        # Test 4: Raw extraction comparison
        print("\n4. Raw Extraction Comparison...")
        
        print("   🔄 Direct stagehand raw extract...")
        direct_raw = await direct_stagehand.page.extract(instruction)
        print(f"   📊 Direct raw: {direct_raw}")
        
        print("   🔄 Tool stagehand raw extract...")
        tool_raw = await tool_stagehand.page.extract(instruction)
        print(f"   📊 Tool raw: {tool_raw}")
        
        print(f"   🔍 Raw results equal: {direct_raw == tool_raw}")
        
        print("\n✅ Debug comparison completed!")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_extract_direct())
