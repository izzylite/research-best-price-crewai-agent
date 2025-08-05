#!/usr/bin/env python3
"""Test the schema resolution fix for Agent 2 extraction issue."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_schema_resolution():
    """Test that the StagehandTool can resolve schema names correctly."""
    print("Testing schema resolution fix...")
    
    try:
        # Test StagehandTool schema resolution
        print("1. Testing StagehandTool schema resolution...")
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        
        tool = EcommerceStagehandTool()
        print("   ✅ StagehandTool created successfully")
        
        # Test schema registry
        print("2. Testing schema registry...")
        registry = tool._schema_registry
        print(f"   Available schemas: {list(registry.keys())}")
        
        # Test schema resolution
        print("3. Testing schema resolution...")
        schema = tool._resolve_schema("StandardizedProduct")
        if schema:
            print(f"   ✅ Schema resolved: {schema.__name__}")
            print(f"   Schema fields: {list(schema.model_fields.keys())}")
        else:
            print("   ❌ Schema resolution failed")
            return False
        
        # Test invalid schema
        print("4. Testing invalid schema handling...")
        invalid_schema = tool._resolve_schema("InvalidSchema")
        if invalid_schema is None:
            print("   ✅ Invalid schema correctly returns None")
        else:
            print("   ❌ Invalid schema should return None")
            return False
        
        print("\n🎉 ALL SCHEMA RESOLUTION TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Schema resolution test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_task_creation():
    """Test that the ExtractionAgent can create tasks with schema instructions."""
    print("\nTesting agent task creation...")
    
    try:
        from ecommerce_scraper.agents.extraction_agent import ExtractionAgent
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        
        # Create agent
        tool = EcommerceStagehandTool()
        agent = ExtractionAgent(stagehand_tool=tool, verbose=False)
        print("   ✅ ExtractionAgent created successfully")
        
        # Create task
        task = agent.create_extraction_task(
            vendor="asda",
            category="fruit",
            page_number=1
        )
        print("   ✅ Extraction task created successfully")
        
        # Check task description contains schema instruction
        task_desc = task.description
        if 'extraction_schema="StandardizedProduct"' in task_desc:
            print("   ✅ Task contains correct schema instruction")
        else:
            print("   ❌ Task missing schema instruction")
            print(f"   Task description: {task_desc[:200]}...")
            return False
        
        print("   ✅ Agent task creation test passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Agent task creation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Testing Agent 2 Extraction Issue Fixes\n")
    
    success1 = test_schema_resolution()
    success2 = test_agent_task_creation()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED! The schema resolution fix should work.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. The fix needs more work.")
        sys.exit(1)
