#!/usr/bin/env python3
"""
Debug the SimplifiedStagehandTool extract method to find why it returns empty results
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

async def debug_extract_method():
    """Debug the SimplifiedStagehandTool extract method"""
    
    print("🔍 Debugging SimplifiedStagehandTool Extract Method")
    print("=" * 60)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        # Create tool instance
        print("\n1. Creating SimplifiedStagehandTool...")
        tool = SimplifiedStagehandTool()
        
        # Navigate to ASDA page
        print("\n2. Navigating to ASDA fruit page...")
        navigate_result = await tool.navigate("https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        print(f"   Navigation result: {navigate_result}")
        
        # Handle popups
        print("\n3. Handling popups...")
        try:
            popup_result = await tool.act("Click the accept or dismiss button on the privacy dialog")
            print(f"   Popup handling result: {popup_result}")
        except Exception as e:
            print(f"   Popup handling failed (might be OK): {e}")
        
        # Test extraction with detailed logging
        print("\n4. Testing extraction with detailed logging...")
        
        # Monkey patch the extract method to add debug logging
        original_extract = tool.extract
        
        async def debug_extract(instruction: str) -> str:
            print(f"   📝 Extract instruction: {instruction}")
            
            try:
                stagehand = await tool._get_stagehand()
                print(f"   ✅ Got stagehand instance: {type(stagehand)}")
                
                # Direct API call
                print(f"   🔄 Calling stagehand.page.extract...")
                extraction = await stagehand.page.extract(instruction)
                print(f"   📊 Raw extraction type: {type(extraction)}")
                print(f"   📊 Raw extraction: {extraction}")
                
                # Check if it has model_dump
                if hasattr(extraction, 'model_dump'):
                    print(f"   🔧 Has model_dump - converting...")
                    extraction_dict = extraction.model_dump()
                    print(f"   📊 After model_dump: {extraction_dict}")
                elif hasattr(extraction, '__dict__'):
                    print(f"   🔧 Has __dict__ - converting...")
                    extraction_dict = extraction.__dict__
                    print(f"   📊 After __dict__: {extraction_dict}")
                else:
                    print(f"   🔧 Using as-is...")
                    extraction_dict = extraction
                
                # Check for "extraction" key
                if isinstance(extraction_dict, dict) and "extraction" in extraction_dict:
                    print(f"   🔍 Found 'extraction' key in result")
                    inner_extraction = extraction_dict["extraction"]
                    print(f"   📊 Inner extraction type: {type(inner_extraction)}")
                    print(f"   📊 Inner extraction: {inner_extraction}")
                    
                    if isinstance(inner_extraction, str):
                        print(f"   🔧 Trying to parse inner extraction as JSON...")
                        try:
                            parsed = json.loads(inner_extraction)
                            print(f"   ✅ Successfully parsed JSON: {parsed}")
                            extraction_dict = parsed
                        except json.JSONDecodeError as je:
                            print(f"   ❌ JSON parse failed: {je}")
                    else:
                        extraction_dict = inner_extraction
                
                # Final result
                result = json.dumps(extraction_dict, indent=2, default=str)
                print(f"   📊 Final result length: {len(result)} characters")
                print(f"   📊 Final result preview: {result[:200]}...")
                
                return result
                
            except Exception as error:
                print(f"   ❌ Extract error: {error}")
                import traceback
                traceback.print_exc()
                raise
        
        # Replace extract method with debug version
        tool.extract = debug_extract
        
        # Test extraction
        instruction = "Extract all product data from the page. For each product, get: name (string), description (string), price (string), image_url (string), weight (string if available). Return valid JSON array."
        result = await tool.extract(instruction)
        
        print(f"\n5. Final extraction result:")
        print(f"   Length: {len(result)} characters")
        print(f"   Content: {result}")
        
        # Parse and analyze result
        try:
            parsed_result = json.loads(result)
            print(f"   Parsed type: {type(parsed_result)}")
            if isinstance(parsed_result, list):
                print(f"   Array length: {len(parsed_result)}")
                if len(parsed_result) > 0:
                    print(f"   First item: {parsed_result[0]}")
            else:
                print(f"   Not an array: {parsed_result}")
        except json.JSONDecodeError as e:
            print(f"   JSON parse error: {e}")
        
        print("\n✅ Debug completed!")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_extract_method())
