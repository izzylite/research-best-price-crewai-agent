"""Standardized product schema for multi-vendor ecommerce scraping."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import ValidationError


class StandardizedPrice(BaseModel):
    """Standardized price information."""
    
    amount: float = Field(..., description="Price amount as a number", gt=0)
    currency: str = Field(default="GBP", description="Currency code (ISO 4217)")
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code."""
        valid_currencies = ['GBP', 'USD', 'EUR']
        if v.upper() not in valid_currencies:
            # Default to GBP for UK retailers
            return 'GBP'
        return v.upper()
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate price amount."""
        if v <= 0:
            raise ValueError("Price amount must be greater than 0")
        # Round to 2 decimal places for currency
        return round(v, 2)


class StandardizedProduct(BaseModel):
    """Standardized product schema for multi-vendor scraping.
    
    This schema matches the user's requirements exactly:
    - name (string, required): Product title/name
    - description (string, required): Product description 
    - price (object, required): Contains amount (number) and currency (string)
    - image_url (string, required): Primary product image URL
    - weight (string, optional): Product weight if available, null otherwise
    - category (string, required): Product category
    - vendor (string, required): Source website identifier
    - scraped_at (timestamp, required): When the data was extracted
    """
    
    # Required fields
    name: str = Field(..., description="Product title/name", min_length=1)
    description: str = Field(..., description="Product description", min_length=1)
    price: StandardizedPrice = Field(..., description="Product pricing information")
    image_url: str = Field(..., description="Primary product image URL")
    category: str = Field(..., description="Product category", min_length=1)
    vendor: str = Field(..., description="Source website identifier", min_length=1)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the data was extracted")
    
    # Optional fields
    weight: Optional[str] = Field(None, description="Product weight if available, null otherwise")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Clean and validate product name."""
        if not v or not v.strip():
            raise ValueError("Product name cannot be empty")
        # Clean up common issues
        cleaned = v.strip()
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Clean and validate product description."""
        if not v or not v.strip():
            raise ValueError("Product description cannot be empty")
        # Clean up common issues
        cleaned = v.strip()
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        # Remove HTML tags if present
        import re
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        return cleaned
    
    @field_validator('image_url')
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        """Validate image URL format."""
        if not v or not v.strip():
            raise ValueError("Image URL cannot be empty")
        
        v = v.strip()
        
        # Check if it's a valid URL format
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('//')):
            raise ValueError("Image URL must be a valid HTTP/HTTPS URL")
        
        # Convert protocol-relative URLs to HTTPS
        if v.startswith('//'):
            v = 'https:' + v
            
        return v
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Clean and validate category."""
        if not v or not v.strip():
            raise ValueError("Category cannot be empty")
        return v.strip().title()
    
    @field_validator('vendor')
    @classmethod
    def validate_vendor(cls, v: str) -> str:
        """Validate vendor identifier."""
        if not v or not v.strip():
            raise ValueError("Vendor cannot be empty")
        return v.strip().lower()
    
    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v: Optional[str]) -> Optional[str]:
        """Validate weight format if provided."""
        if v is None:
            return None
        
        v = v.strip()
        if not v:
            return None
            
        # Basic weight format validation (e.g., "500g", "1.5kg", "2 lbs")
        import re
        weight_pattern = r'^\d+(\.\d+)?\s*(g|kg|lb|lbs|oz|ml|l)$'
        if not re.match(weight_pattern, v.lower()):
            # If format doesn't match, still return it but log a warning
            return v
        
        return v
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
        "str_strip_whitespace": True,
        "validate_assignment": True
    }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "price": {
                "amount": self.price.amount,
                "currency": self.price.currency
            },
            "image_url": self.image_url,
            "weight": self.weight,
            "category": self.category,
            "vendor": self.vendor,
            "scraped_at": self.scraped_at.isoformat()
        }
    
    @classmethod
    def from_raw_data(cls, raw_data: Dict[str, Any], vendor: str, category: str) -> 'StandardizedProduct':
        """Create StandardizedProduct from raw scraped data.
        
        Args:
            raw_data: Raw product data from scraping
            vendor: Vendor identifier
            category: Product category
            
        Returns:
            StandardizedProduct instance
            
        Raises:
            ValidationError: If required fields are missing or invalid
        """
        try:
            # Extract price information
            price_data = raw_data.get('price', {})
            if isinstance(price_data, (int, float)):
                # Handle simple numeric price
                price = StandardizedPrice(amount=float(price_data), currency="GBP")
            elif isinstance(price_data, dict):
                # Handle structured price data
                amount = price_data.get('amount') or price_data.get('current') or price_data.get('value')
                currency = price_data.get('currency', 'GBP')
                if amount is None:
                    raise ValueError("Price amount not found in price data")
                price = StandardizedPrice(amount=float(amount), currency=currency)
            else:
                raise ValueError("Invalid price data format")
            
            # Extract other fields with fallbacks
            name = raw_data.get('title') or raw_data.get('name') or raw_data.get('product_name')
            if not name:
                raise ValueError("Product name/title not found")
            
            description = (raw_data.get('description') or 
                          raw_data.get('summary') or 
                          raw_data.get('details') or 
                          name)  # Fallback to name if no description
            
            # Handle image URL
            image_url = None
            images = raw_data.get('images', [])
            if images and isinstance(images, list):
                # Get first image URL
                first_image = images[0]
                if isinstance(first_image, dict):
                    image_url = first_image.get('url') or first_image.get('src')
                else:
                    image_url = str(first_image)
            else:
                image_url = raw_data.get('image_url') or raw_data.get('image') or raw_data.get('thumbnail')
            
            if not image_url:
                raise ValueError("Product image URL not found")
            
            # Extract weight (optional)
            weight = raw_data.get('weight') or raw_data.get('size') or raw_data.get('dimensions')
            
            return cls(
                name=name,
                description=description,
                price=price,
                image_url=image_url,
                weight=weight,
                category=category,
                vendor=vendor
            )
            
        except Exception as e:
            raise ValidationError(f"Failed to create StandardizedProduct: {str(e)}")
    
    def get_quality_score(self) -> float:
        """Calculate data quality score (0.0 to 1.0).
        
        Returns:
            Quality score based on completeness and validity
        """
        score = 0.0
        total_checks = 8
        
        # Required field checks (6 points)
        if self.name and len(self.name.strip()) > 0:
            score += 1
        if self.description and len(self.description.strip()) > 10:  # Meaningful description
            score += 1
        if self.price and self.price.amount > 0:
            score += 1
        if self.image_url and self.image_url.startswith(('http', '//')):
            score += 1
        if self.category and len(self.category.strip()) > 0:
            score += 1
        if self.vendor and len(self.vendor.strip()) > 0:
            score += 1
        
        # Optional field checks (1 point)
        if self.weight:
            score += 1
        
        # Data quality checks (1 point)
        if len(self.description) > 50:  # Rich description
            score += 1
        
        return score / total_checks
    
    def is_valid_for_export(self) -> bool:
        """Check if product meets minimum quality standards for export."""
        return (
            self.name and len(self.name.strip()) > 0 and
            self.description and len(self.description.strip()) > 0 and
            self.price and self.price.amount > 0 and
            self.image_url and self.image_url.startswith(('http', '//')) and
            self.category and len(self.category.strip()) > 0 and
            self.vendor and len(self.vendor.strip()) > 0
        )


# Utility functions for batch processing
def validate_product_batch(products: list[Dict[str, Any]], vendor: str, category: str) -> tuple[list[StandardizedProduct], list[Dict[str, Any]]]:
    """Validate a batch of raw product data.
    
    Args:
        products: List of raw product data dictionaries
        vendor: Vendor identifier
        category: Product category
        
    Returns:
        Tuple of (valid_products, failed_products)
    """
    valid_products = []
    failed_products = []
    
    for raw_product in products:
        try:
            product = StandardizedProduct.from_raw_data(raw_product, vendor, category)
            if product.is_valid_for_export():
                valid_products.append(product)
            else:
                failed_products.append({
                    "data": raw_product,
                    "error": "Failed quality validation"
                })
        except Exception as e:
            failed_products.append({
                "data": raw_product,
                "error": str(e)
            })
    
    return valid_products, failed_products


def export_products_to_json(products: list[StandardizedProduct], filename: str) -> None:
    """Export standardized products to JSON file.
    
    Args:
        products: List of StandardizedProduct instances
        filename: Output filename
    """
    import json
    from pathlib import Path
    
    # Ensure output directory exists
    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dictionaries
    products_data = [product.to_dict() for product in products]
    
    # Add metadata
    export_data = {
        "metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_products": len(products),
            "schema_version": "1.0"
        },
        "products": products_data
    }
    
    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


class ProductBatch(BaseModel):
    """Batch of standardized products with metadata."""

    products: List[StandardizedProduct] = Field(..., description="List of products in the batch")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Batch metadata")

    @field_validator('products')
    @classmethod
    def validate_products(cls, v: List[StandardizedProduct]) -> List[StandardizedProduct]:
        """Validate products list."""
        if not v:
            raise ValueError("Products list cannot be empty")
        return v

    def get_batch_summary(self) -> Dict[str, Any]:
        """Get summary of the batch."""
        vendors = set(product.vendor for product in self.products)
        categories = set(product.category for product in self.products)

        return {
            "total_products": len(self.products),
            "unique_vendors": len(vendors),
            "unique_categories": len(categories),
            "vendors": list(vendors),
            "categories": list(categories),
            "metadata": self.metadata
        }

    def filter_by_vendor(self, vendor: str) -> 'ProductBatch':
        """Filter products by vendor."""
        filtered_products = [p for p in self.products if p.vendor == vendor]
        return ProductBatch(
            products=filtered_products,
            metadata={**self.metadata, "filtered_by": f"vendor:{vendor}"}
        )

    def filter_by_category(self, category: str) -> 'ProductBatch':
        """Filter products by category."""
        filtered_products = [p for p in self.products if p.category == category]
        return ProductBatch(
            products=filtered_products,
            metadata={**self.metadata, "filtered_by": f"category:{category}"}
        )
