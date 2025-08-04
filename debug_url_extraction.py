#!/usr/bin/env python3
"""
Debug URL extraction in CrewAI ecommerce scraper.
Tests if the agent is properly extracting and using the full URL from task descriptions.
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_task_description_url():
    """Test if the task description contains the full URL."""
    print("🧪 Testing task description URL inclusion...")
    
    try:
        from ecommerce_scraper.agents.product_scraper import ProductScraperAgent
        
        # Test URL from ASDA Fruit category
        test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        vendor = "asda"
        category_name = "Fruit, Veg & Flowers > Fruit"
        session_id = "test_session"
        
        print(f"📍 Test URL: {test_url}")
        print(f"📏 URL Length: {len(test_url)} characters")
        
        # Create ProductScraperAgent
        agent = ProductScraperAgent(tools=[])
        
        # Create the task
        task = agent.create_direct_category_scraping_task(
            vendor=vendor,
            category=category_name,
            category_url=test_url,
            session_id=session_id,
            max_pages=1
        )
        
        # Check if the full URL is in the task description
        task_description = task.description
        print(f"\n📋 Task Description Preview:")
        print(f"   Length: {len(task_description)} characters")
        print(f"   Contains full URL: {test_url in task_description}")
        
        # Extract URL from task description
        lines = task_description.split('\n')
        url_line = None
        for line in lines:
            if line.strip().startswith('URL:'):
                url_line = line.strip()
                break
        
        if url_line:
            extracted_url = url_line.replace('URL:', '').strip()
            print(f"\n🔍 URL Extraction Results:")
            print(f"   URL Line: {url_line}")
            print(f"   Extracted URL: {extracted_url}")
            print(f"   Extracted Length: {len(extracted_url)} characters")
            print(f"   URLs Match: {extracted_url == test_url}")
            
            if extracted_url != test_url:
                print(f"❌ URL MISMATCH DETECTED!")
                print(f"   Expected: {test_url}")
                print(f"   Got:      {extracted_url}")
                return False
            else:
                print(f"✅ URL extraction successful!")
                return True
        else:
            print(f"❌ No URL line found in task description!")
            return False
            
    except Exception as e:
        print(f"❌ Task description test failed: {e}")
        return False

def test_stagehand_tool_url_handling():
    """Test if StagehandTool properly handles the full URL."""
    print("\n🛠️ Testing StagehandTool URL handling...")
    
    try:
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        
        test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        
        print(f"📍 Testing URL: {test_url}")
        print(f"📏 URL Length: {len(test_url)} characters")
        
        # Create tool (but don't actually execute to avoid Browserbase usage)
        tool = EcommerceStagehandTool()
        
        # Test URL validation
        from ecommerce_scraper.utils.url_utils import is_valid_url
        is_valid = is_valid_url(test_url)
        print(f"🔍 URL Validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        # Test URL parsing
        from urllib.parse import urlparse
        parsed = urlparse(test_url)
        print(f"🔍 URL Parsing:")
        print(f"   Scheme: {parsed.scheme}")
        print(f"   Domain: {parsed.netloc}")
        print(f"   Path: {parsed.path}")
        print(f"   Full URL reconstructed: {parsed.geturl()}")
        print(f"   Reconstruction matches: {parsed.geturl() == test_url}")
        
        return is_valid and parsed.geturl() == test_url
        
    except Exception as e:
        print(f"❌ StagehandTool URL test failed: {e}")
        return False

def test_crew_execution_simulation():
    """Simulate crew execution to see URL handling."""
    print("\n🤖 Testing crew execution simulation...")
    
    try:
        from ecommerce_scraper.main import EcommerceScraper
        
        test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        vendor = "asda"
        category_name = "Fruit, Veg & Flowers > Fruit"
        
        print(f"📍 Test URL: {test_url}")
        print(f"🏪 Vendor: {vendor}")
        print(f"📂 Category: {category_name}")
        
        # Create scraper instance (but don't execute to avoid Browserbase)
        scraper = EcommerceScraper(verbose=True)
        
        # Test task creation
        temp_session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        scraping_task = scraper.product_scraper.create_direct_category_scraping_task(
            vendor=vendor,
            category=category_name,
            category_url=test_url,
            session_id=temp_session_id,
            max_pages=1
        )
        
        print(f"✅ Task created successfully")
        print(f"📋 Task description contains URL: {test_url in scraping_task.description}")
        
        # Extract URL from task description to simulate what agent would do
        task_desc = scraping_task.description
        url_start = task_desc.find("URL: ") + 4
        if url_start > 3:  # Found "URL: "
            # Find the end of the URL (next newline or end of string)
            url_end = task_desc.find("\n", url_start)
            if url_end == -1:
                url_end = len(task_desc)
            
            extracted_url = task_desc[url_start:url_end].strip()
            print(f"🔍 Extracted URL: {extracted_url}")
            print(f"📏 Extracted Length: {len(extracted_url)} characters")
            print(f"✅ URL Match: {extracted_url == test_url}")
            
            return extracted_url == test_url
        else:
            print(f"❌ Could not find URL in task description")
            return False
            
    except Exception as e:
        print(f"❌ Crew execution simulation failed: {e}")
        return False

def main():
    """Run all URL debugging tests."""
    print("🚀 Starting URL extraction debugging...")
    print("=" * 60)
    
    results = []
    
    # Test 1: Task description URL inclusion
    results.append(("Task Description URL", test_task_description_url()))
    
    # Test 2: StagehandTool URL handling
    results.append(("StagehandTool URL Handling", test_stagehand_tool_url_handling()))
    
    # Test 3: Crew execution simulation
    results.append(("Crew Execution Simulation", test_crew_execution_simulation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEBUGGING RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! URL handling appears correct.")
        print("💡 The issue might be in the CrewAI agent execution itself.")
        print("   Consider adding logging to see what URL the agent actually uses.")
    else:
        print("🚨 Some tests failed! URL truncation issue identified.")
        print("💡 Check the failed tests above for specific issues.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
