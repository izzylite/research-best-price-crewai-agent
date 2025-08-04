#!/usr/bin/env python3
"""
Test script using the exact official Stagehand API from the documentation.
"""

import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Ensure OpenAI API key is available for CrewAI
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

from stagehand import Stagehand, StagehandConfig

# Define Pydantic models for structured data extraction
class TestData(BaseModel):
    title: str = Field(..., description="Page title")

async def test_official_api():
    """Test the official Stagehand API exactly as documented."""
    print("🧪 Testing official Stagehand API...")
    
    try:
        # Create configuration exactly as in the documentation
        config = StagehandConfig(
            env="BROWSERBASE",  # or LOCAL
            api_key=os.getenv("BROWSERBASE_API_KEY"),
            project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
            model_name="openai/gpt-4o",  # Using OpenAI model
            model_client_options={"apiKey": os.getenv("OPENAI_API_KEY")},
        )
        
        print("✅ StagehandConfig created successfully")
        
        stagehand = Stagehand(config)
        print("✅ Stagehand instance created successfully")
        
        try:
            print("\n🚀 Initializing Stagehand...")
            # Initialize Stagehand
            await stagehand.init()
            print("✅ Stagehand initialized successfully!")
            
            if stagehand.env == "BROWSERBASE":    
                print(f"🌐 View your live browser: https://www.browserbase.com/sessions/{stagehand.session_id}")

            page = stagehand.page
            print("✅ Page object obtained")

            print("\n🌐 Testing navigation...")
            await page.goto("https://example.com")
            print("✅ Navigation successful!")
            
            print("\n📄 Testing extraction...")
            # Extract page title using structured schema        
            result = await page.extract(
                "Extract the page title",
                schema=TestData
            )
            
            print(f"✅ Extraction successful: {result.title}")
            
            print("\n👀 Testing observe...")
            observe_result = await page.observe("find any links on the page")
            print(f"✅ Observe successful: {observe_result}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during Stagehand operations: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            return False
        finally:
            # Close the client
            print("\n🔄 Closing Stagehand...")
            await stagehand.close()
            print("✅ Stagehand closed successfully")
            
    except Exception as e:
        print(f"❌ Error creating Stagehand: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

def main():
    """Main function."""
    print("🤘 Official Stagehand API Test")
    print("=" * 50)
    
    # Check environment variables
    required_vars = [
        "BROWSERBASE_API_KEY",
        "BROWSERBASE_PROJECT_ID", 
        "OPENAI_API_KEY"
    ]
    
    print("🔍 Checking environment variables...")
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:10]}...")
        else:
            print(f"❌ {var}: Not set")
            all_present = False
    
    if not all_present:
        print("\n❌ Missing required environment variables. Please check your .env file.")
        return
    
    # Run the test
    print("\n🧪 Running official API test...")
    success = asyncio.run(test_official_api())
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Official Stagehand API test PASSED!")
        print("The URL truncation issue should now be resolved.")
    else:
        print("❌ Official Stagehand API test FAILED!")
        print("There may still be configuration issues.")

if __name__ == "__main__":
    main()
