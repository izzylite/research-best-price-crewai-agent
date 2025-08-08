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

logger = logging.getLogger(__name__)


class RetailerResearchInput(BaseModel):
    """Input schema for retailer research."""
    product_query: str = Field(..., description="Specific product to search for (e.g., 'iPhone 15 Pro', 'Samsung Galaxy S24')")
    max_retailers: int = Field(5, description="Maximum number of retailers to find")
    search_instructions: Optional[str] = Field(None, description="Optional enhanced search instructions based on feedback (e.g., 'Focus on major UK supermarkets, avoid price comparison sites')")
    # Optional quality controls (do not break existing callers)
    min_retailers: Optional[int] = Field(None, description="Minimum desired retailers (for evaluation only)")
    require_gbp: Optional[bool] = Field(True, description="Require prices to be in GBP '£' format")
    require_product_page: Optional[bool] = Field(True, description="Require URLs to look like direct product pages (not search/category)")
    # Optional Perplexity search controls
    search_domain_filter: Optional[List[str]] = Field(
        default=None,
        description="List of domains to allowlist or denylist (prefix with '-' to denylist), e.g. ['currys.co.uk', '-pinterest.com']"
    )
    search_context_size: Optional[str] = Field(
        default="low",
        description="Search context size: 'low' | 'medium' | 'high'"
    )
    user_country: Optional[str] = Field(
        default="GB",
        description="Two-letter ISO country code to bias web results (e.g., 'GB' for United Kingdom)"
    )
    search_after_date_filter: Optional[str] = Field(
        default=None,
        description="Only include sources on/after this date (MM/DD/YYYY)"
    )
    search_before_date_filter: Optional[str] = Field(
        default=None,
        description="Only include sources on/before this date (MM/DD/YYYY)"
    )
    search_mode: Optional[str] = Field(
        default=None,
        description="Search mode override (e.g., 'web', 'academic', 'sec'). Leave None for default."
    )


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
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Get API key from environment or config
        # Prefer PERPLEXITY_API_KEY, fallback to SONAR_API_KEY per docs examples
        self._api_key = os.getenv("PERPLEXITY_API_KEY") or os.getenv("SONAR_API_KEY")
        if not self._api_key:
            self._logger.warning("PERPLEXITY_API_KEY not found in environment variables")

        self._base_url = "https://api.perplexity.ai/chat/completions"
        # store last response metadata (usage/citations/search_results)
        self._last_response_meta: Dict[str, Any] = {}

    def _run(
        self,
        product_query: str,
        max_retailers: int = 5,
        search_instructions: Optional[str] = None,
        min_retailers: Optional[int] = None,
        require_gbp: Optional[bool] = True,
        require_product_page: Optional[bool] = True,
        # Perplexity search controls (all optional):
        search_domain_filter: Optional[List[str]] = None,
        search_context_size: Optional[str] = "low",
        user_country: Optional[str] = "GB",
        search_after_date_filter: Optional[str] = None,
        search_before_date_filter: Optional[str] = None,
        search_mode: Optional[str] = None,
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
            self._logger.info(f"[PERPLEXITY] Researching retailers for: {product_query}")
            if search_instructions:
                self._logger.info(f"[PERPLEXITY] Using enhanced search instructions: {search_instructions[:100]}...")

            if not self._api_key:
                return self._fallback_retailer_result(product_query, max_retailers)

            # Build research prompt (now uses search_instructions if provided)
            prompt = self._build_retailer_research_prompt(
                product_query, max_retailers, search_instructions
            )

            # Call Perplexity API
            retailer_data = self._call_perplexity_api(
                prompt,
                search_domain_filter=search_domain_filter,
                search_context_size=search_context_size,
                user_country=user_country,
                search_after_date_filter=search_after_date_filter,
                search_before_date_filter=search_before_date_filter,
                search_mode=search_mode,
            )

            # Parse and structure the response
            structured_result = self._structure_retailer_response(
                retailer_data,
                product_query,
                max_retailers,
                min_retailers=min_retailers,
                require_gbp=require_gbp,
                require_product_page=require_product_page,
            )

            self._logger.info(f"[PERPLEXITY] Found {len(structured_result.get('retailers', []))} retailers")
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
"price": "£[Price]"
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
"price": "£[Price]"
}}
]

Repeat this format for each retailer you find.

If you encounter any issues or limitations during your search, such as the product being out of stock everywhere or only available from non-UK retailers, please mention this in your response.

Remember, your final output should only include the retailer information in the specified format, along with any necessary explanations about your findings. Do not include any of your search process or internal thoughts in the final response."""

        return prompt

    def _call_perplexity_api(
        self,
        prompt: str,
        *,
        search_domain_filter: Optional[List[str]] = None,
        search_context_size: Optional[str] = None,
        user_country: Optional[str] = None,
        search_after_date_filter: Optional[str] = None,
        search_before_date_filter: Optional[str] = None,
        search_mode: Optional[str] = None,
    ) -> str:
        """Call Perplexity API for retailer research with search controls."""
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            payload = {
                "model": "sonar-pro",
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

RESPONSE FORMAT:
Always output ONLY a JSON array (no prose, no code fences) with elements:
{
"vendor": "Retailer Name",
"url": "Direct Product URL",
"price": "£Price" 
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
            }

            # Apply search controls if provided
            if search_mode:
                payload["search_mode"] = search_mode
            if search_after_date_filter:
                payload["search_after_date_filter"] = search_after_date_filter
            if search_before_date_filter:
                payload["search_before_date_filter"] = search_before_date_filter
            # Default denylist to reduce noise if caller did not specify
            default_denylist = [
                "-pinterest.com",
                "-reddit.com",
                "-quora.com",
                "-pricerunner.com",
                "-idealo.co.uk",
                "-pricespy.co.uk",
                "-kelkoo.co.uk",
                "-hotukdeals.com",
            ]
            if search_domain_filter is not None and isinstance(search_domain_filter, list) and len(search_domain_filter) > 0:
                payload["search_domain_filter"] = search_domain_filter
            else:
                payload["search_domain_filter"] = default_denylist

            web_search_options: Dict[str, Any] = {}
            if search_context_size in {"low", "medium", "high"}:
                web_search_options["search_context_size"] = search_context_size
            if user_country and isinstance(user_country, str) and len(user_country) == 2:
                web_search_options["user_location"] = {"country": user_country.upper()}
            if web_search_options:
                payload["web_search_options"] = web_search_options
            
            result = self._post_with_retries(self._base_url, headers=headers, json=payload, timeout=30)
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
            self._logger.error(f"Perplexity API call failed: {e}")
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
                self._logger.warning(f"[PERPLEXITY] Request failed (attempt {attempt+1}/{max_retries+1}): {exc}. Retrying in {sleep_s:.2f}s...")
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
        *,
        min_retailers: Optional[int] = None,
        require_gbp: Optional[bool] = True,
        require_product_page: Optional[bool] = True,
    ) -> Dict[str, Any]:
        """Structure the Perplexity response into a standardized format."""
        try:
            # Try to parse as JSON first - expecting array format
            content = raw_response.strip()
            if content.startswith('['):
                parsed_data = json.loads(content)
            else:
                # Try to salvage a JSON array from mixed content
                parsed_data = self._salvage_json_array(content)

            # Ensure we don't exceed max_retailers
            if len(parsed_data) > max_retailers:
                parsed_data = parsed_data[:max_retailers]

            # Validate each retailer entry and convert to our internal format
            validated_retailers = []
            issues: List[str] = []

            for retailer in parsed_data:
                if not (isinstance(retailer, dict) and retailer.get('vendor') and retailer.get('url')):
                    issues.append("Malformed entry encountered; missing vendor/url")
                    continue

                vendor_name = retailer.get('vendor', 'Unknown')
                url = retailer.get('url', '')
                price = retailer.get('price', 'Price not available')

                # Optional quality constraints
                url_l = url.lower()
                if require_product_page:
                    if any(frag in url_l for frag in ["/search", "/s?", "?q=", "/category", "/categories"]):
                        issues.append(f"Not a product page: {url}")
                        continue
                if require_gbp and isinstance(price, str) and price and not price.strip().startswith('£'):
                    issues.append(f"Non-GBP price: {price} for {url}")
                    continue

                validated_retailers.append({
                    "name": vendor_name,
                    "website": self._extract_domain_from_url(url),
                    "product_url": url,
                    "price": price if price else 'Price not available',
                    "notes": f"Found via AI research for {product_query}"
                })

            result = {
                "product_query": product_query,
                "retailers": validated_retailers,
                "research_summary": f"Found {len(validated_retailers)} UK retailers selling {product_query}",
                "ai_search_response": raw_response,
                "total_found": len(validated_retailers),
                "issues": issues,
                "requirements": {
                    "require_gbp": require_gbp,
                    "require_product_page": require_product_page,
                    "requested_max": max_retailers,
                    "requested_min": min_retailers,
                },
                "api_available": True,
                # Per API docs: include useful metadata when available
                "api_usage": self._last_response_meta.get("usage"),
                "citations": self._last_response_meta.get("citations"),
                "search_results": self._last_response_meta.get("search_results"),
                "api_model": self._last_response_meta.get("model"),
                "api_response_id": self._last_response_meta.get("id"),
            }

            return result

        except json.JSONDecodeError:
            # Fallback to text extraction
            return self._extract_retailers_from_text(raw_response, product_query, max_retailers)

    def _salvage_json_array(self, text: str) -> List[Dict[str, Any]]:
        """Try to extract the first top-level JSON array from a text blob."""
        import re
        match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except Exception:
            return []

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
        
        # Common UK retailers to look for in the response (with domain mapping)
        uk_retailers = [
            ("ASDA", "asda.com"),
            ("Tesco", "tesco.com"),
            ("Waitrose", "waitrose.com"),
            ("Amazon UK", "amazon.co.uk"),
            ("eBay UK", "ebay.co.uk"),
            ("Argos", "argos.co.uk"),
            ("Currys", "currys.co.uk"),
            ("John Lewis", "johnlewis.com"),
            ("Next", "next.co.uk"),
            ("Marks & Spencer", "marksandspencer.com"),
            ("Sainsbury's", "sainsburys.co.uk"),
            ("B&Q", "diy.com"),
        ]
        
        lt = text_response.lower()
        for retailer_name, domain in uk_retailers:
            if retailer_name.lower() in lt and len(retailers) < max_retailers:
                retailers.append({
                    "name": retailer_name,
                    "website": domain,
                    "product_url": "",
                    "price": "Price not available",
                    "availability": "Unknown",
                    "notes": f"Found mention of {retailer_name} in research"
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
