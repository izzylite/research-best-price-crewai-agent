#!/usr/bin/env python3
"""Test script to validate URL extraction functionality."""

import sys
import json
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_interactive_scraper import extract_urls_from_selections, UK_VENDORS

def test_url_extraction():
    """Test the URL extraction functionality."""
    print("🧪 Testing URL extraction functionality...")
    
    # Test data: select ASDA with a few categories
    vendors = ["asda"]
    vendor_categories = {
        "asda": [1, 2]  # Rollback and Summer categories
    }
    
    print(f"Test vendors: {vendors}")
    print(f"Test categories: {vendor_categories}")
    
    # Extract URLs
    try:
        scraping_urls = extract_urls_from_selections(vendors, vendor_categories)
        
        print(f"\n✅ Successfully extracted {len(scraping_urls)} URLs:")
        for i, url_info in enumerate(scraping_urls, 1):
            print(f"  {i}. {url_info['vendor_name']} - {url_info['category_name']}")
            print(f"     URL: {url_info['url']}")
            print(f"     Type: {url_info['type']}")
            print()
        
        return scraping_urls
        
    except Exception as e:
        print(f"❌ Error extracting URLs: {e}")
        return []

def test_batch_processor_integration():
    """Test integration with batch processor."""
    print("🧪 Testing batch processor integration...")
    
    # Get URLs from extraction test
    scraping_urls = test_url_extraction()
    
    if not scraping_urls:
        print("❌ No URLs to test with")
        return
    
    try:
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
        
        print(f"Created {len(jobs)} test jobs")
        
        # Add jobs to processor
        session_id = "test_session"
        job_ids = batch_processor.add_url_based_jobs(jobs, session_id)
        
        print(f"✅ Successfully added {len(job_ids)} jobs to batch processor")
        print(f"Job IDs: {job_ids}")
        
        # Test job status
        for job_id in job_ids:
            status = batch_processor.get_job_status(job_id)
            if status:
                print(f"Job {job_id}: {status['status']}")
            else:
                print(f"❌ Could not get status for job {job_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing batch processor: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting URL extraction and batch processor tests...\n")
    
    # Test URL extraction
    urls_success = test_url_extraction()
    
    print("\n" + "="*60 + "\n")
    
    # Test batch processor integration
    batch_success = test_batch_processor_integration()
    
    print("\n" + "="*60 + "\n")
    
    if urls_success and batch_success:
        print("🎉 All tests passed! The scraping execution implementation is working.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
