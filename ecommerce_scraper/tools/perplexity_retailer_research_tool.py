"""Perplexity-powered Retailer Research Tool for product-specific searches."""

import json
import logging
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests
import os

logger = logging.getLogger(__name__)


class RetailerResearchInput(BaseModel):
    """Input schema for retailer research."""
    product_query: str = Field(..., description="Specific product to search for (e.g., 'iPhone 15 Pro', 'Samsung Galaxy S24')")
    max_retailers: int = Field(5, description="Maximum number of retailers to find")


class PerplexityRetailerResearchTool(BaseTool):
    """Perplexity-powered tool for finding UK retailers that sell specific products."""

    name: str = "perplexity_retailer_research_tool"
    description: str = """
    AI-powered retailer discovery tool using Perplexity AI for product-specific searches.

    Features:
    - Find legitimate UK retailers that sell specific products
    - Focus on major UK retailers like ASDA, Tesco, Amazon UK, eBay UK, etc.
    - Provide direct product URLs where possible
    - Research product availability and pricing information

    Use this tool to discover which UK retailers sell a specific product and get
    direct links to product pages for targeted scraping.
    """
    args_schema: type[BaseModel] = RetailerResearchInput

    def __init__(self):
        """Initialize the Perplexity retailer research tool."""
        super().__init__()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Get API key from environment or config
        self._api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self._api_key:
            self._logger.warning("PERPLEXITY_API_KEY not found in environment variables")

        self._base_url = "https://api.perplexity.ai/chat/completions"

    def _run(
        self,
        product_query: str,
        max_retailers: int = 5
    ) -> str:
        """
        Research UK retailers that sell the specified product.

        Args:
            product_query: Specific product to search for
            max_retailers: Maximum number of retailers to find

        Returns:
            JSON string with retailer information and product URLs
        """
        try:
            self._logger.info(f"[PERPLEXITY] Researching retailers for: {product_query}")

            if not self._api_key:
                return self._fallback_retailer_result(product_query, max_retailers)

            # Build research prompt
            prompt = self._build_retailer_research_prompt(
                product_query, max_retailers
            )

            # Call Perplexity API
            retailer_data = self._call_perplexity_api(prompt)

            # Parse and structure the response
            structured_result = self._structure_retailer_response(
                retailer_data, product_query, max_retailers
            )

            self._logger.info(f"[PERPLEXITY] Found {len(structured_result.get('retailers', []))} retailers")
            return json.dumps(structured_result, indent=2)

        except Exception as e:
            self._logger.error(f"[PERPLEXITY] Retailer research failed: {e}")
            return self._fallback_retailer_result(product_query, max_retailers)

    def _build_retailer_research_prompt(
        self,
        product_query: str,
        max_retailers: int
    ) -> str:
        """Build context-aware prompt for retailer research."""

        prompt = f"""You are tasked with finding UK retailers that currently sell "{product_query}" online. Your goal is to provide accurate and up-to-date information about where UK customers can purchase this product.

Follow these guidelines:
1. Search for reputable UK-based online retailers that sell the specified product.
2. Focus on sources where customers can actually make a purchase, not comparison websites or marketplaces.
3. Verify that the retailer ships to UK addresses.
4. Ensure the product is currently in stock and available for purchase.
5. Collect the following information for each retailer:
   - Retailer name
   - Product URL (direct link to the product page)
   - Current price in GBP (£)

Present your findings for at least 3 different retailers (if available) and no more than {max_retailers}. If you cannot find at least 3 retailers, explain why in your response.

Format your response as JSON list as follows:
[
{{
"vendor": "[Retailer Name]",
"url": "[Product URL]",
"price": "£[Price]"
}}
]

Repeat this format for each retailer you find.

If you encounter any issues or limitations during your search, such as the product being out of stock everywhere or only available from non-UK retailers, please mention this in your response.

Remember, your final output should only include the retailer information in the specified format, along with any necessary explanations about your findings. Do not include any of your search process or internal thoughts in the final response."""

        return prompt

    def _call_perplexity_api(self, prompt: str) -> str:
        """Call Perplexity API for retailer research."""
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert UK retail researcher specializing in finding legitimate online retailers that sell specific products. You have comprehensive knowledge of UK ecommerce sites and can find direct product URLs."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.2,
                "top_p": 0.9
            }
            
            response = requests.post(self._base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            retailer_data = result["choices"][0]["message"]["content"].strip()
            
            return retailer_data
            
        except Exception as e:
            self._logger.error(f"Perplexity API call failed: {e}")
            raise

    def _structure_retailer_response(
        self,
        raw_response: str,
        product_query: str,
        max_retailers: int
    ) -> Dict[str, Any]:
        """Structure the Perplexity response into a standardized format."""
        try:
            # Try to parse as JSON first - expecting array format
            if raw_response.strip().startswith('['):
                parsed_data = json.loads(raw_response)

                # Ensure we don't exceed max_retailers
                if len(parsed_data) > max_retailers:
                    parsed_data = parsed_data[:max_retailers]

                # Validate each retailer entry and convert to our internal format
                validated_retailers = []
                for retailer in parsed_data:
                    if isinstance(retailer, dict) and retailer.get('vendor') and retailer.get('url'):
                        validated_retailers.append({
                            "name": retailer.get('vendor', 'Unknown'),
                            "website": self._extract_domain_from_url(retailer.get('url', '')),
                            "product_url": retailer.get('url', ''),
                            "price": retailer.get('price', 'Price not available'),
                            "notes": f"Found via AI research for {product_query}"
                        })

                return {
                    "product_query": product_query,
                    "retailers": validated_retailers,
                    "research_summary": f"Found {len(validated_retailers)} UK retailers selling {product_query}",
                    "ai_search_response": raw_response,
                    "total_found": len(validated_retailers),
                    "api_available": True
                }

            else:
                # Handle non-JSON response by extracting information
                return self._extract_retailers_from_text(raw_response, product_query, max_retailers)

        except json.JSONDecodeError:
            # Fallback to text extraction
            return self._extract_retailers_from_text(raw_response, product_query, max_retailers)

    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL for website field."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc if parsed.netloc else url
        except Exception:
            return url

    def _extract_retailers_from_text(
        self,
        text_response: str,
        product_query: str,
        max_retailers: int
    ) -> Dict[str, Any]:
        """Extract retailer information from text response."""
        # Simple text parsing fallback
        retailers = []
        
        # Common UK retailers to look for in the response
        uk_retailers = [
            "ASDA", "Tesco", "Waitrose", "Amazon UK", "eBay UK", "Argos",
            "Currys", "John Lewis", "Next", "Marks & Spencer", "Sainsbury's"
        ]
        
        for retailer in uk_retailers:
            if retailer.lower() in text_response.lower() and len(retailers) < max_retailers:
                retailers.append({
                    "name": retailer,
                    "website": f"{retailer.lower().replace(' ', '').replace('uk', '')}.co.uk",
                    "product_url": "",
                    "price": "Price not available",
                    "availability": "Unknown",
                    "notes": f"Found mention of {retailer} in research"
                })
        
        return {
            "product_query": product_query,
            "retailers": retailers,
            "research_summary": "Extracted retailer information from text response",
            "total_found": len(retailers),
            "api_available": True
        }

    def _fallback_retailer_result(self, product_query: str, max_retailers: int) -> str:
        """Provide fallback result when Perplexity is unavailable."""
        # Default UK retailers for common product searches with proper URLs
        # Instead of fallback, raise the actual error so it can be properly handled
        raise Exception("Perplexity API is required for retailer research. Please check your PERPLEXITY_API_KEY environment variable and ensure it's valid.")
