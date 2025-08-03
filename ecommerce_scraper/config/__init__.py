"""Configuration module for ecommerce scraper."""

from .settings import Settings
from .sites import SiteConfig, get_site_config

__all__ = ["Settings", "SiteConfig", "get_site_config"]
