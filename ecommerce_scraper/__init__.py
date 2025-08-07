"""
Ecommerce Scraper - AI-powered web scraping for ecommerce sites using Stagehand and CrewAI.

This package provides a comprehensive solution for scraping product information
from various ecommerce platforms using AI-driven browser automation.
"""

__version__ = "0.1.0"
__author__ = "Ecommerce Scraper Team"

from .schemas.product_search_result import ProductSearchResult, ProductSearchItem
from .schemas.product_search_extraction import ProductSearchExtraction
from .workflows.product_search_flow import ProductSearchFlow

__all__ = [
    "ProductSearchResult",
    "ProductSearchItem",
    "ProductSearchExtraction",
    "ProductSearchFlow"
]
