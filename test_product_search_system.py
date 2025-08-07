"""Test script for the product-specific search system."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_schema_validation():
    """Test the product search schemas."""
    print("🧪 Testing Schema Validation...")
    
    try:
        from ecommerce_scraper.schemas.product_search_result import ProductSearchResult, ProductSearchItem
        from ecommerce_scraper.schemas.product_search_extraction import ProductSearchExtraction
        
        # Test ProductSearchItem creation
        item = ProductSearchItem(
            product_name="iPhone 15 Pro",
            price="£999.99",
            url="https://amazon.co.uk/iphone-15-pro",
            retailer="Amazon UK"
        )
        
        # Test ProductSearchResult creation
        result = ProductSearchResult(
            search_query="iPhone 15 Pro",
            results=[item],
            metadata={"test": True}
        )
        
        # Test ProductSearchExtraction creation
        extraction = ProductSearchExtraction(
            product_name="iPhone 15 Pro",
            price="£999.99",
            url="https://amazon.co.uk/iphone-15-pro",
            retailer="Amazon UK"
        )
        
        print("✅ Schema validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False


def test_retailer_research_tool():
    """Test the Perplexity retailer research tool."""
    print("🧪 Testing Retailer Research Tool...")
    
    try:
        from ecommerce_scraper.tools.perplexity_retailer_research_tool import PerplexityRetailerResearchTool
        
        # Create tool instance
        tool = PerplexityRetailerResearchTool()
        
        # Test with a simple product query (will use fallback if no API key)
        result = tool._run(
            product_query="iPhone 15 Pro",
            max_retailers=3
        )
        
        # Parse result
        result_data = json.loads(result)
        
        # Validate result structure
        assert "product_query" in result_data
        assert "retailers" in result_data
        assert isinstance(result_data["retailers"], list)
        
        print(f"✅ Retailer research tool passed - found {len(result_data['retailers'])} retailers")
        return True
        
    except Exception as e:
        print(f"❌ Retailer research tool failed: {e}")
        return False


def test_validation_agent():
    """Test the product search validation agent."""
    print("🧪 Testing Validation Agent...")
    
    try:
        from ecommerce_scraper.agents.product_search_validation_agent import ProductSearchValidationAgent
        
        # Create agent instance
        agent = ProductSearchValidationAgent(verbose=False)
        
        # Test validation methods
        match_score = agent.validate_product_match("iPhone 15 Pro Max", "iPhone 15 Pro")
        assert 0.0 <= match_score <= 1.0
        
        is_uk_retailer = agent.is_legitimate_uk_retailer("https://amazon.co.uk/product")
        assert is_uk_retailer == True
        
        is_comparison_site = agent.is_legitimate_uk_retailer("https://pricerunner.com/product")
        assert is_comparison_site == False
        
        print("✅ Validation agent passed")
        return True
        
    except Exception as e:
        print(f"❌ Validation agent failed: {e}")
        return False


def test_flow_result_processor():
    """Test the flow result processor."""
    print("🧪 Testing Flow Result Processor...")
    
    try:
        from product_search_scraper import ProductSearchScraper
        
        # Create scraper instance
        scraper = ProductSearchScraper(verbose=False)
        
        # Test result data
        test_result = {
            "search_query": "iPhone 15 Pro",
            "results": [
                {
                    "product_name": "iPhone 15 Pro",
                    "price": "£999.99",
                    "url": "https://amazon.co.uk/iphone-15-pro",
                    "retailer": "Amazon UK",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "metadata": {
                "session_id": "test_session",
                "retailers_searched": 1,
                "total_attempts": 1,
                "success_rate": 1.0
            }
        }
        
        # Test saving results
        saved_path = scraper._save_results(test_result)

        if saved_path:
            
            print("✅ Flow result processor passed")
            return True
        else:
            print("❌ Flow result processor failed - could not save file")
            return False
        
    except Exception as e:
        print(f"❌ Flow result processor failed: {e}")
        return False


def test_cli_imports():
    """Test that the CLI script imports work correctly."""
    print("🧪 Testing CLI Imports...")
    
    try:
        # Test main CLI imports (without running the main function)
        import product_search_scraper
        
        # Test that key functions exist
        assert hasattr(product_search_scraper, 'ProductSearchScraper')
        assert hasattr(product_search_scraper, 'get_product_search_query')
        assert hasattr(product_search_scraper, 'get_search_options')
        assert hasattr(product_search_scraper, 'display_search_results')
        
        print("✅ CLI imports passed")
        return True
        
    except Exception as e:
        print(f"❌ CLI imports failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("🚀 Running Product Search System Tests")
    print("=" * 50)
    
    tests = [
        ("Schema Validation", test_schema_validation),
        ("Retailer Research Tool", test_retailer_research_tool),
        ("Validation Agent", test_validation_agent),
        ("Flow Result Processor", test_flow_result_processor),
        ("CLI Imports", test_cli_imports),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The product search system is ready to use.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
