"""CrewAI Flow-based Ecommerce Scraper - Main Module.

This module implements the CrewAI Flow architecture for ecommerce scraping with
multi-agent coordination, automatic routing, and state management.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is available for CrewAI
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

from rich.console import Console

# CrewAI Flow architecture imports
from .workflows.ecommerce_flow import EcommerceScrapingFlow
from .workflows.flow_utils import FlowResultProcessor

from .schemas.standardized_product import StandardizedProduct
from .ai_logging.ai_logger import get_ai_logger, close_ai_logger
from .utils.crewai_setup import ensure_crewai_directories

logger = logging.getLogger(__name__)

class ScrapingResult:
    """Container for scraping results."""

    def __init__(self, success: bool, products: List[StandardizedProduct] = None,
                 error: str = None, session_id: str = None, vendor: str = None,
                 category: str = None, statistics: Dict = None):
        """Initialize scraping result."""
        self.success = success
        self.products = products or []
        self.error = error
        self.session_id = session_id
        self.vendor = vendor
        self.category = category
        self.statistics = statistics or {}

class EcommerceScraper:
    """CrewAI Flow-based ecommerce scraper."""

    def __init__(self,
                 verbose: bool = True,
                 session_id: Optional[str] = None):
        """Initialize the scraper with CrewAI Flow architecture."""
        self.verbose = verbose
        self.console = Console()

        # Create session ID for this scraping run
        self.session_id = session_id or f"flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Ensure CrewAI directories exist
        ensure_crewai_directories("lastAttempt")

        self.ai_logger = get_ai_logger(self.session_id)

        if self.verbose:
            self.console.print(f"[bold blue]🔍 AI Logging enabled for session: {self.session_id}[/bold blue]")
            self.console.print(f"[cyan]📁 Logs will be saved to: logs/{self.session_id}/[/cyan]")

        # Flow instance will be created per scraping session
        self._current_flow = None

        if self.verbose:
            self.console.print("[bold green]🚀 CrewAI Flow Architecture Ready[/bold green]")



    def scrape_category(self,
                       category_url: str,
                       vendor: str,
                       category_name: str,
                       max_pages: Optional[int] = None) -> ScrapingResult:
        """
        Scrape a category using the CrewAI Flow architecture.

        Args:
            category_url: Direct URL to the category page to scrape
            vendor: Vendor name (e.g., 'asda', 'tesco')
            category_name: Human-readable category name
            max_pages: Maximum pages to scrape per category (None = all pages)

        Returns:
            DynamicScrapingResult with products and metadata
        """
        try:
            if self.verbose:
                self.console.print(f"[bold green]🚀 CrewAI Flow Scraping: {vendor}/{category_name}[/bold green]")
                self.console.print(f"[cyan]URL: {category_url}[/cyan]")
                self.console.print(f"[cyan]Max pages: {max_pages or 'All available'}[/cyan]")

            # Create Flow instance with initial state
            flow = EcommerceScrapingFlow(verbose=self.verbose)
            self._current_flow = flow

            # Set up initial state
            flow_inputs = {
                "category_url": category_url,
                "vendor": vendor,
                "category_name": category_name,
                "max_pages": max_pages,
                "session_id": self.session_id
            }

            if self.verbose:
                self.console.print(f"[cyan]🔄 Starting Flow execution...[/cyan]")

            # Execute the Flow
            flow.kickoff(inputs=flow_inputs)

            # Process Flow result
            if hasattr(flow, 'state') and flow.state:
                final_state = flow.state

                # Get products from final_products or fallback to raw products
                final_products = getattr(final_state, 'final_products', [])
                raw_products = getattr(final_state, 'products', [])
                success = getattr(final_state, 'success', False)

                # Use raw products if finalization failed
                if not final_products and raw_products:
                    if self.verbose:
                        self.console.print(f"[yellow]⚠️ Using raw products ({len(raw_products)}) as finalization failed[/yellow]")
                    final_products = raw_products
                    success = True

                # Create result
                result = ScrapingResult(
                    success=success,
                    products=final_products,
                    error=getattr(final_state, 'error_message', None),
                    session_id=self.session_id,
                    vendor=vendor,
                    category=category_name,
                    statistics={
                        "total_pages_processed": getattr(final_state, 'pages_processed', 0),
                        "total_products_found": len(final_products),
                        "successful_extractions": getattr(final_state, 'successful_extractions', 0),
                        "failed_extractions": getattr(final_state, 'failed_extractions', 0)
                    }
                )

                # Save results
                if result.success and result.products:
                    result_dict = {
                        "success": result.success,
                        "products": result.products,
                        "error": result.error,
                        "session_id": result.session_id,
                        "vendor": result.vendor,
                        "category": result.category,
                        "statistics": result.statistics
                    }
                    saved_path = FlowResultProcessor.save_flow_results(
                        result_dict, vendor, category_name
                    )
                    if saved_path and self.verbose:
                        self.console.print(f"[green]✅ Results saved to: {saved_path}[/green]")

                return result
            else:
                # Flow failed to produce state
                return ScrapingResult(
                    success=False,
                    error="Flow completed but no state available",
                    session_id=self.session_id,
                    vendor=vendor,
                    category=category_name
                )

        except Exception as e:
            logger.error(f"Flow scraping failed: {str(e)}")

            return ScrapingResult(
                success=False,
                error=str(e),
                session_id=self.session_id,
                vendor=vendor,
                category=category_name
            )
        finally:
            # Cleanup Flow resources
            if self._current_flow:
                try:
                    self._current_flow.cleanup()
                except Exception as cleanup_error:
                    logger.warning(f"Flow cleanup failed: {cleanup_error}")
                finally:
                    self._current_flow = None

    def get_architecture_info(self) -> Dict[str, Any]:
        """Get information about the current architecture configuration."""
        return {
            "architecture_type": "crewai_flow",
            "session_id": self.session_id,
            "components": {
                "current_flow": self._current_flow is not None,
                "flow_state_persistence": True,  # Built-in with @persist
                "automatic_routing": True,       # Built-in with @router
                "feedback_loops": True          # Built-in with @listen
            },
            "features": {
                "state_management": "Automatic with Pydantic + SQLite",
                "persistence": "Built-in with @persist decorator",
                "routing": "Native CrewAI Flow routing",
                "feedback_loops": "Native @listen decorators",
                "visualization": "Built-in flow.plot() support",
                "error_handling": "Integrated Flow error management"
            }
        }

    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics from Flow state."""
        if self._current_flow and hasattr(self._current_flow, 'state'):
            state = self._current_flow.state
            return {
                "session_id": self.session_id,
                "architecture": "crewai_flow",
                "vendor": getattr(state, 'vendor', 'unknown'),
                "category": getattr(state, 'category_name', 'unknown'),
                "pages_processed": getattr(state, 'pages_processed', 0),
                "total_products_found": len(getattr(state, 'products', [])),
                "successful_extractions": getattr(state, 'successful_extractions', 0),
                "failed_extractions": getattr(state, 'failed_extractions', 0),
                "success": getattr(state, 'success', False)
            }
        else:
            return {
                "session_id": self.session_id,
                "architecture": "crewai_flow",
                "status": "No active Flow session",
                "message": "Statistics available only during active Flow execution"
            }



    def cleanup(self):
        """Cleanup resources and finalize session."""
        try:
            # Cleanup current Flow if active
            if self._current_flow:
                try:
                    self._current_flow.cleanup()
                    if self.verbose:
                        self.console.print("[cyan]🔄 Flow resources cleaned up[/cyan]")
                except Exception as flow_error:
                    logger.warning(f"Flow cleanup failed: {flow_error}")
                finally:
                    self._current_flow = None

            # Close AI logger
            if hasattr(self, 'ai_logger'):
                close_ai_logger(self.session_id)

            if self.verbose:
                self.console.print(f"[green]✅ Flow session cleanup completed: {self.session_id}[/green]")

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            if self.verbose:
                self.console.print(f"[red]❌ Cleanup failed: {str(e)}[/red]")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()

    def create_flow_plot(self, plot_name: str = None) -> Optional[str]:
        """Create a visual plot of the Flow for debugging and documentation."""
        try:
            if not plot_name:
                plot_name = f"ecommerce_flow_{self.session_id}"

            # Create a temporary Flow instance for plotting
            temp_flow = EcommerceScrapingFlow(verbose=False)
            temp_flow.plot(plot_name)

            if self.verbose:
                self.console.print(f"[cyan]📊 Flow plot created: {plot_name}.html[/cyan]")

            return f"{plot_name}.html"

        except Exception as e:
            logger.error(f"Failed to create Flow plot: {e}")
            if self.verbose:
                self.console.print(f"[red]❌ Flow plot creation failed: {str(e)}[/red]")
            return None

    def get_flow_progress(self) -> Dict[str, Any]:
        """Get current Flow progress information."""
        if self._current_flow and hasattr(self._current_flow, 'state'):
            state = self._current_flow.state
            return {
                "session_id": self.session_id,
                "current_page": getattr(state, 'current_page', 1),
                "max_pages": getattr(state, 'max_pages', None),
                "pages_processed": getattr(state, 'pages_processed', 0),
                "products_extracted": len(getattr(state, 'products', [])),
                "extraction_attempts": getattr(state, 'extraction_attempts', 0),
                "successful_extractions": getattr(state, 'successful_extractions', 0),
                "failed_extractions": getattr(state, 'failed_extractions', 0),
                "status": "active"
            }
        else:
            return {
                "session_id": self.session_id,
                "status": "No active Flow session",
                "message": "Progress available only during active Flow execution"
            }

