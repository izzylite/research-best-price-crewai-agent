"""Utility functions for the ecommerce scraper."""

from .encoding_utils import (
    safe_log_message,
    safe_print,
    configure_safe_logging,
    get_console_encoding,
    is_unicode_safe,
    setup_encoding_safety
)

__all__ = [
    'safe_log_message',
    'safe_print', 
    'configure_safe_logging',
    'get_console_encoding',
    'is_unicode_safe',
    'setup_encoding_safety'
]
