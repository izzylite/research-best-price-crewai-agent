"""Data processing and validation tools for ecommerce scraping."""

import re
import json
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ValidationError

from ..schemas.product import Product, ProductPrice, ProductImage, ProductReview, ProductAvailability


class DataValidationInput(BaseModel):
    """Input schema for data validation tools."""
    data: Union[str, Dict[str, Any]] = Field(..., description="Raw data to validate and clean")
    base_url: Optional[str] = Field(None, description="Base URL for resolving relative URLs")


class ProductDataValidator(BaseTool):
    """Tool for validating and cleaning extracted product data."""
    
    name: str = "product_data_validator"
    description: str = """
    Validates and cleans extracted product data, converting it to standardized Product schema.
    Handles data type conversion, URL resolution, and data quality checks.
    """
    args_schema: type[BaseModel] = DataValidationInput
    
    def _run(self, **kwargs) -> str:
        """Validate and clean product data."""
        try:
            data = kwargs.get("data")
            base_url = kwargs.get("base_url")
            
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON data provided"
            
            if not isinstance(data, dict):
                return f"Error: Data must be a dictionary or JSON string"
            
            # Clean and validate the data
            cleaned_data = self._clean_product_data(data, base_url)
            
            # Try to create a Product instance to validate
            try:
                product = Product(**cleaned_data)
                return json.dumps(product.model_dump(), indent=2, default=str)
            except ValidationError as e:
                # Return cleaned data even if validation fails, with error info
                return json.dumps({
                    "cleaned_data": cleaned_data,
                    "validation_errors": str(e)
                }, indent=2, default=str)
                
        except Exception as e:
            return f"Error validating product data: {str(e)}"
    
    def _clean_product_data(self, data: Dict[str, Any], base_url: Optional[str] = None) -> Dict[str, Any]:
        """Clean and standardize product data."""
        cleaned = {}
        
        # Basic information
        cleaned["title"] = self._clean_text(data.get("title") or data.get("name") or data.get("product_name"))
        cleaned["description"] = self._clean_text(data.get("description") or data.get("product_description"))
        cleaned["brand"] = self._clean_text(data.get("brand") or data.get("manufacturer"))
        cleaned["model"] = self._clean_text(data.get("model") or data.get("model_number"))
        cleaned["sku"] = self._clean_text(data.get("sku") or data.get("product_id"))
        
        # Price information
        price_data = self._extract_price_info(data)
        if price_data:
            cleaned["price"] = price_data
        
        # Availability
        availability = self._extract_availability(data)
        if availability:
            cleaned["availability"] = availability
        
        # Images
        images = self._extract_images(data, base_url)
        if images:
            cleaned["images"] = images
        
        # Reviews
        reviews = self._extract_reviews(data)
        if reviews:
            cleaned["reviews"] = reviews
        
        # Categories and tags
        if data.get("category"):
            cleaned["category"] = self._clean_text(data["category"])
        if data.get("categories"):
            cleaned["categories"] = [self._clean_text(cat) for cat in data["categories"] if cat]
        
        # Source information
        if data.get("url") or base_url:
            cleaned["source_url"] = data.get("url") or base_url
        
        return {k: v for k, v in cleaned.items() if v is not None}
    
    def _clean_text(self, text: Any) -> Optional[str]:
        """Clean and normalize text data."""
        if not text:
            return None
        
        text = str(text).strip()
        if not text:
            return None
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _extract_price_info(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and clean price information."""
        price_info = {}
        
        # Try different price field names
        current_price = (data.get("price") or data.get("current_price") or 
                        data.get("selling_price") or data.get("sale_price"))
        original_price = (data.get("original_price") or data.get("list_price") or 
                         data.get("msrp") or data.get("regular_price"))
        
        if current_price:
            price_info["current_price"] = self._parse_price(current_price)
        if original_price:
            price_info["original_price"] = self._parse_price(original_price)
        
        # Currency
        currency = data.get("currency", "USD")
        if currency:
            price_info["currency"] = currency
        
        # Calculate discount if both prices available
        if price_info.get("current_price") and price_info.get("original_price"):
            current = price_info["current_price"]
            original = price_info["original_price"]
            if current < original:
                discount = ((original - current) / original) * 100
                price_info["discount_percentage"] = round(discount, 2)
        
        return price_info if price_info else None
    
    def _parse_price(self, price_str: Any) -> Optional[Decimal]:
        """Parse price string to Decimal."""
        if not price_str:
            return None
        
        # Convert to string and clean
        price_str = str(price_str).strip()
        
        # Remove currency symbols and common formatting
        price_str = re.sub(r'[^\d.,]', '', price_str)
        
        # Handle different decimal separators
        if ',' in price_str and '.' in price_str:
            # Assume comma is thousands separator
            price_str = price_str.replace(',', '')
        elif ',' in price_str:
            # Could be decimal separator in some locales
            if price_str.count(',') == 1 and len(price_str.split(',')[1]) <= 2:
                price_str = price_str.replace(',', '.')
            else:
                price_str = price_str.replace(',', '')
        
        try:
            return Decimal(price_str)
        except (InvalidOperation, ValueError):
            return None
    
    def _extract_availability(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract availability status."""
        availability = (data.get("availability") or data.get("stock_status") or 
                       data.get("in_stock"))
        
        if not availability:
            return None
        
        availability_str = str(availability).lower()
        
        if any(term in availability_str for term in ["in stock", "available", "yes", "true"]):
            return ProductAvailability.IN_STOCK
        elif any(term in availability_str for term in ["out of stock", "unavailable", "no", "false"]):
            return ProductAvailability.OUT_OF_STOCK
        elif "limited" in availability_str:
            return ProductAvailability.LIMITED_STOCK
        elif "preorder" in availability_str:
            return ProductAvailability.PREORDER
        else:
            return ProductAvailability.UNKNOWN
    
    def _extract_images(self, data: Dict[str, Any], base_url: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Extract and clean image URLs."""
        images_data = data.get("images") or data.get("image_urls") or data.get("photos")
        
        if not images_data:
            # Try single image fields
            single_image = data.get("image") or data.get("image_url") or data.get("photo")
            if single_image:
                images_data = [single_image]
        
        if not images_data:
            return None
        
        images = []
        for i, img in enumerate(images_data):
            if isinstance(img, str):
                url = self._resolve_url(img, base_url)
                if url:
                    images.append({
                        "url": url,
                        "is_primary": i == 0
                    })
            elif isinstance(img, dict):
                url = self._resolve_url(img.get("url") or img.get("src"), base_url)
                if url:
                    images.append({
                        "url": url,
                        "alt_text": img.get("alt"),
                        "is_primary": img.get("is_primary", i == 0)
                    })
        
        return images if images else None
    
    def _extract_reviews(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract review information."""
        reviews = {}
        
        rating = data.get("rating") or data.get("average_rating") or data.get("stars")
        if rating:
            try:
                reviews["rating"] = float(rating)
            except (ValueError, TypeError):
                pass
        
        review_count = data.get("review_count") or data.get("reviews") or data.get("num_reviews")
        if review_count:
            try:
                reviews["review_count"] = int(review_count)
            except (ValueError, TypeError):
                pass
        
        return reviews if reviews else None
    
    def _resolve_url(self, url: Optional[str], base_url: Optional[str] = None) -> Optional[str]:
        """Resolve relative URLs to absolute URLs."""
        if not url:
            return None
        
        url = url.strip()
        if not url:
            return None
        
        # If already absolute, return as-is
        if url.startswith(('http://', 'https://')):
            return url
        
        # If relative and we have a base URL, resolve it
        if base_url:
            try:
                return urljoin(base_url, url)
            except Exception:
                pass
        
        return url


class PriceExtractor(BaseTool):
    """Specialized tool for extracting price information."""
    
    name: str = "price_extractor"
    description: str = "Extract and parse price information from text or HTML content."
    args_schema: type[BaseModel] = DataValidationInput
    
    def _run(self, **kwargs) -> str:
        """Extract price information."""
        try:
            data = kwargs.get("data", "")
            
            if isinstance(data, dict):
                data = json.dumps(data)
            
            prices = self._extract_prices_from_text(str(data))
            return json.dumps(prices, indent=2, default=str)
            
        except Exception as e:
            return f"Error extracting prices: {str(e)}"
    
    def _extract_prices_from_text(self, text: str) -> Dict[str, Any]:
        """Extract price patterns from text."""
        # Common price patterns
        price_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $123.45, $1,234.56
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 123.45 USD
            r'Price:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Price: $123.45
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',  # 123.45 dollars
        ]
        
        found_prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean and convert to Decimal
                    clean_price = match.replace(',', '')
                    price = Decimal(clean_price)
                    found_prices.append(float(price))
                except (InvalidOperation, ValueError):
                    continue
        
        result = {"found_prices": found_prices}
        if found_prices:
            result["min_price"] = min(found_prices)
            result["max_price"] = max(found_prices)
            result["avg_price"] = sum(found_prices) / len(found_prices)
        
        return result


class ImageExtractor(BaseTool):
    """Tool for extracting and validating image URLs."""
    
    name: str = "image_extractor"
    description: str = "Extract and validate image URLs from content."
    args_schema: type[BaseModel] = DataValidationInput
    
    def _run(self, **kwargs) -> str:
        """Extract image URLs."""
        try:
            data = kwargs.get("data", "")
            base_url = kwargs.get("base_url")
            
            if isinstance(data, dict):
                data = json.dumps(data)
            
            images = self._extract_images_from_text(str(data), base_url)
            return json.dumps(images, indent=2)
            
        except Exception as e:
            return f"Error extracting images: {str(e)}"
    
    def _extract_images_from_text(self, text: str, base_url: Optional[str] = None) -> List[Dict[str, str]]:
        """Extract image URLs from text."""
        # Image URL patterns
        img_patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',  # HTML img tags
            r'background-image:\s*url\(["\']?([^"\']+)["\']?\)',  # CSS background images
            r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|svg)',  # Direct image URLs
        ]
        
        found_images = []
        for pattern in img_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                url = match.strip()
                if base_url and not url.startswith(('http://', 'https://')):
                    url = urljoin(base_url, url)
                
                if self._is_valid_image_url(url):
                    found_images.append({
                        "url": url,
                        "type": self._get_image_type(url)
                    })
        
        return found_images
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL appears to be a valid image URL."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def _get_image_type(self, url: str) -> str:
        """Get image type from URL."""
        url_lower = url.lower()
        if '.jpg' in url_lower or '.jpeg' in url_lower:
            return 'jpeg'
        elif '.png' in url_lower:
            return 'png'
        elif '.gif' in url_lower:
            return 'gif'
        elif '.webp' in url_lower:
            return 'webp'
        elif '.svg' in url_lower:
            return 'svg'
        else:
            return 'unknown'
