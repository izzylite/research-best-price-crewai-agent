"""Perplexity-powered tool to confirm if a specific retailer sells a specific product.

This tool mirrors the HTTP integration style of PerplexityRetailerResearchTool but
optimizes the prompt and response format for a single retailer + single product
confirmation. It returns a minimal JSON payload that indicates whether the product
is purchasable from the retailer and, when available, the product name, direct URL,
and price in GBP.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Any, Dict, Optional

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..ai_logging.error_logger import get_error_logger

logger = logging.getLogger(__name__)


class RetailerProductInput(BaseModel):
    """Input schema for confirming product availability at a retailer."""

    product_query: str = Field(..., description="Specific product to search for (e.g., 'Heinz Baked Beans 415g')")
    retailer: str = Field(..., description="Retailer name (e.g., 'Amazon')")
    retailer_url: Optional[str] = Field(
        default=None,
        description="Optional candidate direct product URL to prefer if valid (e.g., a page discovered upstream)",
    )
    retailer_domain: Optional[str] = Field(
        default=None,
        description="Optional official retailer domain to constrain results (e.g., 'tesco.com')",
    )
    keywords: bool = Field(True, description="Allow keywords related to the product to be used in the search")
    search_instructions: Optional[str] = Field(
        default=None,
        description="Optional feedback-driven instructions to disambiguate variants and improve confirmation",
    )


class PerplexityRetailerProductTool(BaseTool):
    """Perplexity-powered tool for confirming whether a retailer sells a specific product."""

    name: str = "perplexity_retailer_product_tool"
    description: str = (
        "Confirm if a specific retailer sells a given product. If purchasable, "
        "return the product name, direct product URL on the retailer domain, and price in GBP."
    )
    args_schema: type[BaseModel] = RetailerProductInput

    def __init__(self):
        super().__init__()
        self._logger = get_error_logger(self.__class__.__name__)
        self._api_key = os.getenv("PERPLEXITY_API_KEY") or os.getenv("SONAR_API_KEY")
        self._base_url = "https://api.perplexity.ai/chat/completions"
        self._model = os.getenv("PERPLEXITY_MODEL") or "llama-3.1-sonar-large-128k-online"

    def _run(
        self,
        product_query: str,
        retailer: str,
        retailer_url: Optional[str] = None,
        retailer_domain: Optional[str] = None,
        keywords: bool = True,
        search_instructions: Optional[str] = None,
    ) -> str:
        """Confirm product availability for a specific retailer and return minimal product details.

        Returns a JSON string of shape:
        {
          "retailer": "Tesco",
          "product_query": "Heinz Baked Beans 415g",
          "exists": true,
          "name": "Heinz Baked Beans In Tomato Sauce 415G",
          "url": "https://www.tesco.com/...",
          "price": "£1.20"
        }
        """
        try:
            if not self._api_key:
                raise Exception(
                    "Perplexity API is required for product confirmation. Set PERPLEXITY_API_KEY."
                )

            prompt = self._build_prompt(
                product_query=product_query,
                retailer=retailer,
                retailer_url=retailer_url,
                retailer_domain=retailer_domain,
                keywords=keywords,
                search_instructions=search_instructions,
            )

            response_text = self._call_perplexity_api(prompt)
            structured = self._structure_response(
                response_text, product_query=product_query, retailer=retailer
            )
            return json.dumps(structured, indent=2)
        except Exception as e:
            self._logger.error(f"[PERPLEXITY] Retailer product confirmation failed: {e}")
            # Return a deterministic negative response so the caller can proceed
            return json.dumps(
                {
                    "retailer": retailer,
                    "product_query": product_query,
                    "exists": False,
                    "name": None,
                    "url": None,
                    "price": None,
                    "error": str(e),
                }
            )

    def _build_prompt(
        self,
        *,
        product_query: str,
        retailer: str,
        retailer_url: Optional[str],
        retailer_domain: Optional[str],
        keywords: bool,
        search_instructions: Optional[str],
    ) -> str:
         
        return (
            f"{"" if not search_instructions else str(search_instructions)}"

            f"Verifying if '{retailer}' sells {product_query} {"" if not keywords else "keywords related to the product"} at {retailer_url}"
            f" and if a customer can buy it online right now.\n\n"
            f"REQUIREMENTS:\n"
            f"- If the product is not available at {retailer_url}, Check if the {retailer} sells the product.\n"
            f"- Confirm if the product is purchasable from {retailer} online (in stock or orderable).\n" 
            f"- Provide a direct product page URL (not a search or category page).\n"
            
            f"RESPONSE:\n"
            f"Return ONLY a single JSON object with keys: exists (boolean), name (string), url (string), price (string).\n"
            f"If you cannot confirm purchase availability on {retailer}, set exists=false and set name, url, price to null."
        )

    def _call_perplexity_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise UK retail product verifier. Answer ONLY with a JSON object "
                        "that states whether a specific retailer sells a specific product and, when available, "
                        "includes the product name, direct product URL, and GBP price."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 800,
            "temperature": 0.0,
            "top_p": 0.9,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "exists": {"type": "boolean"},
                            "name": {"type": ["string", "null"]},
                            "url": {"type": ["string", "null"]},
                            "price": {"type": ["string", "null"]},
                        },
                        "required": ["exists", "name", "url", "price"],
                        "additionalProperties": False,
                    }
                },
            },
        }

        try:
            result = self._post_with_retries(self._base_url, headers=headers, json=payload, timeout=30)
        except requests.HTTPError as http_err:
            # Retry once without response_format if model refuses schema
            status_code = getattr(http_err.response, "status_code", None)
            if status_code == 400 and "response_format" in payload:
                payload2 = dict(payload)
                payload2.pop("response_format", None)
                result = self._post_with_retries(self._base_url, headers=headers, json=payload2, timeout=30)
            else:
                raise

        content = result["choices"][0]["message"]["content"].strip()
        return content

    def _post_with_retries(
        self,
        url: str,
        *,
        headers: Dict[str, str],
        json: Dict[str, Any],
        timeout: int,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= max_retries:
            try:
                resp = requests.post(url, headers=headers, json=json, timeout=timeout)
                if resp.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"HTTP {resp.status_code}: {resp.text}")
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt == max_retries:
                    break
                sleep_s = (2 ** attempt) + random.uniform(0, 0.25)
                time.sleep(sleep_s)
                attempt += 1
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected retry loop termination")

    def _structure_response(
        self, raw: str, *, product_query: str, retailer: str
    ) -> Dict[str, Any]:
        """Normalize model output into a deterministic dict."""
        content = (raw or "").strip()
        exists = False
        name: Optional[str] = None
        url: Optional[str] = None
        price: Optional[str] = None

        if content:
            try:
                if content.startswith("{"):
                    data = json.loads(content)
                else:
                    # salvage largest object
                    start = content.find("{")
                    end = content.rfind("}")
                    data = json.loads(content[start : end + 1]) if start != -1 and end != -1 else {}
                exists = bool(data.get("exists", False))
                name = data.get("name") if isinstance(data.get("name"), (str, type(None))) else None
                url = data.get("url") if isinstance(data.get("url"), (str, type(None))) else None
                price = data.get("price") if isinstance(data.get("price"), (str, type(None))) else None
            except Exception:
                # keep defaults
                pass

        return {
            "retailer": retailer,
            "product_query": product_query,
            "exists": exists,
            "name": name,
            "url": url,
            "price": price,
        }

