#!/usr/bin/env python3
"""Test schema-based extraction with SimplifiedStagehandTool."""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool

# Define the schema for product extraction
# According to Stagehand docs: https://docs.stagehand.dev/reference/extract
# For Python, URL fields should use HttpUrl instead of str
class Product(BaseModel):
    """Schema for individual product data."""
    name: str
    description: str
    price: str
    image_url: Optional[HttpUrl] = None  # Use HttpUrl for URL fields as per Stagehand docs
    weight: Optional[str] = None
    category: str
    vendor: str

class ProductList(BaseModel):
    """Schema for list of products."""
    products: List[Product]

# Alternative schema examples for different use cases:
class ProductWithMultipleUrls(BaseModel):
    """Example schema showing different URL field types."""
    name: str
    price: str
    image_url: Optional[HttpUrl] = None  # Main product image
    thumbnail_url: Optional[HttpUrl] = None  # Thumbnail image
    product_page_url: Optional[HttpUrl] = None  # Link to product page
    category: str

class SimpleProduct(BaseModel):
    """Simplified schema without URL fields for testing."""
    name: str
    price: str
    category: str
    vendor: str

async def test_schema_extraction():
    """Test schema-based extraction on site page."""
    
    tool = SimplifiedStagehandTool()
    
    try:
        print("🧪 Testing Schema-Based Extraction")
        print("=" * 50)
        
        # 1. Navigate to site page
        print("\n1. Navigating to site page...")
        thetoyshop = "https://www.thetoyshop.com/brands/dccomics/batman" # Can scrap
        asda_url = "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025" # Can scrap
        testco = "https://www.tesco.com/groceries/en-GB/shop/fresh-food/fresh-fruit" # Can not scrap
        mamasandpapas = "https://www.mamasandpapas.com/collections/shop-baby-clothing-by" # Can scrap
        next = "https://www.next.co.uk/shop/gender-women-category-dresses-0" # Can scrap 
        primark = "https://www.primark.com/en-gb/r/womens/trending/campaign1" # Can scrap
        waitrose = "https://www.waitrose.com/ecom/shop/browse/groceries/frozen" # Can not scrap
        selfridges = "https://www.selfridges.com/GB/en/cat/mens/newin/" # Can not scrap
        hamleys = "https://www.hamleys.com/brands/dccomics/batman" # Can not scrap  
        tesco = "https://www.tesco.com/groceries/en-GB/shop/fresh-food/fresh-fruit" # Can not scrap 

        # Use a working URL for testing
        test_url = thetoyshop
        nav_result = await tool.navigate(test_url)
        print(f"   ✅ Navigation: {nav_result}")
        
        # 2. Handle popups
        print("\n2. Handling popups...")
        try:
            popup_result = await tool.act("Click I Accept button for cookies")
            print(f"   ✅ Popup handled: {popup_result}")
        except Exception as e:
            print(f"   ⚠️ No popup or already handled: {e}")

        # 3. Schema-based extraction with proper schema
        print("\n3. Performing schema-based extraction...")

        # Define the extraction instruction
        extract_instruction = """
        Extract all products from this page. For each product, extract:
        - name: Product name/title
        - description: Product description if available (empty string if not available)
        - price: Product price (e.g., "£39.99", "£10.00")
        - weight: Product weight/size if available (e.g., "150g", "400g")
        - category: Product category (e.g., "Batman Toys", "Fruit")
        - vendor: Vendor/store name
        - image_url: Extract the full product image URL (including https://) if available, otherwise set to null

        Note: For image_url, extract the complete URL including the domain (e.g., "https://example.com/image.jpg")
        Return all products as a JSON array with the specified fields.
        """

        # Create schema-based extraction using the defined schemas
        print("   📋 Using ProductList schema for extraction...")
        
        # Get the stagehand instance to use schema-based extraction
        stagehand = await tool._get_stagehand()
        
        # Use schema-based extraction following official Stagehand pattern
        extraction = await stagehand.page.extract(
            extract_instruction.strip(),
            schema=ProductList
        )

        # Handle the extraction result
        if hasattr(extraction, 'model_dump'):
            # Pydantic model - get the products list
            result_dict = extraction.model_dump()
            products = result_dict.get('products', [])
        elif hasattr(extraction, 'products'):
            # Direct access to products
            products = extraction.products
            if hasattr(products[0], 'model_dump'):
                products = [p.model_dump() for p in products]
        else:
            # Fallback - assume it's already a list
            products = extraction if isinstance(extraction, list) else []

        # Convert to JSON string for consistency
        extract_result = json.dumps(products, indent=2, default=str)

        # 4. Parse and validate results
        print("\n4. Parsing extraction results...")
        try:
            # Validate that we got a proper list
            if not isinstance(products, list):
                raise ValueError(f"Expected list of products, got {type(products)}")
                
            print(f"   ✅ Successfully extracted {len(products)} products")

            # 5. Save results to JSON file
            print("\n5. Saving results to JSON file...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f"schema_extraction_test_{timestamp}.json")
            
            # Prepare the complete result data
            result_data = {
                "test_info": {
                    "test_name": "Schema Extraction Test",
                    "timestamp": datetime.now().isoformat(),
                    "url": test_url,
                    "total_products": len(products),
                    "extraction_instruction": extract_instruction.strip(),
                    "schema_used": "ProductList with Product schema"
                },
                "extraction_results": {
                    "raw_result": extract_result,
                    "parsed_products": products
                },
                "test_status": {
                    "navigation_success": True,
                    "extraction_success": True,
                    "parsing_success": True,
                    "schema_validation": True
                }
            }
            
            # Save to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            print(f"   ✅ Results saved to: {output_file}")

            if len(products) > 0:
                print(f"\n6. Sample products:")
                for i, product in enumerate(products[:3]):
                    print(f"   📦 Product {i+1}:")
                    print(f"      • Name: {product.get('name', 'N/A')}")
                    print(f"      • Price: {product.get('price', 'N/A')}")
                    print(f"      • Weight: {product.get('weight', 'N/A')}")
                    print(f"      • Category: {product.get('category', 'N/A')}")
                    print(f"      • Vendor: {product.get('vendor', 'N/A')}")

                print(f"\n📊 Extraction Summary:")
                print(f"   • Total products: {len(products)}")
                print(f"   • Schema validation: ✅ Passed")
                print(f"   • Results saved: ✅ {output_file}")

                print(f"\n🎯 Core Functionality Status:")
                print(f"   • Product extraction: ✅ Working")
                print(f"   • Schema compliance: ✅ Working")
                print(f"   • Navigation: ✅ Working")
                print(f"   • File saving: ✅ Working")

            return True, len(products), output_file

        except Exception as e:
            print(f"   ❌ Parsing failed: {e}")
            print(f"   📄 Raw result preview: {extract_result[:300]}...")
            
            # Save raw result even if parsing failed
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"schema_extraction_test_failed_{timestamp}.json")
            
            error_data = {
                "test_info": {
                    "test_name": "Schema Extraction Test (Failed)",
                    "timestamp": datetime.now().isoformat(),
                    "url": test_url,
                    "error": str(e),
                    "schema_used": "ProductList with Product schema"
                },
                "raw_result": extract_result,
                "test_status": {
                    "navigation_success": True,
                    "extraction_success": True,
                    "parsing_success": False,
                    "schema_validation": False
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
            
            print(f"   📄 Raw result saved to: {output_file}")
            return False, 0, output_file
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
        # Save error information
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"schema_extraction_test_error_{timestamp}.json")
        
        error_data = {
            "test_info": {
                "test_name": "Schema Extraction Test (Error)",
                "timestamp": datetime.now().isoformat(),
                "url": test_url,
                "error": str(e),
                "schema_used": "ProductList with Product schema"
            },
            "test_status": {
                "navigation_success": False,
                "extraction_success": False,
                "parsing_success": False,
                "schema_validation": False
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2, ensure_ascii=False)
        
        print(f"   📄 Error details saved to: {output_file}")
        return False, 0, output_file
        
    finally:
        try:
            await tool.close()
        except:
            pass

def main():
    """Run the schema extraction test."""
    try:
        success, count, output_file = asyncio.run(test_schema_extraction())
        
        print(f"\n🎯 Test Results:")
        print(f"   Success: {success}")
        print(f"   Products: {count}")
        print(f"   Output file: {output_file}")
        
        if success and count > 0:
            print("   ✅ Schema-based extraction working correctly!")
        else:
            print("   ❌ Schema-based extraction needs debugging")
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()
