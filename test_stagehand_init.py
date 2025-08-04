#!/usr/bin/env python3
"""
Test Stagehand initialization directly to isolate the URL protocol error.
"""

import os
import sys
import asyncio

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is available
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

def test_stagehand_direct():
    """Test Stagehand initialization directly."""
    print("🧪 Testing Stagehand initialization directly...")
    
    try:
        from stagehand import Stagehand
        from stagehand.schemas import AvailableModel
        
        print("📦 Stagehand imported successfully")
        
        # Get configuration from environment
        browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
        browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        print(f"🔑 API Key: {browserbase_api_key[:10]}..." if browserbase_api_key else "❌ No API key")
        print(f"🆔 Project ID: {browserbase_project_id[:10]}..." if browserbase_project_id else "❌ No Project ID")
        print(f"🤖 OpenAI Key: {openai_api_key[:10]}..." if openai_api_key else "❌ No OpenAI key")
        
        if not all([browserbase_api_key, browserbase_project_id, openai_api_key]):
            print("❌ Missing required environment variables")
            return False
        
        print("🔧 Creating Stagehand instance...")
        stagehand = Stagehand(
            api_key=browserbase_api_key,
            project_id=browserbase_project_id,
            model_api_key=openai_api_key,
            model_name=AvailableModel.GPT_4O,
            headless=True,
            verbose=1
        )
        
        print("✅ Stagehand instance created")
        
        print("🚀 Initializing Stagehand...")
        
        async def init_stagehand():
            try:
                await stagehand.init()
                print("✅ Stagehand initialized successfully")
                return True
            except Exception as e:
                print(f"❌ Stagehand initialization failed: {e}")
                print(f"Error type: {type(e)}")
                return False
        
        # Run the async initialization
        result = asyncio.run(init_stagehand())
        
        if result:
            print("🌐 Testing basic navigation...")
            
            async def test_navigation():
                try:
                    await stagehand.page.goto("https://example.com")
                    print("✅ Navigation successful")
                    return True
                except Exception as e:
                    print(f"❌ Navigation failed: {e}")
                    return False
            
            nav_result = asyncio.run(test_navigation())
            return nav_result
        else:
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_environment_variables():
    """Test environment variable configuration."""
    print("🔍 Testing environment variables...")
    
    required_vars = [
        "BROWSERBASE_API_KEY",
        "BROWSERBASE_PROJECT_ID", 
        "OPENAI_API_KEY"
    ]
    
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:10]}...")
        else:
            print(f"❌ {var}: Not set")
            all_present = False
    
    return all_present

def test_settings_loading():
    """Test settings loading from our configuration."""
    print("⚙️ Testing settings loading...")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ecommerce_scraper.config.settings import settings
        
        print("✅ Settings imported successfully")
        print(f"🔑 Browserbase API Key: {settings.browserbase_api_key[:10]}...")
        print(f"🆔 Project ID: {settings.browserbase_project_id[:10]}...")
        print(f"🤖 Model: {settings.stagehand_model_name}")
        print(f"🔇 Headless: {settings.stagehand_headless}")
        print(f"📢 Verbose: {settings.stagehand_verbose}")
        
        # Test get_model_api_key method
        try:
            model_key = settings.get_model_api_key()
            print(f"🔑 Model API Key: {model_key[:10]}...")
            return True
        except Exception as e:
            print(f"❌ Error getting model API key: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Settings loading failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Stagehand Initialization Test Suite")
    print("=" * 50)
    
    # Test 1: Environment variables
    print("\n1️⃣ Testing environment variables...")
    env_success = test_environment_variables()
    
    # Test 2: Settings loading
    print("\n2️⃣ Testing settings loading...")
    settings_success = test_settings_loading()
    
    # Test 3: Direct Stagehand initialization
    print("\n3️⃣ Testing direct Stagehand initialization...")
    stagehand_success = test_stagehand_direct()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Environment Variables: {'✅ PASS' if env_success else '❌ FAIL'}")
    print(f"Settings Loading: {'✅ PASS' if settings_success else '❌ FAIL'}")
    print(f"Stagehand Initialization: {'✅ PASS' if stagehand_success else '❌ FAIL'}")
    
    if all([env_success, settings_success, stagehand_success]):
        print("\n🎉 All tests passed! Stagehand initialization is working correctly.")
    else:
        print("\n⚠️ Some tests failed. There's an issue with Stagehand initialization.")

if __name__ == "__main__":
    main()
