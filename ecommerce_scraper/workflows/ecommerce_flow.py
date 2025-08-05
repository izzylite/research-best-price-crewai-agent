"""CrewAI Flow-based Ecommerce Scraping Architecture.

This module implements the recommended CrewAI Flow pattern for ecommerce scraping,
replacing the custom CyclicalProcessor with native CrewAI workflows.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from crewai.flow.flow import Flow, listen, start, router
# from crewai.flow import persist  # Temporarily disabled for testing
from crewai import Crew
from rich.console import Console

from ..agents.navigation_agent import NavigationAgent
from ..agents.extraction_agent import ExtractionAgent
from ..agents.validation_agent import ValidationAgent
from ..schemas.standardized_product import StandardizedProduct
from ..tools.stagehand_tool import EcommerceStagehandTool

logger = logging.getLogger(__name__)


class EcommerceScrapingState(BaseModel):
    """Structured state for ecommerce scraping flow with automatic persistence."""
    
    # Input parameters
    category_url: str = ""
    vendor: str = ""
    category_name: str = ""
    max_pages: Optional[int] = None
    session_id: str = ""
    
    # Processing state
    current_page: int = 1
    products: List[Dict[str, Any]] = Field(default_factory=list)
    total_products_found: int = 0
    
    # Validation and feedback
    validation_feedback: Optional[str] = None
    extraction_attempts: int = 0
    max_extraction_attempts: int = 3
    
    # Progress tracking
    pages_processed: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    
    # Results
    final_products: List[StandardizedProduct] = Field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None


# @persist  # Automatic state persistence using CrewAI's built-in SQLite backend - temporarily disabled for testing
class EcommerceScrapingFlow(Flow[EcommerceScrapingState]):
    """
    CrewAI Flow for ecommerce scraping with cyclical feedback loops.
    
    Flow: Navigation → Extraction → Validation → [Feedback Loop] → Next Page → Complete
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize the ecommerce scraping flow."""
        super().__init__()
        self.verbose = verbose
        self.console = Console()
        
        # Initialize agents (will be created on-demand)
        self._navigation_agent = None
        self._extraction_agent = None
        self._validation_agent = None
        
        # Shared tools and session management
        self._stagehand_tool = None
        self._shared_session_id = None

    def _get_stagehand_tool(self, reuse_session: bool = True) -> EcommerceStagehandTool:
        """Get or create StagehandTool instance with session sharing support."""
        if self._stagehand_tool is None:
            # Create tool with taller viewport (1920x1080) for better extraction coverage
            self._stagehand_tool = EcommerceStagehandTool(
                session_id=self._shared_session_id if reuse_session else None,
                viewport_width=1920,
                viewport_height=1080
            )

            # If this is the first tool creation, capture the session ID for sharing
            if self._shared_session_id is None and reuse_session:
                # Initialize the tool to get session ID
                try:
                    # Force initialization to get session ID
                    self._stagehand_tool._get_stagehand()
                    self._shared_session_id = self._stagehand_tool.get_session_id()
                    if self._shared_session_id and self.verbose:
                        self.console.print(f"[dim]🔗 Session created for sharing: {self._shared_session_id}[/dim]")
                except Exception as e:
                    logger.warning(f"Failed to initialize session for sharing: {e}")

        return self._stagehand_tool
    
    def _get_navigation_agent(self) -> NavigationAgent:
        """Get or create NavigationAgent instance."""
        if self._navigation_agent is None:
            self._navigation_agent = NavigationAgent(
                stagehand_tool=self._get_stagehand_tool(),
                verbose=self.verbose
            )
        return self._navigation_agent
    
    def _get_extraction_agent(self) -> ExtractionAgent:
        """Get or create ExtractionAgent instance."""
        if self._extraction_agent is None:
            self._extraction_agent = ExtractionAgent(
                stagehand_tool=self._get_stagehand_tool(),
                verbose=self.verbose
            )
        return self._extraction_agent
    
    def _get_validation_agent(self) -> ValidationAgent:
        """Get or create ValidationAgent instance."""
        if self._validation_agent is None:
            self._validation_agent = ValidationAgent(
                stagehand_tool=self._get_stagehand_tool(),
                verbose=self.verbose
            )
        return self._validation_agent
    
    @start()
    def initialize_scraping(self) -> Dict[str, Any]:
        """Initialize the scraping session and prepare for navigation."""
        if self.verbose:
            self.console.print(f"[bold green]🚀 Starting Flow-based Scraping[/bold green]")
            self.console.print(f"[cyan]Vendor: {self.state.vendor}[/cyan]")
            self.console.print(f"[cyan]Category: {self.state.category_name}[/cyan]")
            self.console.print(f"[cyan]URL: {self.state.category_url}[/cyan]")
            self.console.print(f"[cyan]Max Pages: {self.state.max_pages or 'All'}[/cyan]")
            self.console.print(f"[cyan]Flow State ID: {self.state.id}[/cyan]")
        
        # Reset processing state for new session
        self.state.current_page = 1
        self.state.pages_processed = 0
        self.state.extraction_attempts = 0
        
        return {
            "action": "navigate",
            "page": self.state.current_page,
            "url": self.state.category_url
        }
    
    @listen(initialize_scraping)
    def navigate_and_prepare(self, _init_result: Dict[str, Any]) -> Dict[str, Any]:
        """NavigationAgent: Handle popups, prepare page for extraction."""
        try:
            if self.verbose:
                self.console.print(f"[blue]🧭 Navigation Phase - Page {self.state.current_page}[/blue]")
            
            # Create navigation task
            navigation_task = self._get_navigation_agent().create_navigation_task(
                vendor=self.state.vendor,
                category_url=self.state.category_url,
                page_number=self.state.current_page
            )
            
            # Create and execute navigation crew
            navigation_crew = Crew(
                agents=[self._get_navigation_agent().get_agent()],
                tasks=[navigation_task],
                verbose=self.verbose
            )
            
            result = navigation_crew.kickoff()
            
            if self.verbose:
                self.console.print("[green]✅ Navigation completed[/green]")
            
            return {
                "action": "extract",
                "navigation_result": result,
                "page": self.state.current_page
            }
            
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            self.state.error_message = f"Navigation failed: {str(e)}"
            return {
                "action": "error",
                "error": str(e)
            }
    
    @listen(navigate_and_prepare)
    def extract_products(self, _nav_result: Dict[str, Any]) -> Dict[str, Any]:
        """ExtractionAgent: Extract product data from the current page using shared session."""
        try:
            if self.verbose:
                self.console.print(f"[yellow]📦 Extraction Phase - Page {self.state.current_page}[/yellow]")
                if self._shared_session_id:
                    self.console.print(f"[dim]🔗 Using shared session: {self._shared_session_id}[/dim]")

            # Create a new Extraction Agent with a tool that reuses the Navigation session
            extraction_stagehand_tool = EcommerceStagehandTool(
                session_id=self._shared_session_id,
                viewport_width=1920,
                viewport_height=1080
            )

            extraction_agent = ExtractionAgent(
                stagehand_tool=extraction_stagehand_tool,
                verbose=self.verbose
            )

            # Create extraction task with feedback if available
            extraction_task = extraction_agent.create_extraction_task(
                vendor=self.state.vendor,
                category=self.state.category_name,
                page_number=self.state.current_page,
                feedback=self.state.validation_feedback
            )

            # Create and execute extraction crew
            extraction_crew = Crew(
                agents=[extraction_agent.get_agent()],
                tasks=[extraction_task],
                verbose=self.verbose
            )
            
            result = extraction_crew.kickoff()
            
            # Parse extracted products
            if hasattr(result, 'products') and result.products:
                extracted_products = result.products
            elif hasattr(result, 'raw') and result.raw:
                # Try to parse from raw output
                extracted_products = self._parse_extraction_result(result.raw)
            else:
                extracted_products = []
            
            # Update state
            self.state.products.extend(extracted_products)
            self.state.total_products_found = len(self.state.products)
            
            if self.verbose:
                self.console.print(f"[green]✅ Extracted {len(extracted_products)} products[/green]")
                self.console.print(f"[cyan]Total products so far: {self.state.total_products_found}[/cyan]")
            
            return {
                "action": "validate",
                "extracted_products": extracted_products,
                "extraction_result": result,
                "page": self.state.current_page
            }
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            self.state.failed_extractions += 1
            return {
                "action": "error",
                "error": str(e)
            }
    
    def _parse_extraction_result(self, raw_result: str) -> List[Dict[str, Any]]:
        """Parse extraction result from raw output."""
        # This is a simplified parser - in practice, the agents should return structured data
        try:
            import json
            if isinstance(raw_result, str) and raw_result.strip().startswith('['):
                return json.loads(raw_result)
            elif isinstance(raw_result, str) and raw_result.strip().startswith('{'):
                parsed = json.loads(raw_result)
                if 'products' in parsed:
                    return parsed['products']
                return [parsed]
            return []
        except Exception as e:
            logger.warning(f"Failed to parse extraction result: {e}")
            return []

    @listen(extract_products)
    @router
    def validate_and_route(self, extraction_result: Dict[str, Any]) -> str:
        """ValidationAgent: Validate products and determine next action."""
        try:
            if extraction_result.get("action") == "error":
                return "handle_error"

            if self.verbose:
                self.console.print(f"[magenta]🔍 Validation Phase - Page {self.state.current_page}[/magenta]")

            # Create validation task
            validation_task = self._get_validation_agent().create_validation_task(
                vendor=self.state.vendor,
                category=self.state.category_name,
                products=extraction_result.get("extracted_products", []),
                page_number=self.state.current_page
            )

            # Create and execute validation crew
            validation_crew = Crew(
                agents=[self._get_validation_agent().get_agent()],
                tasks=[validation_task],
                verbose=self.verbose
            )

            result = validation_crew.kickoff()

            # Parse validation result
            validation_passed = self._parse_validation_result(result)

            if validation_passed:
                self.state.successful_extractions += 1
                self.state.pages_processed += 1
                self.state.extraction_attempts = 0  # Reset for next page

                # Check if we should continue to next page
                if (self.state.max_pages is None or
                    self.state.current_page < self.state.max_pages):

                    # Check if there are more pages available
                    if self._has_more_pages():
                        self.state.current_page += 1
                        return "next_page"
                    else:
                        return "complete"
                else:
                    return "complete"
            else:
                # Validation failed - check if we should retry
                self.state.extraction_attempts += 1

                if self.state.extraction_attempts < self.state.max_extraction_attempts:
                    # Store feedback for re-extraction
                    self.state.validation_feedback = self._get_validation_feedback(result)

                    if self.verbose:
                        self.console.print(f"[yellow]🔄 Re-extraction needed (attempt {self.state.extraction_attempts})[/yellow]")
                        self.console.print(f"[yellow]Feedback: {self.state.validation_feedback}[/yellow]")

                    return "re_extract"
                else:
                    # Max attempts reached, move to next page or complete
                    if self.verbose:
                        self.console.print(f"[red]❌ Max extraction attempts reached for page {self.state.current_page}[/red]")

                    self.state.failed_extractions += 1
                    self.state.pages_processed += 1
                    self.state.extraction_attempts = 0

                    if (self.state.max_pages is None or
                        self.state.current_page < self.state.max_pages):
                        if self._has_more_pages():
                            self.state.current_page += 1
                            return "next_page"

                    return "complete"

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            self.state.error_message = f"Validation failed: {str(e)}"
            return "handle_error"

    def _parse_validation_result(self, result: Any) -> bool:
        """Parse validation result to determine if validation passed."""
        try:
            if hasattr(result, 'validation_passed'):
                return result.validation_passed
            elif hasattr(result, 'raw') and result.raw:
                # Try to parse from raw output
                raw = result.raw.lower()
                return 'valid' in raw or 'passed' in raw or 'success' in raw
            return False
        except Exception as e:
            logger.warning(f"Failed to parse validation result: {e}")
            return False

    def _get_validation_feedback(self, result: Any) -> str:
        """Extract validation feedback for re-extraction."""
        try:
            if hasattr(result, 'feedback'):
                return result.feedback
            elif hasattr(result, 'raw') and result.raw:
                return result.raw
            return "Please improve data extraction quality"
        except Exception as e:
            logger.warning(f"Failed to get validation feedback: {e}")
            return "Please improve data extraction quality"

    def _has_more_pages(self) -> bool:
        """Check if there are more pages to process using NavigationAgent."""
        try:
            # Use NavigationAgent to detect pagination
            nav_agent = self._get_navigation_agent()
            pagination_task = nav_agent.create_pagination_detection_task(
                vendor=self.state.vendor,
                category=self.state.category_name,
                current_page=self.state.current_page
            )

            # Create and execute pagination detection crew
            from crewai import Crew
            pagination_crew = Crew(
                agents=[nav_agent.get_agent()],
                tasks=[pagination_task],
                verbose=False  # Keep quiet for pagination checks
            )

            result = pagination_crew.kickoff()

            # Parse pagination result
            import json
            if hasattr(result, 'raw'):
                pagination_data = json.loads(result.raw)
            else:
                pagination_data = json.loads(str(result))

            # Check if more pages are available
            pagination_info = pagination_data.get('pagination_info', {})
            has_more = pagination_info.get('has_more_pages', False)

            if self.verbose:
                self.console.print(f"[dim]📄 Pagination check: {has_more}[/dim]")

            return has_more

        except Exception as e:
            logger.warning(f"Failed to check for more pages: {e}")
            # Default to False to prevent infinite pagination
            return False

    @listen("next_page")
    def navigate_next_page(self) -> Dict[str, Any]:
        """Navigate to the next page and continue extraction."""
        try:
            if self.verbose:
                self.console.print(f"[blue]📄 Moving to page {self.state.current_page}[/blue]")

            # Clear validation feedback for new page
            self.state.validation_feedback = None

            # Use NavigationAgent to handle pagination navigation
            nav_agent = self._get_navigation_agent()
            pagination_task = nav_agent.create_pagination_detection_task(
                vendor=self.state.vendor,
                category=self.state.category_name,
                current_page=self.state.current_page - 1  # Previous page since we already incremented
            )

            # Create and execute pagination crew
            from crewai import Crew
            pagination_crew = Crew(
                agents=[nav_agent.get_agent()],
                tasks=[pagination_task],
                verbose=self.verbose
            )

            result = pagination_crew.kickoff()

            if self.verbose:
                self.console.print("[green]✅ Pagination navigation completed[/green]")

            # After pagination navigation, we need to prepare the new page
            return self.navigate_and_prepare({
                "action": "navigate",
                "page": self.state.current_page,
                "url": self.state.category_url
            })

        except Exception as e:
            logger.error(f"Failed to navigate to next page: {e}")
            return {
                "action": "error",
                "error": str(e)
            }

    @listen("re_extract")
    def re_extract_with_feedback(self) -> Dict[str, Any]:
        """Re-extract products with validation feedback."""
        if self.verbose:
            self.console.print(f"[yellow]🔄 Re-extracting with feedback[/yellow]")

        return {
            "action": "extract",
            "page": self.state.current_page,
            "feedback": self.state.validation_feedback
        }

    @listen("complete")
    def finalize_results(self) -> Dict[str, Any]:
        """Finalize scraping results and prepare output."""
        try:
            if self.verbose:
                self.console.print("[bold green]🎉 Scraping completed![/bold green]")
                self.console.print(f"[cyan]Total pages processed: {self.state.pages_processed}[/cyan]")
                self.console.print(f"[cyan]Total products found: {self.state.total_products_found}[/cyan]")
                self.console.print(f"[cyan]Successful extractions: {self.state.successful_extractions}[/cyan]")
                self.console.print(f"[cyan]Failed extractions: {self.state.failed_extractions}[/cyan]")

            # Convert products to StandardizedProduct objects
            standardized_products = []
            for product_data in self.state.products:
                try:
                    if isinstance(product_data, dict):
                        product = StandardizedProduct(**product_data)
                        standardized_products.append(product)
                    elif isinstance(product_data, StandardizedProduct):
                        standardized_products.append(product_data)
                except Exception as e:
                    logger.warning(f"Failed to standardize product: {e}")
                    continue

            self.state.final_products = standardized_products
            self.state.success = True

            # Create final result
            result = {
                "success": True,
                "products": standardized_products,
                "session_id": self.state.id,
                "vendor": self.state.vendor,
                "category": self.state.category_name,
                "statistics": {
                    "total_pages_processed": self.state.pages_processed,
                    "total_products_found": len(standardized_products),
                    "successful_extractions": self.state.successful_extractions,
                    "failed_extractions": self.state.failed_extractions,
                    "extraction_success_rate": (
                        self.state.successful_extractions /
                        max(1, self.state.successful_extractions + self.state.failed_extractions)
                    ) * 100
                }
            }

            if self.verbose:
                success_rate = result["statistics"]["extraction_success_rate"]
                self.console.print(f"[green]✅ Success rate: {success_rate:.1f}%[/green]")

            return result

        except Exception as e:
            logger.error(f"Failed to finalize results: {str(e)}")
            self.state.error_message = f"Finalization failed: {str(e)}"
            self.state.success = False

            return {
                "success": False,
                "error": str(e),
                "session_id": self.state.id,
                "vendor": self.state.vendor,
                "category": self.state.category_name
            }

    @listen("handle_error")
    def handle_error(self) -> Dict[str, Any]:
        """Handle errors and return error result."""
        if self.verbose:
            self.console.print(f"[red]❌ Error occurred: {self.state.error_message}[/red]")

        self.state.success = False

        return {
            "success": False,
            "error": self.state.error_message,
            "session_id": self.state.id,
            "vendor": self.state.vendor,
            "category": self.state.category_name,
            "products": self.state.final_products,
            "statistics": {
                "total_pages_processed": self.state.pages_processed,
                "total_products_found": self.state.total_products_found,
                "successful_extractions": self.state.successful_extractions,
                "failed_extractions": self.state.failed_extractions
            }
        }

    def cleanup(self):
        """Clean up resources."""
        try:
            if self._stagehand_tool:
                self._stagehand_tool.close()

            if self.verbose:
                self.console.print("[dim]🧹 Flow resources cleaned up[/dim]")

        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        return False
