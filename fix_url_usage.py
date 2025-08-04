#!/usr/bin/env python3
"""
Fix URL usage in CrewAI ecommerce scraper.
Enhances the ProductScraperAgent task description to ensure the agent uses the correct URL.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def enhance_product_scraper_task():
    """Enhance the ProductScraperAgent task description to be more explicit about URL usage."""
    
    print("🔧 Enhancing ProductScraperAgent task description...")
    
    # Read the current file
    file_path = "ecommerce_scraper/agents/product_scraper.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the task description in create_direct_category_scraping_task
        old_task_description = '''task_description = f"""
        Scrape products from url.

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}
        Max Pages: {max_pages or 'unlimited'}
        URL: {category_url}'''
        
        # Enhanced task description with explicit URL instructions
        new_task_description = '''task_description = f"""
        Scrape products from the specified category URL using the Web Automation Tool (Stagehand).

        CRITICAL INSTRUCTIONS:
        1. **MUST USE THIS EXACT URL**: {category_url}
        2. **DO NOT modify, truncate, or change this URL in any way**
        3. **Navigate directly to this URL using the Web Automation Tool**
        4. **Verify you are on the correct page before extracting products**

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}
        Max Pages: {max_pages or 'unlimited'}
        
        TARGET URL (USE EXACTLY AS PROVIDED): {category_url}
        
        STEP-BY-STEP PROCESS:
        1. Use Web Automation Tool to navigate to: {category_url}
        2. Handle any popups, banners, or consent dialogs immediately
        3. Verify the main product listing is visible and accessible
        4. Extract product data from the category page
        5. Handle pagination if max_pages allows multiple pages'''
        
        if old_task_description in content:
            content = content.replace(old_task_description, new_task_description)
            
            # Write the enhanced content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Enhanced ProductScraperAgent task description")
            print("📋 Added explicit URL usage instructions")
            print("🎯 Agent will now be more likely to use the correct URL")
            return True
        else:
            print("❌ Could not find the target task description to replace")
            return False
            
    except Exception as e:
        print(f"❌ Error enhancing task description: {e}")
        return False

def add_url_validation_to_stagehand_tool():
    """Add URL validation and logging to StagehandTool for better debugging."""
    
    print("\n🔧 Adding URL validation to StagehandTool...")
    
    file_path = "ecommerce_scraper/tools/stagehand_tool.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the navigation section and enhance it
        old_navigation = '''                try:
                    print(f"🌐 Navigating to: {url[:100]}{'...' if len(url) > 100 else ''}")
                    print(f"📏 Full URL length: {len(url)} characters")

                    # Use the full URL for navigation
                    run_async_safely(stagehand.page.goto(url))'''
        
        new_navigation = '''                try:
                    print(f"🌐 Navigating to: {url[:100]}{'...' if len(url) > 100 else ''}")
                    print(f"📏 Full URL length: {len(url)} characters")
                    
                    # CRITICAL: Validate URL before navigation
                    if not url.startswith(('http://', 'https://')):
                        return f"Error: Invalid URL protocol. URL must start with http:// or https://. Got: {url[:100]}"
                    
                    if len(url) > 2048:
                        print(f"⚠️ Warning: Very long URL ({len(url)} chars), but proceeding...")
                    
                    # Log the exact URL being used for debugging
                    print(f"🔍 EXACT URL BEING USED: {url}")
                    
                    # Use the full URL for navigation
                    run_async_safely(stagehand.page.goto(url))'''
        
        if old_navigation in content:
            content = content.replace(old_navigation, new_navigation)
            
            # Write the enhanced content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Enhanced StagehandTool URL validation")
            print("🔍 Added detailed URL logging for debugging")
            return True
        else:
            print("❌ Could not find the target navigation code to replace")
            return False
            
    except Exception as e:
        print(f"❌ Error enhancing StagehandTool: {e}")
        return False

def test_enhanced_scraper():
    """Test the enhanced scraper with the problematic URL."""
    
    print("\n🧪 Testing enhanced scraper...")
    
    try:
        from ecommerce_scraper.main import EcommerceScraper
        
        test_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        vendor = "asda"
        category_name = "Fruit, Veg & Flowers > Fruit"
        
        print(f"📍 Test URL: {test_url}")
        print(f"🏪 Vendor: {vendor}")
        print(f"📂 Category: {category_name}")
        
        # Create scraper instance
        scraper = EcommerceScraper(verbose=True)
        
        # Test task creation with enhanced description
        temp_session_id = f"enhanced_test"
        
        scraping_task = scraper.product_scraper.create_direct_category_scraping_task(
            vendor=vendor,
            category=category_name,
            category_url=test_url,
            session_id=temp_session_id,
            max_pages=1
        )
        
        print(f"✅ Enhanced task created successfully")
        
        # Check if the enhanced instructions are in the task description
        task_desc = scraping_task.description
        has_critical_instructions = "CRITICAL INSTRUCTIONS" in task_desc
        has_exact_url = "TARGET URL (USE EXACTLY AS PROVIDED)" in task_desc
        has_step_by_step = "STEP-BY-STEP PROCESS" in task_desc
        
        print(f"🔍 Enhanced Task Features:")
        print(f"   Critical Instructions: {'✅' if has_critical_instructions else '❌'}")
        print(f"   Exact URL Section: {'✅' if has_exact_url else '❌'}")
        print(f"   Step-by-Step Process: {'✅' if has_step_by_step else '❌'}")
        
        return has_critical_instructions and has_exact_url and has_step_by_step
        
    except Exception as e:
        print(f"❌ Enhanced scraper test failed: {e}")
        return False

def main():
    """Apply all enhancements to fix URL usage."""
    print("🚀 Fixing URL usage in CrewAI ecommerce scraper...")
    print("=" * 60)
    
    results = []
    
    # Enhancement 1: Improve task description
    results.append(("Enhanced Task Description", enhance_product_scraper_task()))
    
    # Enhancement 2: Add URL validation to StagehandTool
    results.append(("Enhanced StagehandTool", add_url_validation_to_stagehand_tool()))
    
    # Test 3: Verify enhancements
    results.append(("Enhanced Scraper Test", test_enhanced_scraper()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ENHANCEMENT RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for enhancement_name, passed in results:
        status = "✅ SUCCESS" if passed else "❌ FAILED"
        print(f"{status} {enhancement_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All enhancements applied successfully!")
        print("💡 The scraper should now use the full URL correctly.")
        print("🧪 Test with: python enhanced_interactive_scraper.py")
    else:
        print("🚨 Some enhancements failed!")
        print("💡 Check the failed enhancements above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
