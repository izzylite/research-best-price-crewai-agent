#!/usr/bin/env python3
"""
Perplexity Retailer Research - Recursive/Improvement Test

Iteratively calls PerplexityRetailerResearchTool, evaluates result quality,
and refines search_instructions to converge on high-quality outputs.

Usage:
  python examples/perplexity_recursive_test.py \
    --product "iPhone 15 Pro" \
    --max-retailers 5 \
    --rounds 3 \
    --out results.json

Requires PERPLEXITY_API_KEY to be set.
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List, Tuple

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ecommerce_scraper.tools.perplexity_retailer_research_tool import (
    PerplexityRetailerResearchTool,
)


COMPARISON_SITES = [
    "pricerunner", "shopping.com", "google.com/shopping",
    "kelkoo", "pricegrabber", "nextag", "bizrate"
]

UK_SUFFIXES = (".co.uk", ".uk")
UK_ALLOWED_COM_DOMAINS = {
    # Known UK retailer sites using .com
    "apple.com",       # must include /uk/ in path
    "johnlewis.com",
    "marksandspencer.com",
    "boots.com",
    "superdrug.com",
    "ao.com",
}


def is_gbp_price(price: str) -> bool:
    if not isinstance(price, str):
        return False
    price = price.strip()
    return price.startswith("£")


def is_legitimate_uk_retailer(url: str) -> bool:
    url_lower = (url or "").lower()
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        return False
    if any(site in url_lower for site in COMPARISON_SITES):
        return False
    try:
        from urllib.parse import urlparse
        p = urlparse(url_lower)
        host = p.netloc
        path = p.path
    except Exception:
        return False

    # Accept UK ccTLDs
    if host.endswith(UK_SUFFIXES):
        return True

    # Accept known UK retailers on .com with UK section
    if host.endswith(".com"):
        base = host.split(":")[0]
        if any(base.endswith(dom) for dom in UK_ALLOWED_COM_DOMAINS):
            if base.endswith("apple.com"):
                return "/uk/" in path
            return True

    return False


def looks_like_product_page(url: str) -> bool:
    """Heuristic: avoid search/category endpoints; favor deeper product paths."""
    url_lower = (url or "").lower()
    bad_fragments = ["/search", "/s?", "?q=", "/category", "/categories"]
    if any(frag in url_lower for frag in bad_fragments):
        return False
    # Require at least one path segment after domain
    try:
        from urllib.parse import urlparse
        p = urlparse(url_lower)
        return p.path and p.path != "/"
    except Exception:
        return False


def evaluate_results(data: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Return (num_good, issues)."""
    issues: List[str] = []
    retailers: List[Dict[str, Any]] = data.get("retailers", []) if isinstance(data, dict) else []

    if not retailers:
        issues.append("No retailers returned")
        return 0, issues

    num_good = 0
    for r in retailers:
        name = r.get("name") or r.get("vendor") or ""
        url = r.get("product_url") or r.get("url") or ""
        price = r.get("price") or ""

        if not url:
            issues.append(f"Missing product URL for retailer '{name}'")
            continue
        if not is_legitimate_uk_retailer(url):
            issues.append(f"Non-UK or comparison/invalid URL: {url}")
            continue
        if not looks_like_product_page(url):
            issues.append(f"URL not a direct product page: {url}")
            continue
        if price and not is_gbp_price(price):
            issues.append(f"Non-GBP price format for {url}: {price}")
            continue
        num_good += 1

    return num_good, issues


def build_refinement_instructions(product: str, issues: List[str], target: int) -> str:
    base = [
        f"Find online retailers that sell {product}.",
        f"Return at least {target} retailers if available (JSON array only).",
        "Avoid price comparison and affiliate sites.",
        "Provide direct product page URLs (not search or category pages).",
    ]

    if issues:
        base.append("Address these issues from the previous attempt:")
        base.extend(f"- {i}" for i in issues[:10])

    base.extend([
        "Ensure all URLs are complete (start with https://) and accessible.",
    ])

    return "\n".join(base)


def save_output(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Recursive test for PerplexityRetailerResearchTool")
    parser.add_argument("--product", required=True, help="Product query (e.g., 'iPhone 15 Pro')")
    parser.add_argument("--max-retailers", type=int, default=5, help="Max retailers to request")
    parser.add_argument("--rounds", type=int, default=3, help="Max refinement rounds")
    parser.add_argument("--out", type=str, default="", help="Output JSON path")
    args = parser.parse_args()

    if not os.getenv("PERPLEXITY_API_KEY"):
        print("ERROR: PERPLEXITY_API_KEY is not set. Please set it and retry.")
        return 1

    tool = PerplexityRetailerResearchTool()

    product = args.product
    max_retailers = args.max_retailers
    rounds = max(1, args.rounds)

    history: List[Dict[str, Any]] = []
    search_instructions: str | None = None
    best_payload: Dict[str, Any] | None = None
    best_good = -1

    for attempt in range(1, rounds + 1):
        print(f"\nAttempt {attempt}/{rounds}")
        if search_instructions:
            print("Instructions:\n" + search_instructions)

        raw = tool._run(
            product_query=product,
            max_retailers=max_retailers,
            search_instructions=search_instructions,
            min_retailers=max_retailers,
            require_gbp=True,
            require_product_page=True,
        )

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            print("❌ Non-JSON response from Perplexity; aborting round.")
            payload = {"raw": raw, "retailers": []}

        good, issues = evaluate_results(payload)
        print(f"Good retailers: {payload.get('ai_search_response', '')}")
        print(f"Good retailers: {good}/{max_retailers}")
        if issues:
            print("Issues:")
            for i in issues[:10]:
                print(f" - {i}")

        history.append({
            "attempt": attempt,
            "instructions": search_instructions,
            "result": payload,
            "good": good,
            "issues": issues,
        })

        if good > best_good:
            best_good = good
            best_payload = payload

        if good >= max_retailers:
            print("Target quality achieved; stopping early.")
            break

        search_instructions = build_refinement_instructions(product, issues, max_retailers)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = (
        Path(args.out)
        if args.out
        else Path("product-search-results/test_session") / f"perplexity_recursive_{timestamp}.json"
    )

    final_output = {
        "product_query": product,
        "requested_max_retailers": max_retailers,
        "rounds": rounds,
        "best_good": best_good,
        "best_result": best_payload,
        "history": history,
        "completed_at": datetime.now().isoformat(),
    }

    save_output(out_path, final_output)
    print(f"\nSaved report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

