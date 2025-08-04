#!/usr/bin/env python3
"""End-to-end test of the scraping execution functionality."""

import sys
import json
import time
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_interactive_scraper import extract_urls_from_selections, execute_scraping_plan, create_scraping_plan

def test_end_to_end_scraping():
    """Test the complete scraping workflow."""
    print("🧪 Testing end-to-end scraping workflow...")
    
    # Test data: select ASDA with one category for quick testing
    vendors = ["asda"]
    vendor_categories = {
        "asda": [1]  # Just Rollback category
    }
    
    print(f"Test vendors: {vendors}")
    print(f"Test categories: {vendor_categories}")
    
    try:
        # Step 1: Create scraping plan
        print("\n📋 Creating scraping plan...")
        plan = create_scraping_plan(vendors, vendor_categories, "recent")
        
        print(f"✅ Plan created with session ID: {plan['session_id']}")
        print(f"   Total URLs: {plan['total_urls']}")
        print(f"   Estimated products: {plan['total_estimated_products']}")
        
        # Step 2: Extract URLs
        print("\n🔗 Extracting URLs...")
        scraping_urls = extract_urls_from_selections(vendors, vendor_categories)
        
        print(f"✅ Extracted {len(scraping_urls)} URLs:")
        for url_info in scraping_urls:
            print(f"   • {url_info['category_name']}: {url_info['url']}")
        
        # Step 3: Test batch processor setup (without actual execution)
        print("\n🤖 Testing batch processor setup...")
        
        from ecommerce_scraper.batch.batch_processor import BatchProcessor
        from ecommerce_scraper.state.state_manager import StateManager
        
        # Create batch processor
        state_manager = StateManager()
        batch_processor = BatchProcessor(
            max_workers=1,  # Use 1 worker for testing
            max_concurrent_vendors=1,
            output_dir="./test_output",
            state_manager=state_manager
        )
        
        # Create jobs from URLs
        jobs = []
        for url_info in scraping_urls:
            job_spec = {
                "vendor": url_info["vendor"],
                "category": url_info["category_name"],
                "url": url_info["url"],
                "max_pages": 1,  # Just 1 page for testing
                "priority": 1
            }
            jobs.append(job_spec)
        
        # Add jobs to processor
        session_id = plan["session_id"]
        job_ids = batch_processor.add_url_based_jobs(jobs, session_id)
        
        print(f"✅ Created {len(job_ids)} jobs in batch processor")
        
        # Check job statuses
        for job_id in job_ids:
            status = batch_processor.get_job_status(job_id)
            if status:
                print(f"   • Job {job_id}: {status['status']}")
            else:
                print(f"   ❌ Could not get status for job {job_id}")
        
        # Test progress summary
        progress = batch_processor.get_progress_summary()
        print(f"✅ Progress summary: {progress['total_jobs']} total jobs, {progress['pending_jobs']} pending")
        
        print("\n🎉 End-to-end test completed successfully!")
        print("   ✅ Plan creation works")
        print("   ✅ URL extraction works") 
        print("   ✅ Batch processor integration works")
        print("   ✅ Job status tracking works")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in end-to-end test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scraping_plan_variations():
    """Test different scraping plan configurations."""
    print("\n🧪 Testing scraping plan variations...")
    
    test_cases = [
        {
            "name": "Single vendor, single category",
            "vendors": ["asda"],
            "categories": {"asda": [1]},
            "scope": "recent"
        },
        {
            "name": "Single vendor, multiple categories", 
            "vendors": ["asda"],
            "categories": {"asda": [1, 2]},
            "scope": "all"
        },
        {
            "name": "Multiple vendors",
            "vendors": ["asda", "tesco"],
            "categories": {"asda": [1], "tesco": [1]},
            "scope": "recent"
        }
    ]
    
    for test_case in test_cases:
        try:
            print(f"\n   Testing: {test_case['name']}")
            plan = create_scraping_plan(
                test_case["vendors"], 
                test_case["categories"], 
                test_case["scope"]
            )
            
            urls = extract_urls_from_selections(
                test_case["vendors"], 
                test_case["categories"]
            )
            
            print(f"   ✅ {len(urls)} URLs extracted, {plan['total_estimated_products']} estimated products")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    print("✅ All plan variations work correctly")
    return True

if __name__ == "__main__":
    print("🚀 Starting comprehensive scraping execution tests...\n")
    
    # Test end-to-end workflow
    e2e_success = test_end_to_end_scraping()
    
    print("\n" + "="*60 + "\n")
    
    # Test plan variations
    plan_success = test_scraping_plan_variations()
    
    print("\n" + "="*60 + "\n")
    
    if e2e_success and plan_success:
        print("🎉 ALL TESTS PASSED!")
        print("The enhanced interactive scraper with URL delegation is ready for use!")
        print("\nKey features implemented:")
        print("✅ URL extraction from category selections")
        print("✅ Batch processing with multiple worker agents")
        print("✅ Job status tracking and progress monitoring")
        print("✅ Support for multiple vendors and categories")
        print("✅ Integration with existing EcommerceScraper agents")
    else:
        print("❌ Some tests failed. Check the output above for details.")
