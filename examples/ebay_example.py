"""Example of scraping products from eBay using the ecommerce scraper."""

import json
import os
from dotenv import load_dotenv
from ecommerce_scraper import EcommerceScraper, scrape_product, search_and_scrape

# Load environment variables
load_dotenv()


def scrape_single_ebay_product():
    """Example: Scrape a single product from eBay."""
    print("🛒 Example: Scraping a single eBay product")
    print("=" * 50)
    
    # Example eBay product URL (replace with actual product URL)
    product_url = "https://www.ebay.com/itm/123456789012"  # Replace with real eBay item
    
    try:
        # Scrape the product
        result = scrape_product(product_url, site_type="ebay", verbose=True)
        
        if result["success"]:
            print("\n✅ Successfully scraped eBay product!")
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
            print(f"  Condition: {product_data.get('condition', 'N/A')}")
            print(f"  Seller: {product_data.get('seller', 'N/A')}")
            print(f"  Shipping: {product_data.get('shipping_info', 'N/A')}")
            print(f"  Availability: {product_data.get('availability', 'N/A')}")
            
            # Save to file
            with open("ebay_product_example.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            print("\n💾 Full data saved to 'ebay_product_example.json'")
            
        else:
            print(f"❌ Failed to scrape product: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def scrape_ebay_auction_vs_buy_now():
    """Example: Compare auction vs Buy It Now listings."""
    print("\n🛒 Example: eBay Auction vs Buy It Now comparison")
    print("=" * 50)
    
    # Example URLs for different listing types
    product_urls = [
        "https://www.ebay.com/itm/auction-item-123",     # Auction item
        "https://www.ebay.com/itm/buy-it-now-456",       # Buy It Now item
        "https://www.ebay.com/itm/best-offer-789",       # Best Offer item
    ]
    
    try:
        with EcommerceScraper(verbose=True) as scraper:
            results = scraper.scrape_products(product_urls, site_type="ebay")
        
        print(f"\n📊 Scraped {len(results)} eBay listings")
        
        for i, result in enumerate(results, 1):
            if result["success"]:
                product_data = result["data"]
                if isinstance(product_data, str):
                    try:
                        product_data = json.loads(product_data)
                    except json.JSONDecodeError:
                        continue
                
                print(f"\n📦 Listing {i}:")
                print(f"  URL: {result['product_url']}")
                print(f"  Title: {product_data.get('title', 'N/A')}")
                print(f"  Price: {product_data.get('price', 'N/A')}")
                print(f"  Listing Type: {product_data.get('listing_type', 'N/A')}")
                print(f"  Time Left: {product_data.get('time_left', 'N/A')}")
                print(f"  Condition: {product_data.get('condition', 'N/A')}")
                print(f"  Seller Rating: {product_data.get('seller_rating', 'N/A')}")
            else:
                print(f"\n❌ Failed to scrape listing {i}: {result.get('error')}")
        
        # Save results
        with open("ebay_listings_comparison.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\n💾 Results saved to 'ebay_listings_comparison.json'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def search_ebay_products():
    """Example: Search for products on eBay."""
    print("\n🔍 Example: Searching eBay for products")
    print("=" * 50)
    
    search_query = "vintage camera"
    ebay_url = "https://www.ebay.com"
    max_products = 5
    
    try:
        result = search_and_scrape(
            search_query=search_query,
            site_url=ebay_url,
            max_products=max_products,
            verbose=True
        )
        
        if result["success"]:
            print(f"\n✅ Successfully searched eBay for '{search_query}'!")
            
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
                print(f"  Condition: {product.get('condition', 'N/A')}")
                print(f"  Listing Type: {product.get('listing_type', 'N/A')}")
                print(f"  Seller: {product.get('seller', 'N/A')}")
                print(f"  URL: {product.get('source_url', 'N/A')}")
            
            # Save search results
            with open("ebay_search_example.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            print("\n💾 Search results saved to 'ebay_search_example.json'")
            
        else:
            print(f"❌ Search failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def scrape_ebay_categories():
    """Example: Scrape products from specific eBay categories."""
    print("\n📂 Example: Scraping eBay category products")
    print("=" * 50)
    
    # Example category URLs
    category_urls = [
        "https://www.ebay.com/sch/i.html?_nkw=&_sacat=58058",  # Cell Phones & Smartphones
        "https://www.ebay.com/sch/i.html?_nkw=&_sacat=171485", # Laptops & Netbooks
    ]
    
    try:
        with EcommerceScraper(verbose=True) as scraper:
            all_results = []
            
            for category_url in category_urls:
                print(f"\n🔍 Scraping category: {category_url}")
                
                # Use search and scrape for category pages
                result = scraper.search_and_scrape(
                    search_query="",  # Empty query for category browsing
                    site_url=category_url,
                    max_products=3
                )
                
                if result["success"]:
                    all_results.append(result)
                    print(f"✅ Successfully scraped category")
                else:
                    print(f"❌ Failed to scrape category: {result.get('error')}")
        
        print(f"\n📊 Scraped {len(all_results)} categories")
        
        # Save category results
        with open("ebay_categories_example.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print("💾 Category results saved to 'ebay_categories_example.json'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Run all eBay examples."""
    print("🚀 eBay Scraping Examples")
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
        # Run examples (comment out specific ones if needed)
        print("\n⚠️  Note: Replace example URLs with real eBay product URLs")
        
        # scrape_single_ebay_product()
        # scrape_ebay_auction_vs_buy_now()
        search_ebay_products()
        # scrape_ebay_categories()
        
        print("\n🎉 eBay examples completed!")
        print("\nFiles that may be created:")
        print("  - ebay_product_example.json")
        print("  - ebay_listings_comparison.json")
        print("  - ebay_search_example.json")
        print("  - ebay_categories_example.json")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
