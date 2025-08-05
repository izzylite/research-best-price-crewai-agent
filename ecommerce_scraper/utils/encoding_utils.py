"""
Encoding utilities to handle Unicode issues in Windows console logging.
"""

import sys
import logging
import locale
from typing import Any, Optional


def get_console_encoding() -> str:
    """Get the console encoding, defaulting to utf-8."""
    try:
        return sys.stdout.encoding or 'utf-8'
    except AttributeError:
        return 'utf-8'


def is_unicode_safe(text: str) -> bool:
    """Check if text can be safely encoded for console output."""
    try:
        encoding = get_console_encoding()
        text.encode(encoding)
        return True
    except (UnicodeEncodeError, AttributeError):
        return False


def safe_log_message(message: str) -> str:
    """Convert a message to be safe for console logging by removing problematic Unicode characters."""
    if not isinstance(message, str):
        message = str(message)
    
    # Replace common emoji and Unicode characters that cause issues in Windows console
    replacements = {
        '🔗': '[LINK]',
        '📐': '[VIEWPORT]',
        '🧹': '[CLEANUP]',
        '📦': '[PACKAGE]',
        '✅': '[SUCCESS]',
        '❌': '[ERROR]',
        '⚠️': '[WARNING]',
        '🚀': '[ROCKET]',
        '🔧': '[TOOL]',
        '📊': '[CHART]',
        '🎉': '[CELEBRATION]',
        '💾': '[SAVE]',
        '📄': '[FILE]',
        '🌊': '[FLOW]',
        '🔄': '[REFRESH]',
        '📋': '[TASK]',
        '🤖': '[BOT]',
        '🧪': '[TEST]',
        '⠋': '[LOADING]',
        '⠙': '[LOADING]',
        '⠹': '[LOADING]',
        '⠸': '[LOADING]',
        '⠼': '[LOADING]',
        '⠴': '[LOADING]',
        '⠦': '[LOADING]',
        '⠧': '[LOADING]',
        '⠇': '[LOADING]',
        '⠏': '[LOADING]',
    }
    
    # Apply replacements
    for emoji, replacement in replacements.items():
        message = message.replace(emoji, replacement)
    
    # If still not safe, try to encode/decode to remove problematic characters
    if not is_unicode_safe(message):
        try:
            encoding = get_console_encoding()
            message = message.encode(encoding, errors='replace').decode(encoding)
        except (UnicodeError, AttributeError):
            # Last resort: remove all non-ASCII characters
            message = ''.join(char if ord(char) < 128 else '?' for char in message)
    
    return message


def safe_print(message: Any, **kwargs) -> None:
    """Print a message safely to console, handling Unicode issues."""
    safe_message = safe_log_message(str(message))
    print(safe_message, **kwargs)


def configure_safe_logging(logger: logging.Logger) -> None:
    """Configure a logger to use safe message formatting."""
    
    class SafeFormatter(logging.Formatter):
        """Custom formatter that makes log messages safe for console output."""
        
        def format(self, record):
            # Format the record normally first
            formatted = super().format(record)
            # Then make it safe for console output
            return safe_log_message(formatted)
    
    # Apply safe formatter to all handlers
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(SafeFormatter(handler.formatter._fmt if hasattr(handler.formatter, '_fmt') else '%(message)s'))


def setup_encoding_safety() -> None:
    """Setup encoding safety for the entire application."""
    # Configure the root logger to use safe formatting
    root_logger = logging.getLogger()
    configure_safe_logging(root_logger)
    
    # Set console encoding if possible
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        # Not available on all systems
        pass
