#!/usr/bin/env python3
"""
Test Browserbase configuration to identify the URL protocol issue.
"""

import os
import sys
import asyncio
import httpx

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_browserbase_api():
    """Test Browserbase API directly."""
    print("🌐 Testing Browserbase API directly...")
    
    api_key = os.getenv("BROWSERBASE_API_KEY")
    project_id = os.getenv("BROWSERBASE_PROJECT_ID")
    
    if not api_key or not project_id:
        print("❌ Missing Browserbase credentials")
        return False
    
    print(f"🔑 API Key: {api_key[:20]}...")
    print(f"🆔 Project ID: {project_id}")
    
    # Test Browserbase API endpoint
    try:
        headers = {
            "X-BB-API-Key": api_key,
            "Content-Type": "application/json"
        }

        # Try to create a session
        create_url = "https://api.browserbase.com/v1/sessions"
        
        print(f"📡 Testing API endpoint: {create_url}")
        
        with httpx.Client() as client:
            response = client.post(
                create_url,
                headers=headers,
                json={
                    "projectId": project_id,
                    "browserSettings": {
                        "viewport": {"width": 1280, "height": 720}
                    }
                },
                timeout=30
            )
            
            print(f"📊 Response status: {response.status_code}")
            print(f"📄 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ Browserbase API is working")
                session_data = response.json()
                print(f"🆔 Session ID: {session_data.get('id', 'N/A')}")
                return True
            else:
                print(f"❌ API error: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_environment_variables_detailed():
    """Test all environment variables in detail."""
    print("🔍 Detailed environment variable analysis...")
    
    all_env_vars = dict(os.environ)
    
    # Check for any variables that might contain URLs
    url_vars = {}
    for key, value in all_env_vars.items():
        if any(keyword in key.lower() for keyword in ['url', 'endpoint', 'host', 'base']):
            url_vars[key] = value
    
    if url_vars:
        print("🔗 Found URL-related environment variables:")
        for key, value in url_vars.items():
            print(f"  {key}: {value}")
    else:
        print("✅ No suspicious URL-related environment variables found")
    
    # Check specific Browserbase variables
    browserbase_vars = {
        "BROWSERBASE_API_KEY": os.getenv("BROWSERBASE_API_KEY"),
        "BROWSERBASE_PROJECT_ID": os.getenv("BROWSERBASE_PROJECT_ID"),
        "BROWSERBASE_URL": os.getenv("BROWSERBASE_URL"),
        "BROWSERBASE_ENDPOINT": os.getenv("BROWSERBASE_ENDPOINT"),
    }
    
    print("\n🏢 Browserbase-specific variables:")
    for key, value in browserbase_vars.items():
        if value:
            if "url" in key.lower() or "endpoint" in key.lower():
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value[:20]}..." if len(value) > 20 else f"  {key}: {value}")
        else:
            print(f"  {key}: Not set")
    
    return True

def test_stagehand_with_minimal_config():
    """Test Stagehand with minimal configuration."""
    print("🧪 Testing Stagehand with minimal configuration...")
    
    try:
        from stagehand import Stagehand
        from stagehand.schemas import AvailableModel
        
        api_key = os.getenv("BROWSERBASE_API_KEY")
        project_id = os.getenv("BROWSERBASE_PROJECT_ID")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        # Try with minimal configuration
        print("🔧 Creating Stagehand with minimal config...")
        stagehand = Stagehand(
            api_key=api_key,
            project_id=project_id,
            model_api_key=openai_key,
            model_name=AvailableModel.GPT_4O
        )
        
        print("✅ Stagehand instance created with minimal config")
        
        async def test_init():
            try:
                await stagehand.init()
                print("✅ Minimal config initialization successful")
                return True
            except Exception as e:
                print(f"❌ Minimal config initialization failed: {e}")
                print(f"Error details: {type(e).__name__}: {str(e)}")
                
                # Try to get more details about the error
                if hasattr(e, '__cause__') and e.__cause__:
                    print(f"Caused by: {type(e.__cause__).__name__}: {str(e.__cause__)}")
                
                return False
        
        return asyncio.run(test_init())
        
    except Exception as e:
        print(f"❌ Error creating Stagehand instance: {e}")
        return False

def main():
    """Main test function."""
    print("🔧 Browserbase Configuration Test Suite")
    print("=" * 60)
    
    # Test 1: Environment variables
    print("\n1️⃣ Testing environment variables...")
    env_success = test_environment_variables_detailed()
    
    # Test 2: Browserbase API
    print("\n2️⃣ Testing Browserbase API...")
    api_success = test_browserbase_api()
    
    # Test 3: Minimal Stagehand config
    print("\n3️⃣ Testing minimal Stagehand configuration...")
    minimal_success = test_stagehand_with_minimal_config()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"Environment Variables: {'✅ PASS' if env_success else '❌ FAIL'}")
    print(f"Browserbase API: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"Minimal Stagehand Config: {'✅ PASS' if minimal_success else '❌ FAIL'}")
    
    if all([env_success, api_success, minimal_success]):
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check the configuration.")

if __name__ == "__main__":
    main()
