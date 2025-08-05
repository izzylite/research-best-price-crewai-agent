#!/usr/bin/env python3
"""Test Flow integration to ensure everything works together."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_flow_integration():
    """Test the complete Flow integration."""
    print("Testing Flow integration...")
    
    try:
        # Test imports
        print("1. Testing imports...")
        from ecommerce_scraper.main import EcommerceScraper
        from ecommerce_scraper.workflows.ecommerce_flow import EcommerceScrapingFlow
        from ecommerce_scraper.workflows.flow_utils import FlowResultProcessor, FlowStateManager, FlowPerformanceMonitor
        print("   ✅ All imports successful")
        
        # Test EcommerceScraper initialization
        print("2. Testing EcommerceScraper initialization...")
        scraper = EcommerceScraper(verbose=True)
        print("   ✅ EcommerceScraper created successfully")
        
        # Test architecture info
        print("3. Testing architecture info...")
        info = scraper.get_architecture_info()
        print(f"   Architecture type: {info['architecture_type']}")
        assert info['architecture_type'] == 'crewai_flow', f"Expected 'crewai_flow', got {info['architecture_type']}"
        print("   ✅ Architecture info correct")
        
        # Test Flow creation
        print("4. Testing Flow creation...")
        flow = EcommerceScrapingFlow(verbose=True)
        print("   ✅ EcommerceScrapingFlow created successfully")
        
        # Test agent creation within Flow
        print("5. Testing agent creation...")
        nav_agent = flow._get_navigation_agent()
        ext_agent = flow._get_extraction_agent()
        val_agent = flow._get_validation_agent()
        print("   ✅ All agents created successfully")
        
        # Test task creation methods
        print("6. Testing task creation methods...")
        assert hasattr(nav_agent, 'create_navigation_task'), "NavigationAgent missing create_navigation_task"
        assert hasattr(ext_agent, 'create_extraction_task'), "ExtractionAgent missing create_extraction_task"
        assert hasattr(val_agent, 'create_validation_task'), "ValidationAgent missing create_validation_task"
        print("   ✅ All task creation methods exist")
        
        # Test Flow utilities
        print("7. Testing Flow utilities...")
        monitor = FlowPerformanceMonitor()
        monitor.start_monitoring()
        monitor.checkpoint("test_checkpoint")
        summary = monitor.get_performance_summary()
        assert 'total_duration_seconds' in summary, "Performance summary missing duration"
        print("   ✅ Flow utilities working")
        
        print("\n🎉 ALL FLOW INTEGRATION TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Flow integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_flow_integration()
    sys.exit(0 if success else 1)
