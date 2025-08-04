"""Site-specific configurations for different ecommerce platforms."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class SiteType(str, Enum):
    """Supported ecommerce site types."""
    AMAZON = "amazon"
    EBAY = "ebay"
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    MAGENTO = "magento"
    GENERIC = "generic"


@dataclass
class SiteConfig:
    """Configuration for a specific ecommerce site."""
    name: str
    site_type: SiteType
    base_url: str
    search_url_pattern: Optional[str] = None
    product_url_pattern: Optional[str] = None
    
    # Navigation settings
    requires_cookie_consent: bool = False
    has_age_verification: bool = False
    has_location_selection: bool = False
    
    # Scraping settings
    delay_between_requests: int = 2
    max_retries: int = 3
    respect_robots_txt: bool = True
    
    # Site-specific selectors (optional hints)
    selectors: Dict[str, str] = None
    
    # Site-specific instructions
    navigation_instructions: Dict[str, str] = None
    extraction_instructions: Dict[str, str] = None
    
    def __post_init__(self):
        if self.selectors is None:
            self.selectors = {}
        if self.navigation_instructions is None:
            self.navigation_instructions = {}
        if self.extraction_instructions is None:
            self.extraction_instructions = {}


# Site configurations
SITE_CONFIGS = {
    # UK Retail Sites
    "asda": SiteConfig(
        name="ASDA",
        site_type=SiteType.GENERIC,
        base_url="https://www.asda.com",
        search_url_pattern="https://www.asda.com/search/{query}",
        requires_cookie_consent=True,
        has_location_selection=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-button']",
            "product_title": "h1[data-testid='product-title']",
            "price_current": "[data-testid='price-current']",
            "price_original": "[data-testid='price-was']",
            "availability": "[data-testid='availability']",
            "product_images": "[data-testid='product-image']",
            "description": "[data-testid='product-description']",
            "category_nav": "[data-testid='category-navigation']",
        },
        navigation_instructions={
            "handle_popups": "CRITICAL: Look for privacy dialog with 'Your privacy is important to us' text and click 'I Accept' button. Also dismiss any location prompts, promotional banners, and cookie consent overlays. Check for newsletter signup popups and close them.",
            "search_strategy": "Use main search in header, handle autocomplete suggestions",
            "category_discovery": "Navigate through main menu and category pages",
            "product_access": "Wait for dynamic content to load, handle lazy-loaded images",
        },
        extraction_instructions={
            "title": "Extract clean product title without promotional text",
            "price": "Handle £ symbol, extract current and was prices",
            "availability": "Check stock status and delivery information",
            "images": "Extract high-resolution product images",
            "category": "Extract from breadcrumb navigation",
            "weight": "Look for weight/size information in product details",
        }
    ),

    "costco": SiteConfig(
        name="Costco UK",
        site_type=SiteType.GENERIC,
        base_url="https://www.costco.com",
        search_url_pattern="https://www.costco.com/CatalogSearch?keyword={query}",
        requires_cookie_consent=True,
        has_location_selection=True,
        delay_between_requests=4,  # Slower for wholesale site
        selectors={
            "search_box": "#search-field",
            "search_button": "#search-button",
            "product_title": ".product-title",
            "price_current": ".price-current",
            "price_member": ".member-price",
            "availability": ".availability-msg",
            "product_images": ".product-image-main",
            "description": ".product-description",
            "bulk_info": ".bulk-pricing",
        },
        navigation_instructions={
            "handle_popups": "Handle membership prompts, cookie consent, and location selection",
            "search_strategy": "Use main search, may require membership for full access",
            "category_discovery": "Navigate warehouse-style category structure",
            "membership_handling": "Note membership requirements for pricing",
        },
        extraction_instructions={
            "title": "Extract product title, include bulk/case information",
            "price": "Extract member vs non-member pricing, handle bulk pricing",
            "availability": "Check warehouse availability and shipping options",
            "images": "Extract product images, handle zoom functionality",
            "bulk_details": "Extract case/bulk quantity information",
            "weight": "Extract package weight and dimensions",
        }
    ),

    SiteType.AMAZON: SiteConfig(
        name="Amazon",
        site_type=SiteType.AMAZON,
        base_url="https://www.amazon.com",
        search_url_pattern="https://www.amazon.com/s?k={query}",
        product_url_pattern=r"https://www\.amazon\.com/.*?/dp/[A-Z0-9]{10}",
        requires_cookie_consent=True,
        has_location_selection=True,
        delay_between_requests=3,
        selectors={
            "search_box": "#twotabsearchtextbox",
            "search_button": "#nav-search-submit-button",
            "product_title": "#productTitle",
            "price_current": ".a-price-whole",
            "price_original": ".a-price.a-text-price .a-offscreen",
            "availability": "#availability span",
            "rating": ".a-icon-alt",
            "review_count": "#acrCustomerReviewText",
            "product_images": "#landingImage, .a-dynamic-image",
            "description": "#feature-bullets ul",
        },
        navigation_instructions={
            "handle_popups": "CRITICAL: Look for cookie consent banners and click 'Accept All' or 'Accept Cookies'. Dismiss Clubcard signup prompts, location/delivery area selection, and age verification for alcohol products. Handle promotional offer overlays.",
            "search_strategy": "Use the main search box in the header, wait for autocomplete to load",
            "product_access": "Ensure product page is fully loaded including images and pricing",
        },
        extraction_instructions={
            "title": "Extract the main product title, clean any extra formatting",
            "price": "Look for current price and crossed-out original price, handle different formats",
            "availability": "Check availability status, handle 'In Stock', 'Out of Stock', etc.",
            "images": "Extract all product images including zoom versions",
            "reviews": "Get overall rating and total review count",
            "variants": "Look for size, color, and style options",
        }
    ),

    "waitrose": SiteConfig(
        name="Waitrose",
        site_type=SiteType.GENERIC,
        base_url="https://www.waitrose.com",
        search_url_pattern="https://www.waitrose.com/ecom/shop/search?&searchTerm={query}",
        requires_cookie_consent=True,
        has_location_selection=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-test='header-search-input']",
            "search_button": "[data-test='header-search-button']",
            "product_title": "[data-test='product-title']",
            "price_current": "[data-test='product-price']",
            "price_per_unit": "[data-test='price-per-unit']",
            "availability": "[data-test='product-availability']",
            "product_images": "[data-test='product-image']",
            "description": "[data-test='product-description']",
            "category_nav": "[data-test='category-menu']",
        },
        navigation_instructions={
            "handle_popups": "Accept cookie consent, handle postcode entry for delivery",
            "search_strategy": "Use header search, handle product suggestions",
            "category_discovery": "Navigate through department menu structure",
            "location_handling": "May require postcode for full product availability",
        },
        extraction_instructions={
            "title": "Extract product name, include brand information",
            "price": "Handle £ pricing, extract per-unit pricing where available",
            "availability": "Check delivery availability for location",
            "images": "Extract high-quality product images",
            "category": "Extract from navigation breadcrumbs",
            "weight": "Extract weight/volume from product details",
        }
    ),

    "tesco": SiteConfig(
        name="Tesco",
        site_type=SiteType.GENERIC,
        base_url="https://www.tesco.com/groceries/en-GB",
        search_url_pattern="https://www.tesco.com/groceries/en-GB/search?query={query}",
        requires_cookie_consent=True,
        has_location_selection=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-button']",
            "product_title": "[data-testid='product-title']",
            "price_current": "[data-testid='price-current']",
            "price_per_unit": "[data-testid='unit-price']",
            "availability": "[data-testid='product-availability']",
            "product_images": "[data-testid='product-image']",
            "description": "[data-testid='product-description']",
            "category_nav": "[data-testid='category-navigation']",
        },
        navigation_instructions={
            "handle_popups": "Accept GDPR consent, handle postcode entry and store selection",
            "search_strategy": "Use main search, handle autocomplete and filters",
            "category_discovery": "Navigate through grocery department structure",
            "store_selection": "May require store/postcode selection for pricing",
        },
        extraction_instructions={
            "title": "Extract product title with brand and variety information",
            "price": "Handle £ pricing, extract unit pricing (per kg, per 100g, etc.)",
            "availability": "Check stock status and delivery slots",
            "images": "Extract product images, handle multiple angles",
            "category": "Extract from department and aisle information",
            "weight": "Extract package size and weight information",
        }
    ),

    "hamleys": SiteConfig(
        name="Hamleys",
        site_type=SiteType.GENERIC,
        base_url="https://www.hamleys.com",
        search_url_pattern="https://www.hamleys.com/search?q={query}",
        requires_cookie_consent=True,
        has_age_verification=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-submit']",
            "product_title": ".product-title",
            "price_current": ".price-current",
            "price_original": ".price-was",
            "availability": ".stock-status",
            "product_images": ".product-image",
            "description": ".product-description",
            "age_range": ".age-range",
        },
        navigation_instructions={
            "handle_popups": "Accept cookies, handle age verification if required",
            "search_strategy": "Use main search, handle toy category filters",
            "category_discovery": "Navigate through age-based and toy-type categories",
            "age_verification": "Handle age verification prompts for certain products",
        },
        extraction_instructions={
            "title": "Extract toy name, include brand and series information",
            "price": "Handle £ pricing, look for sale prices",
            "availability": "Check stock status and delivery information",
            "images": "Extract multiple product images and packaging shots",
            "category": "Extract toy category and age range",
            "age_range": "Extract recommended age range information",
        }
    ),

    SiteType.EBAY: SiteConfig(
        name="eBay",
        site_type=SiteType.EBAY,
        base_url="https://www.ebay.com",
        search_url_pattern="https://www.ebay.com/sch/i.html?_nkw={query}",
        product_url_pattern=r"https://www\.ebay\.com/itm/.*?/\d+",
        requires_cookie_consent=True,
        delay_between_requests=2,
        selectors={
            "search_box": "#gh-ac",
            "search_button": "#gh-btn",
            "product_title": "#x-title-label-lbl",
            "price_current": ".notranslate",
            "condition": "#u_kp_1 .u-flL",
            "availability": "#qtySubTxt",
            "seller_info": ".seller-persona",
            "product_images": "#icImg",
            "description": "#desc_div",
        },
        navigation_instructions={
            "handle_popups": "Accept cookie consent, dismiss any promotional banners",
            "search_strategy": "Use main search box, handle category suggestions",
            "product_access": "Wait for all product details to load, including seller information",
        },
        extraction_instructions={
            "title": "Extract product title, remove seller-added prefixes/suffixes",
            "price": "Handle auction vs Buy It Now pricing, extract shipping costs",
            "condition": "Extract item condition (New, Used, Refurbished, etc.)",
            "seller": "Get seller information and ratings",
            "shipping": "Extract shipping costs and delivery estimates",
        }
    ),

    "mamasandpapas": SiteConfig(
        name="Mamas & Papas",
        site_type=SiteType.GENERIC,
        base_url="https://www.mamasandpapas.com",
        search_url_pattern="https://www.mamasandpapas.com/search?q={query}",
        requires_cookie_consent=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-button']",
            "product_title": ".product-name",
            "price_current": ".price-current",
            "price_original": ".price-was",
            "availability": ".availability-status",
            "product_images": ".product-image",
            "description": ".product-description",
            "variants": ".product-variants",
        },
        navigation_instructions={
            "handle_popups": "Accept GDPR consent, dismiss newsletter signup",
            "search_strategy": "Use header search, handle product filters",
            "category_discovery": "Navigate through baby/child age-based categories",
            "variant_handling": "Handle size, color, and style variants",
        },
        extraction_instructions={
            "title": "Extract product name with brand and model information",
            "price": "Handle £ pricing, extract variant pricing",
            "availability": "Check stock for different variants",
            "images": "Extract multiple product images and lifestyle shots",
            "category": "Extract product category and age suitability",
            "variants": "Extract size, color, and style options with pricing",
        }
    ),

    "selfridges": SiteConfig(
        name="Selfridges",
        site_type=SiteType.GENERIC,
        base_url="https://www.selfridges.com/GB/en",
        search_url_pattern="https://www.selfridges.com/GB/en/search/{query}",
        requires_cookie_consent=True,
        delay_between_requests=4,  # Slower for luxury site
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-submit']",
            "product_title": ".product-title",
            "price_current": ".price-current",
            "price_original": ".price-was",
            "availability": ".stock-availability",
            "product_images": ".product-image",
            "description": ".product-description",
            "brand": ".product-brand",
        },
        navigation_instructions={
            "handle_popups": "Accept cookies, handle luxury brand protection measures",
            "search_strategy": "Use main search, handle designer brand filters",
            "category_discovery": "Navigate through luxury department structure",
            "brand_protection": "Respect brand protection and anti-bot measures",
        },
        extraction_instructions={
            "title": "Extract product name with designer brand prominence",
            "price": "Handle £ pricing, may have high-value items",
            "availability": "Check luxury item availability and delivery",
            "images": "Extract high-quality product and lifestyle images",
            "category": "Extract luxury category and designer brand",
            "brand": "Extract designer brand information prominently",
        }
    ),

    "next": SiteConfig(
        name="Next",
        site_type=SiteType.GENERIC,
        base_url="https://www.next.co.uk",
        search_url_pattern="https://www.next.co.uk/search?w={query}",
        requires_cookie_consent=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-button']",
            "product_title": ".product-title",
            "price_current": ".price-current",
            "price_original": ".price-was",
            "availability": ".stock-status",
            "product_images": ".product-image",
            "description": ".product-description",
            "size_guide": ".size-guide",
        },
        navigation_instructions={
            "handle_popups": "Accept GDPR consent, dismiss promotional banners",
            "search_strategy": "Use header search, handle fashion filters",
            "category_discovery": "Navigate through fashion and home categories",
            "size_handling": "Handle extensive size and fit options",
        },
        extraction_instructions={
            "title": "Extract fashion item name with style details",
            "price": "Handle £ pricing, extract size-based pricing",
            "availability": "Check size availability and stock levels",
            "images": "Extract fashion images including model shots",
            "category": "Extract fashion category and subcategory",
            "sizes": "Extract available sizes and fit information",
        }
    ),

    SiteType.SHOPIFY: SiteConfig(
        name="Shopify Store",
        site_type=SiteType.SHOPIFY,
        base_url="",  # Will be set per store
        requires_cookie_consent=True,
        delay_between_requests=2,
        selectors={
            "search_box": "[name='q'], .search-input",
            "product_title": ".product-title, h1.product__title",
            "price_current": ".price, .product-price",
            "price_original": ".compare-at-price, .was-price",
            "availability": ".product-availability, .stock-status",
            "product_images": ".product-image img, .product__media img",
            "add_to_cart": "[name='add'], .btn-cart",
            "variants": ".product-variants select, .variant-input",
        },
        navigation_instructions={
            "handle_popups": "Handle cookie consent, newsletter popups, age verification",
            "search_strategy": "Look for search icon or search box, often in header",
            "product_access": "Wait for product options and pricing to load",
        },
        extraction_instructions={
            "title": "Extract clean product title without store branding",
            "price": "Handle variant pricing, look for sale prices",
            "variants": "Extract all available options (size, color, etc.)",
            "inventory": "Check stock levels for different variants",
        }
    ),

    "primark": SiteConfig(
        name="Primark",
        site_type=SiteType.GENERIC,
        base_url="https://www.primark.com/en-gb",
        search_url_pattern="https://www.primark.com/en-gb/search?q={query}",
        requires_cookie_consent=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-submit']",
            "product_title": ".product-title",
            "price_current": ".price",
            "availability": ".availability",
            "product_images": ".product-image",
            "description": ".product-description",
            "store_availability": ".store-stock",
        },
        navigation_instructions={
            "handle_popups": "Accept GDPR consent, handle store finder prompts",
            "search_strategy": "Use main search, limited online catalog",
            "category_discovery": "Navigate through fashion categories",
            "store_focus": "Note focus on store availability over online sales",
        },
        extraction_instructions={
            "title": "Extract fashion item name and style code",
            "price": "Handle £ pricing, typically low-cost fashion",
            "availability": "Check store availability rather than online stock",
            "images": "Extract product images, may be limited online",
            "category": "Extract fashion category and target demographic",
            "store_info": "Extract store availability information",
        }
    ),

    "thetoyshop": SiteConfig(
        name="The Toy Shop",
        site_type=SiteType.GENERIC,
        base_url="https://www.thetoyshop.com",
        search_url_pattern="https://www.thetoyshop.com/search?q={query}",
        requires_cookie_consent=True,
        has_age_verification=True,
        delay_between_requests=3,
        selectors={
            "search_box": "[data-testid='search-input']",
            "search_button": "[data-testid='search-button']",
            "product_title": ".product-title",
            "price_current": ".price-current",
            "price_original": ".price-was",
            "availability": ".stock-status",
            "product_images": ".product-image",
            "description": ".product-description",
            "age_range": ".age-suitability",
        },
        navigation_instructions={
            "handle_popups": "Accept cookies, handle age verification",
            "search_strategy": "Use main search, handle toy category filters",
            "category_discovery": "Navigate through toy categories and age ranges",
            "seasonal_handling": "Handle seasonal toy availability",
        },
        extraction_instructions={
            "title": "Extract toy name with brand and series information",
            "price": "Handle £ pricing, look for promotional offers",
            "availability": "Check toy availability and delivery options",
            "images": "Extract toy images and packaging information",
            "category": "Extract toy category and age appropriateness",
            "age_range": "Extract recommended age range and safety information",
        }
    ),

    SiteType.GENERIC: SiteConfig(
        name="Generic Ecommerce",
        site_type=SiteType.GENERIC,
        base_url="",
        requires_cookie_consent=True,
        delay_between_requests=2,
        navigation_instructions={
            "handle_popups": "Dismiss any popups, banners, or consent requests",
            "search_strategy": "Look for search functionality in header or main navigation",
            "product_access": "Ensure product page is fully loaded with all content",
        },
        extraction_instructions={
            "adaptive": "Use AI to identify and extract product information based on page structure",
            "comprehensive": "Extract all visible product information including specs and media",
            "structured": "Organize extracted data into the standard product schema",
        }
    )
}


def get_site_config(url: str) -> SiteConfig:
    """Get site configuration based on URL."""
    url_lower = url.lower()

    # UK Retail Sites
    if "asda.com" in url_lower:
        return SITE_CONFIGS["asda"]
    elif "costco.com" in url_lower:
        return SITE_CONFIGS["costco"]
    elif "waitrose.com" in url_lower:
        return SITE_CONFIGS["waitrose"]
    elif "tesco.com" in url_lower:
        return SITE_CONFIGS["tesco"]
    elif "hamleys.com" in url_lower:
        return SITE_CONFIGS["hamleys"]
    elif "mamasandpapas.com" in url_lower:
        return SITE_CONFIGS["mamasandpapas"]
    elif "selfridges.com" in url_lower:
        return SITE_CONFIGS["selfridges"]
    elif "next.co.uk" in url_lower:
        return SITE_CONFIGS["next"]
    elif "primark.com" in url_lower:
        return SITE_CONFIGS["primark"]
    elif "thetoyshop.com" in url_lower:
        return SITE_CONFIGS["thetoyshop"]
    # International Sites
    elif "amazon." in url_lower:
        return SITE_CONFIGS[SiteType.AMAZON]
    elif "ebay." in url_lower:
        return SITE_CONFIGS[SiteType.EBAY]
    elif "shopify" in url_lower or "myshopify.com" in url_lower:
        config = SITE_CONFIGS[SiteType.SHOPIFY].copy()
        # Extract base URL for Shopify stores
        from urllib.parse import urlparse
        parsed = urlparse(url)
        config.base_url = f"{parsed.scheme}://{parsed.netloc}"
        return config
    else:
        # Return generic config for unknown sites
        config = SITE_CONFIGS[SiteType.GENERIC]
        from urllib.parse import urlparse
        parsed = urlparse(url)
        config.base_url = f"{parsed.scheme}://{parsed.netloc}"
        return config


def get_site_config_by_vendor(vendor_name: str) -> SiteConfig:
    """Get site configuration by vendor name.

    Args:
        vendor_name: Vendor identifier (e.g., 'asda', 'tesco', 'amazon')

    Returns:
        SiteConfig for the vendor

    Raises:
        KeyError: If vendor is not supported
    """
    vendor_lower = vendor_name.lower()

    # Direct lookup for UK retailers
    if vendor_lower in SITE_CONFIGS:
        return SITE_CONFIGS[vendor_lower]

    # Handle legacy site types
    site_type_mapping = {
        "amazon": SiteType.AMAZON,
        "ebay": SiteType.EBAY,
        "shopify": SiteType.SHOPIFY,
        "generic": SiteType.GENERIC
    }

    if vendor_lower in site_type_mapping:
        return SITE_CONFIGS[site_type_mapping[vendor_lower]]

    raise KeyError(f"Unsupported vendor: {vendor_name}")


def get_supported_uk_vendors() -> List[str]:
    """Get list of supported UK retail vendors."""
    uk_vendors = [
        "asda", "costco", "waitrose", "tesco", "hamleys",
        "mamasandpapas", "selfridges", "next", "primark", "thetoyshop"
    ]
    return uk_vendors


def get_all_supported_vendors() -> List[str]:
    """Get list of all supported vendors including UK and international."""
    uk_vendors = get_supported_uk_vendors()
    international = ["amazon", "ebay", "shopify", "generic"]
    return uk_vendors + international


def detect_site_type(url: str) -> SiteType:
    """Detect the type of ecommerce site from URL."""
    url_lower = url.lower()
    
    if "amazon." in url_lower:
        return SiteType.AMAZON
    elif "ebay." in url_lower:
        return SiteType.EBAY
    elif "shopify" in url_lower or "myshopify.com" in url_lower:
        return SiteType.SHOPIFY
    else:
        return SiteType.GENERIC


def get_extraction_strategy(site_type: SiteType) -> Dict[str, Any]:
    """Get extraction strategy for a specific site type."""
    strategies = {
        SiteType.AMAZON: {
            "approach": "structured_selectors",
            "fallback": "ai_extraction",
            "priority_fields": ["title", "price", "availability", "rating", "images"],
            "special_handling": ["variants", "prime_shipping", "amazon_choice"],
        },
        SiteType.EBAY: {
            "approach": "mixed_extraction",
            "fallback": "ai_extraction", 
            "priority_fields": ["title", "price", "condition", "seller", "shipping"],
            "special_handling": ["auction_vs_buy_now", "seller_ratings", "return_policy"],
        },
        SiteType.SHOPIFY: {
            "approach": "adaptive_ai",
            "fallback": "common_selectors",
            "priority_fields": ["title", "price", "variants", "inventory"],
            "special_handling": ["variant_pricing", "inventory_tracking"],
        },
        SiteType.GENERIC: {
            "approach": "ai_first",
            "fallback": "structured_data",
            "priority_fields": ["title", "price", "description", "images"],
            "special_handling": ["schema_detection", "adaptive_extraction"],
        }
    }
    
    return strategies.get(site_type, strategies[SiteType.GENERIC])


def get_navigation_strategy(site_type: SiteType) -> Dict[str, Any]:
    """Get navigation strategy for a specific site type."""
    strategies = {
        SiteType.AMAZON: {
            "initial_actions": ["dismiss_location_popup", "accept_cookies"],
            "search_method": "main_search_box",
            "wait_strategy": "dynamic_content",
            "anti_bot_handling": "slow_human_like",
        },
        SiteType.EBAY: {
            "initial_actions": ["accept_cookies", "dismiss_promotions"],
            "search_method": "header_search",
            "wait_strategy": "page_complete",
            "anti_bot_handling": "moderate_delays",
        },
        SiteType.SHOPIFY: {
            "initial_actions": ["handle_age_gate", "dismiss_newsletter"],
            "search_method": "adaptive_search",
            "wait_strategy": "content_loaded",
            "anti_bot_handling": "respectful_timing",
        },
        SiteType.GENERIC: {
            "initial_actions": ["dismiss_popups"],
            "search_method": "ai_guided",
            "wait_strategy": "intelligent_wait",
            "anti_bot_handling": "adaptive_behavior",
        }
    }
    
    return strategies.get(site_type, strategies[SiteType.GENERIC])
