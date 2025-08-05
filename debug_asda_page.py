#!/usr/bin/env python3
"""Debug script to investigate ASDA page loading and product visibility issues."""

import sys
import os
import asyncio

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_asda_page():
    """Debug the ASDA page to see what's happening."""
    print("🔍 Debugging ASDA page loading and product visibility...")

    try:
        from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool

        # Create tool
        tool = EcommerceStagehandTool()
        print("✅ StagehandTool created")

        # Test URL from the logs
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"

        print(f"🌐 Testing URL: {asda_url}")

        # Navigate to the page
        print("1. Navigating to ASDA page...")
        nav_result = tool._run(
            instruction=f"Navigate to {asda_url}",
            command_type="act"
        )
        print(f"   Navigation result: {nav_result}")

        # Check for popups
        print("2. Checking for popups...")
        popup_result = tool._run(
            instruction="Check for and dismiss any popups, cookie banners, or overlays",
            command_type="act"
        )
        print(f"   Popup handling: {popup_result}")

        # Observe the page structure
        print("3. Observing page structure...")
        observe_result = tool._run(
            instruction="Find all product elements, product cards, or product listings on this page",
            command_type="observe"
        )
        print(f"   Page observation: {observe_result}")

        # Try to extract page content
        print("4. Extracting page content...")
        extract_result = tool._run(
            instruction="Extract any visible product information from this page",
            command_type="extract"
        )
        print(f"   Content extraction: {extract_result}")

        # Check page source for product indicators
        print("5. Checking for product indicators...")
        indicators_result = tool._run(
            instruction="Look for elements containing text like 'product', 'price', '£', 'add to basket', or product images",
            command_type="observe"
        )
        print(f"   Product indicators: {indicators_result}")

        print("\n🎉 ASDA page debugging completed!")

    except Exception as e:
        print(f"\n❌ ASDA page debugging failed: {str(e)}")
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
    print("🔧 ASDA Page Debugging Script\n")
    debug_asda_page()
