#!/usr/bin/env python3
"""
Test the complete Navigation Agent workflow
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_navigation_workflow():
    """Test the complete navigation workflow that the agent performs"""
    print("🧪 Testing Navigation Agent Workflow")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        
        print("Step 1: Navigate to ASDA page...")
        start_time = time.time()
        nav_result = tool._run(operation="navigate", url=asda_url)
        nav_duration = time.time() - start_time
        print(f"   ✅ Navigation completed in {nav_duration:.2f}s")
        print(f"   📄 Result: {nav_result}")
        
        print("\nStep 2: Detect popups (what agent is trying to do)...")
        start_time = time.time()
        
        # This is likely what the Navigation Agent is trying to do
        popup_detection = tool._run(
            operation="observe",
            instruction="Look for any modal dialogs, popup windows, or overlay elements that might be blocking the main content. Focus on cookie consent banners, privacy dialogs with text like 'Your privacy is important', 'Accept Cookies', or promotional overlays.",
            return_action=False
        )
        
        popup_duration = time.time() - start_time
        print(f"   ⏱️ Popup detection took {popup_duration:.2f}s")
        print(f"   📊 Result length: {len(popup_detection)} characters")
        print(f"   📄 Popup detection result: {popup_detection[:300]}...")
        
        # Check if popups were found
        import json
        try:
            popup_data = json.loads(popup_detection)
            if popup_data and len(popup_data) > 0:
                print(f"   🎯 Found {len(popup_data)} potential popup elements")
                
                print("\nStep 3: Dismiss detected popups...")
                start_time = time.time()
                
                # Try to dismiss the first popup found
                dismiss_result = tool._run(
                    operation="act",
                    action="Click the 'I Accept' or 'Accept All' button to dismiss the privacy/cookie consent popup"
                )
                
                dismiss_duration = time.time() - start_time
                print(f"   ⏱️ Popup dismissal took {dismiss_duration:.2f}s")
                print(f"   📄 Dismiss result: {dismiss_result}")
                
            else:
                print("   ℹ️ No blocking popups detected")
                
        except json.JSONDecodeError:
            print("   ⚠️ Could not parse popup detection result as JSON")
        
        print("\nStep 4: Verify page accessibility...")
        start_time = time.time()
        
        accessibility_check = tool._run(
            operation="extract",
            instruction="Count the number of visible product items on the page. Return just the number as a simple integer."
        )
        
        access_duration = time.time() - start_time
        print(f"   ⏱️ Accessibility check took {access_duration:.2f}s")
        print(f"   📄 Product count: {accessibility_check}")
        
        print("\nStep 5: Cleanup...")
        tool.close()
        print("   ✅ Session closed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Navigation workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_timeout_scenario():
    """Test if the tool operations have timeout issues"""
    print("\n⏰ Testing Timeout Scenarios")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        tool = SimplifiedStagehandTool()
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        
        # Navigate first
        tool._run(operation="navigate", url=asda_url)
        
        print("Testing observe operation with timeout monitoring...")
        start_time = time.time()
        
        # Set a reasonable timeout expectation
        timeout_seconds = 30
        
        try:
            result = tool._run(
                operation="observe",
                instruction="Find any popup dialogs or modal windows on the page",
                return_action=False
            )
            
            duration = time.time() - start_time
            
            if duration > timeout_seconds:
                print(f"   ⚠️ Operation took {duration:.2f}s (longer than {timeout_seconds}s)")
                print("   🔍 This might explain why the Navigation Agent gets stuck")
            else:
                print(f"   ✅ Operation completed in {duration:.2f}s (within timeout)")
            
            print(f"   📄 Result: {result[:100]}...")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ Operation failed after {duration:.2f}s: {e}")
        
        tool.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Timeout test failed: {e}")
        return False

def main():
    """Run navigation workflow tests"""
    print("🚀 Navigation Agent Workflow Test")
    print("=" * 60)
    
    # Test complete workflow
    workflow_success = test_navigation_workflow()
    
    # Test timeout scenarios
    timeout_success = test_timeout_scenario()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    print(f"Navigation Workflow: {'✅ Success' if workflow_success else '❌ Failed'}")
    print(f"Timeout Testing: {'✅ Success' if timeout_success else '❌ Failed'}")
    
    if workflow_success and timeout_success:
        print("\n🎉 NAVIGATION WORKFLOW WORKING!")
        print("   The SimplifiedStagehandTool can complete the full navigation workflow.")
        print("   The issue might be in the CrewAI agent logic or Flow architecture.")
    else:
        print("\n🔧 NAVIGATION WORKFLOW ISSUES")
        print("   The SimplifiedStagehandTool has issues with the navigation workflow.")
        print("   This explains why the Navigation Agent gets stuck.")
    
    return workflow_success and timeout_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
