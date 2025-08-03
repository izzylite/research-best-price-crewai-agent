#!/usr/bin/env python3
"""
Test script to validate the enhanced interactive CLI interface.
This script tests the CLI components without requiring user interaction.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_cli_imports():
    """Test that all CLI components can be imported."""
    print("🧪 Testing CLI Imports...")
    
    try:
        import enhanced_interactive_scraper
        print("  ✅ Enhanced interactive scraper imported successfully")
        
        # Test UK_VENDORS configuration
        uk_vendors = enhanced_interactive_scraper.UK_VENDORS
        print(f"  ✅ UK_VENDORS loaded: {len(uk_vendors)} vendors")
        
        # Test vendor details
        for vendor_id, vendor_info in uk_vendors.items():
            assert "name" in vendor_info
            assert "url" in vendor_info
            assert "type" in vendor_info
            print(f"    ✓ {vendor_info['name']} ({vendor_info['type']})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ CLI import test failed: {e}")
        return False


def test_site_config_integration():
    """Test integration with site configurations."""
    print("\n🧪 Testing Site Configuration Integration...")
    
    try:
        from ecommerce_scraper.config.sites import get_supported_uk_vendors, get_site_config_by_vendor
        
        # Get supported vendors
        supported_vendors = get_supported_uk_vendors()
        print(f"  ✅ Supported UK vendors: {len(supported_vendors)}")
        
        # Test each vendor configuration
        for vendor in supported_vendors:
            config = get_site_config_by_vendor(vendor)
            assert config is not None
            print(f"    ✓ {config.name} configuration loaded")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Site config integration test failed: {e}")
        return False


def test_cli_functions():
    """Test CLI utility functions."""
    print("\n🧪 Testing CLI Utility Functions...")
    
    try:
        import enhanced_interactive_scraper
        
        # Test if main functions exist
        assert hasattr(enhanced_interactive_scraper, 'UK_VENDORS')
        print("  ✅ UK_VENDORS configuration exists")
        
        # Test vendor data structure
        sample_vendor = list(enhanced_interactive_scraper.UK_VENDORS.values())[0]
        required_fields = ['name', 'url', 'type']
        for field in required_fields:
            assert field in sample_vendor
        print("  ✅ Vendor data structure is correct")
        
        return True
        
    except Exception as e:
        print(f"  ❌ CLI utility functions test failed: {e}")
        return False


def main():
    """Run CLI validation tests."""
    print("🚀 Testing Enhanced Interactive CLI Interface")
    print("=" * 60)
    
    test_results = []
    
    # Run tests
    test_results.append(("CLI Imports", test_cli_imports()))
    test_results.append(("Site Config Integration", test_site_config_integration()))
    test_results.append(("CLI Utility Functions", test_cli_functions()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 CLI TEST SUMMARY")
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
        print("\n🎉 ENHANCED CLI INTERFACE IS READY!")
        print("✅ You can now run: python enhanced_interactive_scraper.py")
    else:
        print(f"\n⚠️  {total - passed} CLI component(s) need attention")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
