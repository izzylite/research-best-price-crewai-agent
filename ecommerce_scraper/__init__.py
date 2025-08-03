"""
Ecommerce Scraper - AI-powered web scraping for ecommerce sites using Stagehand and CrewAI.

This package provides a comprehensive solution for scraping product information
from various ecommerce platforms using AI-driven browser automation.
"""

__version__ = "0.1.0"
__author__ = "Ecommerce Scraper Team"

from .main import EcommerceScraper
from .schemas.product import Product, ProductVariant, ProductImage

__all__ = ["EcommerceScraper", "Product", "ProductVariant", "ProductImage"]
