"""Logging package for ecommerce scraping."""

from .ai_logger import get_ai_logger, close_ai_logger

__all__ = [
    'get_ai_logger',
    'close_ai_logger'
]