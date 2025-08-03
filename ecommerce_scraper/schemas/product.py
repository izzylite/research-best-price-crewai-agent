"""Product data schemas for standardized ecommerce data extraction."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from enum import Enum


class ProductAvailability(str, Enum):
    """Product availability status."""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LIMITED_STOCK = "limited_stock"
    PREORDER = "preorder"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"


class ProductCondition(str, Enum):
    """Product condition."""
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    OPEN_BOX = "open_box"
    UNKNOWN = "unknown"


class ProductPrice(BaseModel):
    """Product pricing information."""
    current_price: Optional[Decimal] = Field(None, description="Current selling price")
    original_price: Optional[Decimal] = Field(None, description="Original/MSRP price")
    currency: str = Field("USD", description="Currency code (ISO 4217)")
    discount_percentage: Optional[float] = Field(None, description="Discount percentage if on sale")
    price_range_min: Optional[Decimal] = Field(None, description="Minimum price for variable pricing")
    price_range_max: Optional[Decimal] = Field(None, description="Maximum price for variable pricing")
    
    @validator('discount_percentage')
    def validate_discount(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Discount percentage must be between 0 and 100')
        return v


class ProductImage(BaseModel):
    """Product image information."""
    url: HttpUrl = Field(..., description="Image URL")
    alt_text: Optional[str] = Field(None, description="Alt text for the image")
    is_primary: bool = Field(False, description="Whether this is the primary product image")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")


class ProductVariant(BaseModel):
    """Product variant information (size, color, etc.)."""
    name: str = Field(..., description="Variant name (e.g., 'Large', 'Red', 'iPhone 15 Pro')")
    type: str = Field(..., description="Variant type (e.g., 'size', 'color', 'model')")
    value: str = Field(..., description="Variant value")
    price: Optional[ProductPrice] = Field(None, description="Variant-specific pricing")
    availability: ProductAvailability = Field(ProductAvailability.UNKNOWN, description="Variant availability")
    sku: Optional[str] = Field(None, description="Variant SKU")
    image_urls: List[HttpUrl] = Field(default_factory=list, description="Variant-specific images")


class ProductReview(BaseModel):
    """Product review information."""
    rating: Optional[float] = Field(None, description="Review rating (e.g., 4.5 out of 5)")
    review_count: Optional[int] = Field(None, description="Total number of reviews")
    rating_distribution: Optional[Dict[str, int]] = Field(None, description="Rating distribution (e.g., {'5': 100, '4': 50})")
    
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v


class Product(BaseModel):
    """Complete product information schema."""
    
    # Basic Information
    title: str = Field(..., description="Product title/name")
    description: Optional[str] = Field(None, description="Product description")
    brand: Optional[str] = Field(None, description="Product brand")
    model: Optional[str] = Field(None, description="Product model")
    sku: Optional[str] = Field(None, description="Stock Keeping Unit")
    upc: Optional[str] = Field(None, description="Universal Product Code")
    
    # Pricing
    price: Optional[ProductPrice] = Field(None, description="Product pricing information")
    
    # Availability
    availability: ProductAvailability = Field(ProductAvailability.UNKNOWN, description="Product availability")
    condition: ProductCondition = Field(ProductCondition.UNKNOWN, description="Product condition")
    stock_quantity: Optional[int] = Field(None, description="Available stock quantity")
    
    # Media
    images: List[ProductImage] = Field(default_factory=list, description="Product images")
    
    # Variants
    variants: List[ProductVariant] = Field(default_factory=list, description="Product variants")
    
    # Reviews and Ratings
    reviews: Optional[ProductReview] = Field(None, description="Product review information")
    
    # Categories and Tags
    category: Optional[str] = Field(None, description="Primary product category")
    categories: List[str] = Field(default_factory=list, description="All product categories")
    tags: List[str] = Field(default_factory=list, description="Product tags")
    
    # Specifications
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Product specifications")
    features: List[str] = Field(default_factory=list, description="Product features")
    
    # Shipping and Delivery
    shipping_info: Optional[str] = Field(None, description="Shipping information")
    delivery_time: Optional[str] = Field(None, description="Estimated delivery time")
    
    # Source Information
    source_url: Optional[HttpUrl] = Field(None, description="URL where the product was scraped from")
    source_site: Optional[str] = Field(None, description="Source website name")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When the data was scraped")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }
    
    def get_primary_image(self) -> Optional[ProductImage]:
        """Get the primary product image."""
        for image in self.images:
            if image.is_primary:
                return image
        return self.images[0] if self.images else None
    
    def get_current_price(self) -> Optional[Decimal]:
        """Get the current price of the product."""
        return self.price.current_price if self.price else None
    
    def is_on_sale(self) -> bool:
        """Check if the product is currently on sale."""
        if not self.price:
            return False
        return (self.price.current_price is not None and 
                self.price.original_price is not None and 
                self.price.current_price < self.price.original_price)
