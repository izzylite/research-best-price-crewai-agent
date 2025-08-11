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


