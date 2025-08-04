#!/usr/bin/env python3
"""
Test Stagehand URL handling directly to isolate the URL truncation issue.
This bypasses CrewAI and tests Stagehand's URL navigation directly.
"""

import sys
import os
import asyncio
import signal
from datetime import datetime
from urllib.parse import quote, unquote

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Global flag for graceful termination
terminate_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global terminate_requested
    print(f"\n🛑 Termination requested (signal {signum})")
    terminate_requested = True

async def test_stagehand_url_direct():
    """Test Stagehand URL handling directly without CrewAI."""
    print("🧪 Testing Stagehand URL handling directly...")
    
    # Test URL from ASDA Fruit category
    test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
    
    print(f"📍 Test URL: {test_url}")
    print(f"📏 URL Length: {len(test_url)} characters")
    print()
    
    try:
        from stagehand import Stagehand
        
        print("🤖 Creating Stagehand instance...")
        
        # Create Stagehand instance
        stagehand = Stagehand(
            env="BROWSERBASE",  # Use Browserbase environment
            verbose=1,
            debug_dom=True
        )
        
        print("🔧 Initializing Stagehand...")
        await stagehand.init()
        
        print("🌐 Testing direct URL navigation...")
        print(f"📍 Navigating to: {test_url}")
        
        # Test 1: Direct navigation
        print("\n🧪 Test 1: Direct URL navigation")
        try:
            await stagehand.page.goto(test_url)
            current_url = stagehand.page.url
            print(f"✅ Navigation successful!")
            print(f"🔍 Current URL: {current_url}")
            print(f"📊 URL Match: {'✅ Yes' if current_url == test_url else '❌ No'}")
            
            if current_url != test_url:
                print(f"⚠️ URL MISMATCH DETECTED!")
                print(f"   Expected: {test_url}")
                print(f"   Got:      {current_url}")
                print(f"   Difference: {len(test_url) - len(current_url)} characters")
                
        except Exception as e:
            print(f"❌ Direct navigation failed: {e}")
            return False
        
        # Test 2: URL encoding
        print("\n🧪 Test 2: URL encoding navigation")
        try:
            encoded_url = quote(test_url, safe=':/?#[]@!$&\'()*+,;=')
            print(f"📍 Encoded URL: {encoded_url}")
            
            await stagehand.page.goto(encoded_url)
            current_url = stagehand.page.url
            print(f"✅ Encoded navigation successful!")
            print(f"🔍 Current URL: {current_url}")
            
        except Exception as e:
            print(f"❌ Encoded navigation failed: {e}")
        
        # Test 3: URL with wait options
        print("\n🧪 Test 3: URL navigation with wait options")
        try:
            await stagehand.page.goto(test_url, wait_until='networkidle')
            current_url = stagehand.page.url
            print(f"✅ Navigation with wait successful!")
            print(f"🔍 Current URL: {current_url}")
            
        except Exception as e:
            print(f"❌ Navigation with wait failed: {e}")
        
        # Test 4: Extract page title to verify correct page
        print("\n🧪 Test 4: Page content verification")
        try:
            page_title = await stagehand.page.title()
            page_url = stagehand.page.url
            print(f"📄 Page Title: {page_title}")
            print(f"🔍 Final URL: {page_url}")
            
            # Check if we're on the right page
            is_asda = "asda" in page_title.lower() or "asda" in page_url.lower()
            is_fruit = "fruit" in page_title.lower() or "fruit" in page_url.lower()
            
            print(f"🏪 Is ASDA page: {'✅ Yes' if is_asda else '❌ No'}")
            print(f"🍎 Is Fruit page: {'✅ Yes' if is_fruit else '❌ No'}")
            
            return is_asda and is_fruit
            
        except Exception as e:
            print(f"❌ Page verification failed: {e}")
            return False
        
        finally:
            print("\n🧹 Cleaning up Stagehand...")
            try:
                await stagehand.close()
                print("✅ Stagehand closed successfully")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")
        
    except Exception as e:
        print(f"❌ Stagehand test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_url_properties():
    """Test URL properties and potential issues."""
    print("\n🔍 Testing URL properties...")
    
    test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
    
    print(f"📍 URL: {test_url}")
    print(f"📏 Length: {len(test_url)} characters")
    
    # Test URL parsing
    from urllib.parse import urlparse
    parsed = urlparse(test_url)
    
    print(f"🔍 URL Components:")
    print(f"   Scheme: {parsed.scheme}")
    print(f"   Domain: {parsed.netloc}")
    print(f"   Path: {parsed.path}")
    print(f"   Path Length: {len(parsed.path)} characters")
    
    # Check for potential issues
    issues = []
    
    if len(test_url) > 2048:
        issues.append("URL exceeds 2048 character limit")
    
    if len(parsed.path) > 1024:
        issues.append("Path exceeds 1024 character limit")
    
    special_chars = set(test_url) - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;=")
    if special_chars:
        issues.append(f"Contains special characters: {special_chars}")
    
    consecutive_hyphens = "--" in test_url
    if consecutive_hyphens:
        issues.append("Contains consecutive hyphens")
    
    print(f"⚠️ Potential Issues: {len(issues)}")
    for issue in issues:
        print(f"   - {issue}")
    
    return len(issues) == 0

async def main():
    """Run all Stagehand URL handling tests."""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("🚀 Stagehand URL Handling Test Suite")
    print("=" * 60)
    print("This test suite directly tests Stagehand's URL handling")
    print("to isolate the URL truncation issue from CrewAI.")
    print("=" * 60)
    print()

    results = []
    
    try:
        # Test 1: URL properties
        print("📊 Phase 1: URL Properties Analysis")
        url_props_ok = test_url_properties()
        results.append(("URL Properties", url_props_ok))
        
        if terminate_requested:
            print("🛑 Tests terminated by user request")
            return False
        
        # Test 2: Direct Stagehand URL handling
        print("\n🤖 Phase 2: Direct Stagehand Testing")
        stagehand_ok = await test_stagehand_url_direct()
        results.append(("Stagehand URL Handling", stagehand_ok))
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 STAGEHAND URL HANDLING TEST RESULTS")
        print("=" * 60)
        
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {test_name}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Stagehand URL handling is working correctly")
            print("💡 The issue might be in CrewAI agent behavior")
        else:
            print("🚨 STAGEHAND URL ISSUE CONFIRMED!")
            print("❌ Stagehand has URL handling problems")
            print("💡 Consider:")
            print("   1. URL encoding before navigation")
            print("   2. Using a different Stagehand version")
            print("   3. Reporting the issue to Stagehand team")
        print("=" * 60)
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ Test suite execution failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n🛑 Test suite interrupted by user")
        sys.exit(1)
