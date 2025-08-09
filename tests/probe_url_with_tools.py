"""Probe a single URL with CrewAI web scraping tools.

Usage:
  python -m tests.probe_url_with_tools --url https://example.com
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List


def try_import(name: str):
    from importlib import import_module

    mod = import_module("crewai_tools")
    return getattr(mod, name)


def exec_tool(tool: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if hasattr(tool, "_run"):
            out = tool._run(**params)
            return {"ok": True, "result": str(out)[:2000]}
    except Exception as e:
        last = str(e)
    else:
        last = ""
    try:
        if hasattr(tool, "run"):
            out = tool.run(**params)
            return {"ok": True, "result": str(out)[:2000]}
    except Exception as e:
        last = str(e)
    return {"ok": False, "error": last}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    args = ap.parse_args()
    url = args.url

    summary: Dict[str, Any] = {"url": url}

    # ScrapeWebsiteTool
    try:
        ScrapeWebsiteTool = try_import("ScrapeWebsiteTool")
        t = ScrapeWebsiteTool()
        res = exec_tool(t, {"website_url": url})
        summary["ScrapeWebsiteTool"] = {
            **res,
            "has_gbp": ("£" in res.get("result", "")) if res.get("ok") else False,
            "title_hint": ("playstation" in res.get("result", "").lower()),
            "len": len(res.get("result", "")) if res.get("ok") else 0,
        }
    except Exception as e:
        summary["ScrapeWebsiteTool"] = {"ok": False, "error": str(e)}

    # ScrapeElementFromWebsiteTool - try common selectors
    try:
        ScrapeElementFromWebsiteTool = try_import("ScrapeElementFromWebsiteTool")
        t = ScrapeElementFromWebsiteTool()
        selectors: List[str] = [
            "h1",
            "[class*=title]",
            "[data-testid*=title]",
            "[class*=price]",
            "[data-testid*=price]",
            "[itemprop=price]",
        ]
        sel_results: Dict[str, Any] = {}
        for sel in selectors:
            r = exec_tool(t, {"website_url": url, "css_element": sel})
            sel_results[sel] = r
        summary["ScrapeElementFromWebsiteTool"] = sel_results
    except Exception as e:
        summary["ScrapeElementFromWebsiteTool"] = {"ok": False, "error": str(e)}

    # SeleniumScrapingTool (best effort open)
    try:
        SeleniumScrapingTool = try_import("SeleniumScrapingTool")
        t = SeleniumScrapingTool()
        res = exec_tool(t, {"website_url": url})
        if not res.get("ok"):
            # try url param name variant
            res = exec_tool(t, {"url": url})
        summary["SeleniumScrapingTool"] = res
    except Exception as e:
        summary["SeleniumScrapingTool"] = {"ok": False, "error": str(e)}

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

