"""Simplified product extraction schema for product-specific search system."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class ProductSearchExtraction(BaseModel):
    """Simplified product extraction schema focused on core search fields."""
    
    # Core fields for product search
    product_name: str = Field(..., description="Product name as found on the page")
    price: str = Field(..., description="Product price in GBP format (e.g., '£99.99')")
    url: str = Field(..., description="Direct URL to the product page")
    
    # Context fields
    retailer: str = Field(..., description="Retailer name (e.g., 'Amazon')")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the data was extracted")
    
    @field_validator('product_name')
    @classmethod
    def validate_product_name(cls, v: str) -> str:
        """Clean and validate product name."""
        if not v or not v.strip():
            raise ValueError("Product name cannot be empty")
        # Clean up common issues
        cleaned = v.strip()
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: str) -> str:
        """Validate and clean price format."""
        if not v or not v.strip():
            raise ValueError("Price cannot be empty")
        
        v = v.strip()
        
        # Ensure price starts with £ symbol
        if not v.startswith('£'):
            # Try to extract numeric value and add £
            import re
            price_match = re.search(r'[\d,]+\.?\d*', v)
            if price_match:
                v = f"£{price_match.group()}"
            else:
                # Fallback for invalid prices
                v = "£0.00"
        
        return v
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        
        v = v.strip()
        
        # Check if it's a valid URL format
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('//')):
            raise ValueError("URL must be a valid web address")
        
        # Convert protocol-relative URLs to HTTPS
        if v.startswith('//'):
            v = 'https:' + v
        
        return v
    
    @field_validator('retailer')
    @classmethod
    def validate_retailer(cls, v: str) -> str:
        """Clean and validate retailer name."""
        if not v or not v.strip():
            raise ValueError("Retailer name cannot be empty")
        return v.strip().title()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "product_name": self.product_name,
            "price": self.price,
            "url": self.url,
            "retailer": self.retailer,
            "extracted_at": self.extracted_at.isoformat()
        }
    
    def matches_search_query(self, search_query: str, similarity_threshold: float = 0.7) -> bool:
        """Check if this product matches the original search query."""
        import re
        
        # Normalize both strings for comparison
        def normalize_text(text: str) -> str:
            # Convert to lowercase, remove special characters, normalize whitespace
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            return ' '.join(text.split())
        
        normalized_product = normalize_text(self.product_name)
        normalized_query = normalize_text(search_query)
        
        # Simple keyword matching - check if most query words are in product name
        query_words = set(normalized_query.split())
        product_words = set(normalized_product.split())
        
        if not query_words:
            return False
        
        # Calculate overlap ratio
        overlap = len(query_words.intersection(product_words))
        similarity = overlap / len(query_words)
        
        return similarity >= similarity_threshold
    
   
    def extract_price_value(self) -> float:
        """Extract numeric price value for comparison."""
        try:
            # Remove currency symbols and convert to float
            import re
            price_clean = re.sub(r'[£,]', '', self.price).strip()
            return float(price_clean)
        except (ValueError, AttributeError):
            return 0.0
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
        "str_strip_whitespace": True,
        "validate_assignment": True
    }


class ProductSearchExtractionBatch(BaseModel):
    """Batch of product search extractions with metadata."""
    
    products: List[ProductSearchExtraction] = Field(..., description="List of extracted products")
    search_query: str = Field(..., description="Original search query")
    retailer: str = Field(..., description="Retailer name")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Extraction metadata")
    
    @field_validator('products')
    @classmethod
    def validate_products(cls, v: List[ProductSearchExtraction]) -> List[ProductSearchExtraction]:
        """Validate products list."""
        if not isinstance(v, list):
            raise ValueError("Products must be a list")
        return v
    
    def filter_matching_products(self, similarity_threshold: float = 0.7) -> 'ProductSearchExtractionBatch':
        """Filter products that match the search query."""
        matching_products = [
            product for product in self.products 
            if product.matches_search_query(self.search_query, similarity_threshold)
        ]
        
        return ProductSearchExtractionBatch(
            products=matching_products,
            search_query=self.search_query,
            retailer=self.retailer,
            extraction_metadata={
                **self.extraction_metadata,
                "filtered_by": "search_query_match",
                "original_count": len(self.products),
                "filtered_count": len(matching_products)
            }
        )
    
   
        
        return ProductSearchExtractionBatch(
            products=valid_products,
            search_query=self.search_query,
            retailer=self.retailer,
            extraction_metadata={
                **self.extraction_metadata,
                "filtered_by": "valid_uk_retailers",
                "original_count": len(self.products),
                "filtered_count": len(valid_products)
            }
        )
    
    def get_best_price(self) -> Optional[ProductSearchExtraction]:
        """Get the product with the best (lowest) price."""
        if not self.products:
            return None
        
        return min(self.products, key=lambda p: p.extract_price_value())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "products": [product.to_dict() for product in self.products],
            "search_query": self.search_query,
            "retailer": self.retailer,
            "extraction_metadata": self.extraction_metadata
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the extraction batch."""
        if not self.products:
            return {
                "search_query": self.search_query,
                "retailer": self.retailer,
                "total_products": 0,
                "price_range": None,
                "extraction_metadata": self.extraction_metadata
            }
        
        prices = [p.extract_price_value() for p in self.products if p.extract_price_value() > 0]
        
        return {
            "search_query": self.search_query,
            "retailer": self.retailer,
            "total_products": len(self.products),
            "price_range": {
                "min": f"£{min(prices):.2f}" if prices else "N/A",
                "max": f"£{max(prices):.2f}" if prices else "N/A",
                "avg": f"£{sum(prices)/len(prices):.2f}" if prices else "N/A"
            },
            "extraction_metadata": self.extraction_metadata
        }


# Utility functions
def create_extraction_from_raw(
    raw_data: Dict[str, Any],
    search_query: str,
    retailer: str
) -> ProductSearchExtraction:
    """Create ProductSearchExtraction from raw scraped data."""
    
    # Extract product name
    product_name = (
        raw_data.get('name') or 
        raw_data.get('title') or 
        raw_data.get('product_name') or
        'Unknown Product'
    )
    
    # Extract price
    price_data = raw_data.get('price', {})
    if isinstance(price_data, dict):
        price = price_data.get('amount') or price_data.get('current') or price_data.get('value') or '£0.00'
        if isinstance(price, (int, float)):
            price = f"£{price:.2f}"
    else:
        price = str(price_data) if price_data else '£0.00'
    
    # Extract URL
    url = (
        raw_data.get('url') or 
        raw_data.get('product_url') or 
        raw_data.get('link') or
        'https://example.com'
    )
    
    return ProductSearchExtraction(
        product_name=product_name,
        price=price,
        url=url,
        retailer=retailer
    )


def validate_extraction_batch(
    raw_products: List[Dict[str, Any]],
    search_query: str,
    retailer: str
) -> ProductSearchExtractionBatch:
    """Validate and create extraction batch from raw product data."""
    
    valid_products = []
    for raw_product in raw_products:
        try:
            product = create_extraction_from_raw(raw_product, search_query, retailer)
            valid_products.append(product)
        except Exception:
            # Continue processing without warning logs
            continue
    
    return ProductSearchExtractionBatch(
        products=valid_products,
        search_query=search_query,
        retailer=retailer,
        extraction_metadata={
            "total_raw_products": len(raw_products),
            "valid_products": len(valid_products),
            "validation_success_rate": len(valid_products) / len(raw_products) if raw_products else 0.0
        }
    )
