#!/usr/bin/env python3
"""
Test the act operation fix
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_act_operation():
    """Test the fixed act operation"""
    print("🧪 Testing Fixed Act Operation")
    print("=" * 40)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        
        print("1. Navigate to ASDA...")
        tool._run(operation="navigate", url=asda_url)
        
        print("2. Test act operation...")
        start_time = time.time()
        
        act_result = tool._run(
            operation="act",
            action="Click the 'I Accept' button to dismiss the privacy popup"
        )
        
        duration = time.time() - start_time
        print(f"   ⏱️ Act operation took {duration:.2f}s")
        print(f"   📄 Result: {act_result}")
        
        # Check if it worked by verifying no error
        if "Error:" not in act_result:
            print("   ✅ Act operation successful!")
            
            print("3. Verify popup was dismissed...")
            verify_result = tool._run(
                operation="extract",
                instruction="Count visible products on the page. Return just the number."
            )
            print(f"   📄 Product count after popup dismissal: {verify_result}")
            
        else:
            print("   ❌ Act operation still has errors")
        
        tool.close()
        return "Error:" not in act_result
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test the act fix"""
    print("🚀 Act Operation Fix Test")
    print("=" * 50)
    
    success = test_act_operation()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ACT OPERATION FIXED!")
        print("   The Navigation Agent should now be able to dismiss popups.")
        print("   This should resolve the stuck terminal issue.")
    else:
        print("🔧 ACT OPERATION STILL HAS ISSUES")
        print("   The Navigation Agent will continue to get stuck on popup dismissal.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
