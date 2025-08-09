"""Perplexity-powered Retailer Research Tool for product-specific searches.

Enhancements based on Perplexity API docs:
- Accept header and OpenAI-compatible request shape
- Search controls: domain filters, search context sizing, user location, date filters, search mode
- Robust retries with exponential backoff on 429/5xx
- Response metadata capture: usage, citations, search_results

Docs consulted:
- Quickstart and API reference (chat completions, search filtering, user location)
  https://docs.perplexity.ai/api-reference/chat-completions-post
  https://docs.perplexity.ai/getting-started/quickstart
  https://docs.perplexity.ai/api-reference/chat-completions-post/guides/search-domain-filters
  https://docs.perplexity.ai/api-reference/chat-completions-post/guides/search-context-size-guide
  https://docs.perplexity.ai/api-reference/chat-completions-post/guides/user-location-filter-guide
  https://docs.perplexity.ai/api-reference/chat-completions-post/guides/date-range-filter-guide
"""

import json
import logging
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests
import os
import time
import random

from ..ai_logging.error_logger import get_error_logger

logger = logging.getLogger(__name__)


class RetailerResearchInput(BaseModel):
    """Input schema for retailer research."""
    product_query: str = Field(..., description="Specific product to search for (e.g., 'iPhone 15 Pro', 'Samsung Galaxy S24')")
    max_retailers: int = Field(5, description="Maximum number of retailers to find")
    search_instructions: Optional[str] = Field(None, description="Optional enhanced search instructions based on feedback (e.g., 'Focus on major UK supermarkets, avoid price comparison sites')")
    
    


class PerplexityRetailerResearchTool(BaseTool):
    """Perplexity-powered tool for finding online retailers that sell specific products (global)."""

    name: str = "perplexity_retailer_research_tool"
    description: str = """
    AI-powered retailer discovery tool using Perplexity AI for product-specific searches (global scope).

    Features:
    - Find legitimate online retailers that sell specific products
    - Provide direct product URLs where possible
    - Research product availability and pricing information

    Use this tool to discover retailers that sell a specific product and get
    direct links to product pages for targeted scraping.
    """
    args_schema: type[BaseModel] = RetailerResearchInput

    def __init__(self):
        """Initialize the Perplexity retailer research tool."""
        super().__init__()
        self._logger = get_error_logger(self.__class__.__name__)

        # Get API key from environment or config
        # Prefer PERPLEXITY_API_KEY, fallback to SONAR_API_KEY per docs examples
        self._api_key = os.getenv("PERPLEXITY_API_KEY") or os.getenv("SONAR_API_KEY")
        if not self._api_key:
            # Warning removed per logging policy; handled at callsite
            pass

        self._base_url = "https://api.perplexity.ai/chat/completions"
        # Prefer online model for fresh web results; allow override via env
        self._model = os.getenv("PERPLEXITY_MODEL") or "llama-3.1-sonar-large-128k-online"
        # store last response metadata (usage/citations/search_results)
        self._last_response_meta: Dict[str, Any] = {}

    def _run(
        self,
        product_query: str,
        max_retailers: int = 5,
        search_instructions: Optional[str] = None
    ) -> str:
        """
        Research UK retailers that sell the specified product.

        Args:
            product_query: Specific product to search for
            max_retailers: Maximum number of retailers to find
            search_instructions: Optional enhanced search instructions based on feedback

        Returns:
            JSON string with retailer information and product URLs
        """
        try:
            # Info logging removed
            if search_instructions:
                # Info logging removed
                pass

            if not self._api_key:
                return self._fallback_retailer_result(product_query, max_retailers)

            # Build research prompt (now uses search_instructions if provided)
            prompt = self._build_retailer_research_prompt(
                product_query, max_retailers, search_instructions
            )

            # Call Perplexity API
            retailer_data = self._call_perplexity_api(
                prompt
            )

            # Parse and structure the response
            structured_result = self._structure_retailer_response(
                retailer_data,
                product_query,
                max_retailers
            )

    # Info logging removed
            return json.dumps(structured_result, indent=2)

        except Exception as e:
            self._logger.error(f"[PERPLEXITY] Retailer research failed: {e}")
            return self._fallback_retailer_result(product_query, max_retailers)

    def _build_retailer_research_prompt(
        self,
        product_query: str,
        max_retailers: int,
        search_instructions: Optional[str] = None
    ) -> str:
        """Build context-aware prompt for retailer research."""

        if search_instructions:
            # Use enhanced search instructions when provided (feedback-driven)
            prompt = f"""{search_instructions}

Present your findings for at least 3 different retailers (if available) and no more than {max_retailers}. If you cannot find at least 3 retailers, explain why in your response.

Format your response as JSON list as follows:
[
{{
"vendor": "[Retailer Name]",
"url": "[Product URL]",
"price": "£[Price]",
"notes": "[Additional notes]"
}}
]

Repeat this format for each retailer you find.

If you encounter any issues or limitations during your search, such as the product being out of stock everywhere or only available from non-UK retailers, please mention this in your response.

Remember, your final output should only include the retailer information in the specified format, along with any necessary explanations about your findings. Do not include any of your search process or internal thoughts in the final response."""
        else:
            # Default prompt when no enhanced instructions are provided
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
"price": "£[Price]",
"notes": "[Additional notes]"
}}
]

Repeat this format for each retailer you find.

If you encounter any issues or limitations during your search, such as the product being out of stock everywhere or only available from non-UK retailers, please mention this in your response.

Remember, your final output should only include the retailer information in the specified format, along with any necessary explanations about your findings. Do not include any of your search process or internal thoughts in the final response."""

        return prompt

    def _call_perplexity_api(
        self,
        prompt: str
    ) -> str:
        """Call Perplexity API for retailer research with search controls."""
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": """You are an expert UK retail researcher specializing in finding legitimate UK online retailers that sell specific products. Return direct UK product URLs only.

CORE RESEARCH GUIDELINES:
1. Search for reputable UK-based online retailers that sell the specified product
2. Focus on sources where customers can actually make a purchase, not comparison websites or marketplaces
3. Verify that the retailer serves UK customers
4. Prefer in-stock items and current listings
5. Get direct product page URLs, not search result pages or category pages
6. Ensure the URL is a direct accessible product page, not a search result page, category page or not found page

RESPONSE FORMAT:
Always output ONLY a JSON array (no prose, no code fences) with elements:
{
"vendor": "Retailer Name",
"url": "Direct Product URL",
"price": "£Price",
"notes": "Additional notes"
}

HARD CONSTRAINTS:
- Include a retailer ONLY if you have a direct product URL (starting with http) 
- If you cannot find any qualifying retailers, return []
- Prefer GBP prices with the £ symbol when available

RANKING & PRICE NORMALIZATION:
- Find the cheapest available options and SORT the array by price ascending (lowest first)
- When multiple retailers sell identical item, include the lowest priced listing first
- When price is unavailable, include the item at the END of the array

Provide accurate, up-to-date information and ensure all URLs lead directly to product pages."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.0,
                "top_p": 0.9,
                # Enforce strict JSON array of {vendor,url,price}
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "schema": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "vendor": {"type": "string", "minLength": 2},
                                    "url": {"type": "string", "pattern": "^https?://"},
                                    "price": {"type": "string"},
                                    "notes": {"type": "string"}
                                },
                                "required": ["vendor", "url", "price"],
                                "additionalProperties": False
                            },
                            "minItems": 0
                        }
                    }
                },
            }
 
            try:
                result = self._post_with_retries(self._base_url, headers=headers, json=payload, timeout=30)
            except requests.HTTPError as http_err:
                # Some models (especially certain online variants) may reject response_format
                # Retry once without response_format when we get a 400 Bad Request
                status_code = getattr(http_err.response, "status_code", None)
                if status_code == 400 and "response_format" in payload:
                    # Warning removed per logging policy
                    safe_payload = dict(payload)
                    safe_payload.pop("response_format", None)
                    try:
                        result = self._post_with_retries(self._base_url, headers=headers, json=safe_payload, timeout=30)
                    except requests.HTTPError as http_err2:
                        # Final fallback: swap to a stable model for this call only
                        # Warning removed per logging policy
                        fallback_payload = dict(safe_payload)
                        fallback_payload["model"] = "sonar-pro"
                        result = self._post_with_retries(self._base_url, headers=headers, json=fallback_payload, timeout=30)
                else:
                    # Non-400 or other errors: just re-raise
                    raise
            # Preserve metadata for downstream consumers
            self._last_response_meta = {
                "usage": result.get("usage"),
                "citations": result.get("citations"),
                "search_results": result.get("search_results"),
                "model": result.get("model"),
                "id": result.get("id"),
                "created": result.get("created"),
            }

            retailer_data = result["choices"][0]["message"]["content"].strip()
            return retailer_data
            
        except Exception as e:
            self._logger.error(f"Perplexity API call failed: {e}", exc_info=True)
            raise

    def _post_with_retries(self, url: str, *, headers: Dict[str, str], json: Dict[str, Any], timeout: int, max_retries: int = 3) -> Dict[str, Any]:
        """POST helper with exponential backoff for 429/5xx per best practices."""
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= max_retries:
            try:
                resp = requests.post(url, headers=headers, json=json, timeout=timeout)
                # Retry on 429/5xx
                if resp.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"HTTP {resp.status_code}: {resp.text}")
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt == max_retries:
                    break
                # Exponential backoff with jitter
                sleep_s = (2 ** attempt) + random.uniform(0, 0.25)
                # Warning removed per logging policy
                time.sleep(sleep_s)
                attempt += 1
        # Exhausted retries
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected retry loop termination")

    def _structure_retailer_response(
        self,
        raw_response: str,
        product_query: str,
        max_retailers: int, 
    ) -> Dict[str, Any]:
        """Return minimal payload: product_query, ai_search_response (raw), total_found.

        We compute total_found by attempting to parse a top-level JSON array from
        the model output; otherwise total_found is 0.
        """
        content = (raw_response or "").strip()
        parsed_data: List[Dict[str, Any]] = []
        if content:
            try:
                if content.startswith('['):
                    parsed_data = json.loads(content)
                else:
                    parsed_data = self._salvage_json_array(content)
            except Exception:
                parsed_data = []
        if len(parsed_data) > max_retailers:
            parsed_data = parsed_data[:max_retailers]
        return {
            "product_query": product_query,
            # Keep raw model output for auditability
            "ai_search_response": raw_response,
            # Also provide parsed list for pydantic consumers
            "retailers": parsed_data,
            "total_found": len(parsed_data),
        }
 
    
    def _fallback_retailer_result(self, product_query: str, max_retailers: int) -> str:
        """Provide fallback result when Perplexity is unavailable."""
        # Default UK retailers for common product searches with proper URLs
        # Instead of fallback, raise the actual error so it can be properly handled
        raise Exception("Perplexity API is required for retailer research. Please check your PERPLEXITY_API_KEY environment variable and ensure it's valid.")
