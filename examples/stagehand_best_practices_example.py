#!/usr/bin/env python3
"""
Stagehand Best Practices Example

This example demonstrates how to use the enhanced EcommerceStagehandTool
with all the best practices from the official Stagehand documentation.

Features demonstrated:
- Variable substitution for sensitive data
- Action previewing with observe()
- Atomic and specific instructions
- Caching for repeated operations
- Proper error handling and retry logic
- Context manager pattern
"""

import os
import json
from dotenv import load_dotenv
from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool

# Load environment variables
load_dotenv()

def demonstrate_variable_substitution():
    """Demonstrate secure variable substitution."""
    print("=" * 60)
    print("🔐 DEMONSTRATING VARIABLE SUBSTITUTION")
    print("=" * 60)

    # Use context manager for automatic cleanup
    with EcommerceStagehandTool.create_with_context() as tool:
        # Navigate to a demo login page
        result = tool._run(
            instruction="Navigate to the demo login page",
            url="https://demo.vercel.store",
            command_type="act"
        )
        print(f"Navigation: {result}")

        # Example: Secure form filling with variables
        # Instead of: "Type 'user@example.com' in the email field"
        # Use variables to avoid sending sensitive data to LLMs
        result = tool._run(
            instruction="Type %email% in the email field",
            command_type="act",
            variables={"email": "secure.user@example.com"}
        )
        print(f"Secure input: {result}")

        # Show session info
        session_info = tool.get_session_info()
        print(f"Session info: {session_info}")
        # Context manager will automatically call tool.close()

def demonstrate_action_previewing():
    """Demonstrate action previewing with observe()."""
    print("\n" + "=" * 60)
    print("👀 DEMONSTRATING ACTION PREVIEWING")
    print("=" * 60)

    with EcommerceStagehandTool.create_with_context() as tool:
        # Navigate to product page
        tool._run(
            instruction="Navigate to product page",
            url="https://demo.vercel.store/products/acme-mug",
            command_type="act"
        )
        
        # Preview actions before executing them
        preview_result = tool.preview_action(
            instruction="Find the add to cart button"
        )
        print(f"Preview result: {preview_result}")
        
        # Preview form interactions
        form_preview = tool.preview_action(
            instruction="Find all form input fields on the page"
        )
        print(f"Form preview: {form_preview}")

        # Show cache stats
        cache_stats = tool.get_cache_stats()
        print(f"Cache stats: {cache_stats}")

def demonstrate_atomic_instructions():
    """Demonstrate atomic and specific instructions."""
    print("\n" + "=" * 60)
    print("⚛️ DEMONSTRATING ATOMIC INSTRUCTIONS")
    print("=" * 60)
    
    tool = EcommerceStagehandTool()
    
    try:
        # Navigate first
        tool._run(
            instruction="Navigate to the product page",
            url="https://demo.vercel.store/products/acme-mug",
            command_type="act"
        )
        
        # ❌ BAD: Broad, multi-step instruction
        # "Fill out the form and submit it"
        
        # ✅ GOOD: Atomic, specific instructions
        
        # Step 1: Extract product title specifically
        title_result = tool._run(
            instruction="Extract the product title from the main heading",
            command_type="extract"
        )
        print(f"Product title: {title_result}")
        
        # Step 2: Extract price specifically
        price_result = tool._run(
            instruction="Extract the current price displayed on the page",
            command_type="extract"
        )
        print(f"Product price: {price_result}")
        
        # Step 3: Find specific button
        button_result = tool._run(
            instruction="Find the 'Add to Cart' button",
            command_type="observe"
        )
        print(f"Button location: {button_result}")
        
    finally:
        tool.close()

def demonstrate_caching():
    """Demonstrate caching for repeated operations."""
    print("\n" + "=" * 60)
    print("💾 DEMONSTRATING CACHING")
    print("=" * 60)
    
    tool = EcommerceStagehandTool()
    
    try:
        # Navigate to product page
        tool._run(
            instruction="Navigate to product page",
            url="https://demo.vercel.store/products/acme-mug",
            command_type="act"
        )
        
        # First extraction (will be cached)
        print("First extraction (will be cached):")
        result1 = tool._run(
            instruction="Extract product information including title and price",
            command_type="extract",
            use_cache=True
        )
        print(f"Result 1: {result1[:100]}...")
        
        # Second extraction (should use cache)
        print("\nSecond extraction (should use cache):")
        result2 = tool._run(
            instruction="Extract product information including title and price",
            command_type="extract",
            use_cache=True
        )
        print(f"Result 2: {result2[:100]}...")
        
        # Verify caching worked
        print(f"\nCache hit: {result1 == result2}")
        
    finally:
        tool.close()

def demonstrate_comprehensive_extraction():
    """Demonstrate comprehensive product data extraction."""
    print("\n" + "=" * 60)
    print("📊 DEMONSTRATING COMPREHENSIVE EXTRACTION")
    print("=" * 60)
    
    tool = EcommerceStagehandTool()
    
    try:
        # Navigate to product page
        tool._run(
            instruction="Navigate to product page",
            url="https://demo.vercel.store/products/acme-circles-t-shirt",
            command_type="act"
        )
        
        # Use the enhanced extract_product_data method
        product_data = tool.extract_product_data()
        
        print("Extracted product data:")
        try:
            # Try to parse and pretty print JSON
            parsed_data = json.loads(product_data)
            print(json.dumps(parsed_data, indent=2))
        except json.JSONDecodeError:
            print(product_data)
        
    finally:
        tool.close()

def demonstrate_error_handling():
    """Demonstrate error handling and retry logic."""
    print("\n" + "=" * 60)
    print("🔄 DEMONSTRATING ERROR HANDLING")
    print("=" * 60)
    
    tool = EcommerceStagehandTool()
    
    try:
        # Try to navigate to an invalid URL (will trigger retry logic)
        result = tool._run(
            instruction="Navigate to invalid page",
            url="https://invalid-url-that-does-not-exist.com",
            command_type="act"
        )
        print(f"Invalid URL result: {result}")
        
        # Try an invalid command type
        result = tool._run(
            instruction="Test invalid command",
            command_type="invalid_command"
        )
        print(f"Invalid command result: {result}")
        
    finally:
        tool.close()

def main():
    """Run all demonstrations."""
    print("🤘 STAGEHAND BEST PRACTICES DEMONSTRATION")
    print("This example shows how to use Stagehand like a goated developer!")
    
    # Check environment variables
    required_vars = ["BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return
    
    try:
        demonstrate_variable_substitution()
        demonstrate_action_previewing()
        demonstrate_atomic_instructions()
        demonstrate_caching()
        demonstrate_comprehensive_extraction()
        demonstrate_error_handling()
        
        print("\n" + "=" * 60)
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("🎉 You're now ready to use Stagehand with best practices!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
