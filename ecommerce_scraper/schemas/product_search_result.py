"""Product Search Result Schema for product-specific search system."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class ProductSearchItem(BaseModel):
    """Individual product search result item."""
    
    product_name: str = Field(..., description="Product name as found on retailer site")
    price: str = Field(..., description="Product price in GBP format (e.g., '£99.99')")
    url: str = Field(..., description="Direct URL to product page")
    retailer: str = Field(..., description="Retailer name (e.g., 'Amazon')")
    availability: Optional[str] = Field(None, description="Stock status such as 'In stock' or 'Out of stock'")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the product was found")
    
    @field_validator('product_name')
    @classmethod
    def validate_product_name(cls, v: str) -> str:
        """Clean and validate product name."""
        if not v or not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: str) -> str:
        """Validate price format."""
        if not v or not v.strip():
            raise ValueError("Price cannot be empty")
        return v.strip()
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        
        v = v.strip()
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("URL must start with http:// or https://")
        
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
            "availability": self.availability,
            "timestamp": self.timestamp.isoformat()
        }


class ProductSearchResult(BaseModel):
    """Complete product search result with metadata."""
    
    search_query: str = Field(..., description="Original product search query")
    results: List[ProductSearchItem] = Field(default_factory=list, description="List of found products")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Search metadata and statistics")
    
    @field_validator('search_query')
    @classmethod
    def validate_search_query(cls, v: str) -> str:
        """Validate search query."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()
    
    @field_validator('results')
    @classmethod
    def validate_results(cls, v: List[ProductSearchItem]) -> List[ProductSearchItem]:
        """Validate results list."""
        # Results can be empty, but must be a list
        if not isinstance(v, list):
            raise ValueError("Results must be a list")
        return v
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of search results."""
        retailers = set(item.retailer for item in self.results)
        
        return {
            "search_query": self.search_query,
            "total_products_found": len(self.results),
            "unique_retailers": len(retailers),
            "retailers": list(retailers),
            "metadata": self.metadata
        }
    
    def filter_by_retailer(self, retailer: str) -> 'ProductSearchResult':
        """Filter results by retailer."""
        filtered_results = [item for item in self.results if item.retailer.lower() == retailer.lower()]
        
        return ProductSearchResult(
            search_query=self.search_query,
            results=filtered_results,
            metadata={
                **self.metadata,
                "filtered_by": f"retailer:{retailer}",
                "original_count": len(self.results)
            }
        )
    
    def get_best_price(self) -> Optional[ProductSearchItem]:
        """Get the product with the best (lowest) price."""
        if not self.results:
            return None
        
        # Simple price comparison - assumes prices are in format "£XX.XX"
        def extract_price_value(price_str: str) -> float:
            try:
                # Remove currency symbols and convert to float
                price_clean = price_str.replace('£', '').replace(',', '').strip()
                return float(price_clean)
            except (ValueError, AttributeError):
                return float('inf')  # Return high value for invalid prices
        
        return min(self.results, key=lambda item: extract_price_value(item.price))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "search_query": self.search_query,
            "results": [item.to_dict() for item in self.results],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductSearchResult':
        """Create ProductSearchResult from dictionary."""
        # Convert result items to ProductSearchItem objects
        results = []
        for item_data in data.get('results', []):
            if isinstance(item_data, dict):
                # Handle timestamp conversion
                if 'timestamp' in item_data and isinstance(item_data['timestamp'], str):
                    try:
                        item_data['timestamp'] = datetime.fromisoformat(item_data['timestamp'].replace('Z', '+00:00'))
                    except ValueError:
                        item_data['timestamp'] = datetime.now(timezone.utc)
                
                results.append(ProductSearchItem(**item_data))
            else:
                # Handle raw dictionary format
                results.append(ProductSearchItem(
                    product_name=item_data.get('product_name', 'Unknown'),
                    price=item_data.get('price', '£0.00'),
                    url=item_data.get('url', ''),
                    retailer=item_data.get('retailer', 'Unknown'),
                    availability=item_data.get('availability')
                ))
        
        return cls(
            search_query=data.get('search_query', ''),
            results=results,
            metadata=data.get('metadata', {})
        )
    
    def export_to_json(self, filename: str) -> None:
        """Export search results to JSON file."""
        import json
        from pathlib import Path
        
        # Ensure output directory exists
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create export data
        export_data = {
            "search_query": self.search_query,
            "results": [item.to_dict() for item in self.results],
            "metadata": {
                **self.metadata,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_products": len(self.results)
            }
        }
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
        "str_strip_whitespace": True,
        "validate_assignment": True
    }


# Utility functions
def create_search_result_from_raw(
    search_query: str,
    raw_results: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None
) -> ProductSearchResult:
    """Create ProductSearchResult from raw search data."""
    
    results = []
    for raw_item in raw_results:
        try:
            item = ProductSearchItem(
                product_name=raw_item.get('product_name', raw_item.get('name', 'Unknown')),
                price=raw_item.get('price', '£0.00'),
                url=raw_item.get('url', raw_item.get('product_url', '')),
                retailer=raw_item.get('retailer', raw_item.get('vendor', 'Unknown'))
            )
            results.append(item)
        except Exception:
            # Continue processing other items without warning logs
            continue
    
    return ProductSearchResult(
        search_query=search_query,
        results=results,
        metadata=metadata or {}
    )


def merge_search_results(results: List[ProductSearchResult]) -> ProductSearchResult:
    """Merge multiple ProductSearchResult objects into one."""
    if not results:
        return ProductSearchResult(search_query="", results=[], metadata={})
    
    # Use the first result's search query
    merged_query = results[0].search_query
    
    # Combine all results
    all_results = []
    for result in results:
        all_results.extend(result.results)
    
    # Combine metadata
    merged_metadata = {
        "merged_from": len(results),
        "total_results": len(all_results)
    }
    
    # Add metadata from individual results
    for i, result in enumerate(results):
        merged_metadata[f"source_{i}"] = result.metadata
    
    return ProductSearchResult(
        search_query=merged_query,
        results=all_results,
        metadata=merged_metadata
    )
