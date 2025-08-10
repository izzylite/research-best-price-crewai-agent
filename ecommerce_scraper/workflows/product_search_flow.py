"""Product Search Flow - CrewAI Flow for product-specific search across UK retailers."""

import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import re
from pydantic import BaseModel, Field

from crewai import Flow, Crew
from crewai.flow.flow import listen, start
from rich.console import Console
from ..config.settings import settings

from ..agents.research_agent import ResearchAgent
from ..agents.confirmation_agent import ConfirmationAgent
from ..agents.validation_agent import ProductSearchValidationAgent 
from ..agents.feedback_agent import FeedbackAgent
from ..ai_logging.error_logger import get_error_logger

logger = logging.getLogger(__name__)


class ProductSearchState(BaseModel):
    """State management for product search flow."""

    # Input parameters
    product_query: str = Field("", description="Product to search for")
    max_retailers: int = Field(5, description="Maximum retailers to search")
    max_retries: int = Field(3, description="Maximum retry attempts per retailer")
    session_id: str = Field("", description="Session identifier")
    
    # Flow state
    current_retailer_index: int = Field(0, description="Current retailer being processed")
    current_attempt: int = Field(1, description="Current attempt number for current retailer") 
    
    # Research results
    retailers: List[Dict[str, Any]] = Field(default_factory=list, description="Retailers discovered for confirmation (vendor,url,price)") 
    research_result: Optional[Dict[str, Any]] = Field(default=None, description="Research result")
    # confirmation results
    current_retailer_product: Optional[Dict[str, Any]] = Field(default=None, description="Single confirmed product for current retailer")
    confirmation_result: Optional[Dict[str, Any]] = Field(default=None, description="Confirmation result")
    
    # Validation results
    validated_products: List[Dict[str, Any]] = Field(default_factory=list, description="All validated products")
    validated_product: Optional[Dict[str, Any]] = Field(default=None, description="Last validated product")
    validation_feedback: Optional[Dict[str, Any]] = Field(None, description="Validation feedback for retries")
    targeted_feedback: Optional[Dict[str, Any]] = Field(None, description="Targeted feedback for both agents")
    excluded_urls: List[str] = Field(default_factory=list, description="Excluded URLs")
    validation_result: Optional[Dict[str, Any]] = Field(default=None, description="Validation result")
    
    # Final results
    search_results: List[Dict[str, Any]] = Field(default_factory=list, description="Final search results")
    final_results: Optional[Dict[str, Any]] = Field(None, description="Final formatted results")
    
    # Statistics
    retailers_searched: int = Field(0, description="Number of retailers searched")
    total_attempts: int = Field(0, description="Total attempts made")
    success_rate: float = Field(0.0, description="Success rate of searches")
     


class ProductSearchFlow(Flow[ProductSearchState]):
    """
    CrewAI Flow for product-specific search across UK retailers.
    
    Flow: Research → Confirm → Validate → [Retry Loop] → Next Retailer → Complete
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize the product search flow."""
        super().__init__()
        self.verbose = verbose
        self.console = Console()
        self.error_logger = get_error_logger("product_search_flow")
        
        # Initialize agents (will be created on-demand)
        self._research_agent = None
        self._confirmation_agent = None
        self._validation_agent = None
        self._feedback_agent = None
         

        # Map event names to bound handlers for local fallback emission
        self._local_event_handlers = {
            "research_retailers": lambda adapter: self.research_retailers(adapter),
            "confirm_products": lambda adapter: self.confirm_products(adapter),
            "validate_products": lambda adapter: self.validate_products(adapter),
            "next_product": lambda adapter: self.next_product(adapter),
            "retry_research_with_feedback": lambda adapter: self.retry_research_with_feedback(adapter),
            "retry_confirmation_with_feedback": lambda adapter: self.retry_confirmation_with_feedback(adapter),
            "end": lambda adapter: self.finalize(),
        }

    def _create_local_event_adapter(self):
        """Create a minimal event adapter to drive the flow when framework context isn't provided."""
        flow = self

        class _Adapter:
            def emit(self_inner, name: str) -> None:
                handler = flow._local_event_handlers.get(str(name))
                if handler is not None:
                    handler(self_inner)

        return _Adapter()

    def _llm_available(self) -> bool:
        """Return True if any supported LLM API key is available."""
        try:
            return bool(
                settings.openai_api_key
                or settings.perplexity_api_key
                or settings.anthropic_api_key
                or settings.google_api_key
            )
        except Exception:
            return False

        
    
    def _safe_parse_json(self, result: Any, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse CrewAI result to JSON dict safely, salvaging when needed.

        Returns a dict. If parsing fails, returns provided default or empty dict.
        """
        if default is None:
            default = {}

        # If result already a dict, return as-is
        if isinstance(result, dict):
            return result

        # If result is a list, wrap into a dict under a generic key
        if isinstance(result, list):
            return {"items": result}

        candidates: List[str] = []

        try:
            if hasattr(result, "raw") and getattr(result, "raw"):
                candidates.append(getattr(result, "raw"))
        except Exception:
            pass

        try:
            s = str(result) if result is not None else ""
            if s:
                candidates.append(s)
        except Exception:
            pass

        def try_load(text: str) -> Optional[Dict[str, Any]]:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    return {"items": parsed}
            except Exception:
                pass

            # Attempt to salvage JSON object
            if "{" in text and "}" in text:
                try:
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        salvaged = text[start : end + 1]
                        parsed = json.loads(salvaged)
                        if isinstance(parsed, dict):
                            return parsed
                        if isinstance(parsed, list):
                            return {"items": parsed}
                except Exception:
                    pass

            # Attempt to salvage JSON array
            if "[" in text and "]" in text:
                try:
                    start = text.find("[")
                    end = text.rfind("]")
                    if start != -1 and end != -1 and end > start:
                        salvaged = text[start : end + 1]
                        parsed = json.loads(salvaged)
                        if isinstance(parsed, dict):
                            return parsed
                        if isinstance(parsed, list):
                            return {"items": parsed}
                except Exception:
                    pass

            # Regex fallback for the largest JSON object block
            try:
                match = re.search(r"\{[\s\S]*\}", text)
                if match:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, dict):
                        return parsed
                    if isinstance(parsed, list):
                        return {"items": parsed}
            except Exception:
                pass

            return None

        for c in candidates:
            parsed = try_load(c)
            if parsed is not None:
                return parsed

        # Warning logs removed; return default silently per logging policy
        return default

    def _parse_retailers_from_raw(self, research_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse retailers from the raw model output when structured list is missing.

        Falls back to parsing the `ai_search_response` JSON string into a list.
        """
        try:
            raw = research_data.get("ai_search_response", [])
            # Already a list
            if isinstance(raw, list):
                return raw
            # Try to parse when it's a JSON string
            if isinstance(raw, str):
                text = raw.strip()
                if not text:
                    return []
                try:
                    # Direct JSON array
                    if text.startswith("["):
                        parsed = json.loads(text)
                        return parsed if isinstance(parsed, list) else []
                    # Salvage the first JSON array in the text
                    match = re.search(r"\[.*\]", text, re.S)
                    if match:
                        parsed = json.loads(match.group(0))
                        return parsed if isinstance(parsed, list) else []
                except Exception:
                    return []
        except Exception:
            return []
        return []

   
    
    def _get_research_agent(self) -> ResearchAgent:
        """Get or create ResearchAgent instance."""
        if self._research_agent is None:
            self._research_agent = ResearchAgent(stagehand_tool=None, verbose=self.verbose)
        return self._research_agent
    
    def _get_confirmation_agent(self) -> ConfirmationAgent:
        """Get or create ConfirmationAgent instance."""
        if self._confirmation_agent is None:
            self._confirmation_agent = ConfirmationAgent(stagehand_tool=None, verbose=self.verbose)
        return self._confirmation_agent
    
    def _get_validation_agent(self) -> ProductSearchValidationAgent:
        """Get or create ProductSearchValidationAgent instance."""
        if self._validation_agent is None:
            self._validation_agent = ProductSearchValidationAgent(stagehand_tool=None, verbose=self.verbose)
        return self._validation_agent

    def _get_feedback_agent(self) -> FeedbackAgent:
        """Get or create FeedbackAgent instance."""
        if self._feedback_agent is None:
            self._feedback_agent = FeedbackAgent(stagehand_tool=None, verbose=self.verbose)
        return self._feedback_agent

    def _build_research_exclusions(self) -> Dict[str, List[str]]:
        """Build exclusion lists from state's `excluded_urls` only.

        Returns a dict with:
        - `exclude_urls`: de-duplicated list of URLs from `self.state.excluded_urls`
        - `exclude_domains`: domains derived solely from `exclude_urls`
        """
        # Start from explicit state-managed exclusion list only
        exclude_urls: List[str] = list(self.state.excluded_urls or [])

        # De-duplicate while preserving order
        def dedupe(items: List[str]) -> List[str]:
            seen = set()
            out: List[str] = []
            for x in items:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        deduped_urls = dedupe(exclude_urls)

        # Derive domains strictly from excluded URLs
        exclude_domains: List[str] = []
        try:
            from urllib.parse import urlparse
            for url in deduped_urls:
                if not isinstance(url, str) or not url:
                    continue
                try:
                    netloc = urlparse(url).netloc
                    if netloc:
                        exclude_domains.append(netloc)
                except Exception:
                    continue
        except Exception:
            # Best-effort; ignore errors
            pass

        return {
            "exclude_urls": deduped_urls,
            "exclude_domains": dedupe(exclude_domains),
        }

    def _merge_improved_retailers(self, improved_retailers: List[Dict[str, Any]]) -> None:
        """Merge improved retailers into current state with de-duplication and capping.

        - Replaces the current retailer with the first improved retailer when index is valid
        - Appends remaining unique retailers by URL up to max_retailers
        - When list is empty/out-of-bounds, seeds from improved list and resets index to 0
        """
        if not improved_retailers:
            return

        # Build a set of existing URLs to avoid duplicates
        existing_urls: set[str] = set()
        try:
            for rr in self.state.retailers or []:
                url = (rr or {}).get('url')
                if isinstance(url, str) and url:
                    existing_urls.add(url)
        except Exception:
            pass


        def append_unique(retailers_list: List[Dict[str, Any]], candidates: List[Dict[str, Any]]):
            for cand in candidates:
                url = (cand or {}).get('url')
                if not isinstance(url, str) or not url:
                    continue
                if url in existing_urls:
                    continue
                if len(retailers_list) >= self.state.max_retailers:
                    break
                retailers_list.append(cand)
                existing_urls.add(url)

        # Validate index before replacement to prevent IndexError
        if self.state.retailers and self.state.current_retailer_index < len(self.state.retailers):
            # Replace current item
            self.state.retailers[self.state.current_retailer_index] = improved_retailers[0]
            # Rebuild existing URLs because we replaced current
            existing_urls = set()
            try:
                for rr in self.state.retailers or []:
                    url = (rr or {}).get('url')
                    if isinstance(url, str) and url:
                        existing_urls.add(url)
            except Exception:
                pass
            # Append remaining unique retailers up to max_retailers
            append_unique(self.state.retailers, improved_retailers[1:])
        else:
            # If index is out of bounds or retailers list is empty, seed from improved list
            self.state.retailers = []
            append_unique(self.state.retailers, improved_retailers)
            # Reset index to start of new retailers
            if not self.state.retailers or self.state.current_retailer_index >= len(self.state.retailers):
                self.state.current_retailer_index = 0

   
    def _generate_targeted_feedback(self, validation_data: Dict[str, Any]):
        """Delegate to FeedbackAgent to generate targeted feedback and routing."""
        try:
            current_retailer = self.state.retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('vendor', 'Unknown')

            # Create targeted feedback task via FeedbackAgent
            feedback_task = self._get_feedback_agent().create_targeted_feedback_task(
                search_query=self.state.product_query,
                validation_failures=validation_data.get('validation_failures', []),
                retailer=retailer_name,
                attempt_number=self.state.current_attempt,
                max_attempts=self.state.max_retries,
                already_searched=self.state.retailers,
            )

            # Create and execute feedback crew
            feedback_crew = Crew(
                agents=[self._get_feedback_agent().get_agent()],
                tasks=[feedback_task],
                verbose=self.verbose
            )

            result = feedback_crew.kickoff()

            # Prefer pydantic output; otherwise salvage JSON safely
            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                feedback_data = result.pydantic.model_dump()
            else:
                feedback_data = self._safe_parse_json(result, default={})

            # Store targeted feedback (ensure non-empty with sensible defaults)
            if not isinstance(feedback_data, dict) or not feedback_data:
                feedback_data = {
                    "research_feedback": {"should_retry": True, "priority": "medium"},
                    "confirmation_feedback": {"should_retry": True, "priority": "medium"},
                    "retry_strategy": {"recommended_approach": "confirmation_first"},
                }
            self.state.targeted_feedback = feedback_data

            if self.verbose:
                research_priority = feedback_data.get('research_feedback', {}).get('priority', 'low')
                confirmation_priority = feedback_data.get('confirmation_feedback', {}).get('priority', 'low')
                self.console.print(f"[yellow]📋 Generated Targeted Feedback - Research: {research_priority}, confirmation: {confirmation_priority}[/yellow]")

        except Exception as e:
            logger.error(f"Failed to generate targeted feedback: {str(e)}", exc_info=True)
            # Fallback to basic feedback
            self.state.targeted_feedback = {
                "research_feedback": {"should_retry": True, "priority": "medium"},
                "confirmation_feedback": {"should_retry": True, "priority": "medium"},
                "retry_strategy": {"recommended_approach": "confirmation_first"}
            }

    def _generate_feedback_for_empty_retailers(self) -> Dict[str, Any]:
        """Use FeedbackAgent to generate research-first targeted feedback when no retailers are available."""
        try:
            feedback_task = self._get_feedback_agent().create_empty_retailers_feedback_task(
                search_query=self.state.product_query,
                attempt_number=self.state.current_attempt,
                max_attempts=self.state.max_retries,
                already_searched=self.state.retailers,
            )
            feedback_crew = Crew(
                agents=[self._get_feedback_agent().get_agent()],
                tasks=[feedback_task],
                verbose=self.verbose
            )
            result = feedback_crew.kickoff()
            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                feedback_data = result.pydantic.model_dump()
            else:
                feedback_data = self._safe_parse_json(result, default={})
            return feedback_data or {
                "research_feedback": {"should_retry": True, "priority": "medium"},
                "confirmation_feedback": {"should_retry": False, "priority": "low"},
                "retry_strategy": {"recommended_approach": "research_first"}
            }
        except Exception as e:
            self.error_logger.error(f"Failed to generate targeted feedback for empty retailers: {e}", exc_info=True)
            # Fallback to a minimal research-first directive
            return {
                "research_feedback": {"should_retry": True, "priority": "medium"},
                "confirmation_feedback": {"should_retry": False, "priority": "low"},
                "retry_strategy": {"recommended_approach": "research_first"}
            }

    def _generate_feedback_for_confirmation_retry(self) -> Dict[str, Any]:
        """Generate confirmation-first fallback feedback when confirmation retry is requested without prior feedback."""
        try:
            current_retailer = {}
            if self.state.retailers and self.state.current_retailer_index < len(self.state.retailers):
                current_retailer = self.state.retailers[self.state.current_retailer_index] or {}
            retailer_name = current_retailer.get('vendor', 'Unknown')

            # Provide a minimal yet helpful confirmation-focused directive
            return {
                "research_feedback": {"should_retry": False, "priority": "low"},
                "confirmation_feedback": {
                    "should_retry": True,
                    "priority": "medium",
                    "hints": {
                        "retailer": retailer_name,
                        "focus": "Navigate to a specific product detail page, avoid category/search pages, avoid comparison sites.",
                    },
                },
                "retry_strategy": {"recommended_approach": "confirmation_first"},
            }
        except Exception:
            # Very defensive fallback
            return {
                "research_feedback": {"should_retry": False, "priority": "low"},
                "confirmation_feedback": {"should_retry": True, "priority": "medium"},
                "retry_strategy": {"recommended_approach": "confirmation_first"},
            }

    @start()
    def initialize_search(self, event=None) -> Dict[str, Any]:
        """Initialize the product search with input parameters."""
        try:
            
            if self.verbose:
                self.console.print(f"[blue]🔍 Initializing Product Search[/blue]")
                self.console.print(f"[cyan]Product: {self.state.product_query}[/cyan]")

 
            if self.verbose:
                self.console.print("[green]✅ Product search initialized[/green]")

            # Prevent expensive LLM stack traces when no provider is configured
            if not self._llm_available():
                msg = (
                    "No LLM API key configured. Set one of OPENAI_API_KEY, PERPLEXITY_API_KEY, "
                    "or ANTHROPIC_API_KEY to enable agent execution."
                )
                self.error_logger.error(msg)
                if event is not None:
                    event.emit("end")
                else:
                    self._create_local_event_adapter().emit("end")
                return {"action": "error", "error": msg}

            # Kick off event-driven flow. Use framework event if provided, otherwise a local adapter.
            if event is not None:
                event.emit("research_retailers")
            else:
                self._create_local_event_adapter().emit("research_retailers")
            return {"action": "research_retailers", "status": "initialized"}

        except Exception as e:
            error_msg = f"Failed to initialize product search: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}
    
    def increment_retailer_index(self) -> bool:
        """Increment the retailer index and reset the attempt number.

        Returns:
            bool: True if there are more retailers to process, False if we've reached the end
        """
        self.state.current_retailer_index += 1
        self.state.current_attempt = 1
        self.state.retailers_searched += 1
        # Clear feedback between retailers to avoid stale guidance
        self.state.targeted_feedback = None
        self.state.validation_feedback = None
        self.state.current_retailer_product = None

        # Boundary check: return False if we've exceeded the retailers list OR max_retailers limit
        has_more_in_list = self.state.current_retailer_index < len(self.state.retailers)
        within_max_limit = self.state.retailers_searched < self.state.max_retailers

        return has_more_in_list and within_max_limit
 

    def has_more_retailers(self) -> bool:
        """Check if there are more retailers to process.

        Returns:
            bool: True if there are more retailers, False otherwise
        """
        return self.state.current_retailer_index < len(self.state.retailers)

    
    @listen("research_retailers")
    def research_retailers(self, event) -> Dict[str, Any]:
        """Research UK retailers that sell the specified product."""
        try:
            # Block early if no LLM provider is configured to avoid noisy auth errors
            if not self._llm_available():
                msg = (
                    "Cannot run research: no LLM API key configured. Set OPENAI_API_KEY, "
                    "PERPLEXITY_API_KEY, or ANTHROPIC_API_KEY."
                )
                self.error_logger.error(msg)
                self.state.research_result = {"action": "error", "error": msg}
                event.emit("end")
                return
            if self.verbose:
                self.console.print(f"[blue]🔬 Researching Retailers[/blue]")
            
            # Create retailer research task
            research_task = self._get_research_agent().create_retailer_research_task(
                product_query=self.state.product_query,
                max_retailers=self.state.max_retailers
            )

            # Create and execute research crew
            research_crew = Crew(
                agents=[self._get_research_agent().get_agent()],
                tasks=[research_task],
                verbose=self.verbose
            )
            
            result = research_crew.kickoff()

            # Prefer pydantic output when available
            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                research_data = result.pydantic.model_dump()
            else:
                # Parse research results safely
                research_data = self._safe_parse_json(result, default={"retailers": []})
            
            # Prefer pydantic `retailers` when present, else parse raw output
            retailers = research_data.get('retailers')
            if isinstance(retailers, list) and retailers:
                self.state.retailers = retailers
            else:
                self.state.retailers = self._parse_retailers_from_raw(research_data)
            
            if self.verbose:
                self.console.print(f"[green]✅ Found {len(self.state.retailers)} retailers[/green]")
            
            self.state.research_result = {"action": "confirm_products", "retailers_found": len(self.state.retailers)}
            # Continue to confirmation step
            event.emit("confirm_products")
        except Exception as e:
            error_msg = f"Retailer research failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            self.state.research_result = {"action": "error", "error": error_msg}
            # Even on error, proceed to confirmation to handle gracefully
            event.emit("confirm_products")
           

    @listen("confirm_products")
    def confirm_products(self, event) -> Dict[str, Any]:
        """confirm products from the current retailer."""
        try:
            if self.state.research_result.get("action") == "error":
                self.state.confirmation_result = {"action": "error", "error": self.state.research_result.get("error")}
                event.emit("validate_products")
                return
            
            if not self.state.retailers: 
                self.state.confirmation_result = {"action": "end", "reason": "empty_retailers"}
                event.emit("validate_products")
                return

            if self.state.current_retailer_index >= len(self.state.retailers): 
                self.state.confirmation_result = {"action": "end", "reason": "no_more_retailers"}
                event.emit("validate_products")
                return
            
            
            
            current_retailer = self.state.retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('vendor', 'Unknown')

            # Get retailer URL; if invalid/missing, skip to next or finalize
            retailer_url = current_retailer.get('url', '')

            if not retailer_url or not retailer_url.startswith('http'): 
                self.state.confirmation_result = {"action": "skipped", "reason": "Invalid retailer URL"}
                event.emit("validate_products")
                return
            
            if self.verbose:
                self.console.print(f"[blue]📦 confirming from {retailer_name}[/blue]")
            
            # Create confirmation task
            confirmation_task = self._get_confirmation_agent().create_product_search_confirmation_task(
                product_query=self.state.product_query,
                retailer=retailer_name,
                retailer_url=retailer_url
            )
            
            # Create and execute confirmation crew
            confirmation_crew = Crew(
                agents=[self._get_confirmation_agent().get_agent()],
                tasks=[confirmation_task],
                verbose=self.verbose
            )
            
            result = confirmation_crew.kickoff()

            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                confirmation_data = result.pydantic.model_dump()
            else:
                # Parse confirmation results safely
                confirmation_data = self._safe_parse_json(result, default={"product": None})
            
            # Store single confirmed product
            product_obj = confirmation_data.get('product')
            self.state.current_retailer_product = product_obj if isinstance(product_obj, dict) else None
             
            
            if self.verbose:
                self.console.print(f"[green]✅ Confirmed {'1' if self.state.current_retailer_product else '0'} product[/green]")
            
            self.state.confirmation_result = {
                "action": "validate_products", 
                "product_confirmed": True if self.state.current_retailer_product else False,
                "retailer": retailer_name
            }
            event.emit("validate_products")
            
        except Exception as e:
            error_msg = f"Product confirmation failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            self.state.confirmation_result = {"action": "error", "error": error_msg}
            event.emit("validate_products")

    @listen("validate_products")
    def validate_products(self, event) -> Dict[str, Any]:
        """Validate confirmed products and provide feedback for retries."""
        try:
            if self.state.confirmation_result.get("action") == "skipped":
                self.state.validation_result = {"action": "skipped", "reason": self.state.confirmation_result.get("reason")}
                event.emit("next_product")
                return
            
            if self.state.confirmation_result.get("action") == "error":
                self.state.validation_result = {"action": "error", "error": self.state.confirmation_result.get("error")}
                event.emit("next_product")
                return

            # Handle terminal/empty cases from confirmation safely before any indexing
            if self.state.confirmation_result.get("action") == "finalize":
                reason = self.state.confirmation_result.get("reason")
                self.state.current_retailer_product = None
                if reason == "no_more_retailers":
                    # We have exhausted the retailer list; finalize immediately
                    self.state.current_retailer_index = len(self.state.retailers)
                    self.state.validation_result = {"action": "end", "reason": "no_more_retailers"} 
                    event.emit("end")
                    return
                   
                elif reason == "empty_retailers":
                    # No retailers found; trigger retry or end immediately
                    self.state.validation_result = {"action": "route_after_validation", "validation_passed": False, "reason": "empty_retailers"}
                    if self.state.current_attempt < self.state.max_retries:
                        event.emit(self.handle_retry())
                    else:
                        event.emit("end")
                    return

           

            # Use product URL from the confirmed product; do not rely on current retailer here
            # This ensures we validate exactly what was confirmed
            if not self.state.current_retailer_product:
                self.state.validation_result =  {"action": "skipped", "reason": "no_product"}
                event.emit("next_product")
                return

            # Extract confirmed product details
            product_name = self.state.current_retailer_product.get('name', '')
            product_url = self.state.current_retailer_product.get('url', '')
            product_price = self.state.current_retailer_product.get('price', '')
            # Use retailer from confirmation step instead of product name
            retailer_name = self.state.confirmation_result.get('retailer') or ''
            
            if not product_url or not product_url.startswith('http'):
                self.state.validation_result =  {"action": "skipped", "reason": "Invalid retailer URL"}
                event.emit("next_product")
                return

            if not retailer_name:
                self.state.validation_result =  {"action": "error", "reason": "retailer_name_missing"}
                event.emit("next_product")
                return

            if self.verbose:
                self.console.print(f"[magenta]✅ Validating Products from {retailer_name}[/magenta]")
            
            # Create validation task
            validation_task = self._get_validation_agent().create_product_search_validation_task(
                search_query=self.state.product_query, 
                retailer=retailer_name,
                retailer_url=product_url,
                product_name=product_name,
                retailer_price = product_price,
                attempt_number=self.state.current_attempt,
                max_attempts=self.state.max_retries
            )
            
            # Create and execute validation crew
            validation_crew = Crew(
                agents=[self._get_validation_agent().get_agent()],
                tasks=[validation_task],
                verbose=self.verbose
            )
            
            result = validation_crew.kickoff()

            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                validation_data = result.pydantic.model_dump()
            else:
                # Parse validation results safely
                validation_data = self._safe_parse_json(result, default={"validated_products": [], "validation_passed": False})
            
            # Store validated product (single)
            self.state.validated_product = validation_data.get('validated_product') if isinstance(validation_data.get('validated_product'), dict) else None
            if self.state.validated_product:
                self.state.validated_products.append(self.state.validated_product)
           

            validation_passed = validation_data.get('validation_passed', False) 
            
            # Store validation feedback for potential retries
            self.state.validation_feedback = validation_data.get('feedback', {})

            # If validation failed, generate targeted feedback for both agents
            if not validation_passed and self.state.current_attempt < self.state.max_retries:
                self.state.excluded_urls.append(product_url)
                self._generate_targeted_feedback(validation_data)

            if self.verbose:
                self.console.print(f"[green]✅ Validated {'1' if self.state.validated_product else '0'} product[/green]")

            self.state.validation_result =  {"action": "route_after_validation", "validation_passed": validation_passed}

            # Event-driven routing after validation
            empty_retailers = self.state.validation_result.get("reason","") == "empty_retailers"
            if (not validation_passed) or empty_retailers:
                if self.state.current_attempt < self.state.max_retries:
                    event.emit(self.handle_retry())
                else:
                    event.emit("end" if empty_retailers else "next_product")
            else:
                event.emit("next_product")
            
        except Exception as e:
            error_msg = f"Product validation failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            self.state.validation_result =  {"action": "error", "error": error_msg}
            event.emit("next_product")

    def handle_retry(self) -> str:
        self.state.current_attempt += 1 
        """Use targeted feedback to determine which agent should retry."""
        if self.state.targeted_feedback:
            retry_strategy = self.state.targeted_feedback.get('retry_strategy', {})
            recommended_approach = retry_strategy.get('recommended_approach', 'research_first')

            research_feedback = self.state.targeted_feedback.get('research_feedback', {})
            confirmation_feedback = self.state.targeted_feedback.get('confirmation_feedback', {})

            research_should_retry = research_feedback.get('should_retry', False)
            confirmation_should_retry = confirmation_feedback.get('should_retry', False)

            if self.verbose:
                self.console.print(f"[cyan]🎯 Retry Strategy: {recommended_approach}[/cyan]")

            # Route based on targeted feedback
            if recommended_approach == "research_first" and research_should_retry:
                return "retry_research_with_feedback"
            elif recommended_approach == "confirmation_first" and confirmation_should_retry:
                return "retry_confirmation_with_feedback"
            elif recommended_approach == "both_parallel":
                # For now, do research first then confirmation
                return "retry_research_with_feedback"
            else:
                # Default to confirmation retry
                return "retry_confirmation_with_feedback"
        else: 
            self.state.targeted_feedback = self._generate_feedback_for_empty_retailers()
            return "retry_research_with_feedback"

    @listen("next_product")
    def next_product(self,event) -> Dict[str, Any]:
        """Move to the next product/retailer or finalize if done."""
        try:
            # Increment index and reset attempt count
            has_more = self.increment_retailer_index()

            if not has_more:
                # If we have no validated products and retries left, retry; else finalize
                if not self.state.validated_products and self.state.current_attempt < self.state.max_retries:
                        event.emit(self.handle_retry())
                else:
                    event.emit("end")
                return

            # Move to confirmation step for the next retailer/product
            event.emit("confirm_products")
            return

        except Exception as e:
            error_msg = f"Failed to move to next product: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            event.emit("end")



    @listen("retry_research_with_feedback")
    def retry_research_with_feedback(self,event) -> Dict[str, Any]:
        """Retry research using targeted validation feedback to improve retailer discovery."""
        try:
            if self.verbose:
                self.console.print(f"[blue]🔬 Retry Research with Feedback (Attempt {self.state.current_attempt})[/blue]")

            # Ensure targeted feedback exists (avoid None/empty). Auto-generate fallback when missing.
            if not self.state.targeted_feedback or not isinstance(self.state.targeted_feedback, dict) or not self.state.targeted_feedback:
                self.state.targeted_feedback = self._generate_feedback_for_empty_retailers()

            # Create feedback-enhanced research task
            exclusions = self._build_research_exclusions()
            research_task = self._get_research_agent().create_feedback_enhanced_research_task(
                product_query=self.state.product_query,
                validation_feedback=self.state.targeted_feedback,
                attempt_number=self.state.current_attempt,
                max_retailers=self.state.max_retailers, 
                exclude_urls=exclusions.get("exclude_urls", []),
                exclude_domains=exclusions.get("exclude_domains", [])
            )

            # Create and execute research crew
            research_crew = Crew(
                agents=[self._get_research_agent().get_agent()],
                tasks=[research_task],
                verbose=self.verbose
            )
            
            result = research_crew.kickoff()

            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                research_data = result.pydantic.model_dump()
            else:
                # Parse research results safely
                research_data = self._safe_parse_json(result, default={"retailers": []})

            # Update researched retailers with improved results (prefer `retailers`)
            improved_retailers = research_data.get('retailers')
            if not isinstance(improved_retailers, list):
                improved_retailers = self._parse_retailers_from_raw(research_data)
            if improved_retailers:
                self._merge_improved_retailers(improved_retailers)

            if self.verbose:
                retailer_count = len(improved_retailers)
                self.console.print(f"[green]✅ Improved Research: {retailer_count} better retailers found[/green]")
            self.state.research_result = {"action": "confirm_products", "research_improved": True}
            event.emit("confirm_products")
            

        except Exception as e:
            error_msg = f"Research retry with feedback failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            self.state.research_result = {"action": "error", "error": error_msg}
            event.emit("end")
            

 

    @listen("retry_confirmation_with_feedback")
    def retry_confirmation_with_feedback(self,event) -> Dict[str, Any]:
        """Retry confirmation using targeted validation feedback to improve results."""
        try:
            if self.verbose:
                self.console.print(f"[yellow]🔄 Retry confirmation with Feedback (Attempt {self.state.current_attempt})[/yellow]")

            # Ensure targeted feedback exists; auto-generate confirmation-focused feedback if missing
            if not self.state.targeted_feedback or not isinstance(self.state.targeted_feedback, dict) or not self.state.targeted_feedback:
                self.state.targeted_feedback = self._generate_feedback_for_confirmation_retry()

            if not self.state.retailers:
                self.state.confirmation_result = {"action": "end", "reason": "empty_retailers"}
                event.emit("validate_products")
                return

            if self.state.current_retailer_index >= len(self.state.retailers):
                self.state.confirmation_result = {"action": "end", "reason": "no_more_retailers"}
                event.emit("validate_products")
                return
            
            
            
            current_retailer = self.state.retailers[self.state.current_retailer_index]
            
           
            retailer_name = current_retailer.get('vendor', 'Unknown')

            # Get retailer URL with fallback logic
            retailer_url = current_retailer.get('url', '')
           
            # Use targeted feedback for confirmation improvements
            confirmation_feedback = self.state.targeted_feedback.get('confirmation_feedback', {}) if self.state.targeted_feedback else {}


            # Create feedback-enhanced confirmation task
            confirmation_task = self._get_confirmation_agent().create_feedback_enhanced_confirmation_task(
                product_query=self.state.product_query,
                retailer=retailer_name,
                retailer_url=retailer_url,
                validation_feedback=confirmation_feedback,
                attempt_number=self.state.current_attempt
            )

            # Create and execute confirmation crew
            confirmation_crew = Crew(
                agents=[self._get_confirmation_agent().get_agent()],
                tasks=[confirmation_task],
                verbose=self.verbose
            )

            result = confirmation_crew.kickoff()

            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                confirmation_data = result.pydantic.model_dump()
            else:
                # Parse confirmation results safely
                confirmation_data = self._safe_parse_json(result, default={"product": None})

            # Store current retailer product
            self.state.current_retailer_product = confirmation_data.get('product') if isinstance(confirmation_data.get('product'), dict) else None
            self.state.total_attempts += 1

            if self.verbose:
                self.console.print(f"[green]✅ Feedback-Enhanced confirmation: {'1' if self.state.current_retailer_product else '0'} product[/green]")
            
            self.state.confirmation_result = {"action": "validate_products", "product_confirmed": True if self.state.current_retailer_product else False}
            event.emit("validate_products")
            

        except Exception as e:
            error_msg = f"Feedback-enhanced confirmation failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            self.state.confirmation_result = {"action": "error", "error": error_msg}
            event.emit("validate_products")
             

      
    @listen("end")
    def finalize(self) -> Dict[str, Any]:
        """Finalize the product search and prepare results. Terminal method - no routing."""
        try:
       
            if self.verbose:
                self.console.print(f"[blue]🎯 Finalizing Product Search[/blue]")

            # Convert validated products to search results format (robust to unexpected shapes)
            search_results: List[Dict[str, Any]] = []
            for item in (self.state.validated_products or []):
                try:
                    if not isinstance(item, dict):
                        continue
                    name = item.get('product_name') or item.get('name') or ''
                    price = item.get('price') or ''
                    url = item.get('url') or ''
                    retailer = item.get('retailer') or ''
                    search_results.append({
                        "product_name": str(name),
                        "price": str(price),
                        "url": str(url),
                        "retailer": str(retailer),
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception:
                    # Skip malformed entries defensively
                    continue

            # Calculate success rate
            if self.state.total_attempts > 0:
                self.state.success_rate = len(self.state.validated_products) / self.state.total_attempts

            # Store final results
            self.state.search_results = search_results
            self.state.final_results = {
                "search_query": self.state.product_query,
                "results": search_results,
                "metadata": {
                    "retailers_searched": self.state.retailers_searched,
                    "total_attempts": self.state.total_attempts,
                    "success_rate": self.state.success_rate,
                    "completed_at": datetime.now().isoformat()
                }
            } 

            if self.verbose:
                self.console.print(f"[green]🎉 Product search completed[/green]")
                self.console.print(f"[cyan]Found {len(search_results)} products across {self.state.retailers_searched} retailers[/cyan]")

            return {"action": "complete", "products_found": len(search_results)}

        except Exception as e:
            error_msg = f"Finalization failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}

    # Remove the router after finalize to make finalize the terminal method
    # The finalize method will be the natural end point of the flow
