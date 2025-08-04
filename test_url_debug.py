#!/usr/bin/env python3
"""
Debug script to test URL handling in the ecommerce scraper.
"""

import os
import sys
import json
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is available for CrewAI
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_url_extraction():
    """Test URL extraction from categories file."""
    print("🔍 Testing URL extraction from categories file...")
    
    # Load ASDA categories
    categories_file = Path(__file__).parent / "categories" / "asda.json"
    
    try:
        with open(categories_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)
    except Exception as e:
        print(f"❌ Error loading categories: {e}")
        return False
    
    # Find Vegetables & Potatoes category
    vegetables_category = None
    for category in categories:
        if "subcategories" in category:
            for subcat in category["subcategories"]:
                if "Vegetables" in subcat["name"] and "Potatoes" in subcat["name"]:
                    vegetables_category = subcat
                    break
        if vegetables_category:
            break
    
    if not vegetables_category:
        print("❌ Vegetables & Potatoes category not found")
        return False
    
    print(f"✅ Found category: {vegetables_category['name']}")
    print(f"📍 URL: {vegetables_category['url']}")
    print(f"📏 URL length: {len(vegetables_category['url'])} characters")
    
    # Test URL validity
    url = vegetables_category['url']
    if url.startswith('https://') or url.startswith('http://'):
        print("✅ URL has valid protocol")
    else:
        print("❌ URL missing protocol")
        return False
    
    return True, vegetables_category

def test_stagehand_tool_directly():
    """Test StagehandTool directly with the problematic URL."""
    print("\n🔧 Testing StagehandTool directly...")
    
    success, vegetables_category = test_url_extraction()
    if not success:
        return False
    
    try:
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        
        print("🛠️ Creating StagehandTool...")
        tool = EcommerceStagehandTool()
        
        url = vegetables_category['url']
        print(f"🌐 Testing navigation to: {url}")
        print(f"📏 URL length: {len(url)} characters")
        
        # Test the tool directly
        result = tool._run(
            instruction="Navigate to the category page for vegetables and potatoes",
            url=url,
            command_type="act"
        )
        
        print(f"📄 Result: {result}")
        
        if "Error" in result and "protocol" in result:
            print("❌ URL truncation confirmed - protocol error detected")
            return False
        else:
            print("✅ Navigation successful or different error")
            return True
            
    except Exception as e:
        print(f"❌ StagehandTool test failed: {e}")
        return False
    finally:
        try:
            tool.close()
        except:
            pass

def test_task_description():
    """Test if the URL is being truncated in task descriptions."""
    print("\n📋 Testing task description...")
    
    success, vegetables_category = test_url_extraction()
    if not success:
        return False
    
    try:
        from ecommerce_scraper.agents.product_scraper import ProductScraperAgent
        
        print("🤖 Creating ProductScraperAgent...")
        agent = ProductScraperAgent()
        
        url = vegetables_category['url']
        print(f"📍 Creating task with URL: {url}")
        print(f"📏 URL length: {len(url)} characters")
        
        # Create the task
        task = agent.create_direct_category_scraping_task(
            vendor="asda",
            category="Fruit, Veg & Flowers > Vegetables & Potatoes",
            category_url=url,
            session_id="test_session",
            max_pages=1
        )
        
        print(f"📋 Task created successfully")
        print(f"📄 Task description preview: {task.description[:200]}...")
        
        # Check if URL appears in task description
        if url in task.description:
            print("✅ Full URL found in task description")
            return True
        else:
            print("❌ URL not found or truncated in task description")
            return False
            
    except Exception as e:
        print(f"❌ Task description test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 URL Debug Test Suite")
    print("=" * 50)
    
    # Test 1: URL extraction
    print("\n1️⃣ Testing URL extraction...")
    success1 = test_url_extraction()
    
    # Test 2: Task description
    print("\n2️⃣ Testing task description...")
    success2 = test_task_description()
    
    # Test 3: StagehandTool direct test
    print("\n3️⃣ Testing StagehandTool directly...")
    success3 = test_stagehand_tool_directly()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"URL Extraction: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Task Description: {'✅ PASS' if success2 else '❌ FAIL'}")
    print(f"StagehandTool Direct: {'✅ PASS' if success3 else '❌ FAIL'}")
    
    if all([success1, success2, success3]):
        print("\n🎉 All tests passed! URL handling appears to be working correctly.")
    else:
        print("\n⚠️ Some tests failed. URL truncation issue confirmed.")

if __name__ == "__main__":
    main()
