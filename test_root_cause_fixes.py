"""Test the root cause fixes for the product search system."""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_stagehand_configuration():
    """Test that Stagehand is properly configured."""
    print("🧪 Testing Stagehand configuration...")
    
    try:
        from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
        
        # Check environment variables
        api_key = os.getenv('BROWSERBASE_API_KEY')
        project_id = os.getenv('BROWSERBASE_PROJECT_ID')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        print(f"   BROWSERBASE_API_KEY: {'✅ Set' if api_key else '❌ Missing'}")
        print(f"   BROWSERBASE_PROJECT_ID: {'✅ Set' if project_id else '❌ Missing'}")
        print(f"   OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Missing'}")
        
        if not all([api_key, project_id, openai_key]):
            print("❌ Missing required environment variables for Stagehand")
            return False
        
        # Test tool creation (should not fail on initialization)
        tool = SimplifiedStagehandTool()
        print("✅ SimplifiedStagehandTool created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Stagehand configuration test failed: {e}")
        return False

def test_perplexity_error_handling():
    """Test that Perplexity tool properly raises errors instead of using fallbacks."""
    print("🧪 Testing Perplexity error handling...")
    
    try:
        from ecommerce_scraper.tools.perplexity_retailer_research_tool import PerplexityRetailerResearchTool
        
        tool = PerplexityRetailerResearchTool()
        
        # This should raise an exception, not return fallback data
        try:
            result = tool._run(
                product_query="iPhone 15 Pro",
                max_retailers=3
            )
            print("❌ Expected exception but got result - fallback mechanism still active")
            return False
        except Exception as e:
            if "Perplexity API is required" in str(e):
                print("✅ Perplexity tool properly raises error instead of using fallback")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
                return False
        
    except Exception as e:
        print(f"❌ Perplexity error handling test failed: {e}")
        return False

def test_environment_setup():
    """Test that all required environment variables are properly set."""
    print("🧪 Testing environment setup...")

    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        'BROWSERBASE_API_KEY',
        'BROWSERBASE_PROJECT_ID',
        'OPENAI_API_KEY'
    ]

    optional_vars = [
        'ANTHROPIC_API_KEY',
        'GOOGLE_API_KEY'
    ]

    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)

    missing_optional = []
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)

    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    else:
        print("✅ All required environment variables are set")

    if missing_optional:
        print(f"⚠️ Missing optional environment variables: {', '.join(missing_optional)}")

    # Check if API keys look valid (not placeholder values)
    api_key = os.getenv('BROWSERBASE_API_KEY', '')
    if api_key.startswith('bb_live_'):
        print("✅ Browserbase API key format looks valid")
    else:
        print("⚠️ Browserbase API key format may be invalid")

    return True

if __name__ == "__main__":
    print("🚀 Testing Root Cause Fixes")
    print("=" * 50)
    
    test1 = test_environment_setup()
    test2 = test_stagehand_configuration()
    test3 = test_perplexity_error_handling()
    
    print("\n" + "=" * 50)
    print("📊 ROOT CAUSE FIX TEST SUMMARY")
    print("=" * 50)
    
    results = [
        ("Environment Setup", test1),
        ("Stagehand Configuration", test2),
        ("Perplexity Error Handling", test3)
    ]
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} root cause fixes verified ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All root cause fixes implemented successfully!")
        print("💡 The system should now work without fallback mechanisms.")
    else:
        print("⚠️ Some root cause fixes need attention.")
        print("💡 Check the failed tests above for specific issues to resolve.")
    
    sys.exit(0 if passed == total else 1)
