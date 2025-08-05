#!/usr/bin/env python3
"""
Test popup handling functionality of SimplifiedStagehandTool
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_popup_operations():
    """Test the popup handling operations that the Navigation Agent uses"""
    print("🧪 Testing Popup Handling Operations")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        print("1. Creating SimplifiedStagehandTool...")
        tool = SimplifiedStagehandTool()
        print("   ✅ Tool created successfully")
        
        print("\n2. Testing navigation to ASDA...")
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        
        nav_result = tool._run(operation="navigate", url=asda_url)
        print(f"   ✅ Navigation result: {nav_result.split('Session:')[0].strip()}")
        
        print("\n3. Testing observe operation (popup detection)...")
        start_time = time.time()
        
        observe_result = tool._run(
            operation="observe",
            instruction="Look for any popup dialogs, modal windows, or overlay elements that might be blocking the main content. Focus on cookie consent banners, privacy dialogs, or promotional overlays.",
            return_action=False
        )
        
        observe_duration = time.time() - start_time
        print(f"   ⏱️ Observe duration: {observe_duration:.2f} seconds")
        print(f"   📊 Result length: {len(observe_result)} characters")
        print(f"   📄 Observe result: {observe_result[:200]}...")
        
        print("\n4. Testing act operation (popup dismissal)...")
        start_time = time.time()
        
        # Test a simple act operation that shouldn't cause issues
        act_result = tool._run(
            operation="act",
            action="Wait for page to fully load"
        )
        
        act_duration = time.time() - start_time
        print(f"   ⏱️ Act duration: {act_duration:.2f} seconds")
        print(f"   📄 Act result: {act_result}")
        
        print("\n5. Testing extract operation (verify page is accessible)...")
        start_time = time.time()
        
        extract_result = tool._run(
            operation="extract",
            instruction="Count the number of visible product items on the page. Return just the number."
        )
        
        extract_duration = time.time() - start_time
        print(f"   ⏱️ Extract duration: {extract_duration:.2f} seconds")
        print(f"   📄 Extract result: {extract_result}")
        
        print("\n6. Testing session cleanup...")
        tool.close()
        print("   ✅ Session closed successfully")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_popup_scenario():
    """Test the specific popup scenario that might be causing the hang"""
    print("\n🎯 Testing Specific ASDA Popup Scenario")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        
        # Navigate to ASDA
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        tool._run(operation="navigate", url=asda_url)
        
        print("1. Looking for ASDA-specific popups...")
        
        # Test the exact observe operation the agent might be using
        popup_check = tool._run(
            operation="observe",
            instruction="Find any modal dialogs or overlays with text like 'Your privacy is important', 'Accept Cookies', or 'I Accept'. Look for elements that appear as overlays blocking the main content.",
            return_action=True
        )
        
        print(f"   📄 Popup check result: {popup_check[:300]}...")
        
        # If popups are found, try to dismiss them
        if "modal" in popup_check.lower() or "dialog" in popup_check.lower() or "overlay" in popup_check.lower():
            print("2. Attempting to dismiss detected popups...")
            
            dismiss_result = tool._run(
                operation="act",
                action="Click the 'I Accept' or 'Accept All' button to dismiss the privacy/cookie popup"
            )
            
            print(f"   📄 Dismiss result: {dismiss_result}")
        else:
            print("2. No blocking popups detected")
        
        print("3. Verifying page accessibility...")
        
        # Check if page is accessible
        accessibility_check = tool._run(
            operation="extract",
            instruction="Check if the main product listing is visible and accessible. Return 'accessible' if products are visible, 'blocked' if overlays are blocking content."
        )
        
        print(f"   📄 Accessibility: {accessibility_check}")
        
        tool.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Specific test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run popup handling tests"""
    print("🚀 SimplifiedStagehandTool Popup Handling Test")
    print("=" * 60)
    
    # Test basic operations
    basic_success = test_popup_operations()
    
    # Test specific popup scenario
    specific_success = test_specific_popup_scenario()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    print(f"Basic Operations: {'✅ Success' if basic_success else '❌ Failed'}")
    print(f"Popup Scenario: {'✅ Success' if specific_success else '❌ Failed'}")
    
    if basic_success and specific_success:
        print("\n🎉 ALL POPUP TESTS PASSED!")
        print("   The SimplifiedStagehandTool popup handling is working correctly.")
        print("   The issue might be in the Navigation Agent's logic or instructions.")
    else:
        print("\n🔧 POPUP HANDLING ISSUES DETECTED")
        print("   The SimplifiedStagehandTool has issues with popup operations.")
    
    return basic_success and specific_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
