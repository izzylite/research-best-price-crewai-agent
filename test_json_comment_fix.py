#!/usr/bin/env python3
"""Test script to verify JSON comment cleaning functionality."""

import json
import re

def clean_json_comments(json_str: str) -> str:
    """Remove JSON comments that break parsing."""
    # Remove // comments that appear on their own lines
    cleaned = re.sub(r'\s*//.*$', '', json_str, flags=re.MULTILINE)
    # Remove trailing commas before closing brackets/braces
    cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
    return cleaned

def test_json_comment_cleaning():
    """Test the JSON comment cleaning functionality."""
    
    # Test case 1: JSON with comment that breaks parsing
    broken_json = '''[
  {
    "name": "Product 1",
    "price": 10.99
  },
  {
    "name": "Product 2", 
    "price": 15.99
  }
  // Additional products omitted for brevity
]'''
    
    print("🧪 Testing JSON Comment Cleaning")
    print("=" * 50)
    
    print("\n1. Original broken JSON:")
    print(broken_json)
    
    print("\n2. Attempting to parse original (should fail):")
    try:
        json.loads(broken_json)
        print("   ❌ Unexpected success - should have failed")
    except json.JSONDecodeError as e:
        print(f"   ✅ Expected failure: {e}")
    
    print("\n3. Cleaning JSON comments:")
    cleaned_json = clean_json_comments(broken_json)
    print(cleaned_json)
    
    print("\n4. Attempting to parse cleaned JSON:")
    try:
        parsed = json.loads(cleaned_json)
        print(f"   ✅ Success! Parsed {len(parsed)} products")
        for i, product in enumerate(parsed):
            print(f"      Product {i+1}: {product['name']} - £{product['price']}")
    except json.JSONDecodeError as e:
        print(f"   ❌ Still failed: {e}")

if __name__ == "__main__":
    test_json_comment_cleaning()
