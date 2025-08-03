"""Main ecommerce scraper class that orchestrates the scraping process."""

import json
import os
import logging
from typing import List, Optional, Dict, Any, Union

# Load settings first to get API keys
from .config.settings import settings

# Setup logging
settings.setup_logging()
logger = logging.getLogger(__name__)

# Set ALL environment variables BEFORE importing any CrewAI or Stagehand modules
# This is critical for proper API key forwarding to remote Browserbase sessions

# Set Browserbase environment variables from settings
os.environ["BROWSERBASE_API_KEY"] = settings.browserbase_api_key
os.environ["BROWSERBASE_PROJECT_ID"] = settings.browserbase_project_id

# Set LLM API keys for CrewAI
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    # CRITICAL: Set MODEL_API_KEY for Stagehand remote session creation
    os.environ["MODEL_API_KEY"] = settings.openai_api_key
    # ADDITIONAL: Set STAGEHAND_MODEL_API_KEY as backup
    os.environ["STAGEHAND_MODEL_API_KEY"] = settings.openai_api_key
    logger.info(f"🔑 Set API keys for Stagehand: {settings.openai_api_key[:20]}...")
else:
    logger.error("OpenAI API key is required but not found in settings")
    raise ValueError("OpenAI API key is required but not found in settings")

if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

# Now import CrewAI after environment variables are set
from crewai import Crew, LLM
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agents.product_scraper import ProductScraperAgent
from .agents.site_navigator import SiteNavigatorAgent
from .agents.data_extractor import DataExtractorAgent
from .agents.data_validator import DataValidatorAgent
from .config.sites import get_site_config, detect_site_type, SiteType
from .schemas.product import Product
from crewai_tools import StagehandTool
from stagehand.schemas import AvailableModel
from .tools.data_tools import ProductDataValidator, PriceExtractor, ImageExtractor
from .tools.stagehand_tool import EcommerceStagehandTool


class EcommerceScraper:
    """Main ecommerce scraper that coordinates agents to extract product data."""
    
    def __init__(self, verbose: bool = True):
        """Initialize the ecommerce scraper."""
        self.console = Console()
        self.verbose = verbose

        # Configure LLM for CrewAI agents
        self.llm = LLM(
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4000
        )

        # Create StagehandTool with proper configuration
        # Environment variables are already set at module level
        # Note: StagehandTool will be created as context manager when needed
        self.stagehand_config = {
            "api_key": settings.browserbase_api_key,
            "project_id": settings.browserbase_project_id,
            "model_api_key": settings.openai_api_key,
            "model_name": AvailableModel.GPT_4O,
            "dom_settle_timeout_ms": settings.stagehand_dom_settle_timeout_ms,
            "headless": settings.stagehand_headless,
            "verbose": settings.stagehand_verbose if verbose else 0
        }
        self.stagehand_tool = None

        # Initialize agents with role-specific tools and LLM
        # Note: StagehandTool will be added dynamically when needed

        # ProductScraperAgent: Coordinator - needs ProductDataValidator
        product_scraper_tools = [ProductDataValidator()]
        self.product_scraper = ProductScraperAgent(tools=product_scraper_tools, llm=self.llm)

        # SiteNavigatorAgent: Navigation - will get StagehandTool dynamically
        site_navigator_tools = []
        self.site_navigator = SiteNavigatorAgent(tools=site_navigator_tools, llm=self.llm)

        # DataExtractorAgent: Data extraction - needs specialized extractors
        data_extractor_tools = [PriceExtractor(), ImageExtractor()]
        self.data_extractor = DataExtractorAgent(tools=data_extractor_tools, llm=self.llm)

        # DataValidatorAgent: Data validation - needs validation and price tools
        data_validator_tools = [ProductDataValidator(), PriceExtractor()]
        self.data_validator = DataValidatorAgent(tools=data_validator_tools, llm=self.llm)

    def _create_stagehand_tool(self):
        """Create a StagehandTool instance with proper configuration."""
        # Use our custom EcommerceStagehandTool instead of the buggy CrewAI StagehandTool
        return EcommerceStagehandTool()

    def scrape_product(self, product_url: str, site_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape a single product from the given URL.

        Args:
            product_url: URL of the product page to scrape
            site_type: Optional site type hint (amazon, ebay, shopify, generic)

        Returns:
            Dictionary containing the scraped product data and metadata
        """
        # Create StagehandTool instance for this scraping session
        stagehand_tool = None
        try:
            if self.verbose:
                self.console.print(f"[bold blue]Scraping product:[/bold blue] {product_url}")

            # Detect site type if not provided
            if site_type is None:
                detected_type = detect_site_type(product_url)
                site_type = detected_type.value

            site_config = get_site_config(product_url)

            if self.verbose:
                self.console.print(f"[green]Detected site type:[/green] {site_type}")

            # Create StagehandTool instance
            stagehand_tool = self._create_stagehand_tool()

            # Add StagehandTool to agents that need it
            self.site_navigator.get_agent().tools = [stagehand_tool]
            self.data_extractor.get_agent().tools = [stagehand_tool, PriceExtractor(), ImageExtractor()]
            self.product_scraper.get_agent().tools = [stagehand_tool, ProductDataValidator()]

            # Create and execute scraping task
            scraping_task = self.product_scraper.create_scraping_task(
                product_url=product_url,
                site_type=site_type
            )

            # Create crew with all agents
            crew = Crew(
                agents=[
                    self.product_scraper.get_agent(),
                    self.site_navigator.get_agent(),
                    self.data_extractor.get_agent(),
                    self.data_validator.get_agent()
                ],
                tasks=[scraping_task],
                verbose=self.verbose,
                memory=True
            )
            
            # Execute the scraping
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Scraping product data...", total=None)
                crew_result = crew.kickoff()
                progress.update(task, completed=True)

            if self.verbose:
                self.console.print("[bold green]✓ Product scraping completed[/bold green]")

            # Convert CrewOutput to serializable format
            if hasattr(crew_result, 'raw'):
                result_data = crew_result.raw
                if self.verbose:
                    self.console.print(f"[dim]Debug: crew_result.raw type: {type(result_data)}[/dim]")
                # Try to parse as JSON if it's a string
                if isinstance(result_data, str):
                    try:
                        import json
                        parsed_data = json.loads(result_data)
                        result_data = parsed_data
                        if self.verbose:
                            self.console.print("[dim]Debug: Successfully parsed JSON from string[/dim]")
                    except (json.JSONDecodeError, ValueError) as e:
                        if self.verbose:
                            self.console.print(f"[dim]Debug: JSON parsing failed: {e}[/dim]")
                        # If parsing fails, keep as string
                        pass
            elif hasattr(crew_result, 'json'):
                result_data = crew_result.json
            else:
                result_data = str(crew_result)

            return {
                "success": True,
                "product_url": product_url,
                "site_type": site_type,
                "data": result_data,
                "metadata": {
                    "site_config": site_config.name,
                    "extraction_method": "ai_powered"
                }
            }

        except Exception as e:
            error_msg = f"Error scraping product {product_url}: {str(e)}"
            if self.verbose:
                self.console.print(f"[bold red]✗ {error_msg}[/bold red]")

            return {
                "success": False,
                "product_url": product_url,
                "error": error_msg,
                "data": None
            }
        finally:
            # Always cleanup the StagehandTool session
            if stagehand_tool:
                try:
                    stagehand_tool.close()
                    if self.verbose:
                        self.console.print("[dim]🧹 StagehandTool session cleaned up[/dim]")
                except Exception as cleanup_error:
                    if self.verbose:
                        self.console.print(f"[dim]⚠️ Warning: StagehandTool cleanup failed: {cleanup_error}[/dim]")
    
    def scrape_products(self, product_urls: List[str], site_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape multiple products from the given URLs.
        
        Args:
            product_urls: List of product URLs to scrape
            site_type: Optional site type hint for all URLs
            
        Returns:
            List of dictionaries containing scraped product data
        """
        results = []
        
        if self.verbose:
            self.console.print(f"[bold blue]Scraping {len(product_urls)} products[/bold blue]")
        
        with Progress(console=self.console) as progress:
            task = progress.add_task("Scraping products...", total=len(product_urls))
            
            for i, url in enumerate(product_urls):
                if self.verbose:
                    progress.update(task, description=f"Scraping product {i+1}/{len(product_urls)}")
                
                result = self.scrape_product(url, site_type)
                results.append(result)
                
                progress.advance(task)
        
        successful = sum(1 for r in results if r["success"])
        if self.verbose:
            self.console.print(f"[bold green]✓ Completed: {successful}/{len(product_urls)} successful[/bold green]")
        
        return results
    
    def search_and_scrape(self, search_query: str, site_url: str, max_products: int = 10) -> Dict[str, Any]:
        """
        Search for products on a site and scrape the results.
        
        Args:
            search_query: Search term to look for
            site_url: Base URL of the ecommerce site
            max_products: Maximum number of products to scrape
            
        Returns:
            Dictionary containing search results and scraped product data
        """
        try:
            if self.verbose:
                self.console.print(f"[bold blue]Searching for '{search_query}' on {site_url}[/bold blue]")
            
            # Create search and scrape task
            search_task = self.product_scraper.create_search_and_scrape_task(
                search_query=search_query,
                site_url=site_url,
                max_products=max_products
            )
            
            # Create crew without memory to avoid API key issues
            crew = Crew(
                agents=[
                    self.product_scraper.get_agent(),
                    self.site_navigator.get_agent(),
                    self.data_extractor.get_agent(),
                    self.data_validator.get_agent()
                ],
                tasks=[search_task],
                verbose=self.verbose,
                memory=False
            )
            
            # Execute the search and scraping
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Searching and scraping...", total=None)
                crew_result = crew.kickoff()
                progress.update(task, completed=True)

            if self.verbose:
                self.console.print("[bold green]✓ Search and scrape completed[/bold green]")

            # Convert CrewOutput to serializable format
            if hasattr(crew_result, 'raw'):
                result_data = crew_result.raw
                # Try to parse as JSON if it's a string
                if isinstance(result_data, str):
                    try:
                        import json
                        result_data = json.loads(result_data)
                    except (json.JSONDecodeError, ValueError):
                        # If parsing fails, keep as string
                        pass
            elif hasattr(crew_result, 'json'):
                result_data = crew_result.json
            else:
                result_data = str(crew_result)

            return {
                "success": True,
                "search_query": search_query,
                "site_url": site_url,
                "max_products": max_products,
                "data": result_data
            }
            
        except Exception as e:
            error_msg = f"Error searching and scraping {site_url}: {str(e)}"
            if self.verbose:
                self.console.print(f"[bold red]✗ {error_msg}[/bold red]")
            
            return {
                "success": False,
                "search_query": search_query,
                "site_url": site_url,
                "error": error_msg,
                "data": None
            }
    
    def validate_product_data(self, raw_data: Union[str, Dict[str, Any]], base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate and clean raw product data.
        
        Args:
            raw_data: Raw extracted product data
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Validated and cleaned product data
        """
        try:
            validation_task = self.data_validator.create_validation_task("comprehensive")
            
            # Create a simple crew with just the validator
            crew = Crew(
                agents=[self.data_validator.get_agent()],
                tasks=[validation_task],
                verbose=False
            )
            
            # Pass data to the validator
            result = crew.kickoff()
            
            return {
                "success": True,
                "validated_data": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Validation error: {str(e)}"
            }
    
    def close(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'stagehand_tool') and hasattr(self.stagehand_tool, 'close'):
                if self.verbose:
                    self.console.print("🔄 Closing Stagehand session...")
                self.stagehand_tool.close()
                if self.verbose:
                    self.console.print("✅ Stagehand session closed successfully")
        except Exception as e:
            if self.verbose:
                self.console.print(f"[yellow]Warning: Error during cleanup: {e}[/yellow]")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience functions for quick usage
def scrape_product(product_url: str, site_type: Optional[str] = None, verbose: bool = True) -> Dict[str, Any]:
    """Quick function to scrape a single product."""
    with EcommerceScraper(verbose=verbose) as scraper:
        return scraper.scrape_product(product_url, site_type)


def scrape_products(product_urls: List[str], site_type: Optional[str] = None, verbose: bool = True) -> List[Dict[str, Any]]:
    """Quick function to scrape multiple products."""
    with EcommerceScraper(verbose=verbose) as scraper:
        return scraper.scrape_products(product_urls, site_type)


def search_and_scrape(search_query: str, site_url: str, max_products: int = 10, verbose: bool = True) -> Dict[str, Any]:
    """Quick function to search and scrape products."""
    with EcommerceScraper(verbose=verbose) as scraper:
        return scraper.search_and_scrape(search_query, site_url, max_products)
