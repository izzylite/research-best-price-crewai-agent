"""Main module for ecommerce scraping functionality."""

import logging
import os
from datetime import datetime

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is available for CrewAI
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

from rich.console import Console

from datetime import datetime
from typing import Any, Dict, List, Optional

# Enhanced architecture imports - Flow-based
from .workflows.ecommerce_flow import EcommerceScrapingFlow, EcommerceScrapingState
from .workflows.flow_utils import FlowResultProcessor, FlowStateManager, FlowPerformanceMonitor
from .workflows.flow_routing import FlowRouter

from .schemas.standardized_product import StandardizedProduct
from .ai_logging.ai_logger import get_ai_logger, close_ai_logger
from .utils.crewai_setup import ensure_crewai_directories

logger = logging.getLogger(__name__)

class DynamicScrapingResult:
    """Container for dynamic scraping results."""

    def __init__(self, success: bool, products: List[StandardizedProduct] = None,
                 error: str = None, agent_results: List[Dict] = None,
                 session_id: str = None, vendor: str = None, category: str = None,
                 raw_crew_result: Any = None, statistics: Dict = None):
        """Initialize scraping result."""
        self.success = success
        self.products = products or []
        self.error = error
        self.agent_results = agent_results or []
        self.session_id = session_id
        self.vendor = vendor
        self.category = category
        self.raw_crew_result = raw_crew_result
        self.statistics = statistics or {}

class EcommerceScraper:
    """Enhanced ecommerce scraper with cyclical multi-agent orchestration."""

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

        # Initialize Flow-based architecture
        self._initialize_flow_architecture()

    def _initialize_flow_architecture(self):
        """Initialize the CrewAI Flow-based architecture."""
        if self.verbose:
            self.console.print("[bold green]🚀 Initializing CrewAI Flow Architecture[/bold green]")

        # Initialize Flow-based components
        self.flow_router = FlowRouter(max_retries=3)
        self.performance_monitor = FlowPerformanceMonitor()

        # Flow instance will be created per scraping session
        self._current_flow = None

        if self.verbose:
            self.console.print("[cyan]   ✅ Cyclical Processor initialized[/cyan]")
            self.console.print("[cyan]   ✅ JSON Manager initialized[/cyan]")
            self.console.print("[cyan]   ✅ Enhanced Progress Tracker initialized[/cyan]")
            self.console.print("[cyan]   ✅ Performance Metrics initialized[/cyan]")
            self.console.print("[cyan]   ✅ Feedback Coordinator initialized[/cyan]")



    def scrape_category(self,
                       category_url: str,
                       vendor: str,
                       category_name: str,
                       max_pages: Optional[int] = None) -> DynamicScrapingResult:
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

            # Start performance monitoring
            self.performance_monitor.start_monitoring()

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
            flow_result = flow.kickoff(inputs=flow_inputs)

            # Add performance checkpoint
            self.performance_monitor.checkpoint("flow_completed")

            # Convert Flow result to DynamicScrapingResult for backward compatibility
            # The Flow result might be a Flow object or dict, handle both cases
            if hasattr(flow_result, 'state'):
                # Flow object - extract final state
                final_state = flow_result.state
                result_dict = {
                    "success": getattr(final_state, 'success', False),
                    "products": getattr(final_state, 'final_products', []),
                    "error": getattr(final_state, 'error_message', None),
                    "session_id": getattr(final_state, 'session_id', self.session_id),
                    "vendor": getattr(final_state, 'vendor', vendor),
                    "category": getattr(final_state, 'category_name', category_name),
                    "statistics": {
                        "total_pages_processed": getattr(final_state, 'pages_processed', 0),
                        "total_products_found": getattr(final_state, 'total_products_found', 0),
                        "successful_extractions": getattr(final_state, 'successful_extractions', 0),
                        "failed_extractions": getattr(final_state, 'failed_extractions', 0)
                    }
                }
            else:
                # Already a dict
                result_dict = flow_result

            result = FlowResultProcessor.create_dynamic_scraping_result(result_dict)

            # Save results using Flow utilities
            if result.success and result.products:
                saved_path = FlowResultProcessor.save_flow_results(
                    flow_result, vendor, category_name
                )
                if saved_path and self.verbose:
                    self.console.print(f"[green]✅ Results saved to: {saved_path}[/green]")

            # Performance summary
            if self.verbose:
                performance_summary = self.performance_monitor.get_performance_summary()
                self.console.print(f"[cyan]📊 Performance Summary:[/cyan]")
                self.console.print(f"[cyan]   Duration: {performance_summary['total_duration_seconds']:.1f}s[/cyan]")
                if 'checkpoint_durations' in performance_summary:
                    for checkpoint, duration in performance_summary['checkpoint_durations'].items():
                        self.console.print(f"[cyan]   {checkpoint}: {duration:.1f}s[/cyan]")

            return result

        except Exception as e:
            logger.error(f"Flow scraping failed: {str(e)}")

            return DynamicScrapingResult(
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
        info = {
            "architecture_type": "crewai_flow",
            "session_id": self.session_id,
            "components": {
                "flow_router": hasattr(self, 'flow_router'),
                "performance_monitor": hasattr(self, 'performance_monitor'),
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

        return info

    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics from Flow state."""
        if self._current_flow and hasattr(self._current_flow, 'state'):
            return FlowStateManager.get_flow_statistics(self._current_flow.state)
        else:
            return {
                "session_id": self.session_id,
                "architecture": "crewai_flow",
                "status": "No active Flow session",
                "message": "Statistics available only during active Flow execution"
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics from Flow monitoring."""
        return self.performance_monitor.get_performance_summary()



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

            # Export performance metrics
            if hasattr(self, 'performance_monitor') and self.verbose:
                try:
                    performance_summary = self.performance_monitor.get_performance_summary()
                    if performance_summary and "total_duration_seconds" in performance_summary:
                        self.console.print(f"[cyan]📊 Total session duration: {performance_summary['total_duration_seconds']:.1f}s[/cyan]")
                except Exception as perf_error:
                    logger.warning(f"Performance summary failed: {perf_error}")

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
            return FlowStateManager.get_flow_progress(self._current_flow.state)
        else:
            return {
                "session_id": self.session_id,
                "status": "No active Flow session",
                "message": "Progress available only during active Flow execution"
            }

