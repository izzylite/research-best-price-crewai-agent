"""List/collection utility helpers for flows.

These helpers are intentionally simple and dependency-free to keep them safe to
use in agent/flow contexts without introducing additional side effects.
"""

from typing import Any, Dict, Iterable, List, Optional, Set, TypeVar

T = TypeVar("T")


def dedupe_preserve_order(items: Iterable[T]) -> List[T]:
    """Return a new list with duplicates removed while preserving order."""
    seen: Set[Any] = set()
    out: List[T] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def existing_urls(items: Iterable[Dict[str, Any]]) -> Set[str]:
    """Collect a set of URL strings from a list of dict objects.

    Items without a string `url` field are ignored.
    """
    urls: Set[str] = set()
    for item in items or []:
        try:
            url = (item or {}).get("url")
            if isinstance(url, str) and url:
                urls.add(url)
        except Exception:
            continue
    return urls


def append_unique_by_url(
    target: List[Dict[str, Any]],
    candidates: Iterable[Dict[str, Any]],
    *,
    max_items: Optional[int] = None,
) -> None:
    """Append candidate dicts to target when their `url` is unique.

    - Deduplicates against existing `target` URLs
    - If `max_items` is provided, stops once target reaches that length
    """
    existing = existing_urls(target)
    for cand in candidates or []:
        try:
            url = (cand or {}).get("url")
            if not isinstance(url, str) or not url:
                continue
            if url in existing:
                continue
            if max_items is not None and len(target) >= max_items:
                break
            target.append(cand)
            existing.add(url)
        except Exception:
            continue



def restore_product_fields_from_research(
    product: Dict[str, Any],
    research_item: Dict[str, Any],
) -> Dict[str, Any]:
    """Restore missing/placeholder product fields from a research item.

    Rules:
    - Backfill price when missing/empty or equals "Price unavailable" (case-insensitive)
    - Backfill retailer/name/url only when missing/empty
    - Backfill availability only when missing/empty
    - Never overwrite non-empty fields from the product
    """
    try:
        if not isinstance(product, dict):
            return product

        # Price backfill
        price_value = product.get("price")
        price_str = str(price_value).strip() if price_value is not None else ""
        if (not price_str) or (price_str.lower() == "price unavailable"):
            research_price = (research_item or {}).get("price")
            if isinstance(research_price, str) and research_price.strip():
                product["price"] = research_price.strip()

        # Retailer backfill
        retailer_value = product.get("retailer")
        if not isinstance(retailer_value, str) or not retailer_value.strip():
            research_retailer = (research_item or {}).get("vendor") or (research_item or {}).get("retailer")
            if isinstance(research_retailer, str) and research_retailer.strip():
                product["retailer"] = research_retailer.strip()

        # Name backfill
        name_value = product.get("name")
        if not isinstance(name_value, str) or not name_value.strip():
            research_name = (research_item or {}).get("name") or (research_item or {}).get("product_name")
            if isinstance(research_name, str) and research_name.strip():
                product["name"] = research_name.strip()

        # URL backfill
        url_value = product.get("url")
        if not isinstance(url_value, str) or not url_value.strip():
            research_url = (research_item or {}).get("url")
            if isinstance(research_url, str) and research_url.strip():
                product["url"] = research_url.strip()

        # Availability backfill
        availability_value = product.get("availability")
        if not isinstance(availability_value, str) or not availability_value.strip():
            research_availability = (research_item or {}).get("availability")
            if isinstance(research_availability, str) and research_availability.strip():
                product["availability"] = research_availability.strip()

        return product
    except Exception:
        return product