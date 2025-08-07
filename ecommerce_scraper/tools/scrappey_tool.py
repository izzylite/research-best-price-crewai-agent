"""Scrappey-based extraction tool for reliable ecommerce product data extraction."""

import json
import logging
import requests
from typing import Any, Dict, List, Optional, Union
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..schemas.product_search_extraction import ProductSearchExtraction


class ScrappeyInput(BaseModel):
    """Input schema for Scrappey tool."""
    url: str = Field(..., description="URL to scrape")
    instruction: str = Field(..., description="Natural language instruction for data extraction")
    vendor: str = Field(..., description="Vendor name (e.g., 'asda', 'tesco')")
    category: str = Field(..., description="Product category (e.g., 'fruit', 'electronics')")
    extraction_type: str = Field("products", description="Type of extraction: 'products', 'navigation', 'observe'")
    use_browser: bool = Field(True, description="Use browser emulation for anti-bot bypass")
    wait_time: Optional[int] = Field(None, description="Time to wait before extraction (seconds)")


class ScrappeyTool(BaseTool):
    """Scrappey-based tool for reliable ecommerce data extraction with anti-bot bypass."""

    name: str = "scrappey_tool"
    description: str = """
    AI-powered web scraping tool using Scrappey.com for reliable ecommerce data extraction.

    Features:
    - Built-in anti-bot bypass (Cloudflare, Datadome, etc.)
    - Automatic proxy rotation and session management
    - AI-powered structured data extraction
    - CAPTCHA solving and browser fingerprint randomization
    - High success rate on protected ecommerce sites

    Extraction types:
    - 'products': Extract product data with StandardizedProduct schema
    - 'navigation': Navigate and observe page elements
    - 'observe': Identify elements and page structure

    Best for UK retail sites: ASDA, Tesco, Waitrose, Next, etc.
    """
    args_schema: type[BaseModel] = ScrappeyInput

    # Pydantic fields for the tool
    api_key: str = Field(default="", description="Scrappey API key")
    base_url: str = Field(default="https://publisher.scrappey.com/api/v1", description="Scrappey API base URL")

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        # Set the API key before calling super().__init__
        if api_key is None:
            api_key = getattr(settings, 'scrappey_api_key', 'SCmmAiI9H2CnerD8ex4YOcvkmMzQgH0P3DyOWmuqk6Mp9YHmn8Fk2AKxF6nj')

        super().__init__(api_key=api_key, **kwargs)
        self._logger = logging.getLogger(__name__)

        if not self.api_key:
            raise ValueError("Scrappey API key is required. Set SCRAPPEY_API_KEY in environment or pass api_key parameter.")

    def _run(self, **kwargs) -> str:
        """Execute Scrappey extraction based on the instruction and extraction type."""
        try:
            url = kwargs.get("url") 
            vendor = kwargs.get("vendor")
            category = kwargs.get("category")
            extraction_type = kwargs.get("extraction_type", "products")
            use_browser = kwargs.get("use_browser", True)
            wait_time = kwargs.get("wait_time")

            if not url:
                return "Error: URL is required for Scrappey extraction"

            self._logger.info(f"[SCRAPPEY] Starting {extraction_type} extraction from {url}")

            # Build Scrappey request payload
            payload = self._build_payload(
                url=url, 
                vendor=vendor,
                category=category,
                extraction_type=extraction_type,
                use_browser=use_browser,
                wait_time=wait_time
            )

            # Set up headers for Scrappey API
            headers = {
                'Content-Type': 'application/json'
            }

            # Build URL with API key parameter
            url_with_key = f"{self.base_url}?key={self.api_key}"

            # Execute Scrappey request
            response = requests.post(url_with_key, json=payload, headers=headers, timeout=60)
            response.raise_for_status()

            result = response.json()
            
            # Process and format the result
            formatted_result = self._process_result(result, extraction_type, vendor, category)
            
            self._logger.info(f"[SCRAPPEY] Extraction completed successfully")
            return formatted_result

        except requests.exceptions.RequestException as e:
            error_msg = f"Scrappey API request failed: {str(e)}"
            self._logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Scrappey extraction error: {str(e)}"
            self._logger.error(error_msg)
            return error_msg

    def _build_payload(self, url: str,  vendor: str, category: str,
                      extraction_type: str, use_browser: bool, wait_time: Optional[int]) -> Dict[str, Any]:
        """Build Scrappey API request payload based on extraction type."""

        # Enhanced payload for JavaScript-heavy sites like ASDA
        payload = {
            'cmd': 'request.get',
            'url': url,
            'renderType': 'html',  # Render full HTML with JavaScript
            'wait': (wait_time or 10) * 1000,  # Wait time in milliseconds (default 10 seconds)
            'waitForSelector': self._get_wait_selector(vendor),  # Wait for specific elements
            'blockResources': ['image', 'media', 'font'],  # Block unnecessary resources for faster loading
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        return payload

    def _get_wait_selector(self, vendor: str) -> str:
        """Get vendor-specific selector to wait for before considering page loaded."""
        wait_selectors = {
            'asda': '.co-product, [data-auto-id*="product"], .product-tile',
            'tesco': '.product-list--list-item, .product-tile',
            'waitrose': '.productLister-item, .product-item',
            'next': '.Product, .ProductItem',
            'mamas-papas': '.product-item, .product-tile',
            'primark': '.product-item, .product-card',
            'toy-shop': '.product-item, .product-card',
            'costco': '.product-item, .product-tile',
            'hamleys': '.product-item, .product-card',
            'selfridges': '.product-item, .product-card'
        }

        return wait_selectors.get(vendor.lower(), '.product-item, .product-card, [data-product]')

    def _get_product_selectors(self, vendor: str) -> str:
        """Get vendor-specific product selectors."""
        vendor_selectors = {
            'asda': '.co-product, .product-item, [data-testid*="product"]',
            'tesco': '.product-list--list-item, .product-tile, .product-item',
            'waitrose': '.productLister-item, .product-item, .product-card',
            'next': '.Product, .ProductItem, .product-item',
            'mamas-papas': '.product-item, .product-tile, .product-card',
            'primark': '.product-item, .product-card, .product-tile',
            'toy-shop': '.product-item, .product-card, .product-tile',
            'costco': '.product-item, .product-tile, .product-card',
            'hamleys': '.product-item, .product-card, .product-tile',
            'selfridges': '.product-item, .product-card, .product-tile'
        }
        
        return vendor_selectors.get(vendor.lower(), '.product-item, .product-card, .product-tile, [data-product]')

    def _process_result(self, result: Dict[str, Any], extraction_type: str, vendor: str, category: str) -> str:
        """Process and format Scrappey result based on extraction type."""
        try:
            if extraction_type == "products":
                # Extract HTML from Scrappey response structure
                html_content = ""
                if 'solution' in result and 'response' in result['solution']:
                    html_content = result['solution']['response']
                elif 'data' in result:
                    html_content = result['data']

                if html_content and isinstance(html_content, str):
                    return self._extract_products_from_html(html_content, vendor, category)
                else:
                    self._logger.warning("No HTML content found in Scrappey response")
                    return json.dumps([], indent=2)
            elif extraction_type in ["navigation", "observe"]:
                return json.dumps(result, indent=2, default=str)
            else:
                return json.dumps(result, indent=2, default=str)

        except Exception as e:
            self._logger.error(f"Error processing Scrappey result: {e}")
            return json.dumps(result, indent=2, default=str)

    def _extract_products_from_html(self, html_content: str, vendor: str, category: str) -> str:
        """Extract products from HTML content using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')
            products = []

            # Get vendor-specific selectors
            product_selectors = self._get_product_selectors(vendor).split(', ')

            # Try each selector until we find products
            product_elements = []
            for selector in product_selectors:
                product_elements = soup.select(selector.strip())
                if product_elements:
                    break

            self._logger.info(f"[SCRAPPEY] Found {len(product_elements)} product elements")

            for element in product_elements:
                try:
                    # Extract product data
                    name = self._extract_text_from_element(element, [
                        '.product-title', 'h3', '.name', '[data-testid*="title"]', '.product-name'
                    ])

                    price_text = self._extract_text_from_element(element, [
                        '.price', '.cost', '.amount', '[data-testid*="price"]', '.product-price'
                    ])

                    image_url = self._extract_image_from_element(element)

                    description = self._extract_text_from_element(element, [
                        '.description', '.details', '.product-description'
                    ]) or name

                    weight = self._extract_text_from_element(element, [
                        '.weight', '.size', '.quantity', '.pack-size'
                    ])

                    if name and price_text:
                        product = {
                            "name": self._clean_text(name),
                            "description": self._clean_text(description),
                            "price": self._format_price(price_text),
                            "image_url": self._clean_url(image_url),
                            "category": category,
                            "vendor": vendor,
                            "weight": self._clean_text(weight),
                            "availability": "unknown"
                        }

                        # Only add products with valid price
                        if product['price']['amount'] > 0:
                            products.append(product)

                except Exception as e:
                    self._logger.warning(f"Error extracting product: {e}")
                    continue

            self._logger.info(f"[SCRAPPEY] Successfully extracted {len(products)} products")
            return json.dumps(products, indent=2, default=str)

        except ImportError:
            self._logger.error("BeautifulSoup4 is required for HTML parsing. Install with: pip install beautifulsoup4")
            return json.dumps([], indent=2)
        except Exception as e:
            self._logger.error(f"Error extracting products from HTML: {e}")
            return json.dumps([], indent=2)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        return str(text).strip().replace('\n', ' ').replace('\t', ' ')

    def _clean_url(self, url: str) -> str:
        """Clean and validate image URLs."""
        if not url:
            return ""
        url = str(url).strip()
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            # Relative URL - would need base URL to resolve
            pass
        return url

    def _extract_text_from_element(self, element, selectors: List[str]) -> str:
        """Extract text from element using multiple selectors."""
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found and found.get_text(strip=True):
                    return found.get_text(strip=True)
            except Exception:
                continue
        return ""

    def _extract_image_from_element(self, element) -> str:
        """Extract image URL from element."""
        try:
            # Try different image selectors
            img = element.select_one('img')
            if img:
                # Try src first, then data-src for lazy loading
                return img.get('src') or img.get('data-src') or ""
        except Exception:
            pass
        return ""

    def _format_price(self, price_text: str) -> Dict[str, Any]:
        """Extract and format price information."""
        if not price_text:
            return {"amount": 0.0, "currency": "GBP"}

        # Extract numeric price
        import re
        price_match = re.search(r'[\d,]+\.?\d*', str(price_text).replace(',', ''))
        if price_match:
            try:
                amount = float(price_match.group())
                return {"amount": amount, "currency": "GBP"}
            except ValueError:
                pass

        return {"amount": 0.0, "currency": "GBP"}
