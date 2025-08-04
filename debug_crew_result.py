#!/usr/bin/env python3
"""Debug script to understand CrewAI result structure."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.main import EcommerceScraper

def debug_crew_result():
    """Debug the crew result structure to understand why products aren't being extracted."""
    
    print("🔍 Debugging CrewAI result structure...")
    
    # Test configuration
    test_url = "https://groceries.asda.com/dept/fruit-veg-salad/fruit/1215686352935-910000975210"
    vendor = "asda"
    category_name = "Fruit, Veg & Flowers > Fruit"
    max_pages = 1
    
    try:
        with EcommerceScraper(verbose=True) as scraper:
            print(f"📍 Testing URL: {test_url}")
            print(f"🏪 Vendor: {vendor}")
            print(f"📂 Category: {category_name}")
            
            # Call the scraping method
            result = scraper.scrape_category_directly(
                category_url=test_url,
                vendor=vendor,
                category_name=category_name,
                max_pages=max_pages
            )
            
            print(f"\n📊 Result Analysis:")
            print(f"Success: {result.success}")
            print(f"Products found: {len(result.products)}")
            print(f"Session ID: {result.session_id}")
            
            # Debug the result object
            print(f"\n🔍 Result object type: {type(result)}")
            print(f"Result attributes: {dir(result)}")
            
            if hasattr(result, 'raw_crew_result'):
                crew_result = result.raw_crew_result
                print(f"\n🔍 Crew result type: {type(crew_result)}")
                print(f"Crew result attributes: {dir(crew_result)}")
                
                if hasattr(crew_result, 'tasks_output'):
                    print(f"\n📋 Tasks output available: {len(crew_result.tasks_output) if crew_result.tasks_output else 0}")
                    if crew_result.tasks_output:
                        for i, task_output in enumerate(crew_result.tasks_output):
                            print(f"  Task {i+1} type: {type(task_output)}")
                            print(f"  Task {i+1} attributes: {dir(task_output)}")
                            if hasattr(task_output, 'raw'):
                                print(f"  Task {i+1} raw data preview: {str(task_output.raw)[:200]}...")
                
                if hasattr(crew_result, 'raw'):
                    print(f"\n📄 Crew raw result preview: {str(crew_result.raw)[:200]}...")
                
                if hasattr(crew_result, 'json'):
                    print(f"\n📄 Crew json result preview: {str(crew_result.json)[:200]}...")
            
            return result.success
            
    except Exception as e:
        print(f"❌ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_crew_result()
    if success:
        print("\n✅ Debug completed successfully!")
    else:
        print("\n❌ Debug failed!")
