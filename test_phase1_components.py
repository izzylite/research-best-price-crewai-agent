#!/usr/bin/env python3
"""
Comprehensive test suite for Phase 1 components of the multi-vendor ecommerce scraping system.

Tests:
1. Standardized Schema Implementation
2. State Management Framework  
3. Category Discovery System
4. Enhanced CLI Interface (basic validation)
"""

import sys
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_standardized_schema():
    """Test the standardized product schema implementation."""
    print("🧪 Testing Standardized Schema Implementation...")
    
    try:
        from ecommerce_scraper.schemas.standardized_product import (
            StandardizedProduct, StandardizedPrice, ProductBatch
        )
        
        # Test 1: Create a valid product
        print("  ✓ Testing valid product creation...")
        product = StandardizedProduct(
            name="Test Product",
            description="A sample product for testing",
            price=StandardizedPrice(amount=19.99, currency="GBP"),
            image_url="https://example.com/image.jpg",
            category="electronics",
            vendor="test_vendor",
            weight="500g"
        )
        
        assert product.name == "Test Product"
        assert product.price.amount == 19.99
        assert product.price.currency == "GBP"
        assert product.vendor == "test_vendor"
        print("    ✅ Valid product creation successful")
        
        # Test 2: Test data validation
        print("  ✓ Testing data validation...")
        try:
            invalid_product = StandardizedProduct(
                name="",  # Invalid: empty name
                description="Test",
                price=StandardizedPrice(amount=19.99, currency="GBP"),
                image_url="https://example.com/image.jpg",
                category="electronics",
                vendor="test_vendor"
            )
            print("    ❌ Validation should have failed for empty name")
            return False
        except Exception:
            print("    ✅ Validation correctly rejected empty name")
        
        # Test 3: Test ProductBatch
        print("  ✓ Testing ProductBatch functionality...")
        products = [product for _ in range(3)]
        batch = ProductBatch(
            products=products,
            metadata={"test": "batch", "count": len(products)}
        )
        
        assert len(batch.products) == 3
        assert batch.metadata["count"] == 3
        print("    ✅ ProductBatch creation successful")
        
        # Test 4: Test serialization
        print("  ✓ Testing JSON serialization...")
        product_dict = product.model_dump()
        assert "name" in product_dict
        assert "scraped_at" in product_dict
        print("    ✅ JSON serialization successful")
        
        print("✅ Standardized Schema Implementation: PASSED\n")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_state_management():
    """Test the state management framework."""
    print("🧪 Testing State Management Framework...")
    
    try:
        from ecommerce_scraper.state.state_manager import (
            StateManager, PaginationState, SessionStatus, PaginationMethod
        )
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test 1: StateManager initialization
            print("  ✓ Testing StateManager initialization...")
            state_manager = StateManager(state_dir=temp_dir)
            assert state_manager.state_dir.exists()
            print("    ✅ StateManager initialized successfully")
            
            # Test 2: Session creation
            print("  ✓ Testing session creation...")
            session_id = state_manager.create_session()
            assert session_id is not None
            assert session_id in state_manager.sessions
            print(f"    ✅ Session created: {session_id}")
            
            # Test 3: Pagination state creation
            print("  ✓ Testing pagination state creation...")
            state = state_manager.create_pagination_state(
                session_id=session_id,
                vendor="test_vendor",
                category="test_category",
                max_pages=10
            )
            
            assert state.vendor == "test_vendor"
            assert state.category == "test_category"
            assert state.max_pages == 10
            assert state.current_page == 1
            print("    ✅ Pagination state created successfully")
            
            # Test 4: State persistence
            print("  ✓ Testing state persistence...")
            state.update_progress(5, "https://example.com/product1")
            state.advance_page()
            state_manager.update_pagination_state(state)
            
            # Retrieve state
            retrieved_state = state_manager.get_pagination_state(
                session_id, "test_vendor", "test_category"
            )
            
            assert retrieved_state.products_scraped == 5
            assert retrieved_state.current_page == 2
            print("    ✅ State persistence working correctly")
            
            # Test 5: Session summary
            print("  ✓ Testing session summary...")
            summary = state_manager.get_session_summary(session_id)
            assert "session_id" in summary
            assert summary["total_vendor_categories"] == 1
            assert summary["total_products_scraped"] == 5
            print("    ✅ Session summary generated successfully")
            
            # Test 6: Resume functionality
            print("  ✓ Testing resume functionality...")
            resumable_sessions = state_manager.get_resumable_sessions()
            assert len(resumable_sessions) >= 1
            print("    ✅ Resume functionality working")
        
        print("✅ State Management Framework: PASSED\n")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_category_discovery():
    """Test the category discovery system."""
    print("🧪 Testing Category Discovery System...")
    
    try:
        from ecommerce_scraper.agents.category_discoverer import (
            CategoryDiscovererAgent, CategoryMapper
        )
        
        # Test 1: CategoryMapper utility functions
        print("  ✓ Testing CategoryMapper utilities...")
        
        # Test category name normalization
        normalized = CategoryMapper.normalize_category_name("  Shop Electronics Products  ")
        assert normalized == "electronics"
        print("    ✅ Category name normalization working")
        
        # Test product count extraction
        count = CategoryMapper.extract_product_count("150+ items")
        assert count == 180  # 150 * 1.2 for "+" indicator
        print("    ✅ Product count extraction working")
        
        # Test category ID generation
        category_id = CategoryMapper.generate_category_id("Electronics & Gadgets", "/category/electronics")
        assert category_id == "electronics"
        print("    ✅ Category ID generation working")
        
        # Test 2: CategoryDiscovererAgent initialization
        print("  ✓ Testing CategoryDiscovererAgent initialization...")
        agent = CategoryDiscovererAgent(tools=[], llm=None)
        assert agent.agent is not None
        print("    ✅ CategoryDiscovererAgent initialized successfully")
        
        # Test 3: Task creation
        print("  ✓ Testing task creation...")
        task = agent.create_category_discovery_task(
            website_url="https://example.com",
            vendor_name="test_vendor"
        )
        assert task is not None
        assert "test_vendor" in task.description
        print("    ✅ Category discovery task created successfully")
        
        # Test 4: Category hierarchy building
        print("  ✓ Testing category hierarchy building...")
        sample_categories = [
            {"id": "electronics", "name": "Electronics", "parent_category": None},
            {"id": "phones", "name": "Phones", "parent_category": "electronics"},
            {"id": "laptops", "name": "Laptops", "parent_category": "electronics"}
        ]
        
        hierarchy = CategoryMapper.build_category_hierarchy(sample_categories)
        assert "main_categories" in hierarchy
        assert len(hierarchy["main_categories"]) == 1
        assert "electronics" in hierarchy["subcategories"]
        print("    ✅ Category hierarchy building working")
        
        # Test 5: Category filtering
        print("  ✓ Testing category filtering...")
        filtered = CategoryMapper.filter_categories_by_criteria(
            sample_categories,
            min_products=5,
            exclude_patterns=["clearance"]
        )
        assert len(filtered) == len(sample_categories)  # No filtering should occur with test data
        print("    ✅ Category filtering working")
        
        print("✅ Category Discovery System: PASSED\n")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_enhanced_cli_interface():
    """Test the enhanced CLI interface (basic validation)."""
    print("🧪 Testing Enhanced CLI Interface...")
    
    try:
        # Test 1: Import validation
        print("  ✓ Testing CLI interface imports...")
        import enhanced_interactive_scraper
        print("    ✅ Enhanced interactive scraper imported successfully")
        
        # Test 2: UK_VENDORS configuration
        print("  ✓ Testing UK_VENDORS configuration...")
        uk_vendors = enhanced_interactive_scraper.UK_VENDORS
        assert len(uk_vendors) == 10
        
        required_vendors = [
            "asda", "costco", "waitrose", "tesco", "hamleys",
            "mamasandpapas", "selfridges", "next", "primark", "thetoyshop"
        ]
        
        for vendor in required_vendors:
            assert vendor in uk_vendors
            assert "name" in uk_vendors[vendor]
            assert "url" in uk_vendors[vendor]
            assert "type" in uk_vendors[vendor]
        
        print("    ✅ All 10 UK vendors configured correctly")
        
        # Test 3: Site configuration integration
        print("  ✓ Testing site configuration integration...")
        from ecommerce_scraper.config.sites import get_supported_uk_vendors
        supported_vendors = get_supported_uk_vendors()
        assert len(supported_vendors) == 10
        print("    ✅ Site configuration integration working")
        
        print("✅ Enhanced CLI Interface: PASSED\n")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_site_configurations():
    """Test the UK retail site configurations."""
    print("🧪 Testing UK Retail Site Configurations...")
    
    try:
        from ecommerce_scraper.config.sites import (
            get_site_config_by_vendor, get_supported_uk_vendors, 
            get_all_supported_vendors, SITE_CONFIGS
        )
        
        # Test 1: UK vendors support
        print("  ✓ Testing UK vendors support...")
        uk_vendors = get_supported_uk_vendors()
        assert len(uk_vendors) == 10
        
        expected_vendors = [
            "asda", "costco", "waitrose", "tesco", "hamleys",
            "mamasandpapas", "selfridges", "next", "primark", "thetoyshop"
        ]
        
        for vendor in expected_vendors:
            assert vendor in uk_vendors
        print("    ✅ All 10 UK vendors supported")
        
        # Test 2: Site configuration retrieval
        print("  ✓ Testing site configuration retrieval...")
        for vendor in uk_vendors:
            config = get_site_config_by_vendor(vendor)
            assert config is not None
            assert hasattr(config, 'name')
            assert hasattr(config, 'base_url')
            assert hasattr(config, 'selectors')
            assert hasattr(config, 'navigation_instructions')
            assert hasattr(config, 'extraction_instructions')
        print("    ✅ Site configurations retrieved successfully")
        
        # Test 3: Configuration completeness
        print("  ✓ Testing configuration completeness...")
        asda_config = get_site_config_by_vendor("asda")
        assert asda_config.name == "ASDA"
        assert "asda.com" in asda_config.base_url
        assert "search_box" in asda_config.selectors
        assert "handle_popups" in asda_config.navigation_instructions
        print("    ✅ Configuration completeness verified")
        
        # Test 4: All supported vendors
        print("  ✓ Testing all supported vendors...")
        all_vendors = get_all_supported_vendors()
        assert len(all_vendors) >= 14  # 10 UK + 4 international
        print("    ✅ All supported vendors working")
        
        print("✅ UK Retail Site Configurations: PASSED\n")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Run all Phase 1 component tests."""
    print("🚀 Starting Phase 1 Component Testing\n")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Standardized Schema", test_standardized_schema()))
    test_results.append(("State Management", test_state_management()))
    test_results.append(("Category Discovery", test_category_discovery()))
    test_results.append(("Enhanced CLI Interface", test_enhanced_cli_interface()))
    test_results.append(("Site Configurations", test_site_configurations()))
    
    # Summary
    print("=" * 60)
    print("📊 PHASE 1 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL PHASE 1 COMPONENTS WORKING CORRECTLY!")
        print("✅ Ready to proceed with Phase 2 testing")
    else:
        print(f"\n⚠️  {total - passed} component(s) need attention")
        print("❌ Fix issues before proceeding to Phase 2")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
