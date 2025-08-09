"""Quick sanity checks for CrewAI web scraping tools.

Run:
  python -m tests.verify_scraping_tools

This script tries to import and execute:
  - ScrapeWebsiteTool (fetch example.com)
  - ScrapeElementFromWebsiteTool (extract <h1> from example.com)
  - SeleniumScrapingTool (if available, open example.com)

It prints a compact JSON summary of success/failure for each tool.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict


def try_import_tools():
    try:
        from crewai_tools import (
            ScrapeWebsiteTool,
            ScrapeElementFromWebsiteTool,
            SeleniumScrapingTool,
        )

        return {
            "ScrapeWebsiteTool": ScrapeWebsiteTool,
            "ScrapeElementFromWebsiteTool": ScrapeElementFromWebsiteTool,
            "SeleniumScrapingTool": SeleniumScrapingTool,
        }
    except Exception as e:
        # Try partial imports
        tools = {}
        try:
            from crewai_tools import ScrapeWebsiteTool  # type: ignore
            tools["ScrapeWebsiteTool"] = ScrapeWebsiteTool
        except Exception:
            pass
        try:
            from crewai_tools import ScrapeElementFromWebsiteTool  # type: ignore
            tools["ScrapeElementFromWebsiteTool"] = ScrapeElementFromWebsiteTool
        except Exception:
            pass
        try:
            from crewai_tools import SeleniumScrapingTool  # type: ignore
            tools["SeleniumScrapingTool"] = SeleniumScrapingTool
        except Exception:
            pass
        if not tools:
            raise RuntimeError(f"Failed to import crewai_tools scraping tools: {e}")
        return tools


def execute_tool(tool: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to execute a tool with flexible calling conventions.

    Many CrewAI tools implement BaseTool._run(**kwargs) underneath; some also expose .run.
    This tries several patterns and returns a dict containing status and a short payload.
    """
    # Prefer _run(**kwargs)
    try:
        if hasattr(tool, "_run") and callable(getattr(tool, "_run")):
            out = tool._run(**params)
            return {"ok": True, "result": str(out)[:500]}
    except Exception as e:
        last_err = str(e)
    else:
        last_err = ""

    # Try run(**kwargs)
    try:
        if hasattr(tool, "run") and callable(getattr(tool, "run")):
            out = tool.run(**params)
            return {"ok": True, "result": str(out)[:500]}
    except Exception as e:
        last_err = str(e)

    # Try run(params)
    try:
        if hasattr(tool, "run") and callable(getattr(tool, "run")):
            out = tool.run(params)
            return {"ok": True, "result": str(out)[:500]}
    except Exception as e:
        last_err = str(e)

    # Try call
    try:
        out = tool(params)
        return {"ok": True, "result": str(out)[:500]}
    except Exception as e:
        last_err = str(e)

    return {"ok": False, "error": last_err}


def main() -> int:
    tools_map = try_import_tools()

    summary: Dict[str, Any] = {"ScrapeWebsiteTool": None, "ScrapeElementFromWebsiteTool": None, "SeleniumScrapingTool": None}

    # ScrapeWebsiteTool – fetch example.com
    if "ScrapeWebsiteTool" in tools_map:
        try:
            t = tools_map["ScrapeWebsiteTool"]()
            res = execute_tool(t, {"website_url": "https://example.com"})
            summary["ScrapeWebsiteTool"] = res
        except Exception as e:
            summary["ScrapeWebsiteTool"] = {"ok": False, "error": str(e)}

    # ScrapeElementFromWebsiteTool – extract <h1> from example.com
    if "ScrapeElementFromWebsiteTool" in tools_map:
        try:
            t = tools_map["ScrapeElementFromWebsiteTool"]()
            res = execute_tool(t, {"website_url": "https://example.com", "css_element": "h1"})
            summary["ScrapeElementFromWebsiteTool"] = res
        except Exception as e:
            summary["ScrapeElementFromWebsiteTool"] = {"ok": False, "error": str(e)}

    # SeleniumScrapingTool – open example.com (best-effort)
    if "SeleniumScrapingTool" in tools_map:
        try:
            t = tools_map["SeleniumScrapingTool"]()
            # Attempt common param names
            params_options = [
                {"website_url": "https://example.com"},
                {"url": "https://example.com"},
            ]
            result = None
            for params in params_options:
                result = execute_tool(t, params)
                if result.get("ok"):
                    break
            if result is None:
                result = {"ok": False, "error": "No params tried"}
            summary["SeleniumScrapingTool"] = result
        except Exception as e:
            summary["SeleniumScrapingTool"] = {"ok": False, "error": str(e)}

    print(json.dumps(summary, indent=2))
    # Return non-zero exit if any failed
    failed = [k for k, v in summary.items() if v and not v.get("ok")]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

