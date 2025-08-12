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
from ..utils.list_utils import (
    dedupe_preserve_order,
    existing_urls,
    append_unique_by_url,
    restore_product_fields_from_research,
)
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
    backfill_attempt: int = Field(1, description="Current attempt number for result backfill")
    
    # Research results
    retailers: List[Dict[str, Any]] = Field(default_factory=list, description="Retailers discovered for confirmation (vendor,url,price)") 
    # confirmation results
    current_retailer_product: Optional[Dict[str, Any]] = Field(default=None, description="Single confirmed product for current retailer")
    
    # Validation results
    validated_products: List[Dict[str, Any]] = Field(default_factory=list, description="All validated products")
    validated_product: Optional[Dict[str, Any]] = Field(default=None, description="Last validated product")
    validation_feedback: Optional[Dict[str, Any]] = Field(None, description="Validation feedback for retries")
    targeted_feedback: Optional[Dict[str, Any]] = Field(None, description="Targeted feedback for both agents")
    excluded_urls: List[str] = Field(default_factory=list, description="Excluded URLs")
    
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
        # Centralized event names to avoid typos
        class _Events:
            RESEARCH_RETAILERS = "research_retailers"
            CONFIRM_PRODUCTS = "confirm_products"
            VALIDATE_PRODUCTS = "validate_products"
            NEXT_PRODUCT = "next_product"
            RETRY_RESEARCH_WITH_FEEDBACK = "retry_research_with_feedback"
            RETRY_CONFIRMATION_WITH_FEEDBACK = "retry_confirmation_with_feedback"
            END = "end"

        self.Events = _Events
        
        # Initialize agents (will be created on-demand)
        self._research_agent = None
        self._confirmation_agent = None
        self._validation_agent = None
        self._feedback_agent = None
         

        # Map event names to bound handlers for local fallback emission (payload-aware)
        self._local_event_handlers = {
            self.Events.RESEARCH_RETAILERS: lambda adapter, payload=None: self.research_retailers(adapter, payload),
            self.Events.CONFIRM_PRODUCTS: lambda adapter, payload=None: self.confirm_products(adapter, payload),
            self.Events.VALIDATE_PRODUCTS: lambda adapter, payload=None: self.validate_products(adapter, payload),
            self.Events.NEXT_PRODUCT: lambda adapter, payload=None: self.next_product(adapter, payload),
            self.Events.RETRY_RESEARCH_WITH_FEEDBACK: lambda adapter, payload=None: self.retry_research_with_feedback(adapter, payload),
            self.Events.RETRY_CONFIRMATION_WITH_FEEDBACK: lambda adapter, payload=None: self.retry_confirmation_with_feedback(adapter, payload),
            self.Events.END: lambda adapter, payload=None: self.finalize(payload),
        }

    def _create_local_event_adapter(self):
        """Create a minimal event adapter to drive the flow when framework context isn't provided."""
        flow = self

        class _Adapter:
            def emit(self_inner, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
                handler = flow._local_event_handlers.get(str(name))
                if handler is not None:
                    # Centralized payload→state merge to avoid duplication in handlers
                    if isinstance(payload, dict) and payload:
                        try:
                            for k, v in payload.items():
                                setattr(flow.state, k, v)
                        except Exception:
                            pass
                    try:
                        handler(self_inner, payload)
                    except TypeError:
                        # Backward compatibility: call without payload if handler doesn't accept it
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
        deduped_urls = dedupe_preserve_order(exclude_urls)

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
            "exclude_domains": dedupe_preserve_order(exclude_domains),
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
        existing_urls_set = existing_urls(self.state.retailers or [])


        def append_unique(retailers_list: List[Dict[str, Any]], candidates: List[Dict[str, Any]]):
            append_unique_by_url(retailers_list, candidates, max_items=self.state.max_retailers)

        # Validate index before replacement to prevent IndexError
        if self.state.retailers and self.state.current_retailer_index < len(self.state.retailers):
            # Replace current item
            self.state.retailers[self.state.current_retailer_index] = improved_retailers[0]
            # Rebuild existing URLs because we replaced current
            # Rebuild uniqueness cache not needed; append_unique_by_url handles it
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

    def _generate_static_feedback(
        self,
        feedback_type: str = "research",
        focus: str = "Search broadly for legitimate UK retailers that directly sell the product. Avoid comparison/affiliate sites. Provide direct product URLs and prices. Use closely related keywords to the product name.",
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """Return static feedback for either research or confirmation flows.

        feedback_type:
          - "research": produce research-first guidance
          - "confirmation": produce confirmation-first guidance (includes current retailer name when available)
        """
        try:
            feedback_type_norm = (feedback_type or "research").strip().lower()
            if feedback_type_norm == "confirmation":
                current_retailer = {}
                if self.state.retailers and self.state.current_retailer_index < len(self.state.retailers):
                    current_retailer = self.state.retailers[self.state.current_retailer_index] or {}
                retailer_name = current_retailer.get('vendor', 'Unknown')
                return {
                    "research_feedback": {"should_retry": False, "priority": "low"},
                    "confirmation_feedback": {
                        "should_retry": True,
                        "priority": priority,
                        "hints": {
                            "retailer": retailer_name,
                            "focus": focus,
                        },
                    },
                    "retry_strategy": {"recommended_approach": "confirmation_first"},
                }
            # Default to research feedback
            return {
                "research_feedback": {
                    "should_retry": True,
                    "priority": priority,
                    "hints": {"focus": focus},
                },
                "confirmation_feedback": {"should_retry": False, "priority": "low"},
                "retry_strategy": {"recommended_approach": "research_first"},
            }
        except Exception:
            # Safe default
            if feedback_type == "confirmation":
                return {
                    "research_feedback": {"should_retry": False, "priority": "low"},
                    "confirmation_feedback": {"should_retry": True, "priority": "medium"},
                    "retry_strategy": {"recommended_approach": "confirmation_first"},
                }
            return {
                "research_feedback": {"should_retry": True, "priority": "medium"},
                "confirmation_feedback": {"should_retry": False, "priority": "low"},
                "retry_strategy": {"recommended_approach": "research_first"},
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
                self._create_local_event_adapter().emit(self.Events.END)
                return

            # Kick off event-driven flow. Use framework event if provided, otherwise a local adapter.
            if event is not None:
                event.emit(self.Events.RESEARCH_RETAILERS)
            else:
                self._create_local_event_adapter().emit(self.Events.RESEARCH_RETAILERS)
            return {"action": self.Events.RESEARCH_RETAILERS, "status": "initialized"}

        except Exception as e:
            error_msg = f"Failed to initialize product search: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True)
            event.emit(self.Events.END)
    
    def increment_retailer_index(self) -> bool:
        """Increment the retailer index and reset the attempt number.

        Returns:
            bool: True if there are more retailers to process, False if we've reached the end
        """
        self.state.current_retailer_index += 1 
        self.state.retailers_searched += 1
        # Clear feedback between retailers to avoid stale guidance
        self.state.targeted_feedback = None
        self.state.validation_feedback = None
        self.state.current_retailer_product = None

        # Boundary check: return False if we've exceeded the retailers list OR max_retailers limit
        has_more_in_list = self.state.current_retailer_index < len(self.state.retailers)
        within_max_limit = self.state.retailers_searched < self.state.max_retailers
        has_more = has_more_in_list and within_max_limit
        if not has_more:
            self.state.current_attempt = 1
        return has_more
 

    def has_more_retailers(self) -> bool:
        """Check if there are more retailers to process.

        Returns:
            bool: True if there are more retailers, False otherwise
        """
        return self.state.current_retailer_index < len(self.state.retailers)

    def handle_error_with_feedback(self, feedback_type: str, error_msg: str, route: str = "end") -> str:
                """Handle error by generating targeted feedback and emitting the appropriate event."""
                if self.state.current_attempt < self.state.max_retries:
                    self.state.targeted_feedback = self._generate_static_feedback(
                        feedback_type=feedback_type,
                        focus=error_msg
                    )
                    return self.handle_retry()
                else:
                    return route
           
    
    def research_retailers(self, event, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Research UK retailers that sell the specified product."""
        try:
            # Block early if no LLM provider is configured to avoid noisy auth errors
            if not self._llm_available():
                msg = (
                    "Cannot run research: no LLM API key configured. Set OPENAI_API_KEY, "
                    "PERPLEXITY_API_KEY, or ANTHROPIC_API_KEY."
                )
                self.error_logger.error(msg) 
                event.emit(self.Events.END)
                return
            if self.verbose:
                self.console.print(f"[blue]🔬 Researching Retailers[/blue]")
            
            # Create retailer research task
            research_task = self._get_research_agent().create_retailer_research_task(
                product_query=self.state.product_query,
                max_retailers=self.state.max_retailers,
                backfill_attempt=self.state.backfill_attempt
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
            
            # Continue to confirmation step using payload instead of state flags
            event.emit(self.Events.CONFIRM_PRODUCTS, {"retailers_found": len(self.state.retailers)})
        except Exception as e:
            error_msg = f"Retailer research failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True) 
            event.emit(self.handle_error_with_feedback("research", error_msg))
           

    def confirm_products(self, event, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """confirm products from the current retailer."""
        try:
            # If upstream wanted to route to error, rely on payload/state merge above.
            
            if not self.state.retailers: 
                event.emit(self.Events.VALIDATE_PRODUCTS, {"reason": "empty_retailers"})
                return

            if self.state.current_retailer_index >= len(self.state.retailers): 
                event.emit(self.Events.VALIDATE_PRODUCTS, {"reason": "no_more_retailers"})
                return
            
            
            
            current_retailer = self.state.retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('vendor', 'Unknown')
            retailer_price = current_retailer.get('price')
            retailer_url = current_retailer.get('url', '')
            retailer_product_name = current_retailer.get('name', '')

            # Priority bypass: add directly to validated products and skip agents
            if current_retailer.get('priority') is True:
                try:
                    # De-duplicate by URL before appending
                    if retailer_url:
                        existing = existing_urls(self.state.validated_products or [])
                        if retailer_url not in existing:
                            self.state.validated_products.append({
                                "product_name": str(self.state.product_query or retailer_product_name or ''),
                                "name": str(retailer_product_name or ''),
                                "price": str(retailer_price or ''),
                                "url": str(retailer_url or ''),
                                "retailer": str(retailer_name),
                                "availability": str(current_retailer.get('availability') or ''),
                            })
                except Exception:
                    pass
                event.emit(self.Events.VALIDATE_PRODUCTS, {"reason": "priority_bypass"})
                return

            # Get retailer URL; if invalid/missing, skip to next or finalize
            retailer_url = current_retailer.get('url', '')

            if not retailer_url or not retailer_url.startswith('http'): 
                event.emit(self.Events.VALIDATE_PRODUCTS, {"reason": "invalid_retailer_url"})
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
            
            # Store single confirmed product and restore fields from research when needed
            product_obj = confirmation_data.get('product')
            self.state.current_retailer_product = (
                product_obj if isinstance(product_obj, dict) else None
            )
            if isinstance(self.state.current_retailer_product, dict):
                try:
                    self.state.current_retailer_product = restore_product_fields_from_research(
                        self.state.current_retailer_product, current_retailer
                    )
                except Exception:
                    pass
             
            
            if self.verbose:
                self.console.print(f"[green]✅ Confirmed {'1' if self.state.current_retailer_product else '0'} product[/green]")
            
            event.emit(self.Events.VALIDATE_PRODUCTS, {
                "product_confirmed": True if self.state.current_retailer_product else False,
                "retailer": retailer_name
            })
            
        except Exception as e:
            error_msg = f"Product confirmation failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True) 
            event.emit(self.handle_error_with_feedback("confirmation", error_msg))

    def validate_products(self, event, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate confirmed products and provide feedback for retries."""
        try:
            # Handle simple skip reasons via payload
            reason = payload.get("reason") if isinstance(payload, dict) else None
            if reason in {"priority_bypass", "invalid_retailer_url", "empty_retailers", "no_more_retailers"}:
                if reason == "priority_bypass":
                    event.emit(self.Events.NEXT_PRODUCT)
                    return
                if reason in {"empty_retailers", "no_more_retailers"}:
                    self.state.current_retailer_product = None
                    if reason == "no_more_retailers":
                        self.state.current_retailer_index = len(self.state.retailers)
                        event.emit(self.Events.END)
                        return
                    if reason == "empty_retailers":
                        if self.state.current_attempt < self.state.max_retries:
                            event.emit(self.handle_retry())
                        else:
                            event.emit(self.Events.NEXT_PRODUCT)
                        return
                # default skip → next
                event.emit(self.Events.NEXT_PRODUCT)
                return
            
            if payload.get("action") == "skipped":
                event.emit(self.Events.NEXT_PRODUCT)
                return

            # Handle terminal/empty cases from confirmation safely before any indexing
            if payload.get("action") == "finalize":
                reason = payload.get("reason")
                self.state.current_retailer_product = None
                if reason == "no_more_retailers":
                    # We have exhausted the retailer list; finalize immediately
                    self.state.current_retailer_index = len(self.state.retailers)
                    self.state.validation_result = {"action": self.Events.END, "reason": "no_more_retailers"} 
                    event.emit(self.Events.END)
                    return
                   
                elif reason == "empty_retailers":
                    # No retailers found; trigger retry or end immediately
                    self.state.validation_result = {"action": "route_after_validation", "validation_passed": False, "reason": "empty_retailers"}
                    if self.state.current_attempt < self.state.max_retries:
                        event.emit(self.handle_retry())
                    else:
                        event.emit(self.Events.NEXT_PRODUCT)
                    return

           

            # Use product URL from the confirmed product; do not rely on current retailer here
            # This ensures we validate exactly what was confirmed
            if not self.state.current_retailer_product:
                # Generate feedback and retry confirmation with explicit guidance
                self.state.targeted_feedback = self._generate_static_feedback(
                    feedback_type="confirmation",
                    priority="high",
                    focus="Return a product object with a valid url and price. Avoid category/search pages."
                )
                event.emit(self.handle_retry())
                return

            # Extract confirmed product details
            product_name = self.state.current_retailer_product.get('name', '')
            product_url = self.state.current_retailer_product.get('url', '')
            product_price = self.state.current_retailer_product.get('price', '')
            # Use retailer from payload when provided
            retailer_name = (payload or {}).get('retailer') or ''
            
            if not product_url or not product_url.startswith('http'):
                # Exclude problematic URL if present
                if isinstance(product_url, str) and product_url:
                    self.state.excluded_urls.append(product_url)
                self.state.targeted_feedback = self._generate_static_feedback(
                    feedback_type="confirmation",
                    priority="high",
                     focus="Ensure the product URL is included in the result."
                      if not product_url else "{product_url} is not a valid URL. Ensure the product URL is valid.")
                event.emit(self.handle_retry())
                return

            if not retailer_name: 
                self.state.targeted_feedback = self._generate_static_feedback(
                    feedback_type="confirmation",
                    priority="high",
                    focus="Ensure the retailer name is included in the result."
                )
                event.emit(self.handle_retry())
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
                # Backfill price from research result when missing or marked unavailable
                try:
                    price_value = self.state.validated_product.get('price')
                    price_str = str(price_value).strip() if price_value is not None else "" 
                    if (not price_str) or (price_str.lower() == "price unavailable"): 
                        if isinstance(product_price, str) and product_price.strip():
                            self.state.validated_product['price'] = product_price.strip()
                except Exception:
                    pass

                # Backfill availability from confirmation or research when missing
                try:
                    availability_value = self.state.validated_product.get('availability')
                    if not isinstance(availability_value, str) or not availability_value.strip():
                        source_availability = (self.state.current_retailer_product or {}).get('availability') or \
                                               ((self.state.retailers[self.state.current_retailer_index] or {}).get('availability') if (self.state.retailers and self.state.current_retailer_index < len(self.state.retailers)) else None)
                        if isinstance(source_availability, str) and source_availability.strip():
                            self.state.validated_product['availability'] = source_availability.strip()
                except Exception:
                    pass

                if not self.state.validated_product.get('price'):
                    self.state.targeted_feedback = self._generate_static_feedback(
                        feedback_type="research",
                        priority="high",
                        focus="""Ensure the product price is included in the result.
                        PRODUCT INFORMATION:
                        product_name: {product_name}
                        product_url: {product_url}
                        retailer_name: {retailer_name}
                        retailer_url: {retailer_url}
                         """
                    )
                    event.emit(self.handle_retry())
                    return
                # De-duplicate by URL before appending
                try:
                    new_url = (self.state.validated_product or {}).get('url')
                    existing = existing_urls(self.state.validated_products or [])
                    if not new_url or new_url not in existing:
                        self.state.validated_products.append(self.state.validated_product)
                except Exception:
                    self.state.validated_products.append(self.state.validated_product)
           

            validation_passed = validation_data.get('validation_passed', False) 
            
            # Store validation feedback for potential retries
            self.state.validation_feedback = validation_data.get('feedback', {})

            # If validation failed, generate targeted feedback for both agents
            if not validation_passed and self.state.current_attempt < self.state.max_retries:
                self.state.excluded_urls.append(product_url)
                self._generate_targeted_feedback(validation_data)
                # Immediately route based on feedback and return to avoid duplicate routing below
                event.emit(self.handle_retry())
                return

            if self.verbose:
                self.console.print(f"[green]✅ Validated {'1' if self.state.validated_product else '0'} product[/green]")

            # If we reach here, either validation passed, or attempts exhausted
            event.emit(self.Events.NEXT_PRODUCT, {"validation_passed": validation_passed})
            return
            
        except Exception as e:
            error_msg = f"Product validation failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True) 
            event.emit(self.Events.END)

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
                return self.Events.RETRY_RESEARCH_WITH_FEEDBACK
            elif recommended_approach == "confirmation_first" and confirmation_should_retry:
                return self.Events.RETRY_CONFIRMATION_WITH_FEEDBACK
            elif recommended_approach == "both_parallel":
                # For now, do research first then confirmation
                return self.Events.RETRY_RESEARCH_WITH_FEEDBACK
            else:
                # Default to confirmation retry
                return self.Events.RETRY_CONFIRMATION_WITH_FEEDBACK
        else: 
            self.state.targeted_feedback = self._generate_feedback_for_empty_retailers()
            return self.Events.RETRY_RESEARCH_WITH_FEEDBACK

    def next_product(self,event, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Move to the next product/retailer or finalize if done."""
        try:
            # Increment index and reset attempt count
            has_more = self.increment_retailer_index()

            if not has_more:
                # If we have no validated products and retries left, retry; else finalize
                if not self.state.validated_products and self.state.current_attempt < self.state.max_retries:
                        event.emit(self.handle_retry())
                # If we have less than max_retailers and backfill_attempt is less than 2, retry research
                elif len(self.state.validated_products) < self.state.max_retailers and self.state.backfill_attempt < 2:
                    self.state.backfill_attempt += 1
                    event.emit(self.Events.RESEARCH_RETAILERS)
                else:
                    event.emit(self.Events.END)
                return

            # Move to confirmation step for the next retailer/product
            event.emit(self.Events.CONFIRM_PRODUCTS)
            return

        except Exception as e:
            error_msg = f"Failed to move to next product: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True) 
            event.emit("end")



    def retry_research_with_feedback(self,event, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retry research using targeted validation feedback to improve retailer discovery."""
        try:
            if self.verbose:
                self.console.print(f"[blue]🔬 Retry Research with Feedback (Attempt {self.state.current_attempt})[/blue]")

            # Ensure targeted feedback exists (avoid None/empty). Auto-generate fallback when missing.
            if not self.state.targeted_feedback or not isinstance(self.state.targeted_feedback, dict) or not self.state.targeted_feedback:
                self.state.targeted_feedback = self._generate_static_feedback(feedback_type="research")

            # Create feedback-enhanced research task
            exclusions = self._build_research_exclusions()
            research_task = self._get_research_agent().create_feedback_enhanced_research_task(
                product_query=self.state.product_query,
                validation_feedback=self.state.targeted_feedback,
                attempt_number=self.state.current_attempt,
                max_retailers=self.state.max_retailers, 
                exclude_urls=exclusions.get("exclude_urls", []),
                exclude_domains=exclusions.get("exclude_domains", []),
                backfill_attempt=self.state.backfill_attempt
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
            self.state.research_result = {"action": self.Events.CONFIRM_PRODUCTS, "research_improved": True}
            event.emit(self.Events.CONFIRM_PRODUCTS)
            

        except Exception as e:
            error_msg = f"Research retry with feedback failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True) 
            event.emit(self.handle_error_with_feedback("research", error_msg, self.Events.NEXT_PRODUCT))
            

 

    def retry_confirmation_with_feedback(self,event, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retry confirmation using targeted validation feedback to improve results."""
        try:
            if self.verbose:
                self.console.print(f"[yellow]🔄 Retry confirmation with Feedback (Attempt {self.state.current_attempt})[/yellow]")

            # Ensure targeted feedback exists; auto-generate confirmation-focused feedback if missing
            if not self.state.targeted_feedback or not isinstance(self.state.targeted_feedback, dict) or not self.state.targeted_feedback:
                self.state.targeted_feedback = self._generate_static_feedback(feedback_type="confirmation",
                focus="Navigate to a specific product detail page, avoid category/search pages, avoid comparison sites.")

            if not self.state.retailers:
                event.emit("validate_products", {"reason": "empty_retailers"})
                return

            if self.state.current_retailer_index >= len(self.state.retailers):
                event.emit("validate_products", {"reason": "no_more_retailers"})
                return
            
            
            
            current_retailer = self.state.retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('vendor', 'Unknown')
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

            # Store current retailer product and restore fields from research when needed
            self.state.current_retailer_product = (
                confirmation_data.get('product')
                if isinstance(confirmation_data.get('product'), dict)
                else None
            )
            if isinstance(self.state.current_retailer_product, dict):
                try:
                    self.state.current_retailer_product = restore_product_fields_from_research(
                        self.state.current_retailer_product, current_retailer
                    )
                except Exception:
                    pass

            if self.verbose:
                self.console.print(f"[green]✅ Feedback-Enhanced confirmation: {'1' if self.state.current_retailer_product else '0'} product[/green]")
            
            event.emit("validate_products", {"product_confirmed": True if self.state.current_retailer_product else False})
            

        except Exception as e:
            error_msg = f"Feedback-enhanced confirmation failed: {str(e)}"
            self.error_logger.error(error_msg, exc_info=True) 
            event.emit(self.handle_error_with_feedback("confirmation", error_msg, self.Events.NEXT_PRODUCT))
             

      
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
                    availability = item.get('availability') or ''
                    search_results.append({
                        "product_name": str(name),
                        "price": str(price),
                        "url": str(url),
                        "retailer": str(retailer),
                        "availability": str(availability),
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
            

    # Remove the router after finalize to make finalize the terminal method
    # The finalize method will be the natural end point of the flow
