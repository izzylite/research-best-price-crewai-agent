"""Perplexity-powered tool to validate that a URL is a direct, purchasable product page
on a legitimate retailer (not a comparison/affiliate site).

Returns a minimal structured result with booleans for product page and purchasability,
and notes for audit.
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, Optional

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..ai_logging.error_logger import get_error_logger


class UrlLegitimacyInput(BaseModel):
    url: str = Field(..., description="Candidate product URL to validate")
    retailer: Optional[str] = Field(None, description="Optional retailer name to check alignment")
    product_name: Optional[str] = Field(None, description="Optional product name for sanity matching")
    keywords: bool = Field(True, description="Allow keywords related to the product to be used in the search")
    retailer_url: Optional[str] = Field(
        default=None,
        description="Optional retailer page URL (e.g., retailer home/category) to check domain alignment against",
    )


class PerplexityUrlLegitimacyTool(BaseTool):
    name: str = "perplexity_url_legitimacy_tool"
    description: str = (
        "Validate that a given URL is a direct, purchasable product page on a legitimate retailer "
        "(not a comparison/affiliate site)."
    )
    args_schema: type[BaseModel] = UrlLegitimacyInput

    def __init__(self) -> None:
        super().__init__()
        self._logger = get_error_logger(self.__class__.__name__)
        self._api_key = os.getenv("PERPLEXITY_API_KEY") or os.getenv("SONAR_API_KEY")
        self._base_url = "https://api.perplexity.ai/chat/completions"
        self._model = os.getenv("PERPLEXITY_MODEL") or "llama-3.1-sonar-large-128k-online"

    def _run(
        self,
        url: str,
        retailer: Optional[str] = None,
        product_name: Optional[str] = None,
        keywords: bool = True,
        retailer_url: Optional[str] = None,
    ) -> str:
        try:
            if not self._api_key:
                raise Exception("Perplexity API is required for URL legitimacy validation. Set PERPLEXITY_API_KEY.")

            prompt = self._build_prompt(
                url=url,
                retailer=retailer,
                product_name=product_name,
                keywords=keywords,
                retailer_url=retailer_url,
            )
            content = self._call_perplexity_api(prompt)
            result = self._structure_response(content, url=url, retailer=retailer, product_name=product_name)
            return json.dumps(result, indent=2)
        except Exception as e:
            self._logger.error(f"[PERPLEXITY] URL legitimacy validation failed: {e}")
            return json.dumps(
                {
                    "url": url,
                    "retailer": retailer,
                    "product_name": product_name,
                    "is_product_page": False,
                    "is_purchasable": False,
                    "is_comparison_site": False,
                    "notes": str(e),
                }
            )

    def _build_prompt(self, *, url: str, retailer: Optional[str], product_name: Optional[str], keywords: bool, retailer_url: Optional[str]) -> str:
        retailer_clause = f" for retailer '{retailer}'" if retailer else ""
        if product_name:
            kw_suffix = " or keywords related to the product" if keywords else ""
            product_clause = f" for product '{product_name}{kw_suffix}'"
        else:
            product_clause = ""
        price_clause = (
            "When feasible, confirm price appears in GBP (with £) and keywords related to the product are used in the search."
            if keywords
            else "Keywords related to the product are not used in the search."
        )
        ref_clause = (
            f"Use this reference retailer URL for domain alignment/context if helpful: {retailer_url}." if retailer_url else ""
        )
        return (
            f"Validate that this URL{retailer_clause}{product_clause} is a direct product page and purchasable: {url}.\n"
            f"- It must not be a price comparison site, affiliate aggregator, or search/category page.\n"
            f"- Prefer official retailer domains and canonical product pages.\n"
            f"- {price_clause}\n"
            f"- {ref_clause}\n\n"
            f"Return ONLY a JSON object with keys: is_product_page (bool), is_purchasable (bool), is_comparison_site (bool), notes (string)."
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
                {"role": "system", "content": "You are a precise URL legitimacy validator for UK ecommerce."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 400,
            "temperature": 0.0,
            "top_p": 0.9,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "is_product_page": {"type": "boolean"},
                            "is_purchasable": {"type": "boolean"},
                            "is_comparison_site": {"type": "boolean"},
                            "notes": {"type": "string"},
                        },
                        "required": ["is_product_page", "is_purchasable", "is_comparison_site", "notes"],
                        "additionalProperties": False,
                    }
                },
            },
        }

        try:
            return self._post_with_retries(self._base_url, headers=headers, json=payload, timeout=30)[
                "choices"
            ][0]["message"]["content"].strip()
        except requests.HTTPError as http_err:
            status_code = getattr(http_err.response, "status_code", None)
            if status_code == 400 and "response_format" in payload:
                # Retry without response_format
                payload2 = dict(payload)
                payload2.pop("response_format", None)
                return self._post_with_retries(self._base_url, headers=headers, json=payload2, timeout=30)[
                    "choices"
                ][0]["message"]["content"].strip()
            raise

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

    def _structure_response(self, raw: str, *, url: str, retailer: Optional[str], product_name: Optional[str]) -> Dict[str, Any]:
        content = (raw or "").strip()
        data: Dict[str, Any] = {}
        try:
            if content.startswith("{"):
                data = json.loads(content)
            else:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1 and end > start:
                    data = json.loads(content[start : end + 1])
        except Exception:
            data = {}
        return {
            "url": url,
            "retailer": retailer,
            "product_name": product_name,
            "is_product_page": bool(data.get("is_product_page", False)),
            "is_purchasable": bool(data.get("is_purchasable", False)),
            "is_comparison_site": bool(data.get("is_comparison_site", False)),
            "notes": data.get("notes") if isinstance(data.get("notes"), str) else "",
        }

