#!/usr/bin/env python3
"""
Test observe call using the official Stagehand v0.5.0 API
"""

import os
import sys
import asyncio
import nest_asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_official_stagehand_observe():
    """Test the official Stagehand v0.5.0 observe call."""
    print("🔍 Testing Official Stagehand v0.5.0 Observe Call")
    print("=" * 60)
    
    try:
        # Import official Stagehand v0.5.0
        from stagehand import StagehandConfig, Stagehand
        
        print("1. Creating Stagehand config (Official API v0.5.0)...")
        config = StagehandConfig(
            env="BROWSERBASE",
            api_key=os.getenv("BROWSERBASE_API_KEY"),
            project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
            model_name="gpt-4o",
            model_api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        print("2. Creating Stagehand instance...")
        stagehand = Stagehand(config)
        
        print("3. Initializing Stagehand...")
        await stagehand.init()
        
        print("4. Navigating to ASDA page...")
        page = stagehand.page
        await page.goto("https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        
        print("5. Testing observe call with official API...")
        
        # Test parameters
        instruction = "Find cookie banner or modal dialog"
        
        print(f"   instruction: '{instruction}' (type: {type(instruction)}, len: {len(instruction)})")
        
        # The official API call
        print("\n6. Calling page.observe() with official v0.5.0 API...")
        observations = await page.observe(instruction)
        
        print("7. ✅ SUCCESS! Official Stagehand observe call completed")
        print(f"   Result type: {type(observations)}")
        print(f"   Result: {str(observations)[:200]}...")
        
        # Test different instruction formats
        print("\n8. Testing different instruction formats with official API:")
        
        test_instructions = [
            "Find any popups on the page",
            "Look for modal dialogs", 
            "Check for cookie banners",
            "Count visible product elements"
        ]
        
        for i, test_instruction in enumerate(test_instructions, 1):
            try:
                print(f"   Test {i}: '{test_instruction}'")
                result = await page.observe(test_instruction)
                print(f"      ✅ Success: {str(result)[:50]}...")
                
            except Exception as e:
                print(f"      ❌ Failed: {e}")
        
        # Close Stagehand
        print("\n9. Closing Stagehand...")
        await stagehand.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the official Stagehand test."""
    print("🚀 Official Stagehand v0.5.0 Observe Test")
    print("=" * 70)
    
    # Handle event loop
    try:
        loop = asyncio.get_running_loop()
        nest_asyncio.apply(loop)
        run_async = loop.run_until_complete
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        run_async = loop.run_until_complete
    
    success = run_async(test_official_stagehand_observe())
    
    print("\n" + "=" * 70)
    print("📊 TEST RESULT")
    print("=" * 70)
    
    if success:
        print("✅ OFFICIAL STAGEHAND v0.5.0 OBSERVE WORKS!")
        print("   The observe bug is fixed in the official package")
        print("   We should update SimplifiedStagehandTool to use official API")
    else:
        print("❌ OFFICIAL STAGEHAND v0.5.0 OBSERVE STILL FAILS")
        print("   The issue persists even in the latest official version")
    
    print("\n📋 NEXT STEPS:")
    print("   1. Update SimplifiedStagehandTool to use official Stagehand v0.5.0 API")
    print("   2. Test the updated tool with CrewAI agents")
    print("   3. Verify all operations work correctly")

if __name__ == "__main__":
    main()
