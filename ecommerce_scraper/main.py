"""Main module for ecommerce scraping functionality."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is available for CrewAI
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

from crewai import Crew
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from crewai import Crew
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agents.data_extractor import DataExtractorAgent
from .agents.data_validator import DataValidatorAgent
from .agents.product_scraper import ProductScraperAgent
from .config.sites import get_site_config, detect_site_type
from .schemas.standardized_product import StandardizedProduct
from .state.state_manager import StateManager
from .progress.progress_tracker import ProgressTracker

from .logging.ai_logger import get_ai_logger, close_ai_logger
from stagehand.schemas import AvailableModel
from .tools.data_tools import ProductDataValidator, PriceExtractor, ImageExtractor
from .tools.stagehand_tool import EcommerceStagehandTool
from .tools.url_provider_tool import CategoryURLProviderTool
from .utils.url_utils import (
    is_valid_url,
    normalize_url,
    extract_base_url
)
from .utils.crewai_setup import ensure_crewai_directories
from .config.settings import settings

logger = logging.getLogger(__name__)

class DynamicScrapingResult:
    """Container for dynamic scraping results."""

    def __init__(self, success: bool, products: List[StandardizedProduct] = None,
                 error: str = None, agent_results: List[Dict] = None,
                 session_id: str = None, vendor: str = None, category: str = None,
                 raw_crew_result: Any = None):
        """Initialize scraping result."""
        self.success = success
        self.products = products or []
        self.error = error
        self.agent_results = agent_results or []
        self.session_id = session_id
        self.vendor = vendor
        self.category = category
        self.raw_crew_result = raw_crew_result

class EcommerceScraper:
    """Enhanced ecommerce scraper with dynamic multi-agent orchestration."""
    
    def __init__(self,
                 verbose: bool = True,
                 enable_state_management: bool = True,
                 enable_progress_tracking: bool = True,
                 session_id: Optional[str] = None):
        """Initialize the scraper with dynamic agent configuration."""
        self.verbose = verbose
        self.console = Console()

        # Create session ID for this scraping run
        self.session_id = session_id or f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ensure CrewAI directories exist
        ensure_crewai_directories("lastAttempt")
        
        self.ai_logger = get_ai_logger(self.session_id)

        if self.verbose:
            self.console.print(f"[bold blue]🔍 AI Logging enabled for session: {self.session_id}[/bold blue]")
            self.console.print(f"[cyan]📁 Logs will be saved to: logs/{self.session_id}/[/cyan]")

        # Initialize state management if enabled
        self.state_manager = StateManager() if enable_state_management else None
        if self.state_manager and self.verbose:
            self.console.print("[bold blue]📊 State management enabled[/bold blue]")

        # Initialize progress tracking if enabled
        if enable_progress_tracking:
            if self.state_manager:
                self.progress_tracker = ProgressTracker(state_manager=self.state_manager)
                if self.verbose:
                    self.console.print("[bold blue]📈 Progress tracking enabled[/bold blue]")
            else:
                self.progress_tracker = None
                if self.verbose:
                    self.console.print("[yellow]⚠️ Progress tracking disabled - requires state management[/yellow]")
        else:
            self.progress_tracker = None

        # Create initial tools
        stagehand_tool = self._create_stagehand_tool()
        

        # Initialize dynamic agents with tools
        self.product_scraper = ProductScraperAgent(
            tools=[stagehand_tool, ProductDataValidator()],
            state_manager=self.state_manager,
            progress_tracker=self.progress_tracker
        )
        self.data_extractor = DataExtractorAgent(
            tools=[stagehand_tool, PriceExtractor(), ImageExtractor()]
        )
        self.data_validator = DataValidatorAgent(
            tools=[ProductDataValidator(), PriceExtractor()]
        )

    def _create_stagehand_tool(self):
        """Create a new StagehandTool instance."""
        return EcommerceStagehandTool()

    def scrape_category_directly(self,
                               category_url: str,
                               vendor: str,
                               category_name: str,
                               max_pages: Optional[int] = None) -> DynamicScrapingResult:
        """
        Scrape a category directly using dynamic crew creation.

        Args:
            category_url: Direct URL to the category page to scrape
            vendor: Vendor name (e.g., 'asda', 'tesco')
            category_name: Human-readable category name
            max_pages: Maximum pages to scrape per category (None = all pages)

        Returns:
            DynamicScrapingResult with products and metadata
        """
        start_time = datetime.now()
        stagehand_tool = None

        try:
            if self.verbose:
                self.console.print(f"[bold blue]Starting direct category scraping: {vendor}/{category_name}[/bold blue]")
                self.console.print(f"[cyan]URL: {category_url}[/cyan]")
                self.console.print(f"[cyan]Max pages: {max_pages or 'All available'}[/cyan]")

            # Create StagehandTool instance
            stagehand_tool = self._create_stagehand_tool()

            # Create URL Provider Tool for this specific category
            url_provider_tool = CategoryURLProviderTool(
                category_url=category_url,
                vendor=vendor,
                category_name=category_name
            )

            # Create dynamic agents for this specific category with URL provider tool
            product_scraper_agent = self.product_scraper.get_agent()
            # Add URL provider tool to the product scraper agent
            product_scraper_agent.tools.append(url_provider_tool)

            data_extractor_agent = self.data_extractor.get_agent()
            data_validator_agent = self.data_validator.get_agent()
 
 

            # Create category-specific tasks using existing methods
            # Create a temporary session ID for state management
            temp_session_id = f"category_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            scraping_task = self.product_scraper.create_direct_category_scraping_task(
                vendor=vendor,
                category=category_name,
                category_url=category_url,
                session_id=temp_session_id,
                max_pages=max_pages
            )

            extraction_task = self.data_extractor.create_standardized_extraction_task(
                vendor=vendor,
                category=category_name,
                session_id=temp_session_id
            )

            validation_task = self.data_validator.create_standardized_validation_task(
                vendor=vendor,
                category=category_name,
                session_id=temp_session_id
            )

            # Create dynamic crew for this category
            crew = Crew(
                agents=[product_scraper_agent, data_extractor_agent, data_validator_agent],
                tasks=[scraping_task, extraction_task, validation_task],
                verbose=self.verbose,
                memory=settings.enable_crew_memory
            )

            # Execute the crew
            try:
                if self.verbose:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=self.console,
                        transient=True
                    ) as progress:
                        task = progress.add_task(f"Scraping {vendor}/{category_name}...", total=None)
                        crew_result = crew.kickoff()
                        progress.update(task, completed=True)
                else:
                    crew_result = crew.kickoff()

            except Exception as crew_error:
                raise

            # Parse results into StandardizedProduct objects
            products = self._parse_crew_result(crew_result)

            # Create agent result summary
            agent_results = [{
                'agent_id': 1,
                'subcategory': category_name,
                'success': True,
                'products_found': len(products),
                'url': category_url
            }]

            if self.verbose:
                duration = (datetime.now() - start_time).total_seconds()
                self.console.print(f"[bold green]✅ Category scraping completed: {len(products)} products in {duration:.1f}s[/bold green]")

            # Create the result object
            result = DynamicScrapingResult(
                success=True,
                products=products,
                agent_results=agent_results,
                session_id=temp_session_id,
                vendor=vendor,
                category=category_name,
                raw_crew_result=crew_result
            )

            # Save results to directory
            saved_path = self.save_results_to_directory(result, vendor, category_name)
            if saved_path and self.verbose:
                self.console.print(f"[green]✅ Results saved to: {saved_path}[/green]")

            return result

        except Exception as e:
            error_msg = f"Direct category scraping failed for {vendor}/{category_name}: {str(e)}"
            if self.verbose:
                self.console.print(f"[bold red]❌ {error_msg}[/bold red]")

            return DynamicScrapingResult(
                success=False,
                products=[],
                agent_results=[{
                    'agent_id': 1,
                    'subcategory': category_name,
                    'success': False,
                    'products_found': 0,
                    'url': category_url,
                    'error': str(e)
                }],
                session_id=f"category_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                vendor=vendor,
                category=category_name,
                error=error_msg
            )
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

    def _parse_crew_result(self, crew_result: Any) -> List[StandardizedProduct]:
        """
        Parse CrewAI result into StandardizedProduct objects.

        Since DataValidatorAgent is responsible for standardization,
        this method only does simple extraction and validation.

        Args:
            crew_result: Raw result from CrewAI execution

        Returns:
            List of StandardizedProduct objects
        """
        if not crew_result:
                return []

        # Handle different result formats
        if isinstance(crew_result, list):
            return crew_result  # Already a list of StandardizedProduct objects
        elif isinstance(crew_result, dict):
            if "products" in crew_result:
                return crew_result["products"]  # Extract from dictionary
            else:
                return [crew_result]  # Single product dictionary
        else:
            logger.warning(f"Unexpected crew result type: {type(crew_result)}")
            return []
    
    def close(self):
        """Clean up resources and save final state."""
        try:
                if self.verbose:
                    self.console.print("📊 Saving AI activity logs...")
                if self.verbose:
                    self.console.print(f"✅ Logs saved to: logs/{self.session_id}/")
        except Exception as e:
            if self.verbose:
                self.console.print(f"[yellow]Warning: Error saving logs: {e}[/yellow]")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def save_results_to_directory(self, result, vendor: str, category_name: str) -> Optional[Path]:
        """
        Save scraped results to organized directory structure.

        Directory structure: scrapped-result/vendor/category/

        Args:
            result: DynamicScrapingResult object
            vendor: Vendor name (e.g., 'asda')
            category_name: Category name (e.g., 'Fruit, Veg & Flowers > Fruit')

        Returns:
            Path to saved file or None if no products to save
        """
        if not result.products:
            logger.info("No products to save")
            return None

        # Create directory structure: scrapped-result/vendor/category/
        base_dir = Path("scrapped-result")
        vendor_dir = base_dir / vendor.lower()

        # Clean category name for directory (remove special characters)
        clean_category = category_name.replace(" > ", "_").replace(" ", "_").replace(",", "").replace("&", "and")
        category_dir = vendor_dir / clean_category

        # Create directories if they don't exist
        category_dir.mkdir(parents=True, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"products_{timestamp}.json"
        filepath = category_dir / filename

        # Convert products to dictionaries and save
        products_data = {
            "scraping_info": {
                "vendor": vendor,
                "category": category_name,
                "scraped_at": datetime.now().isoformat(),
                "session_id": result.session_id,
                "total_products": len(result.products),
                "success": result.success
            },
            "products": [product.to_dict() for product in result.products]
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Results saved to: {filepath}")
            logger.info(f"Saved {len(result.products)} products")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return None