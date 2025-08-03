"""Example of scraping products from Amazon using the ecommerce scraper."""

import json
import os
from dotenv import load_dotenv
from ecommerce_scraper import EcommerceScraper, scrape_product, search_and_scrape

# Load environment variables
load_dotenv()


def scrape_single_amazon_product():
    """Example: Scrape a single product from Amazon."""
    print("🛒 Example: Scraping a single Amazon product")
    print("=" * 50)
    
    # Example Amazon product URL (replace with actual product URL)
    product_url = "https://www.amazon.com/dp/B08N5WRWNW"  # Example: Echo Dot
    
    try:
        # Scrape the product
        result = scrape_product(product_url, site_type="amazon", verbose=True)
        
        if result["success"]:
            print("\n✅ Successfully scraped product!")
            print(f"📦 Product URL: {result['product_url']}")
            print(f"🏪 Site Type: {result['site_type']}")
            
            # Parse the product data
            product_data = result["data"]
            if isinstance(product_data, str):
                try:
                    product_data = json.loads(product_data)
                except json.JSONDecodeError:
                    print("⚠️  Raw data (not JSON):")
                    print(product_data)
                    return
            
            # Display key product information
            print("\n📋 Product Information:")
            print(f"  Title: {product_data.get('title', 'N/A')}")
            print(f"  Price: {product_data.get('price', 'N/A')}")
            print(f"  Brand: {product_data.get('brand', 'N/A')}")
            print(f"  Availability: {product_data.get('availability', 'N/A')}")
            print(f"  Rating: {product_data.get('rating', 'N/A')}")
            
            # Save to file
            with open("amazon_product_example.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            print("\n💾 Full data saved to 'amazon_product_example.json'")
            
        else:
            print(f"❌ Failed to scrape product: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def scrape_multiple_amazon_products():
    """Example: Scrape multiple products from Amazon."""
    print("\n🛒 Example: Scraping multiple Amazon products")
    print("=" * 50)
    
    # Example Amazon product URLs (replace with actual product URLs)
    product_urls = [
        "https://www.amazon.com/dp/B08N5WRWNW",  # Echo Dot
        "https://www.amazon.com/dp/B07XJ8C8F5",  # Fire TV Stick
        "https://www.amazon.com/dp/B08KRV7S22",  # Echo Show
    ]
    
    try:
        # Create scraper instance
        with EcommerceScraper(verbose=True) as scraper:
            results = scraper.scrape_products(product_urls, site_type="amazon")
        
        # Process results
        successful_scrapes = [r for r in results if r["success"]]
        failed_scrapes = [r for r in results if not r["success"]]
        
        print(f"\n📊 Results Summary:")
        print(f"  ✅ Successful: {len(successful_scrapes)}")
        print(f"  ❌ Failed: {len(failed_scrapes)}")
        
        # Display successful products
        for i, result in enumerate(successful_scrapes, 1):
            print(f"\n📦 Product {i}:")
            product_data = result["data"]
            if isinstance(product_data, str):
                try:
                    product_data = json.loads(product_data)
                except json.JSONDecodeError:
                    continue
            
            print(f"  URL: {result['product_url']}")
            print(f"  Title: {product_data.get('title', 'N/A')}")
            print(f"  Price: {product_data.get('price', 'N/A')}")
        
        # Display failed products
        for i, result in enumerate(failed_scrapes, 1):
            print(f"\n❌ Failed Product {i}:")
            print(f"  URL: {result['product_url']}")
            print(f"  Error: {result.get('error', 'Unknown error')}")
        
        # Save all results
        with open("amazon_products_example.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\n💾 All results saved to 'amazon_products_example.json'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def search_amazon_products():
    """Example: Search for products on Amazon and scrape results."""
    print("\n🔍 Example: Searching Amazon for products")
    print("=" * 50)
    
    search_query = "wireless bluetooth headphones"
    amazon_url = "https://www.amazon.com"
    max_products = 5
    
    try:
        result = search_and_scrape(
            search_query=search_query,
            site_url=amazon_url,
            max_products=max_products,
            verbose=True
        )
        
        if result["success"]:
            print(f"\n✅ Successfully searched for '{search_query}'!")
            
            search_data = result["data"]
            if isinstance(search_data, str):
                try:
                    search_data = json.loads(search_data)
                except json.JSONDecodeError:
                    print("⚠️  Raw search data (not JSON):")
                    print(search_data)
                    return
            
            # Display search results
            products = search_data.get("products", [])
            print(f"\n📋 Found {len(products)} products:")
            
            for i, product in enumerate(products, 1):
                print(f"\n📦 Product {i}:")
                print(f"  Title: {product.get('title', 'N/A')}")
                print(f"  Price: {product.get('price', 'N/A')}")
                print(f"  Rating: {product.get('rating', 'N/A')}")
                print(f"  URL: {product.get('source_url', 'N/A')}")
            
            # Save search results
            with open("amazon_search_example.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            print("\n💾 Search results saved to 'amazon_search_example.json'")
            
        else:
            print(f"❌ Search failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Run all Amazon examples."""
    print("🚀 Amazon Scraping Examples")
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
        # Run examples
        scrape_single_amazon_product()
        scrape_multiple_amazon_products()
        search_amazon_products()
        
        print("\n🎉 All Amazon examples completed!")
        print("\nFiles created:")
        print("  - amazon_product_example.json")
        print("  - amazon_products_example.json")
        print("  - amazon_search_example.json")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
