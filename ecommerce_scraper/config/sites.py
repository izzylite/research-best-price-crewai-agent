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
            "handle_popups": "Dismiss any cookie banners, location prompts, or promotional popups",
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
    
    if "amazon." in url_lower:
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
