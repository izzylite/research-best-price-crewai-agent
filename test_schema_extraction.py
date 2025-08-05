#!/usr/bin/env python3
"""Test schema-based extraction with the current Browserbase session."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_schema_extraction():
    """Test schema-based extraction using the current session."""
    print("🔍 Testing schema-based extraction...")
    
    try:
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        from ecommerce_scraper.schemas.standardized_product import StandardizedProduct
        
        # Create tool
        tool = EcommerceStagehandTool()
        print("✅ StagehandTool created")
        
        # Test schema-based extraction
        print("1. Testing schema-based extraction...")
        result = tool._run(
            instruction="Extract the first product from this ASDA fruit page",
            command_type="extract",
            extraction_schema="StandardizedProduct"
        )
        print(f"   Schema extraction result: {result}")
        
        # Test multiple products
        print("2. Testing multiple product extraction...")
        result2 = tool._run(
            instruction="Extract the first 3 products from this ASDA fruit page",
            command_type="extract",
            extraction_schema="StandardizedProduct"
        )
        print(f"   Multiple products result: {result2}")
        
        print("\n🎉 Schema extraction testing completed!")
        
    except Exception as e:
        print(f"\n❌ Schema extraction test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        try:
            if 'tool' in locals():
                tool.close()
        except:
            pass

if __name__ == "__main__":
    print("🔧 Schema Extraction Test\n")
    test_schema_extraction()
