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
from typing import Dict, Any, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    exclude_urls: List[str] = Field(default_factory=list, description="Exact product URLs that must be excluded from results")
    exclude_domains: List[str] = Field(default_factory=list, description="Retailer domains that must be excluded from results (e.g., 'example.com')")
    backfill_attempt: int = Field(1, description="Backfill attempt counter from flow")
    
    


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
        # Priority vendors (names and domains) loaded from prioritized-vendors.json at repo root
        self._priority_vendors: List[Dict[str, str]] = []
        self._priority_domains: Set[str] = set()
        self._priority_vendor_names: Set[str] = set()
        # Max parallel calls for priority vendor checks (tune via env)
        try:
            self._priority_max_concurrency: int = max(
                1, int(os.getenv("PERPLEXITY_PRIORITY_MAX_CONCURRENCY", "4"))
            )
        except Exception:
            self._priority_max_concurrency = 4
        try:
            self._load_priority_vendors()
        except Exception:
            # Soft-fail: continue without priority vendors if file missing/invalid
            self._priority_vendors = []
            self._priority_domains = set()
            self._priority_vendor_names = set()

    def _run(
        self,
        product_query: str,
        max_retailers: int = 5,
        search_instructions: Optional[str] = None,
        exclude_urls: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        backfill_attempt: int = 1,
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

            # 1) Iterative research across priority vendors first
            # Skip this step when feedback-enhanced retries are in effect
            # (indicated by non-empty search_instructions), or when this is a backfill pass (>1),
            # to avoid re-checking the same vendors.
            collected: List[Dict[str, Any]] = []
            seen_urls: set[str] = set(exclude_urls or [])
            excluded_domains: set[str] = set(exclude_domains or [])
            if self._priority_vendors and not search_instructions and int(backfill_attempt or 1) <= 1:
                # Run priority vendor checks concurrently for speed
                max_workers = min(self._priority_max_concurrency, len(self._priority_vendors))
                if max_workers <= 0:
                    max_workers = 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_vendor = {}
                    for v in self._priority_vendors:
                        vendor_name = v.get("name") or v.get("vendor") or ""
                        domain = v.get("domain") or ""
                        future = executor.submit(
                            self._research_single_vendor, product_query, vendor_name, domain
                        )
                        future_to_vendor[future] = (vendor_name, domain)

                    for future in as_completed(future_to_vendor):
                        if len(collected) >= max_retailers:
                            break
                        result = None
                        try:
                            result = future.result()
                        except Exception:
                            result = None
                        if not result:
                            continue
                        url = (result or {}).get("url") or ""
                        if not url or url in seen_urls:
                            continue
                        # Exclude unwanted domains if configured
                        try:
                            from urllib.parse import urlparse
                            netloc = urlparse(url).netloc
                        except Exception:
                            netloc = ""
                        if netloc in excluded_domains:
                            continue
                        # Mark as prioritized; if no price present, downgrade to non-priority
                        result["priority"] = True
                        price_value = (result or {}).get("price")
                        if not isinstance(price_value, str) or not price_value.strip():
                            result["priority"] = False
                        collected.append(result)
                        seen_urls.add(url)

            # If we already have enough, return now
            if len(collected) >= max_retailers:
                return json.dumps(
                    {
                        "product_query": product_query,
                        "ai_search_response": "PRIORITY_VENDOR_CHECK",
                        "retailers": collected[:max_retailers],
                        "total_found": len(collected[:max_retailers]),
                    },
                    indent=2,
                )

            # 2) Fallback to current broader research to fill remaining slots
            remaining_needed = max(0, max_retailers - len(collected)) or max_retailers
            prompt = self._build_retailer_research_prompt(
                product_query, remaining_needed, search_instructions, list(seen_urls), list(excluded_domains)
            )

            retailer_data = self._call_perplexity_api(prompt)

            structured_result = self._structure_retailer_response(
                retailer_data, product_query, max_retailers
            )

            # Fallback: if no retailers found, retry once without strict schema
            try:
                if not structured_result.get("retailers"):
                    fallback_raw = self._call_perplexity_api(prompt, enforce_schema=False)
                    structured_result = self._structure_retailer_response(
                        fallback_raw,
                        product_query,
                        max_retailers
                    )
            except Exception:
                pass

            # Enforce exclusions defensively even if the model ignores the prompt
            try:
                seen_domains = set(exclude_domains or [])
                retailers_list = structured_result.get("retailers", []) or []
                if seen_urls or seen_domains:
                    from urllib.parse import urlparse
                    filtered = []
                    for r in retailers_list:
                        url = (r or {}).get("url") or ""
                        if not isinstance(url, str) or not url:
                            filtered.append(r)
                            continue
                        if url in seen_urls:
                            continue
                        try:
                            netloc = urlparse(url).netloc
                        except Exception:
                            netloc = ""
                        if netloc and netloc in seen_domains:
                            continue
                        filtered.append(r)
                    structured_result["retailers"] = filtered
                    structured_result["total_found"] = len(filtered)
            except Exception:
                # Best-effort filtering only
                pass

            # Ensure fallback results are explicitly marked as non-priority
            fallback_list = structured_result.get("retailers", []) or []
            for r in fallback_list:
                if isinstance(r, dict) and "priority" not in r:
                    r["priority"] = False

            # Merge priority results (collected) with fallback results, avoiding duplicates
            merged = collected + [r for r in fallback_list if (r or {}).get("url") not in seen_urls]
            if len(merged) > max_retailers:
                merged = merged[:max_retailers]

            return json.dumps(
                {
                    "product_query": product_query,
                    "ai_search_response": structured_result.get("ai_search_response"),
                    "retailers": merged,
                    "total_found": len(merged),
                },
                indent=2,
            )

        except Exception as e:
            self._logger.error(f"[PERPLEXITY] Retailer research failed: {e}")
            return self._fallback_retailer_result(product_query, max_retailers)

    def _build_retailer_research_prompt(
        self,
        product_query: str,
        max_retailers: int,
        search_instructions: Optional[str] = None,
        exclude_urls: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> str:
        """Build context-aware prompt for retailer research."""
        exclude_urls = exclude_urls or []
        exclude_domains = exclude_domains or []
        exclusions_block = ""
        if exclude_urls or exclude_domains:
            urls_text = "\n".join(f"- {u}" for u in exclude_urls) if exclude_urls else "- (none)"
            domains_text = "\n".join(f"- {d}" for d in exclude_domains) if exclude_domains else "- (none)"
            exclusions_block = f"""

EXCLUSIONS (do NOT include these again):
URLs already seen:
{urls_text}
Domains to exclude:
{domains_text}
"""

        default_prompt = f"""You are tasked with finding UK retailers that currently sell "{product_query}" online.
         Your goal is to provide accurate and up-to-date information about where UK customers can purchase this product directly.
         
         {exclusions_block}

        CORE RESEARCH GUIDELINES:
        1. Search for reputable UK-based online retailers that sell the specified product or keywords related to the product.
        2. Focus on sources where customers can make purchases—not comparison sites or marketplaces.
        3. Verify that the retailer serves UK customers.
        4. Prioritize in-stock items and current listings.
        5. Provide direct product page URLs—not category pages, search results, or 404s.

        HARD CONSTRAINTS:
        - Only include a retailer if you have a direct product URL (starting with http).
        - If none qualify, respond with an empty list: [].
        - Prefer prices in GBP with the £ symbol, when available.

        TARGET COUNT:
        - Aim to return up to {max_retailers} unique UK retailers that meet the criteria. If fewer than {max_retailers} are available, return as many valid results as you can find.

        RANKING & PRICE NORMALIZATION:
        - Return results sorted by price in ascending order (cheapest first).
        - If multiple retailers offer the same item, include only the lowest-priced listing.
        - Place items without price information at the end of the list.

        OUTPUT FORMAT:
        Return a JSON array of objects like this (ensure availability is either "In stock" or "Out of stock"):
        [
            {{
                "vendor": "Retailer Name",
                "url": "https://example.co.uk/product-page",
                "price": "£xx.xx",
                "availability": "In stock",
                "notes": "Additional notes"
            }}
        ]
        
        """

        if search_instructions:
            # Use enhanced search instructions when provided (feedback-driven)
            prompt = f"""{search_instructions}{exclusions_block}

{default_prompt}"""
        else:
            # Default prompt when no enhanced instructions are provided
            prompt = default_prompt

        return prompt
 

    # --------------------- Priority Vendors Helpers ---------------------
    def _load_priority_vendors(self) -> None:
        """Load priority vendors from `prioritized-vendors.json` at repo root.

        Expected JSON shape:
        [ { "name": "Vendor", "url": "https://domain.tld/..." }, ... ]
        """
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        json_path = os.path.join(repo_root, "prioritized-vendors.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            # Nothing to prioritize
            return
        except Exception as exc:  # noqa: BLE001
            # Malformed file: ignore
            logger.warning(f"Failed to load priority vendors from {json_path}: {exc}")
            return

        if not isinstance(data, list):
            return
        from urllib.parse import urlparse

        def normalize_domain(netloc: str) -> str:
            netloc = (netloc or "").strip().lower()
            return netloc[4:] if netloc.startswith("www.") else netloc

        vendors: List[Dict[str, str]] = []
        domains: set[str] = set()
        names: set[str] = set()
        for item in data:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or item.get("vendor") or "").strip()
            url = (item.get("url") or "").strip()
            domain = ""
            try:
                if url:
                    domain = normalize_domain(urlparse(url).netloc)
            except Exception:
                domain = ""
            entry = {"name": name}
            if domain:
                entry["domain"] = domain
                domains.add(domain)
            if name:
                names.add(name.lower())
            vendors.append(entry)
        self._priority_vendors = vendors
        self._priority_domains = domains
        self._priority_vendor_names = names

    def _research_single_vendor(self, product_query: str, vendor_name: str, vendor_domain: Optional[str]) -> Optional[Dict[str, Any]]:
        """Ask Perplexity to find a single product listing for one vendor.

        Returns a single object with keys {vendor, url, price?, notes?} or None when not found.
        """
        if not vendor_name and not vendor_domain:
            return None

        domain_hint = f" ({vendor_domain})" if vendor_domain else ""
        instruction = f"You are checking whether '{vendor_name}{domain_hint}' sells '{product_query}' online in the UK."

        user_prompt = f"""
{instruction}

REQUIREMENTS:
- Only return a single JSON object if you find a direct product page URL on this vendor's own site.
- The JSON object must have: vendor, url, and may include price and notes.
- If the vendor does not sell it or no direct URL exists, return null (the literal JSON null).
- The URL must start with http and belong to this vendor domain{' (' + vendor_domain + ')' if vendor_domain else ''}.
- Prefer current, in-stock listings for UK customers.

SEARCH TIPS:
- You may use closely related keywords, alternate spellings, spacing/punctuation variants, and synonymous naming for the product when searching this vendor's site.
- Avoid different pack sizes or clearly different variants that do not reasonably match the request.

OUTPUT:
- If found: a single JSON object
- If not found: null
"""

        # Encourage the model to scope to a specific domain by including the domain in the instruction
        if vendor_domain:
            user_prompt += f"\nDOMAIN TO SEARCH FIRST: {vendor_domain}\n"

        raw = self._call_perplexity_api(user_prompt, enforce_schema=False)
        content = (raw or "").strip()
        # Normalize to single object or None
        try:
            if content.lower() == "null":
                return None
            # Some models wrap in code fences or text; try to salvage JSON object
            obj: Optional[Dict[str, Any]] = None
            if content.startswith("{"):
                obj = json.loads(content)
            else:
                # Attempt to find first JSON object in the text
                obj = self._salvage_first_json_object(content)
            if not isinstance(obj, dict):
                return None
            # Minimal validation
            url = obj.get("url")
            vendor = obj.get("vendor") or vendor_name
            if not isinstance(url, str) or not url.startswith("http"):
                return None
            obj["vendor"] = vendor
            obj["priority"] = False  # default; upgraded to True when coming from priority path
            return obj
        except Exception:
            return None

    # Utility to salvage first JSON object from a text blob
    def _salvage_first_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            snippet = text[start : end + 1]
            return json.loads(snippet)
        except Exception:
            return None

    def _call_perplexity_api(
        self,
        prompt: str,
        enforce_schema: bool = True,
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
                        "content": """You are an expert UK retail researcher specializing in finding legitimate UK-based online retailers and providing direct product-page URLs. Always maintain a professional, concise tone."""
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
            if enforce_schema:
                # Enforce JSON array of {vendor,url,price?,availability?}
                payload["response_format"] = {
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
                                    "availability": {"type": "string"},
                                    "priority": {"type": "boolean"},
                                    "notes": {"type": "string"},
                                    
                                },
                                # Make price optional to reduce empty [] responses
                                "required": ["vendor", "url"],
                                "additionalProperties": False
                            },
                            "minItems": 0
                        }
                    }
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
        # If we have priority domains, order results so priority vendors come first
        if parsed_data and self._priority_domains:
            from urllib.parse import urlparse

            def is_priority(item: Dict[str, Any]) -> bool:
                try:
                    netloc = urlparse((item or {}).get("url", "")).netloc.lower()
                    if netloc.startswith("www."):
                        netloc = netloc[4:]
                    return netloc in self._priority_domains
                except Exception:
                    return False

            parsed_data = sorted(parsed_data, key=lambda r: (not is_priority(r)))

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
