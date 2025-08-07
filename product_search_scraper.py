"""Product-Specific Search Scraper - New CLI Interface.

This module implements a product-specific search system that allows users to search
for specific products across UK retailers using AI-powered research and validation.
"""

import logging
import os
import signal
import sys
import threading
import time
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
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

# CrewAI Flow architecture imports
from ecommerce_scraper.workflows.product_search_flow import ProductSearchFlow
from ecommerce_scraper.schemas.product_search_result import ProductSearchResult
from ecommerce_scraper.ai_logging.ai_logger import get_ai_logger, close_ai_logger
from ecommerce_scraper.utils.crewai_setup import ensure_crewai_directories

# Global variables for graceful termination
_termination_requested = False
_scraper_instance = None

console = Console()
logger = logging.getLogger(__name__)

# Try to import keyboard for ESC key detection
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global _termination_requested
    console.print("\n🛑 [red]Termination requested...[/red]")
    _termination_requested = True
    
    # Try to gracefully stop the scraper
    if _scraper_instance:
        try:
            _scraper_instance.stop_gracefully()
        except Exception as e:
            console.print(f"[yellow]Warning: Error during graceful shutdown: {e}[/yellow]")
    
    sys.exit(130)  # Standard exit code for SIGINT


def check_termination() -> bool:
    """Check if termination has been requested."""
    return _termination_requested


def esc_key_listener():
    """Listen for ESC key press in a separate thread."""
    global _termination_requested
    if not KEYBOARD_AVAILABLE:
        return

    try:
        while not _termination_requested:
            if keyboard.is_pressed('esc'):
                console.print("\n🛑 [red]ESC key detected - requesting termination...[/red]")
                _termination_requested = True
                break
            time.sleep(0.1)  # Small delay to prevent high CPU usage
    except Exception:
        # Silently handle any keyboard detection errors
        pass


def start_esc_listener():
    """Start ESC key listener in a daemon thread."""
    if KEYBOARD_AVAILABLE:
        listener_thread = threading.Thread(target=esc_key_listener, daemon=True)
        listener_thread.start()
        return listener_thread
    return None


def show_welcome():
    """Display welcome message and instructions."""
    console.print(Panel.fit(
        "[bold blue]🔍 Product-Specific Search Scraper[/bold blue]\n\n"
        "[cyan]Search for specific products across UK retailers using AI-powered research.[/cyan]\n\n"
        "[yellow]Features:[/yellow]\n"
        "• 🤖 AI-powered retailer discovery using Perplexity research\n"
        "• 🎯 Targeted product search across legitimate UK retailers\n"
        "• ✅ Smart validation with feedback loops\n"
        "• 💾 Structured results storage with pricing and URLs\n"
        "• 🔄 Automatic retry logic for failed searches\n\n"
        "[dim]Press Ctrl+C or ESC at any time to stop[/dim]",
        title="Welcome",
        border_style="blue"
    ))


def get_product_search_query() -> str:
    """Get the product search query from the user."""
    console.print("\n[bold yellow]Step 1: Product Search Query[/bold yellow]")
    
    console.print("[cyan]Enter the specific product you want to search for across UK retailers.[/cyan]")
    console.print("[dim]Examples: 'iPhone 15 Pro', 'Samsung Galaxy S24', 'Nike Air Max 90', 'Dyson V15 Detect'[/dim]")
    
    while True:
        product_query = Prompt.ask(
            "\n[bold]What product would you like to search for?[/bold]",
            default=""
        ).strip()
        
        if not product_query:
            console.print("[red]❌ Please enter a product name to search for.[/red]")
            continue
        
        if len(product_query) < 3:
            console.print("[red]❌ Product name must be at least 3 characters long.[/red]")
            continue
        
        # Confirm the search query
        console.print(f"\n[green]🎯 Search Query:[/green] [bold]{product_query}[/bold]")
        
        if Confirm.ask("Proceed with this search query?", default=True):
            return product_query
        
        console.print("[yellow]Let's try again...[/yellow]")


def get_search_options() -> Dict[str, Any]:
    """Get additional search options from the user."""
    console.print("\n[bold yellow]Step 2: Search Options[/bold yellow]")
    
    # Maximum retailers to search
    max_retailers = Prompt.ask(
        "[bold]Maximum number of retailers to search[/bold]",
        default="5",
        show_default=True
    )
    
    try:
        max_retailers = int(max_retailers)
        if max_retailers < 1 or max_retailers > 20:
            console.print("[yellow]⚠️ Using default value of 5 retailers[/yellow]")
            max_retailers = 5
    except ValueError:
        console.print("[yellow]⚠️ Invalid input, using default value of 5 retailers[/yellow]")
        max_retailers = 5
    
    # Maximum retry attempts
    max_retries = Prompt.ask(
        "[bold]Maximum retry attempts per retailer[/bold]",
        default="3",
        show_default=True
    )
    
    try:
        max_retries = int(max_retries)
        if max_retries < 1 or max_retries > 10:
            console.print("[yellow]⚠️ Using default value of 3 retries[/yellow]")
            max_retries = 3
    except ValueError:
        console.print("[yellow]⚠️ Invalid input, using default value of 3 retries[/yellow]")
        max_retries = 3
    
    return {
        "max_retailers": max_retailers,
        "max_retries": max_retries
    }


class ProductSearchScraper:
    """Product-specific search scraper using CrewAI Flow architecture."""
    
    def __init__(self, verbose: bool = True, session_id: Optional[str] = None):
        """Initialize the product search scraper."""
        self.verbose = verbose
        self.console = Console()
        
        # Create session ID for this search run
        self.session_id = session_id or f"product_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ensure CrewAI directories exist
        ensure_crewai_directories("lastAttempt")
        
        self.ai_logger = get_ai_logger(self.session_id)
        
        if self.verbose:
            self.console.print(f"[bold blue]🔍 AI Logging enabled for session: {self.session_id}[/bold blue]")
            self.console.print(f"[cyan]📁 Logs will be saved to: logs/{self.session_id}/[/cyan]")
        
        # Flow instance will be created per search session
        self._current_flow = None
        
        if self.verbose:
            self.console.print("[bold green]🚀 Product Search Flow Architecture Ready[/bold green]")
    
    def search_product(self,
                      product_query: str,
                      max_retailers: int = 5,
                      max_retries: int = 3) -> ProductSearchResult:
        """
        Search for a specific product across UK retailers using AI-powered research.

        Args:
            product_query: The specific product to search for
            max_retailers: Maximum number of retailers to search
            max_retries: Maximum retry attempts per retailer

        Returns:
            ProductSearchResult with found products and metadata
        """
        try:
            if self.verbose:
                self.console.print(f"[bold green]🔍 Product Search: {product_query}[/bold green]")
                self.console.print(f"[cyan]Max retailers: {max_retailers}[/cyan]")
                self.console.print(f"[cyan]Max retries: {max_retries}[/cyan]")

            # Create Flow instance with initial state
            flow = ProductSearchFlow(verbose=self.verbose)
            self._current_flow = flow

            # Set up initial state
            flow_inputs = {
                "product_query": product_query,
                "max_retailers": max_retailers,
                "max_retries": max_retries,
                "session_id": self.session_id
            }
            
            if self.verbose:
                self.console.print(f"[cyan]🔄 Starting Product Search Flow execution...[/cyan]")
            
            # Execute the Flow
            flow.kickoff(inputs=flow_inputs)
            
            # Process results
            
            # Extract final results from Flow state
            if hasattr(flow.state, 'final_results') and flow.state.final_results:
                result_dict = flow.state.final_results
            elif hasattr(flow.state, 'search_results') and flow.state.search_results:
                result_dict = {
                    "search_query": product_query,
                    "results": flow.state.search_results,
                    "metadata": {
                        "session_id": self.session_id,
                        "retailers_searched": getattr(flow.state, 'retailers_searched', 0),
                        "total_attempts": getattr(flow.state, 'total_attempts', 0),
                        "success_rate": getattr(flow.state, 'success_rate', 0.0)
                    }
                }
            else:
                # Fallback result
                result_dict = {
                    "search_query": product_query,
                    "results": [],
                    "metadata": {
                        "session_id": self.session_id,
                        "error": "No results found",
                        "retailers_searched": 0,
                        "total_attempts": 0,
                        "success_rate": 0.0
                    }
                }
            
            # Save results
            saved_path = self._save_results(result_dict)
            
            # Create ProductSearchResult object
            search_result = ProductSearchResult.from_dict(result_dict)
            
            if self.verbose:
                self.console.print(f"[green]✅ Product search completed[/green]")
                self.console.print(f"[cyan]Found {len(search_result.results)} products across retailers[/cyan]")
            
            return search_result
            
        except Exception as e:
            error_msg = f"Product search failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            if self.verbose:
                self.console.print(f"[red]❌ {error_msg}[/red]")
            
            # Return empty result with error
            return ProductSearchResult(
                search_query=product_query,
                results=[],
                metadata={
                    "session_id": self.session_id,
                    "error": error_msg,
                    "retailers_searched": 0,
                    "total_attempts": 0,
                    "success_rate": 0.0
                }
            )
    
    def stop_gracefully(self):
        """Stop the scraper gracefully."""
        if self._current_flow:
            try:
                # Attempt to stop the current flow
                if hasattr(self._current_flow, 'stop'):
                    self._current_flow.stop()
            except Exception as e:
                logger.warning(f"Error stopping flow: {e}")
        
        # Close AI logger
        try:
            close_ai_logger(self.session_id)
        except Exception as e:
            logger.warning(f"Error closing AI logger: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop_gracefully()

    def _save_results(self, result_dict: Dict[str, Any]) -> Optional[str]:
        """Save product search results to JSON file."""
        try:
            import os
            import json
            from pathlib import Path
            from datetime import datetime

            # Create results directory
            results_dir = Path("product-search-results")
            results_dir.mkdir(exist_ok=True)

            # Create session-specific directory
            session_dir = results_dir / self.session_id
            session_dir.mkdir(exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"product_search_{timestamp}.json"
            filepath = session_dir / filename

            # Save results
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False, default=str)

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return None


def main():
    """Main product search workflow."""
    global _scraper_instance

    try:
        # Welcome and setup
        show_welcome()

        # Check for termination before starting
        if check_termination():
            console.print("[yellow]🛑 Termination requested before starting[/yellow]")
            return

        # Step 1: Get product search query
        product_query = get_product_search_query()

        # Check for termination after query input
        if check_termination():
            console.print("[yellow]🛑 Termination requested during query input[/yellow]")
            return

        # Step 2: Get search options
        search_options = get_search_options()

        # Check for termination after options input
        if check_termination():
            console.print("[yellow]🛑 Termination requested during options input[/yellow]")
            return

        # Step 3: Execute product search
        console.print(f"\n[bold blue]🤖 Initializing AI-powered product search...[/bold blue]")
        console.print(f"[cyan]🎯 Product: {product_query}[/cyan]")
        console.print(f"[cyan]🏪 Max retailers: {search_options['max_retailers']}[/cyan]")
        console.print(f"[cyan]🔄 Max retries: {search_options['max_retries']}[/cyan]")

        # Use context manager for proper resource cleanup
        with ProductSearchScraper(verbose=True) as product_scraper:
            _scraper_instance = product_scraper  # Store reference for signal handler

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Searching for '{product_query}' across UK retailers...",
                    total=None
                )

                # Execute product search
                result = product_scraper.search_product(
                    product_query=product_query,
                    max_retailers=search_options['max_retailers'],
                    max_retries=search_options['max_retries']
                )

                progress.update(task, completed=1, total=1)

            # Display results
            display_search_results(result)

    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Product search interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]💥 Unexpected error: {str(e)}[/red]")
        logger.error(f"Unexpected error in main: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        if _scraper_instance:
            _scraper_instance.stop_gracefully()


def display_search_results(result: ProductSearchResult):
    """Display the search results in a formatted table."""
    console.print(f"\n[bold green]🎉 Search Results for '{result.search_query}'[/bold green]")

    if not result.results:
        console.print("[yellow]❌ No products found matching your search criteria.[/yellow]")
        console.print("[dim]Try adjusting your search query or increasing the number of retailers to search.[/dim]")
        return

    # Create results table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Retailer", style="cyan", no_wrap=True, width=15)
    table.add_column("Product Name", style="green", width=30)
    table.add_column("Price", style="yellow", no_wrap=True, width=10)
    table.add_column("URL", style="blue", width=40)

    for product in result.results:
        table.add_row(
            product.get('retailer', 'Unknown'),
            product.get('product_name', 'N/A'),
            product.get('price', 'N/A'),
            product.get('url', 'N/A')[:37] + "..." if len(product.get('url', '')) > 40 else product.get('url', 'N/A')
        )

    console.print(table)

    # Display metadata
    metadata = result.metadata
    console.print(f"\n[bold blue]📊 Search Statistics[/bold blue]")
    console.print(f"[cyan]• Products found: {len(result.results)}[/cyan]")
    console.print(f"[cyan]• Retailers searched: {metadata.get('retailers_searched', 0)}[/cyan]")
    console.print(f"[cyan]• Total attempts: {metadata.get('total_attempts', 0)}[/cyan]")
    console.print(f"[cyan]• Success rate: {metadata.get('success_rate', 0.0):.1%}[/cyan]")
    console.print(f"[cyan]• Session ID: {metadata.get('session_id', 'N/A')}[/cyan]")

    # Display file location
    if 'results_file' in metadata:
        console.print(f"\n[green]💾 Results saved to: {metadata['results_file']}[/green]")


if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Start ESC key listener if available
    esc_thread = start_esc_listener()

    # Display startup message
    console.print("[bold blue]🚀 Product-Specific Search Scraper[/bold blue]")
    if KEYBOARD_AVAILABLE:
        console.print("[dim]💡 Press Ctrl+C or ESC at any time to gracefully terminate[/dim]")
    else:
        console.print("[dim]💡 Press Ctrl+C at any time to gracefully terminate[/dim]")
        console.print("[dim]ℹ️ Install 'keyboard' package for ESC key support: pip install keyboard[/dim]")
    console.print()

    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Scraper interrupted by user[/yellow]")
        sys.exit(130)
