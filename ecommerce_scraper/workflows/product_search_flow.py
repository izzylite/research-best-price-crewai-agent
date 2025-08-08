"""Product Search Flow - CrewAI Flow for product-specific search across UK retailers."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import re
from pydantic import BaseModel, Field

from crewai import Flow, Crew
from crewai.flow.flow import listen, start, router
from rich.console import Console

from ..agents.research_agent import ResearchAgent
from ..agents.extraction_agent import ExtractionAgent
from ..agents.product_search_validation_agent import ProductSearchValidationAgent
from ..schemas.product_search_result import ProductSearchResult, ProductSearchItem
from ..tools.simplified_stagehand_tool import SimplifiedStagehandTool

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
    researched_retailers: List[Dict[str, Any]] = Field(default_factory=list, description="Retailers found by research")
    
    # Extraction results
    current_retailer_products: List[Dict[str, Any]] = Field(default_factory=list, description="Products from current retailer")
    
    # Validation results
    validated_products: List[Dict[str, Any]] = Field(default_factory=list, description="All validated products")
    validation_feedback: Optional[Dict[str, Any]] = Field(None, description="Validation feedback for retries")
    targeted_feedback: Optional[Dict[str, Any]] = Field(None, description="Targeted feedback for both agents")
    
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
    
    Flow: Research → Extract → Validate → [Retry Loop] → Next Retailer → Complete
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize the product search flow."""
        super().__init__()
        self.verbose = verbose
        self.console = Console()
        
        # Initialize agents (will be created on-demand)
        self._research_agent = None
        self._extraction_agent = None
        self._validation_agent = None
        
        # Shared tools and session management
        self._stagehand_tool = None
        self._shared_session_id = None
    
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

        logger.warning("Failed to parse JSON result; returning default")
        return default

    def _get_stagehand_tool(self):
        """Get or create shared Stagehand tool instance."""
        if self._stagehand_tool is None:
            self._stagehand_tool = SimplifiedStagehandTool(
                session_id=self._shared_session_id,
                verbose=self.verbose
            )
        return self._stagehand_tool
    
    def _get_research_agent(self) -> ResearchAgent:
        """Get or create ResearchAgent instance."""
        if self._research_agent is None:
            self._research_agent = ResearchAgent(
                stagehand_tool=self._get_stagehand_tool(),
                verbose=self.verbose
            )
        return self._research_agent
    
    def _get_extraction_agent(self) -> ExtractionAgent:
        """Get or create ExtractionAgent instance."""
        if self._extraction_agent is None:
            self._extraction_agent = ExtractionAgent(
                stagehand_tool=self._get_stagehand_tool(),
                verbose=self.verbose
            )
        return self._extraction_agent
    
    def _get_validation_agent(self) -> ProductSearchValidationAgent:
        """Get or create ProductSearchValidationAgent instance."""
        if self._validation_agent is None:
            self._validation_agent = ProductSearchValidationAgent(
                stagehand_tool=self._get_stagehand_tool(),
                verbose=self.verbose
            )
        return self._validation_agent

    def _generate_targeted_feedback(self, validation_data: Dict[str, Any]):
        """Generate targeted feedback for both ResearchAgent and ExtractionAgent."""
        try:
            current_retailer = self.state.researched_retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('name', 'Unknown')

            # Create targeted feedback task
            feedback_task = self._get_validation_agent().create_targeted_feedback_task(
                search_query=self.state.product_query,
                validation_failures=validation_data.get('validation_failures', []),
                retailer=retailer_name,
                attempt_number=self.state.current_attempt,
                max_attempts=self.state.max_retries,
                session_id=self.state.session_id
            )

            # Create and execute feedback crew
            feedback_crew = Crew(
                agents=[self._get_validation_agent().get_agent()],
                tasks=[feedback_task],
                verbose=self.verbose
            )

            result = feedback_crew.kickoff()

            # Prefer pydantic output; otherwise salvage JSON safely
            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                feedback_data = result.pydantic.model_dump()
            else:
                feedback_data = self._safe_parse_json(result, default={})

            # Store targeted feedback
            self.state.targeted_feedback = feedback_data

            if self.verbose:
                research_priority = feedback_data.get('research_feedback', {}).get('priority', 'low')
                extraction_priority = feedback_data.get('extraction_feedback', {}).get('priority', 'low')
                self.console.print(f"[yellow]📋 Generated Targeted Feedback - Research: {research_priority}, Extraction: {extraction_priority}[/yellow]")

        except Exception as e:
            logger.error(f"Failed to generate targeted feedback: {str(e)}", exc_info=True)
            # Fallback to basic feedback
            self.state.targeted_feedback = {
                "research_feedback": {"should_retry": True, "priority": "medium"},
                "extraction_feedback": {"should_retry": True, "priority": "medium"},
                "retry_strategy": {"recommended_approach": "extraction_first"}
            }

    @start()
    def initialize_search(self) -> Dict[str, Any]:
        """Initialize the product search with input parameters."""
        try:
            if self.verbose:
                self.console.print(f"[blue]🔍 Initializing Product Search[/blue]")
                self.console.print(f"[cyan]Product: {self.state.product_query}[/cyan]")

            # Set shared session ID from state (populated by kickoff)
            self._shared_session_id = self.state.session_id

            if self.verbose:
                self.console.print("[green]✅ Product search initialized[/green]")

            return {"action": "research_retailers", "status": "initialized"}

        except Exception as e:
            error_msg = f"Failed to initialize product search: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}
    
    @listen(initialize_search)
    def research_retailers(self, _init_result: Dict[str, Any]) -> Dict[str, Any]:
        """Research UK retailers that sell the specified product."""
        try:
            if self.verbose:
                self.console.print(f"[blue]🔬 Researching Retailers[/blue]")
            
            # Create retailer research task
            research_task = self._get_research_agent().create_retailer_research_task(
                product_query=self.state.product_query,
                max_retailers=self.state.max_retailers,
                session_id=self.state.session_id
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
            
            # Store researched retailers
            self.state.researched_retailers = research_data.get('retailers', [])
            
            if self.verbose:
                self.console.print(f"[green]✅ Found {len(self.state.researched_retailers)} retailers[/green]")
            
            return {"action": "extract_products", "retailers_found": len(self.state.researched_retailers)}
            
        except Exception as e:
            error_msg = f"Retailer research failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}
    
    @listen(research_retailers)
    def extract_products(self, research_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract products from the current retailer."""
        try:
            if research_result.get("action") == "error":
                return {"action": "error", "error": research_result.get("error")}
            
            # Check if we have retailers to search
            if not self.state.researched_retailers or self.state.current_retailer_index >= len(self.state.researched_retailers):
                return {"action": "finalize", "reason": "no_more_retailers"}
            
            current_retailer = self.state.researched_retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('name', 'Unknown')

            # Get retailer URL, ensuring it's valid
            retailer_url = current_retailer.get('product_url', '')
            if not retailer_url or retailer_url == "Price not available" or not retailer_url.startswith('http'):
                # Fallback to website domain
                website = current_retailer.get('website', '')
                if website:
                    retailer_url = f"https://{website}" if not website.startswith('http') else website
                else:
                    retailer_url = "https://google.com"  # Ultimate fallback
            
            if self.verbose:
                self.console.print(f"[blue]📦 Extracting from {retailer_name}[/blue]")
            
            # Create extraction task
            extraction_task = self._get_extraction_agent().create_product_search_extraction_task(
                product_query=self.state.product_query,
                retailer=retailer_name,
                retailer_url=retailer_url,
                session_id=self.state.session_id
            )
            
            # Create and execute extraction crew
            extraction_crew = Crew(
                agents=[self._get_extraction_agent().get_agent()],
                tasks=[extraction_task],
                verbose=self.verbose
            )
            
            result = extraction_crew.kickoff()

            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                extraction_data = result.pydantic.model_dump()
            else:
                # Parse extraction results safely
                extraction_data = self._safe_parse_json(result, default={"products": []})
            
            # Store current retailer products
            self.state.current_retailer_products = extraction_data.get('products', [])
            self.state.total_attempts += 1
            
            if self.verbose:
                self.console.print(f"[green]✅ Extracted {len(self.state.current_retailer_products)} products[/green]")
            
            return {
                "action": "validate_products", 
                "products_extracted": len(self.state.current_retailer_products),
                "retailer": retailer_name
            }
            
        except Exception as e:
            error_msg = f"Product extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}
    
    @listen(extract_products)
    def validate_products(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted products and provide feedback for retries."""
        try:
            if extraction_result.get("action") == "error":
                return {"action": "error", "error": extraction_result.get("error")}
            
            current_retailer = self.state.researched_retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('name', 'Unknown')
            product_url = current_retailer.get('product_url', current_retailer.get('url', 'Unknown'))
            
            if self.verbose:
                self.console.print(f"[magenta]✅ Validating Products from {retailer_name}[/magenta]")
            
            # Create validation task
            validation_task = self._get_validation_agent().create_product_search_validation_task(
                search_query=self.state.product_query,
                extracted_products=self.state.current_retailer_products,
                retailer=retailer_name,
                retailer_url=product_url,
                attempt_number=self.state.current_attempt,
                max_attempts=self.state.max_retries,
                session_id=self.state.session_id
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
            
            # Store validated products
            validated_products = validation_data.get('validated_products', [])
            self.state.validated_products.extend(validated_products)

            validation_passed = validation_data.get('validation_passed', False)

            # Store validation feedback for potential retries
            self.state.validation_feedback = validation_data.get('feedback', {})

            # If validation failed, generate targeted feedback for both agents
            if not validation_passed and self.state.current_attempt < self.state.max_retries:
                self._generate_targeted_feedback(validation_data)

            if self.verbose:
                self.console.print(f"[green]✅ Validated {len(validated_products)} products[/green]")

            return {"action": "route_after_validation", "validation_passed": validation_passed}
            
        except Exception as e:
            error_msg = f"Product validation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}
    
    @router(validate_products)
    def route_after_validation(self, validation_result: Dict[str, Any]) -> str:
        """Route after validation based on results and retry logic."""
        try:
            if validation_result.get("action") == "error":
                return "finalize"
            
            validation_passed = validation_result.get("validation_passed", False)

            # If extraction produced no products, immediately move to next retailer per spec
            if not self.state.current_retailer_products:
                # Move to next retailer without retries
                self.state.current_retailer_index += 1
                self.state.current_attempt = 1
                self.state.retailers_searched += 1
                
                if self.verbose:
                    self.console.print("[yellow]⏭️ No products extracted; moving to next retailer[/yellow]")
                
                if self.state.current_retailer_index >= len(self.state.researched_retailers):
                    # If we exhausted all retailers and found nothing overall, route to feedback-driven research retry
                    if not self.state.validated_products:
                        if self.verbose:
                            self.console.print("[magenta]🧭 No products found from any retailer; triggering feedback-driven research retry[/magenta]")
                        return "retry_research_with_feedback"
                    return "finalize"
                else:
                    return "extract_products"
            
            # If validation passed or we've reached max retries, move to next retailer
            if validation_passed or self.state.current_attempt >= self.state.max_retries:
                # Move to next retailer
                self.state.current_retailer_index += 1
                self.state.current_attempt = 1
                self.state.retailers_searched += 1
                
                # Check if we have more retailers to process
                if self.state.current_retailer_index >= len(self.state.researched_retailers):
                    return "finalize"
                else:
                    return "extract_products"
            
            # If validation failed and we haven't reached max retries, determine retry strategy
            else:
                self.state.current_attempt += 1

                # Use targeted feedback to determine which agent should retry
                if self.state.targeted_feedback:
                    retry_strategy = self.state.targeted_feedback.get('retry_strategy', {})
                    recommended_approach = retry_strategy.get('recommended_approach', 'extraction_first')

                    research_feedback = self.state.targeted_feedback.get('research_feedback', {})
                    extraction_feedback = self.state.targeted_feedback.get('extraction_feedback', {})

                    research_should_retry = research_feedback.get('should_retry', False)
                    extraction_should_retry = extraction_feedback.get('should_retry', False)

                    if self.verbose:
                        self.console.print(f"[cyan]🎯 Retry Strategy: {recommended_approach}[/cyan]")

                    # Route based on targeted feedback
                    if recommended_approach == "research_first" and research_should_retry:
                        return "retry_research_with_feedback"
                    elif recommended_approach == "extraction_first" and extraction_should_retry:
                        return "retry_extraction_with_feedback"
                    elif recommended_approach == "both_parallel":
                        # For now, do research first then extraction
                        return "retry_research_with_feedback"
                    else:
                        # Default to extraction retry
                        return "retry_extraction_with_feedback"
                else:
                    # Fallback to extraction retry if no targeted feedback
                    return "retry_extraction_with_feedback"
                
        except Exception as e:
            logger.error(f"Routing error: {str(e)}", exc_info=True)
            return "finalize"

    @listen(route_after_validation)
    def retry_research_with_feedback(self, _route_result: Dict[str, Any]) -> Dict[str, Any]:
        """Retry research using targeted validation feedback to improve retailer discovery."""
        try:
            if self.verbose:
                self.console.print(f"[blue]🔬 Retry Research with Feedback (Attempt {self.state.current_attempt})[/blue]")

            # Ensure targeted feedback exists (avoid None)
            if not self.state.targeted_feedback:
                self.state.targeted_feedback = {
                    "research_feedback": {},
                    "extraction_feedback": {},
                    "retry_strategy": {"recommended_approach": "extraction_first"},
                }

            # Create feedback-enhanced research task
            research_task = self._get_research_agent().create_feedback_enhanced_research_task(
                product_query=self.state.product_query,
                validation_feedback=self.state.targeted_feedback,
                attempt_number=self.state.current_attempt,
                max_retailers=self.state.max_retailers,
                session_id=self.state.session_id
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

            # Update researched retailers with improved results (dedupe by product_url)
            improved_retailers = research_data.get('retailers', [])
            if improved_retailers:
                # Replace current retailer with the top improved candidate
                self.state.researched_retailers[self.state.current_retailer_index] = improved_retailers[0]

                # Build set of existing product URLs for dedupe
                existing_urls = set()
                for r in self.state.researched_retailers:
                    url = (r.get('product_url') or '').strip().lower()
                    if url:
                        existing_urls.add(url)

                # Extend with non-duplicate improved retailers
                added = 0
                for r in improved_retailers[1:]:
                    url = (r.get('product_url') or '').strip().lower()
                    if url and url not in existing_urls:
                        self.state.researched_retailers.append(r)
                        existing_urls.add(url)
                        added += 1

            if self.verbose:
                retailer_count = len(improved_retailers)
                self.console.print(f"[green]✅ Improved Research: {retailer_count} better retailers found[/green]")

            return {"action": "extract_products", "research_improved": True}

        except Exception as e:
            error_msg = f"Research retry with feedback failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}

    @listen(route_after_validation)
    def retry_extraction_with_feedback(self, _route_result: Dict[str, Any]) -> Dict[str, Any]:
        """Retry extraction using targeted validation feedback to improve results."""
        try:
            if self.verbose:
                self.console.print(f"[yellow]🔄 Retry Extraction with Feedback (Attempt {self.state.current_attempt})[/yellow]")

            current_retailer = self.state.researched_retailers[self.state.current_retailer_index]
            retailer_name = current_retailer.get('name', 'Unknown')

            # Get retailer URL with fallback logic
            retailer_url = current_retailer.get('product_url', '')
            if not retailer_url or retailer_url == "Price not available" or not retailer_url.startswith('http'):
                website = current_retailer.get('website', '')
                if website:
                    retailer_url = f"https://{website}" if not website.startswith('http') else website
                else:
                    retailer_url = "https://google.com"

            # Use targeted feedback for extraction improvements
            extraction_feedback = self.state.targeted_feedback.get('extraction_feedback', {}) if self.state.targeted_feedback else {}

            # Create feedback-enhanced extraction task
            extraction_task = self._get_extraction_agent().create_feedback_enhanced_extraction_task(
                product_query=self.state.product_query,
                retailer=retailer_name,
                retailer_url=retailer_url,
                validation_feedback=extraction_feedback,
                attempt_number=self.state.current_attempt,
                session_id=self.state.session_id
            )

            # Create and execute extraction crew
            extraction_crew = Crew(
                agents=[self._get_extraction_agent().get_agent()],
                tasks=[extraction_task],
                verbose=self.verbose
            )

            result = extraction_crew.kickoff()

            if hasattr(result, 'pydantic') and getattr(result, 'pydantic') is not None:
                extraction_data = result.pydantic.model_dump()
            else:
                # Parse extraction results safely
                extraction_data = self._safe_parse_json(result, default={"products": []})

            # Store current retailer products
            self.state.current_retailer_products = extraction_data.get('products', [])
            self.state.total_attempts += 1

            if self.verbose:
                product_count = len(self.state.current_retailer_products)
                self.console.print(f"[green]✅ Feedback-Enhanced Extraction: {product_count} products[/green]")

            return {"action": "validate_products", "products_extracted": len(self.state.current_retailer_products)}

        except Exception as e:
            error_msg = f"Feedback-enhanced extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}

    @listen(retry_research_with_feedback)
    def route_after_research_retry(self, retry_result: Dict[str, Any]) -> Dict[str, Any]:
        """Route after research retry - proceed to extraction with improved retailers."""
        if retry_result.get("action") == "error":
            return {"action": "error", "error": retry_result.get("error")}

        # After research retry, proceed to extraction with improved retailers
        return {"action": "extract_products", "research_improved": True}

    @router(route_after_research_retry)
    def route_research_retry_to_extraction(self, research_retry_result: Dict[str, Any]) -> str:
        """Route research retry result to extraction."""
        if research_retry_result.get("action") == "error":
            return "finalize"

        # Proceed to extraction with improved research
        return "extract_products"

    @listen(retry_extraction_with_feedback)
    def validate_extraction_retry_products(self, retry_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate products from feedback-enhanced retry extraction."""
        # This uses the same validation logic as the original validate_products method
        return self.validate_products(retry_result)

    @router(validate_extraction_retry_products)
    def route_after_extraction_retry_validation(self, retry_validation_result: Dict[str, Any]) -> str:
        """Route after extraction retry validation - same logic as original routing."""
        return self.route_after_validation(retry_validation_result)

    @listen(route_after_extraction_retry_validation)
    def finalize(self, _route_result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the product search and prepare results."""
        try:
            if self.verbose:
                self.console.print(f"[blue]🎯 Finalizing Product Search[/blue]")
            
            # Convert validated products to search results format
            search_results = []
            for product in self.state.validated_products:
                search_results.append({
                    "product_name": product.get('product_name', ''),
                    "price": product.get('price', ''),
                    "url": product.get('url', ''),
                    "retailer": product.get('retailer', ''),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Calculate success rate
            if self.state.total_attempts > 0:
                self.state.success_rate = len(self.state.validated_products) / self.state.total_attempts
            
            # Store final results
            self.state.search_results = search_results
            self.state.final_results = {
                "search_query": self.state.product_query,
                "results": search_results,
                "metadata": {
                    "session_id": self.state.session_id,
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
            logger.error(error_msg, exc_info=True)
            return {"action": "error", "error": error_msg}
