# 🛒 AI-Powered Ecommerce Scraper

A comprehensive, multi-agent ecommerce scraping system built with **Stagehand** and **CrewAI** that intelligently extracts product data from major ecommerce platforms including Amazon, eBay, Shopify stores, and generic ecommerce sites.

## ✨ Features

- **🤖 AI-Powered Extraction**: Uses LLMs to intelligently navigate and extract data from dynamic websites
- **🎯 Multi-Agent Architecture**: Specialized agents for navigation, extraction, validation, and coordination
- **🌐 Multi-Platform Support**: Amazon, eBay, Shopify, and generic ecommerce sites
- **🚫 Automatic Popup Handling**: Automatically dismisses cookie banners, privacy dialogs, newsletter popups, and other blocking elements
- **📊 Structured Data Output**: Standardized product schemas with comprehensive data validation
- **🔄 Adaptive Scraping**: Automatically adapts to different site structures and layouts
- **⚡ Cloud Browser Infrastructure**: Powered by Browserbase for reliable, scalable scraping
- **🛡️ Respectful Scraping**: Built-in rate limiting and anti-bot measure handling
- **📈 Batch Processing**: Support for single products, bulk scraping, and search-based extraction
- **🔐 Security Best Practices**: Variable substitution for sensitive data, secure configuration management
- **💾 Performance Optimization**: Intelligent caching, retry logic with exponential backoff
- **👀 Action Previewing**: Preview actions before execution to reduce costs and prevent errors
- **📝 Comprehensive Logging**: Structured logging with configurable levels and automatic log files
- **🏗️ Context Manager Support**: Automatic resource cleanup and session management

## 🏗️ Architecture

The system uses a **multi-agent architecture** with specialized agents:

- **ProductScraperAgent**: Main coordinator that orchestrates the scraping process
- **SiteNavigatorAgent**: Handles site-specific navigation challenges (popups, search, etc.)
- **DataExtractorAgent**: Specialized in extracting structured product data
- **DataValidatorAgent**: Validates, cleans, and standardizes extracted data

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Browserbase](https://browserbase.com) account and API key
- OpenAI API key or Anthropic API key

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd ecommerce-scraper
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```bash
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_project_id
OPENAI_API_KEY=your_openai_api_key

# Optional performance settings
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
MAX_RETRIES=3
LOG_LEVEL=INFO
```

Required environment variables:
```env
# Browserbase (required)
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_browserbase_project_id

# LLM API (choose one)
OPENAI_API_KEY=your_openai_api_key
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional Stagehand configuration
STAGEHAND_MODEL_NAME=gpt-4o  # or claude-3-5-sonnet-20241022
STAGEHAND_ENABLE_CACHING=true
```

### Basic Usage

#### Scrape a Single Product

```python
from ecommerce_scraper import scrape_product

# Scrape an Amazon product
result = scrape_product(
    "https://www.amazon.com/dp/B08N5WRWNW",
    site_type="amazon"
)

if result["success"]:
    product_data = result["data"]
    print(f"Title: {product_data['title']}")
    print(f"Price: {product_data['price']}")
else:
    print(f"Error: {result['error']}")
```

#### Scrape Multiple Products

```python
from ecommerce_scraper import scrape_products

urls = [
    "https://www.amazon.com/dp/B08N5WRWNW",
    "https://www.ebay.com/itm/123456789",
    "https://store.example.com/product/item"
]

results = scrape_products(urls)
successful = [r for r in results if r["success"]]
print(f"Successfully scraped {len(successful)} products")
```

#### Search and Scrape

```python
from ecommerce_scraper import search_and_scrape

result = search_and_scrape(
    search_query="wireless headphones",
    site_url="https://www.amazon.com",
    max_products=5
)

if result["success"]:
    products = result["data"]["products"]
    for product in products:
        print(f"{product['title']} - {product['price']}")
```

#### Advanced Usage with EcommerceScraper Class

```python
from ecommerce_scraper import EcommerceScraper

with EcommerceScraper(verbose=True) as scraper:
    # Scrape single product
    result = scraper.scrape_product("https://example.com/product")
    
    # Validate extracted data
    validation = scraper.validate_product_data(result["data"])
    
    # Search and scrape
    search_result = scraper.search_and_scrape(
        "laptop", 
        "https://www.ebay.com", 
        max_products=10
    )
```

## 📋 Supported Data Fields

The scraper extracts comprehensive product information:

```python
{
    "title": "Product Name",
    "price": {
        "current": 29.99,
        "original": 39.99,
        "currency": "USD"
    },
    "availability": "IN_STOCK",
    "condition": "NEW",
    "brand": "Brand Name",
    "description": "Product description...",
    "images": [
        {
            "url": "https://example.com/image1.jpg",
            "alt_text": "Product image",
            "is_primary": true
        }
    ],
    "variants": [
        {
            "name": "Color",
            "value": "Red",
            "price_modifier": 0.0
        }
    ],
    "reviews": {
        "average_rating": 4.5,
        "total_count": 1250,
        "rating_distribution": {...}
    },
    "specifications": {...},
    "shipping_info": {...},
    "seller_info": {...}
}
```

## 🌐 Supported Platforms

### Amazon
- Product pages
- Search results
- Variant handling
- Prime shipping info
- Reviews and ratings

### eBay
- Auction listings
- Buy It Now items
- Seller information
- Shipping details
- Condition tracking

### Shopify Stores
- Product variants
- Inventory tracking
- Custom themes
- App integrations

### Generic Ecommerce
- Adaptive AI extraction
- Schema.org structured data
- Custom site layouts
- WooCommerce, Magento, etc.

## 🔧 Configuration

### Site-Specific Settings

The scraper automatically detects site types and applies appropriate configurations:

```python
from ecommerce_scraper.config.sites import get_site_config

config = get_site_config("https://www.amazon.com")
print(config.delay_between_requests)  # 3 seconds for Amazon
print(config.requires_cookie_consent)  # True
```

### Custom Site Configuration

```python
from ecommerce_scraper.config.sites import SiteConfig, SiteType

custom_config = SiteConfig(
    name="Custom Store",
    site_type=SiteType.GENERIC,
    base_url="https://custom-store.com",
    delay_between_requests=2,
    requires_cookie_consent=True,
    selectors={
        "product_title": ".product-name",
        "price_current": ".price-now"
    }
)
```

## 📚 Examples

The `examples/` directory contains comprehensive examples:

- **`amazon_example.py`**: Amazon-specific scraping examples
- **`ebay_example.py`**: eBay auction and Buy It Now examples  
- **`generic_example.py`**: Shopify and generic ecommerce examples

Run examples:
```bash
python examples/amazon_example.py
python examples/ebay_example.py
python examples/generic_example.py
```

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Test specific components:
```bash
# Test data validation
python -m pytest tests/test_data_tools.py -v

# Test site configurations
python -m pytest tests/test_site_configs.py -v

# Test agents
python -m pytest tests/test_agents.py -v
```

## 🛠️ Development

### Project Structure

```
ecommerce_scraper/
├── agents/              # CrewAI agents
│   ├── product_scraper.py
│   ├── site_navigator.py
│   ├── data_extractor.py
│   └── data_validator.py
├── config/              # Configuration
│   ├── settings.py
│   └── sites.py
├── schemas/             # Data schemas
│   └── product.py
├── tools/               # Stagehand tools
│   ├── stagehand_tool.py
│   └── data_tools.py
└── main.py              # Main scraper class

examples/                # Usage examples
├── stagehand_best_practices_example.py  # Best practices demo
└── interactive_scraper.py               # Interactive mode
tests/                   # Test suite
```

## 🚫 Popup Handling

The scraper automatically handles common blocking elements that appear on ecommerce websites:

### Automatic Popup Dismissal
- **Cookie Consent Banners**: Automatically clicks "Accept All", "I Accept", or "Accept Cookies"
- **Privacy Policy Dialogs**: Handles GDPR compliance by clicking "Accept" or "Continue"
- **Newsletter Signup Popups**: Dismisses with "Close", "No Thanks", or "Skip"
- **Age Verification Prompts**: Handles age gates by clicking "Yes" or entering appropriate age
- **Location Selection**: Automatically selects "United Kingdom" or "UK" when prompted
- **Promotional Banners**: Dismisses sale offers and promotional overlays
- **Mobile App Prompts**: Clicks "Continue in Browser" to stay on web version

### Vendor-Specific Handling
Each supported vendor has customized popup handling strategies:
- **ASDA**: Privacy dialog with "I Accept" button, location prompts
- **Tesco**: Cookie consent, Clubcard signup, age verification for alcohol
- **Waitrose**: Newsletter overlays, delivery area selection
- **Next**: Newsletter subscription, size guides, mobile app prompts

See `POPUP_HANDLING_GUIDE.md` for comprehensive documentation.

## 🔐 Stagehand Best Practices

This project implements comprehensive Stagehand best practices for production-ready scraping:

### Security Features
- **Variable Substitution**: Secure handling of sensitive data without exposing it to LLMs
- **Environment Variable Management**: Secure configuration with validation
- **Safe Logging**: Automatic masking of sensitive information in logs

### Performance Optimizations
- **Intelligent Caching**: Automatic caching of extract and observe operations
- **Retry Logic**: Exponential backoff for failed operations
- **Action Previewing**: Preview actions before execution to reduce costs

### Usage with Best Practices
```python
from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool

# Use context manager for automatic cleanup
with EcommerceStagehandTool.create_with_context() as tool:
    # Secure form interaction with variables
    tool._run(
        instruction="Type %email% in the email field",
        command_type="act",
        variables={"email": "secure@example.com"}
    )

    # Preview actions before executing
    preview = tool.preview_action("Find the add to cart button")

    # Extract with caching
    product_data = tool._run(
        instruction="Extract product title and price",
        command_type="extract",
        use_cache=True
    )
```

📖 **See [STAGEHAND_BEST_PRACTICES.md](STAGEHAND_BEST_PRACTICES.md) for comprehensive documentation**

### Adding New Sites

1. Add site configuration in `config/sites.py`
2. Update site detection logic
3. Add site-specific extraction strategies
4. Create examples and tests

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## ⚠️ Important Notes

### Rate Limiting and Ethics

- The scraper includes built-in delays and respectful scraping practices
- Always check and respect robots.txt
- Consider the website's terms of service
- Use reasonable request rates to avoid being blocked

### Legal Considerations

- Ensure compliance with website terms of service
- Respect copyright and intellectual property rights
- Consider data privacy regulations (GDPR, CCPA, etc.)
- Use scraped data responsibly

### Reliability

- Websites frequently change their structure
- The AI-powered approach adapts to changes better than fixed selectors
- Monitor scraping success rates and update configurations as needed
- Consider implementing retry logic for production use

## 🔗 Related Projects

- [Stagehand](https://github.com/browserbase/stagehand) - AI-powered browser automation
- [CrewAI](https://github.com/joaomdmoura/crewai) - Multi-agent AI framework
- [Browserbase](https://browserbase.com) - Cloud browser infrastructure

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

- Create an issue for bug reports or feature requests
- Check the examples directory for usage patterns
- Review the test suite for implementation details

---

**Built with ❤️ using Stagehand and CrewAI**

https://www.asda.com/ // Can scrap
https://www.waitrose.com/ // Can scrap
https://www.mamasandpapas.com/ // Can scrap
https://www.next.co.uk/ // Can scrap
https://www.primark.com/en-gb // Can scrap
https://www.thetoyshop.com/ // Can scrap

https://www.tesco.com/groceries/en-GB // Blocked
https://www.hamleys.com/ // Blocked
https://www.selfridges.com/GB/en/ //Blocked












  # ASDA: Grocery subcategories from the Groceries dropdown menu
        "asda": [
            {"id": "rollback", "name": "Rollback", "url": "/groceries/rollback"},
            {"id": "summer", "name": "Summer", "url": "/groceries/summer"},
            {"id": "events-inspiration", "name": "Events & Inspiration", "url": "/groceries/events-inspiration"},
            {"id": "fruit-veg-flowers", "name": "Fruit, Veg & Flowers", "url": "/groceries/fruit-veg-flowers"},
            {"id": "meat-poultry-fish", "name": "Meat, Poultry & Fish", "url": "/groceries/meat-poultry-fish"},
            {"id": "bakery", "name": "Bakery", "url": "/groceries/bakery"},
            {"id": "chilled-food", "name": "Chilled Food", "url": "/groceries/chilled-food"},
            {"id": "frozen-food", "name": "Frozen Food", "url": "/groceries/frozen-food"},
            {"id": "food-cupboard", "name": "Food Cupboard", "url": "/groceries/food-cupboard"},
            {"id": "sweets-treats-snacks", "name": "Sweets, Treats & Snacks", "url": "/groceries/sweets-treats-snacks"},
            {"id": "dietary-lifestyle", "name": "Dietary & Lifestyle", "url": "/groceries/dietary-lifestyle"},
            {"id": "drinks", "name": "Drinks", "url": "/groceries/drinks"},
            {"id": "beer-wine-spirits", "name": "Beer, Wine & Spirits", "url": "/groceries/beer-wine-spirits"},
            {"id": "toiletries-beauty", "name": "Toiletries & Beauty", "url": "/groceries/toiletries-beauty"},
            {"id": "laundry-household", "name": "Laundry & Household", "url": "/groceries/laundry-household"},
            {"id": "baby-toddler-kids", "name": "Baby, Toddler & Kids", "url": "/groceries/baby-toddler-kids"},
            {"id": "pet-food-accessories", "name": "Pet Food & Accessories", "url": "/groceries/pet-food-accessories"},
            {"id": "health-wellness", "name": "Health & Wellness", "url": "/groceries/health-wellness"},
            {"id": "home-entertainment", "name": "Home & Entertainment", "url": "/groceries/home-entertainment"},
            {"id": "world-food", "name": "World Food", "url": "/groceries/world-food"}
        ],

        # Tesco: All Departments subcategories from the dropdown menu
        "tesco": [
            {"id": "marketplace", "name": "Marketplace", "url": "/departments/marketplace"},
            {"id": "clothing-accessories", "name": "Clothing & Accessories", "url": "/departments/clothing-accessories"},
            {"id": "summer", "name": "Summer", "url": "/departments/summer"},
            {"id": "fresh-food", "name": "Fresh Food", "url": "/departments/fresh-food"},
            {"id": "bakery", "name": "Bakery", "url": "/departments/bakery"},
            {"id": "frozen-food", "name": "Frozen Food", "url": "/departments/frozen-food"},
            {"id": "treats-snacks", "name": "Treats & Snacks", "url": "/departments/treats-snacks"},
            {"id": "food-cupboard", "name": "Food Cupboard", "url": "/departments/food-cupboard"},
            {"id": "drinks", "name": "Drinks", "url": "/departments/drinks"},
            {"id": "baby-toddler", "name": "Baby & Toddler", "url": "/departments/baby-toddler"},
            {"id": "health-beauty", "name": "Health & Beauty", "url": "/departments/health-beauty"},
            {"id": "pets", "name": "Pets", "url": "/departments/pets"},
            {"id": "household", "name": "Household", "url": "/departments/household"},
            {"id": "home-ents", "name": "Home & Ents", "url": "/departments/home-ents"},
            {"id": "back-to-school", "name": "Back To School", "url": "/departments/back-to-school"},
            {"id": "electronics-gaming", "name": "Electronics & Gaming", "url": "/departments/electronics-gaming"},
            {"id": "toys-games", "name": "Toys & Games", "url": "/departments/toys-games"},
            {"id": "inspiration-events", "name": "Inspiration & Events", "url": "/departments/inspiration-events"}
        ],

        # Waitrose: Groceries subcategories from the dropdown menu
        "waitrose": [
            {"id": "view-all-groceries", "name": "View all Groceries", "url": "/groceries/view-all"},
            {"id": "groceries-offers", "name": "Groceries OFFERS", "url": "/groceries/offers"},
            {"id": "summer", "name": "Summer", "url": "/groceries/summer"},
            {"id": "fresh-chilled", "name": "Fresh & Chilled", "url": "/groceries/fresh-chilled"},
            {"id": "frozen", "name": "Frozen", "url": "/groceries/frozen"},
            {"id": "bakery", "name": "Bakery", "url": "/groceries/bakery"},
            {"id": "food-cupboard", "name": "Food Cupboard", "url": "/groceries/food-cupboard"},
            {"id": "beer-wine-spirits", "name": "Beer, Wine & Spirits", "url": "/groceries/beer-wine-spirits"},
            {"id": "tea-coffee-soft-drinks", "name": "Tea, Coffee & Soft Drinks", "url": "/groceries/tea-coffee-soft-drinks"},
            {"id": "household", "name": "Household", "url": "/groceries/household"},
            {"id": "toiletries-health-beauty", "name": "Toiletries, Health & Beauty", "url": "/groceries/toiletries-health-beauty"},
            {"id": "baby-toddler", "name": "Baby & Toddler", "url": "/groceries/baby-toddler"},
            {"id": "pet", "name": "Pet", "url": "/groceries/pet"},
            {"id": "home", "name": "Home", "url": "/groceries/home"},
            {"id": "new", "name": "New", "url": "/groceries/new"},
            {"id": "dietary-lifestyle", "name": "Dietary & Lifestyle", "url": "/groceries/dietary-lifestyle"},
            {"id": "organic-shop", "name": "Organic Shop", "url": "/groceries/organic-shop"},
            {"id": "shop-by-occasion", "name": "Shop by Occasion", "url": "/groceries/shop-by-occasion"},
            {"id": "waitrose-brands", "name": "Waitrose Brands", "url": "/groceries/waitrose-brands"},
            {"id": "brandhub-new", "name": "BrandHub New", "url": "/groceries/brandhub-new"},
            {"id": "everyday-value", "name": "Everyday Value", "url": "/groceries/everyday-value"},
            {"id": "best-of-british", "name": "Best of British", "url": "/groceries/best-of-british"}
        ],

        # Next: Bold main categories from the navigation menu
        "next": [
            {
                "id": "women",
                "name": "Women",
                "url": "/women",
                "subcategories": [
                    {"id": "shop-all", "name": "Shop All", "url": "/women/shop-all"},
                    {"id": "clothing", "name": "All Clothing", "url": "/women/clothing"},
                    {"id": "footwear", "name": "All Footwear", "url": "/women/footwear"},
                    {"id": "dresses", "name": "Dresses", "url": "/women/dresses"},
                    {"id": "tops", "name": "Tops", "url": "/women/tops"},
                    {"id": "jeans-trousers", "name": "Jeans & Trousers", "url": "/women/jeans-trousers"},
                    {"id": "accessories", "name": "Accessories", "url": "/women/accessories"}
                ]
            },
            {"id": "men", "name": "Men", "url": "/men"},
            {"id": "girls", "name": "Girls", "url": "/girls"},
            {"id": "boys", "name": "Boys", "url": "/boys"},
            {"id": "home", "name": "Home", "url": "/home"},
            {"id": "beauty", "name": "Beauty", "url": "/beauty"},
            {"id": "designer-brands", "name": "Designer Brands", "url": "/designer-brands"},
            {"id": "lipsy", "name": "Lipsy", "url": "/lipsy"},
            {"id": "shop-clearance", "name": "Shop Clearance", "url": "/shop-clearance"}
        ],

        # Mamas & Papas: Main navigation categories from the website header: https://www.mamasandpapas.com/
        "mamasandpapas": [
            {"id": "sale", "name": "Sale", "url": "/sale"},
            {"id": "pushchairs", "name": "Pushchairs", "url": "/pushchairs"},
            {"id": "furniture", "name": "Furniture", "url": "/furniture"},
            {"id": "clothing", "name": "Clothing", "url": "/clothing"},
            {"id": "nursery", "name": "Nursery", "url": "/nursery"},
            {"id": "car-seats", "name": "Car Seats", "url": "/car-seats"},
            {"id": "bathing-changing", "name": "Bathing & Changing", "url": "/bathing-changing"},
            {"id": "baby-safety", "name": "Baby Safety", "url": "/baby-safety"},
            {"id": "feeding-weaning", "name": "Feeding & Weaning", "url": "/feeding-weaning"},
            {"id": "toys-gifts", "name": "Toys & Gifts", "url": "/toys-gifts"},
            {"id": "brands", "name": "Brands", "url": "/brands"}
        ],

        # Primark: "WOMEN", "KIDS", "BABY", "HOME", "MEN" : https://www.primark.com/en-gb
        "primark": [
            {"id": "women", "name": "Women", "url": "/women"},
            {"id": "men", "name": "Men", "url": "/men"},
            {"id": "kids", "name": "Kids", "url": "/kids"},
            {"id": "baby", "name": "Baby", "url": "/baby"},
            {
                "id": "home",
                "name": "Home",
                "url": "/home",
                "subcategories": [
                    {"id": "new-arrivals", "name": "New Arrivals", "url": "/home/new-arrivals"},
                    {"id": "girly-decor", "name": "Girly Decor", "url": "/home/girly-decor"},
                    {"id": "bedroom", "name": "Bedroom", "url": "/home/bedroom"},
                    {"id": "living-room", "name": "Living Room", "url": "/home/living-room"},
                    {"id": "kitchen-dining", "name": "Kitchen & Dining", "url": "/home/kitchen-dining"},
                    {"id": "bathroom", "name": "Bathroom", "url": "/home/bathroom"},
                    {"id": "all", "name": "All Home", "url": "/home"}
                ]
            }
        ],

        # The Toy Shop: "Brands", "Type of Toy", "Outdoor", "Shop By Age", "Offers", "New Toys", "Clearance" : https://www.thetoyshop.com/
        "thetoyshop": [
            {"id": "brands", "name": "Brands", "url": "/brands"},
            {"id": "type-of-toy", "name": "Type of Toy", "url": "/type-of-toy"},
            {"id": "outdoor", "name": "Outdoor", "url": "/outdoor"},
            {"id": "shop-by-age", "name": "Shop By Age", "url": "/shop-by-age"},
            {"id": "offers", "name": "Offers", "url": "/offers"},
            {"id": "new-toys", "name": "New Toys", "url": "/new-toys"}
        ],

        # Costco: "Shop", "Grocery", "Same Day", "Savings", "Business Delivery", "Optical", "Pharmacy", "Services"
        "costco": [
            {"id": "grocery", "name": "Grocery", "url": "/grocery"},
            {"id": "shop", "name": "Shop", "url": "/shop"},
            {"id": "same-day", "name": "Same Day", "url": "/same-day"},
            {"id": "savings", "name": "Savings", "url": "/savings"},
            {"id": "business-delivery", "name": "Business Delivery", "url": "/business-delivery"}
        ],

        # For blocked sites (Hamleys, Selfridges), use reasonable category estimates
        "hamleys": [
            {"id": "action-figures", "name": "Action Figures", "url": "/action-figures"},
            {"id": "dolls", "name": "Dolls & Accessories", "url": "/dolls"},
            {"id": "educational", "name": "Educational Toys", "url": "/educational"},
            {"id": "outdoor", "name": "Outdoor Toys", "url": "/outdoor"},
            {"id": "board-games", "name": "Board Games", "url": "/board-games"},
            {"id": "brands", "name": "Popular Brands", "url": "/brands"}
        ],

        "selfridges": [
            {"id": "women", "name": "Women", "url": "/women"},
            {"id": "men", "name": "Men", "url": "/men"},
            {"id": "beauty", "name": "Beauty", "url": "/beauty"},
            {"id": "home", "name": "Home & Lifestyle", "url": "/home"},
            {"id": "accessories", "name": "Accessories", "url": "/accessories"},
            {"id": "designer", "name": "Designer", "url": "/designer"}
        ]
    }
