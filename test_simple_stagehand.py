#!/usr/bin/env python3
"""
Simple test for SimplifiedStagehandTool async issues
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool

def test_direct_tool_call():
    """Test the tool directly without CrewAI"""
    print("🧪 Testing SimplifiedStagehandTool directly...")
    
    try:
        # Create tool instance
        tool = SimplifiedStagehandTool()
        print("✅ Tool created successfully")
        
        # Test navigation
        print("🚀 Testing navigation...")
        result = tool._run(operation="navigate", url="https://example.com")
        print(f"✅ Navigation result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_tool_call()
