#!/usr/bin/env python3
"""Test the fixes applied to the ecommerce scraper."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ecommerce_scraper'))

def test_schema_validation():
    """Test that the schema validation works correctly."""
    print("🧪 Testing schema validation...")
    
    try:
        from ecommerce_scraper.schemas.standardized_product import StandardizedProduct, StandardizedPrice
        
        # Test valid product data
        valid_data = {
            "name": "Test Product",
            "description": "Test Description",
            "price": {"amount": 10.99, "currency": "GBP"},
            "image_url": "https://example.com/image.jpg",
            "category": "Test Category",
            "vendor": "test",
            "weight": "100g"
        }
        
        product = StandardizedProduct(**valid_data)
        print(f"   ✅ Valid product created: {product.name}")
        
        # Test field names
        assert hasattr(product, 'image_url'), "image_url field should exist"
        assert product.price.amount == 10.99, "Price amount should be correct"
        assert product.price.currency == "GBP", "Currency should be GBP"
        
        print("   ✅ Schema validation passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Schema validation failed: {e}")
        return False

def test_agent_instructions():
    """Test that agent instructions are properly formatted."""
    print("🧪 Testing agent instructions...")
    
    try:
        from ecommerce_scraper.agents.extraction_agent import ExtractionAgent
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        
        # Create agent
        tool = EcommerceStagehandTool()
        agent = ExtractionAgent(stagehand_tool=tool, verbose=False)
        
        # Create task
        task = agent.create_extraction_task(
            vendor="asda",
            category="Fruit",
            page_number=1
        )
        
        # Check task description for improvements
        description = task.description
        
        # Check for JSON comment removal
        assert "// Current price as float" not in description, "JSON comments should be removed"
        assert "// Always GBP for UK retailers" not in description, "JSON comments should be removed"
        
        # Check for proper field names
        assert '"image_url"' in description, "Should use image_url not imageUrl"
        assert '"amount": 10.99' in description, "Should use amount not current"
        
        # Check for tool reuse prevention
        if "Do NOT repeat" not in description:
            # Search for the text in different parts
            if "EXTRACTION PROCESS" in description:
                extraction_part = description[description.find("EXTRACTION PROCESS"):]
                print(f"   🔍 Extraction process part: {extraction_part[:500]}...")
            assert False, "Should have tool reuse prevention"
        
        print("   ✅ Agent instructions properly formatted")
        return True
        
    except Exception as e:
        print(f"   ❌ Agent instruction test failed: {e}")
        return False

def test_navigation_improvements():
    """Test that navigation agent has ASDA-specific improvements."""
    print("🧪 Testing navigation improvements...")
    
    try:
        from ecommerce_scraper.agents.navigation_agent import NavigationAgent
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
        
        # Create agent
        tool = EcommerceStagehandTool()
        agent = NavigationAgent(stagehand_tool=tool, verbose=False)
        
        # Create task
        task = agent.create_navigation_task(
            vendor="asda",
            category_url="https://groceries.asda.com/aisle/fresh-food/fruit-veg-flowers/fruit/10002834",
            page_number=1
        )
        
        # Check task description for ASDA-specific improvements
        description = task.description
        
        # Check for ASDA-specific handling
        assert "ASDA-SPECIFIC" in description, "Should have ASDA-specific instructions"
        assert "postcode" in description.lower(), "Should mention postcode setup"
        assert "SW1A 1AA" in description, "Should have default postcode"
        assert "menu navigation" in description.lower(), "Should mention menu navigation"
        
        print("   ✅ Navigation improvements added")
        return True
        
    except Exception as e:
        print(f"   ❌ Navigation improvement test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing ecommerce scraper fixes...\n")
    
    tests = [
        test_schema_validation,
        test_agent_instructions,
        test_navigation_improvements
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All fixes validated successfully!")
        return True
    else:
        print("❌ Some fixes need additional work")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
