#!/usr/bin/env python3
"""
Test the new Browserbase MCP Tool
"""

import os
import sys
import time
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_browserbase_mcp_tool():
    """Test the Browserbase MCP Tool in isolation"""
    print("🧪 Testing Browserbase MCP Tool")
    print("=" * 50)
    
    try:
        from ecommerce_scraper.tools.browserbase_mcp_tool import BrowserbaseMCPTool
        
        print("1. Creating BrowserbaseMCPTool...")
        tool = BrowserbaseMCPTool()
        print("   ✅ Tool created successfully")
        
        print("2. Testing navigation...")
        start_time = time.time()
        nav_result = tool._run(
            operation="navigate",
            url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        )
        nav_duration = time.time() - start_time
        
        if "Error:" in nav_result:
            print(f"   ❌ Navigation failed: {nav_result}")
            return False
        else:
            print(f"   ✅ Navigation succeeded in {nav_duration:.2f}s: {nav_result}")
        
        print("3. Testing observe (popup detection)...")
        start_time = time.time()
        observe_result = tool._run(
            operation="observe",
            instruction="Find any popup dialogs, modal windows, or overlay elements that might be blocking the main content",
            return_action=False
        )
        observe_duration = time.time() - start_time
        
        if "Error:" in observe_result:
            print(f"   ❌ Observe failed: {observe_result}")
            return False
        else:
            print(f"   ✅ Observe succeeded in {observe_duration:.2f}s")
            print(f"   📄 Found: {observe_result[:100]}...")
        
        print("4. Testing act (popup dismissal)...")
        start_time = time.time()
        act_result = tool._run(
            operation="act",
            action="Click the 'I Accept' button to dismiss the privacy popup"
        )
        act_duration = time.time() - start_time
        
        if "Error:" in act_result:
            print(f"   ❌ Act failed: {act_result}")
            return False
        else:
            print(f"   ✅ Act succeeded in {act_duration:.2f}s: {act_result}")
        
        print("5. Testing extract (product count)...")
        start_time = time.time()
        extract_result = tool._run(
            operation="extract",
            instruction="Count the number of visible product items on the page. Return just the number."
        )
        extract_duration = time.time() - start_time
        
        if "Error:" in extract_result:
            print(f"   ❌ Extract failed: {extract_result}")
            return False
        else:
            print(f"   ✅ Extract succeeded in {extract_duration:.2f}s: {extract_result}")
        
        print("6. Cleaning up...")
        tool.close()
        print("   ✅ Session closed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_threading_compatibility():
    """Test that the Browserbase MCP Tool works in worker threads"""
    print("\n🧵 Testing Threading Compatibility")
    print("=" * 50)
    
    def run_in_thread():
        """Run tool operations in a separate thread"""
        try:
            from ecommerce_scraper.tools.browserbase_mcp_tool import BrowserbaseMCPTool
            
            print("   1. Creating tool in worker thread...")
            tool = BrowserbaseMCPTool()
            
            print("   2. Testing navigation in worker thread...")
            nav_result = tool._run(
                operation="navigate",
                url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
            )
            
            if "Error:" in nav_result:
                print(f"   ❌ Navigation failed: {nav_result}")
                return False
            else:
                print(f"   ✅ Navigation succeeded in worker thread")
            
            print("   3. Testing observe in worker thread...")
            observe_result = tool._run(
                operation="observe",
                instruction="Find any popup dialogs",
                return_action=False
            )
            
            if "Error:" in observe_result:
                print(f"   ❌ Observe failed: {observe_result}")
                return False
            else:
                print(f"   ✅ Observe succeeded in worker thread")
            
            tool.close()
            return True
            
        except Exception as e:
            print(f"   ❌ Thread test failed: {e}")
            return False
    
    # Test in worker thread
    result = None
    exception = None
    
    def thread_wrapper():
        nonlocal result, exception
        try:
            result = run_in_thread()
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=thread_wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout=120)  # 2 minute timeout
    
    if thread.is_alive():
        print("   ❌ THREAD TEST TIMED OUT")
        return False
    elif exception:
        print(f"   ❌ Thread test failed with exception: {exception}")
        return False
    elif result:
        print("   ✅ THREAD TEST SUCCEEDED")
        print("   🎉 BrowserbaseMCPTool works in worker threads!")
        return True
    else:
        print("   ❌ Thread test returned False")
        return False

def main():
    """Test the Browserbase MCP Tool"""
    print("🚀 Browserbase MCP Tool Test")
    print("=" * 60)
    
    # Test basic functionality
    basic_success = test_browserbase_mcp_tool()
    
    # Test threading compatibility (only if basic works)
    threading_success = False
    if basic_success:
        threading_success = test_threading_compatibility()
    else:
        print("\n⏭️ Skipping threading test - basic functionality failed")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 BROWSERBASE MCP TOOL RESULTS")
    print("=" * 60)
    
    print(f"Basic Functionality: {'✅ Working' if basic_success else '❌ Failed'}")
    print(f"Threading Compatibility: {'✅ Working' if threading_success else '❌ Failed/Skipped'}")
    
    if basic_success and threading_success:
        print("\n🎉 BROWSERBASE MCP TOOL FULLY WORKING!")
        print("   This tool can replace SimplifiedStagehandTool to fix threading issues!")
        print("   The Navigation Agent should work with this tool!")
    elif basic_success:
        print("\n🔧 BROWSERBASE MCP TOOL PARTIALLY WORKING")
        print("   Basic functionality works, but threading compatibility failed")
    else:
        print("\n🔧 BROWSERBASE MCP TOOL NOT WORKING")
        print("   Basic functionality failed")
    
    return basic_success and threading_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
