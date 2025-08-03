"""Example of scraping products from generic ecommerce sites using the ecommerce scraper."""

import json
import os
from dotenv import load_dotenv
from ecommerce_scraper import EcommerceScraper, scrape_product, search_and_scrape

# Load environment variables
load_dotenv()


def scrape_shopify_store():
    """Example: Scrape products from a Shopify store."""
    print("🛒 Example: Scraping Shopify store products")
    print("=" * 50)
    
    # Example Shopify store URLs (replace with actual store URLs)
    shopify_products = [
        "https://example-store.myshopify.com/products/product-1",
        "https://another-store.com/products/awesome-product",
    ]
    
    try:
        print("⚠️  Note: Replace with real Shopify product URLs")
        
        with EcommerceScraper(verbose=True) as scraper:
            results = scraper.scrape_products(shopify_products, site_type="shopify")
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        print(f"\n📊 Results: {len(successful)} successful, {len(failed)} failed")
        
        for i, result in enumerate(successful, 1):
            product_data = result["data"]
            if isinstance(product_data, str):
                try:
                    product_data = json.loads(product_data)
                except json.JSONDecodeError:
                    continue
            
            print(f"\n📦 Shopify Product {i}:")
            print(f"  Title: {product_data.get('title', 'N/A')}")
            print(f"  Price: {product_data.get('price', 'N/A')}")
            print(f"  Variants: {len(product_data.get('variants', []))}")
            print(f"  Availability: {product_data.get('availability', 'N/A')}")
        
        # Save results
        with open("shopify_products_example.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\n💾 Results saved to 'shopify_products_example.json'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def scrape_generic_ecommerce_site():
    """Example: Scrape from a generic ecommerce site."""
    print("\n🛒 Example: Scraping generic ecommerce site")
    print("=" * 50)
    
    # Example generic ecommerce URLs
    generic_products = [
        "https://example-shop.com/product/item-123",
        "https://online-store.net/products/cool-gadget",
    ]
    
    try:
        print("⚠️  Note: Replace with real ecommerce product URLs")
        
        with EcommerceScraper(verbose=True) as scraper:
            results = scraper.scrape_products(generic_products, site_type="generic")
        
        for i, result in enumerate(results, 1):
            if result["success"]:
                product_data = result["data"]
                if isinstance(product_data, str):
                    try:
                        product_data = json.loads(product_data)
                    except json.JSONDecodeError:
                        print(f"📦 Product {i}: Raw data extracted")
                        continue
                
                print(f"\n📦 Generic Product {i}:")
                print(f"  URL: {result['product_url']}")
                print(f"  Title: {product_data.get('title', 'N/A')}")
                print(f"  Price: {product_data.get('price', 'N/A')}")
                print(f"  Description: {product_data.get('description', 'N/A')[:100]}...")
                print(f"  Images: {len(product_data.get('images', []))}")
            else:
                print(f"\n❌ Failed Product {i}: {result.get('error')}")
        
        # Save results
        with open("generic_products_example.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\n💾 Results saved to 'generic_products_example.json'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def search_multiple_sites():
    """Example: Search across multiple different ecommerce sites."""
    print("\n🔍 Example: Searching multiple ecommerce sites")
    print("=" * 50)
    
    search_sites = [
        {
            "name": "Example Electronics Store",
            "url": "https://electronics-store.com",
            "query": "smartphone"
        },
        {
            "name": "Fashion Boutique",
            "url": "https://fashion-boutique.com",
            "query": "summer dress"
        },
        {
            "name": "Home Goods Store",
            "url": "https://home-goods.com",
            "query": "coffee maker"
        }
    ]
    
    try:
        print("⚠️  Note: Replace with real ecommerce site URLs")
        
        all_results = []
        
        with EcommerceScraper(verbose=True) as scraper:
            for site in search_sites:
                print(f"\n🔍 Searching {site['name']} for '{site['query']}'")
                
                result = scraper.search_and_scrape(
                    search_query=site["query"],
                    site_url=site["url"],
                    max_products=3
                )
                
                result["site_name"] = site["name"]
                all_results.append(result)
                
                if result["success"]:
                    print(f"✅ Successfully searched {site['name']}")
                else:
                    print(f"❌ Failed to search {site['name']}: {result.get('error')}")
        
        # Summary
        successful_searches = [r for r in all_results if r["success"]]
        print(f"\n📊 Search Summary: {len(successful_searches)}/{len(search_sites)} successful")
        
        # Save all search results
        with open("multi_site_search_example.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print("💾 All search results saved to 'multi_site_search_example.json'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def adaptive_scraping_demo():
    """Example: Demonstrate adaptive scraping on unknown sites."""
    print("\n🤖 Example: Adaptive scraping demonstration")
    print("=" * 50)
    
    # Mix of different ecommerce platforms
    mixed_urls = [
        "https://unknown-store.com/product/mystery-item",
        "https://new-ecommerce.net/shop/cool-product",
        "https://custom-shop.org/items/special-deal",
    ]
    
    try:
        print("⚠️  Note: This demonstrates adaptive AI-powered extraction")
        print("Replace URLs with real ecommerce sites for testing")
        
        with EcommerceScraper(verbose=True) as scraper:
            results = []
            
            for url in mixed_urls:
                print(f"\n🔍 Adaptively scraping: {url}")
                
                # Let the scraper auto-detect site type and adapt
                result = scraper.scrape_product(url)  # No site_type specified
                results.append(result)
                
                if result["success"]:
                    print(f"✅ Successfully adapted to site structure")
                    
                    # Show what was detected
                    print(f"  Detected site type: {result.get('site_type', 'unknown')}")
                    print(f"  Extraction method: {result.get('metadata', {}).get('extraction_method', 'unknown')}")
                else:
                    print(f"❌ Adaptive scraping failed: {result.get('error')}")
        
        # Save adaptive results
        with open("adaptive_scraping_example.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\n💾 Adaptive scraping results saved to 'adaptive_scraping_example.json'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def data_validation_demo():
    """Example: Demonstrate data validation and cleaning."""
    print("\n🧹 Example: Data validation and cleaning")
    print("=" * 50)
    
    # Example raw product data (simulated)
    raw_product_data = {
        "title": "  Amazing Product!!!  ",
        "price": "$29.99",
        "original_price": "$39.99 USD",
        "description": "This is an <b>amazing</b> product with great features...",
        "images": [
            "/images/product1.jpg",
            "https://example.com/images/product2.png"
        ],
        "rating": "4.5 stars",
        "availability": "In Stock",
        "brand": "ACME Corp",
    }
    
    try:
        with EcommerceScraper(verbose=True) as scraper:
            # Validate and clean the data
            validation_result = scraper.validate_product_data(
                raw_data=raw_product_data,
                base_url="https://example-store.com"
            )
        
        if validation_result["success"]:
            print("✅ Data validation successful!")
            
            validated_data = validation_result["validated_data"]
            if isinstance(validated_data, str):
                try:
                    validated_data = json.loads(validated_data)
                except json.JSONDecodeError:
                    pass
            
            print("\n📋 Validation Results:")
            print(f"  Original title: '{raw_product_data['title']}'")
            print(f"  Cleaned title: '{validated_data.get('title', 'N/A')}'")
            print(f"  Price parsing: {validated_data.get('price', 'N/A')}")
            print(f"  Image URLs resolved: {len(validated_data.get('images', []))}")
            
            # Save validation example
            with open("data_validation_example.json", "w") as f:
                json.dump({
                    "raw_data": raw_product_data,
                    "validated_data": validated_data
                }, f, indent=2, default=str)
            print("\n💾 Validation example saved to 'data_validation_example.json'")
            
        else:
            print(f"❌ Data validation failed: {validation_result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Run all generic ecommerce examples."""
    print("🚀 Generic Ecommerce Scraping Examples")
    print("=" * 50)
    
    # Check if required environment variables are set
    required_vars = ["BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these in your .env file or environment.")
        return
    
    # Check for LLM API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Missing LLM API key. Please set either OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return
    
    print("✅ Environment variables configured!")
    
    try:
        # Run examples (most use placeholder URLs)
        print("\n⚠️  Most examples use placeholder URLs - replace with real sites for testing")
        
        # scrape_shopify_store()
        # scrape_generic_ecommerce_site()
        # search_multiple_sites()
        # adaptive_scraping_demo()
        data_validation_demo()
        
        print("\n🎉 Generic ecommerce examples completed!")
        print("\nFiles that may be created:")
        print("  - shopify_products_example.json")
        print("  - generic_products_example.json")
        print("  - multi_site_search_example.json")
        print("  - adaptive_scraping_example.json")
        print("  - data_validation_example.json")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
