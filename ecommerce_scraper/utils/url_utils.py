"""URL utility functions for ecommerce scraping."""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs, urljoin

from ..config.sites import get_site_config


def is_valid_url(url: str) -> bool:
    """Check if URL is valid.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def normalize_url(url: str) -> str:
    """Normalize URL by removing tracking parameters etc.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    # Parse URL
    parsed = urlparse(url)
    
    # Get query parameters
    params = parse_qs(parsed.query)
    
    # Remove common tracking parameters
    tracking_params = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'gclid', 'fbclid', 'ref', 'source', 'ref_src', 'ref_url'
    ]
    
    for param in tracking_params:
        params.pop(param, None)
    
    # Rebuild query string
    query = '&'.join(f"{k}={v[0]}" for k, v in params.items())
    
    # Rebuild URL
    normalized = parsed._replace(query=query)
    
    return normalized.geturl()


def extract_base_url(url: str) -> str:
    """Extract base URL (scheme + domain).
    
    Args:
        url: Full URL
        
    Returns:
        Base URL
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def is_product_url(url: str) -> bool:
    """Check if URL is a product page.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be a product page
    """
    # Get site configuration
    site_config = get_site_config(url)
    
    if site_config:
        # Check against site-specific product URL patterns
        for pattern in site_config.product_url_patterns:
            if re.search(pattern, url):
                return True
    
    # Generic product URL indicators
    product_indicators = [
        r'/product/',
        r'/item/',
        r'/dp/',
        r'/gp/product/',
        r'/products/',
        r'/p/',
    ]
    
    return any(re.search(pattern, url.lower()) for pattern in product_indicators)


def is_category_url(url: str) -> bool:
    """Check if URL is a category page.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be a category page
    """
    # Get site configuration
    site_config = get_site_config(url)
    
    if site_config:
        # Check against site-specific category URL patterns
        for pattern in site_config.category_url_patterns:
            if re.search(pattern, url):
                return True
    
    # Generic category URL indicators
    category_indicators = [
        r'/category/',
        r'/categories/',
        r'/c/',
        r'/dept/',
        r'/browse/',
        r'/shop/',
        r'/collection/',
        r'/collections/',
    ]
    
    return any(re.search(pattern, url.lower()) for pattern in category_indicators)


def detect_vendor(url: str) -> str:
    """Detect vendor from URL.
    
    Args:
        url: URL to analyze
        
    Returns:
        Vendor identifier
    """
    # Get site configuration
    site_config = get_site_config(url)
    
    if site_config:
        return site_config.name
    
    # Extract domain as fallback
    domain = urlparse(url).netloc.lower()
    # Remove www. and .com/.co.uk/etc
    domain = re.sub(r'^www\.', '', domain)
    domain = re.sub(r'\.(com|co\.uk|net|org)$', '', domain)
    
    return domain


def extract_category_name(url: str) -> str:
    """Extract category name from URL.
    
    Args:
        url: Category URL
        
    Returns:
        Category name
    """
    # Get site configuration
    site_config = get_site_config(url)
    
    if site_config and site_config.category_name_extractor:
        # Use site-specific extractor
        return site_config.category_name_extractor(url)
    
    # Generic extraction
    path = urlparse(url).path
    
    # Remove leading/trailing slashes and split
    parts = [p for p in path.strip('/').split('/') if p]
    
    # Look for category indicators
    category_indicators = ['category', 'categories', 'dept', 'browse', 'shop']
    for i, part in enumerate(parts):
        if part.lower() in category_indicators and i + 1 < len(parts):
            return parts[i + 1].replace('-', ' ').replace('_', ' ').title()
    
    # Fallback to last path component
    if parts:
        return parts[-1].replace('-', ' ').replace('_', ' ').title()
    
    return "Unknown Category"