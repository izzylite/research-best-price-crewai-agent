# 🛒 AI-Powered Ecommerce Scraper

A comprehensive, multi-agent ecommerce scraping system built with **Stagehand** and **CrewAI** that intelligently extracts product data from major ecommerce platforms including Amazon, eBay, Shopify stores, and generic ecommerce sites.

## ✨ Features

- **🤖 AI-Powered Extraction**: Uses LLMs to intelligently navigate and extract data from dynamic websites
- **🎯 Multi-Agent Architecture**: Specialized agents for navigation, extraction, validation, and coordination
- **🌐 Multi-Platform Support**: Amazon, eBay, Shopify, and generic ecommerce sites
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
