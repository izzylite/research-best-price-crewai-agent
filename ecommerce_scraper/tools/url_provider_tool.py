"""URL Provider Tool for CrewAI ecommerce scraper.

This tool provides the exact category URL to agents, eliminating any URL parsing ambiguity.
"""

import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class URLProviderInput(BaseModel):
    """Input schema for URL Provider tool."""
    request_type: str = Field("get_category_url", description="Type of URL request: 'get_category_url', 'get_current_url', or 'validate_url'")
    url_to_validate: Optional[str] = Field(None, description="URL to validate (only for validate_url request)")


class CategoryURLProviderTool(BaseTool):
    """Tool that provides the exact category URL to scraping agents.

    This eliminates URL parsing ambiguity by providing the URL directly as a tool result.
    """

    name: str = "category_url_provider"
    description: str = """
    Provides the exact category URL for scraping. Use this tool to get the correct URL
    instead of trying to parse it from task descriptions.

    Request types:
    - 'get_category_url': Get the current category URL for scraping
    - 'get_current_url': Get the currently active URL
    - 'validate_url': Validate if a URL is correct and complete

    This tool ensures you always get the complete, untruncated URL.
    """
    args_schema: type[BaseModel] = URLProviderInput

    def __init__(self, category_url: str, vendor: str, category_name: str, **kwargs):
        """Initialize the URL provider tool.
        
        Args:
            category_url: The exact category URL to provide
            vendor: Vendor name (e.g., 'asda')
            category_name: Category name for context
        """
        super().__init__(**kwargs)
        self._category_url = category_url
        self._vendor = vendor
        self._category_name = category_name
        self._logger = logging.getLogger(__name__)

    def _run(self, **kwargs) -> str:
        """Provide the category URL based on request type."""
        try:
            request_type = kwargs.get("request_type", "get_category_url")
            url_to_validate = kwargs.get("url_to_validate")

            if request_type == "get_category_url":
                return self._get_category_url()
            elif request_type == "get_current_url":
                return self._get_current_url()
            elif request_type == "validate_url":
                return self._validate_url(url_to_validate)
            else:
                return f"Error: Unknown request type '{request_type}'. Use 'get_category_url', 'get_current_url', or 'validate_url'."

        except Exception as e:
            self._logger.error(f"Error in URL provider tool: {str(e)}")
            return f"Error providing URL: {str(e)}"

    def _get_category_url(self) -> str:
        """Get the exact category URL for scraping."""
        url_info = {
            "url": self._category_url,
            "vendor": self._vendor,
            "category": self._category_name,
            "url_length": len(self._category_url),
            "is_complete": self._category_url.startswith(('http://', 'https://'))
        }

        result = f"""CATEGORY URL INFORMATION:
URL: {self._category_url}
Vendor: {self._vendor}
Category: {self._category_name}
URL Length: {len(self._category_url)} characters
Protocol: {'✅ Valid' if self._category_url.startswith(('http://', 'https://')) else '❌ Missing'}

INSTRUCTIONS FOR USE:
1. Use this EXACT URL for navigation: {self._category_url}
2. Do NOT modify, truncate, or change this URL in any way
3. Navigate directly to this URL using the Web Automation Tool
4. This URL is guaranteed to be complete and correct

EXACT URL TO USE: {self._category_url}"""

        self._logger.info(f"Provided category URL: {self._category_url[:100]}{'...' if len(self._category_url) > 100 else ''}")
        return result

    def _get_current_url(self) -> str:
        """Get the currently configured URL."""
        return f"Current category URL: {self._category_url}"

    def _validate_url(self, url: Optional[str]) -> str:
        """Validate if a URL matches the expected category URL."""
        if not url:
            return "Error: No URL provided for validation"

        is_match = url == self._category_url
        is_valid_protocol = url.startswith(('http://', 'https://'))
        
        result = f"""URL VALIDATION RESULTS:
Provided URL: {url}
Expected URL: {self._category_url}
URLs Match: {'✅ Yes' if is_match else '❌ No'}
Valid Protocol: {'✅ Yes' if is_valid_protocol else '❌ No'}
URL Length: {len(url)} characters (Expected: {len(self._category_url)})

{'✅ URL is correct and ready to use!' if is_match else '❌ URL does not match expected category URL'}"""

        return result

    def get_url(self) -> str:
        """Direct method to get the URL (for programmatic access)."""
        return self._category_url

    def get_url_info(self) -> Dict[str, Any]:
        """Get detailed URL information."""
        return {
            "url": self._category_url,
            "vendor": self._vendor,
            "category": self._category_name,
            "url_length": len(self._category_url),
            "is_complete": self._category_url.startswith(('http://', 'https://'))
        }


class URLProviderToolFactory:
    """Factory for creating URL provider tools with different configurations."""

    @staticmethod
    def create_for_category(category_url: str, vendor: str, category_name: str) -> CategoryURLProviderTool:
        """Create a URL provider tool for a specific category.
        
        Args:
            category_url: The exact category URL
            vendor: Vendor name
            category_name: Category name
            
        Returns:
            Configured CategoryURLProviderTool instance
        """
        return CategoryURLProviderTool(
            category_url=category_url,
            vendor=vendor,
            category_name=category_name
        )

    
