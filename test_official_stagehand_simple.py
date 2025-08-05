#!/usr/bin/env python3
"""
Test observe call using the official Stagehand v0.5.0 API (simplified approach)
"""

import os
import sys
import asyncio
import nest_asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_official_stagehand_simple():
    """Test the official Stagehand v0.5.0 observe call with simple constructor."""
    print("🔍 Testing Official Stagehand v0.5.0 Observe Call (Simple)")
    print("=" * 60)
    
    try:
        # Import official Stagehand v0.5.0
        from stagehand import Stagehand
        
        print("1. Creating Stagehand instance (trying simple constructor)...")
        
        # Try the constructor pattern from the old API first
        stagehand = Stagehand(
            env="BROWSERBASE",
            api_key=os.getenv("BROWSERBASE_API_KEY"),
            project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
            model_name="gpt-4o",
            model_api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        print("2. Initializing Stagehand...")
        await stagehand.init()
        
        print("3. Checking if page attribute exists...")
        if hasattr(stagehand, 'page'):
            print("   ✅ stagehand.page exists")
            page = stagehand.page
        else:
            print("   ❌ stagehand.page does not exist")
            print(f"   Available attributes: {[x for x in dir(stagehand) if not x.startswith('_')]}")
            return False
        
        print("4. Navigating to ASDA page...")
        await page.goto("https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025")
        
        print("5. Testing observe call...")
        instruction = "Find cookie banner or modal dialog"
        print(f"   instruction: '{instruction}'")
        
        # Test the observe call
        print("6. Calling page.observe()...")
        observations = await page.observe(instruction)
        
        print("7. ✅ SUCCESS! Official Stagehand observe call completed")
        print(f"   Result type: {type(observations)}")
        print(f"   Result: {str(observations)[:200]}...")
        
        # Close Stagehand
        print("8. Closing Stagehand...")
        await stagehand.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the official Stagehand test."""
    print("🚀 Official Stagehand v0.5.0 Simple Test")
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
    
    success = run_async(test_official_stagehand_simple())
    
    print("\n" + "=" * 70)
    print("📊 TEST RESULT")
    print("=" * 70)
    
    if success:
        print("✅ OFFICIAL STAGEHAND v0.5.0 OBSERVE WORKS!")
        print("   The observe bug is fixed in the official package")
        print("   We can now update our SimplifiedStagehandTool")
    else:
        print("❌ OFFICIAL STAGEHAND v0.5.0 OBSERVE STILL FAILS")
        print("   Need to investigate the API structure further")

if __name__ == "__main__":
    main()
