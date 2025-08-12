"""Vendor-scoped Perplexity Research Tool

Search for product(s) within a single vendor's site using related keywords.
Intended primarily for feedback retries where a vendor and keywords are known.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os

from .perplexity_retailer_research_tool import PerplexityRetailerResearchTool


logger = logging.getLogger(__name__)


class VendorScopedInput(BaseModel):
    product_query: str = Field(..., description="Product to find within the vendor site")
    vendor_name: str = Field(..., description="Vendor/retailer name")
    vendor_url: Optional[str] = Field(None, description="Vendor website or base URL")
    keywords: Optional[Union[str, List[str]]] = Field(None, description="Related keywords to match variants within the vendor site")
    amount: int = Field(5, description="Number of results to return (cap with max_retailers externally if needed)")
    exclude_urls: List[str] = Field(default_factory=list, description="Exact product URLs to exclude")


class PerplexityVendorScopedResearchTool(BaseTool):
    name: str = "perplexity_vendor_scoped_research_tool"
    description: str = "Search a specific vendor site for matching product pages using related keywords. Returns direct product URLs with optional prices."
    args_schema: type[BaseModel] = VendorScopedInput

    def __init__(self):
        super().__init__()
        # Reuse API config from main research tool
        self._delegate = PerplexityRetailerResearchTool()

    def _run(
        self,
        product_query: str,
        vendor_name: str,
        vendor_url: Optional[str] = None,
        keywords: Optional[Union[str, List[str]]] = None,
        amount: int = 5,
        exclude_urls: Optional[List[str]] = None,
    ) -> str:
        try:
            # Build the vendor-scoped prompt leveraging the helper in the delegate
            # Construct vendor-scoped prompt locally (helper moved here)
            kw_list: List[str] = []
            if isinstance(keywords, str) and keywords.strip():
                kw_list = [keywords.strip()]
            elif isinstance(keywords, list):
                kw_list = [str(k).strip() for k in keywords if str(k).strip()]
            kw_text = ", ".join(kw_list) if kw_list else "(none)"

            exclusions = "\n".join(f"- {u}" for u in (exclude_urls or [])) if exclude_urls else "- (none)"

            prompt = f"""
You are tasked with finding up to {amount} direct product-page URLs on the site
for vendor "{vendor_name}".

SITE CONSTRAINTS:
- Only search within this vendor site: {vendor_url or '(unknown)'}
- If the vendor URL is not available, infer the official UK site for the vendor.

WHAT TO FIND:
- Products that match the user's query: "{product_query}"
- You may also use closely related keywords: {kw_text}
- Accept minor naming/spacing/punctuation variants
- Avoid clearly different sizes/packs that do not reasonably match

HARD CONSTRAINTS:
- Provide only direct product-page URLs (no search or category pages)
- URLs must be HTTP/HTTPS and belong to the vendor domain
- Do not include any of these already-seen URLs:\n{exclusions}

OUTPUT FORMAT:
Return a JSON array of objects like:
[
  {{ "vendor": "{vendor_name}", "url": "https://...", "price": "£xx.xx", "notes": "optional" }}
]

Limits: max {amount} items; prefer items with price; place items without price last.
"""

            raw = self._delegate._call_perplexity_api(prompt, enforce_schema=True)
            # Structure via the same parser to keep outputs consistent
            structured = self._delegate._structure_retailer_response(
                raw_response=raw,
                product_query=product_query,
                max_retailers=amount,
            )
            # Mark all as non-priority and enforce vendor domain if provided
            from urllib.parse import urlparse
            vendor_domain = ""
            try:
                if vendor_url:
                    vendor_domain = urlparse(vendor_url).netloc
            except Exception:
                vendor_domain = ""
            results = []
            for r in structured.get("retailers", []) or []:
                if not isinstance(r, dict):
                    continue
                r["priority"] = False
                if vendor_domain:
                    try:
                        netloc = urlparse((r or {}).get("url", "")).netloc
                        if netloc and netloc != vendor_domain:
                            continue
                    except Exception:
                        continue
                results.append(r)
            structured["retailers"] = results[:amount]
            structured["total_found"] = len(structured["retailers"])
            return json.dumps(structured, indent=2)
        except Exception as exc:
            logger.error(f"Vendor-scoped tool failed: {exc}")
            # Return empty list to signal no results rather than raising
            return json.dumps({
                "product_query": product_query,
                "retailers": [],
                "total_found": 0,
                "ai_search_response": "VENDOR_SCOPED_ERROR"
            }, indent=2)


