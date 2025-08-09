"""Logging package for ecommerce scraping.

Exports error-only logger utilities.
"""

from .error_logger import get_error_logger

__all__ = [
    'get_error_logger',
]