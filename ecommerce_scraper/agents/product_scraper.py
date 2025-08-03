"""Main product scraper agent that coordinates the scraping process."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM

from ..state.state_manager import StateManager
from ..progress.progress_tracker import ProgressTracker
from ..config.sites import get_site_config_by_vendor, SiteConfig


class ProductScraperAgent:
    """Main agent that coordinates product scraping across different ecommerce sites."""

    def __init__(self,
                 tools: List,
                 llm: Optional[LLM] = None,
                 state_manager: Optional[StateManager] = None,
                 progress_tracker: Optional[ProgressTracker] = None):
        """Initialize the product scraper agent with required tools and enhanced capabilities."""

        # Store enhanced components
        self.state_manager = state_manager
        self.progress_tracker = progress_tracker

        agent_config = {
            "role": "Multi-Vendor Product Scraping Coordinator",
            "goal": """
            Coordinate the extraction of comprehensive product information from multiple ecommerce vendors.
            Manage state persistence, progress tracking, and ensure data quality across different platforms.
            Support batch processing and resume functionality for large-scale operations.
            """,
            "backstory": """
            You are an expert ecommerce data analyst with deep knowledge of online retail platforms
            and multi-vendor scraping operations. You understand the structure of product pages across
            different sites and can adapt your approach based on vendor-specific configurations.

            Your enhanced expertise includes:
            - Multi-vendor product data extraction (UK retailers: ASDA, Tesco, Waitrose, etc.)
            - State management and session persistence across interruptions
            - Progress tracking and performance monitoring
            - Batch processing coordination with worker management
            - Standardized data schema compliance across all vendors
            - Site-specific configuration and adaptation
            - Respectful scraping with vendor-specific rate limits
            - Error handling and recovery with resume capabilities
            - Data standardization using the StandardizedProduct schema
            - Integration with progress tracking and state management systems
            """,
            "verbose": True,
            "allow_delegation": True,
            "tools": tools,
            "max_iter": 5,
            "memory": False
        }

        if llm:
            agent_config["llm"] = llm

        self.agent = Agent(**agent_config)

    def create_multi_vendor_scraping_task(self,
                                        vendor: str,
                                        category: str,
                                        session_id: str,
                                        max_pages: Optional[int] = None):
        """Create a task for scraping products from a specific vendor and category."""
        from crewai import Task

        # Get vendor-specific configuration
        site_config = get_site_config_by_vendor(vendor)
        if not site_config:
            raise ValueError(f"No configuration found for vendor: {vendor}")

        task_description = f"""
        Scrape products from {vendor} in the {category} category using standardized data extraction.

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}
        Max Pages: {max_pages or 'unlimited'}
        Base URL: {site_config.base_url}

        CRITICAL REQUIREMENTS:
        1. Use the Web Automation Tool (Stagehand) to navigate the real website
        2. Extract data using the StandardizedProduct schema format
        3. Report progress to the progress tracker if available
        4. Handle vendor-specific navigation patterns and anti-bot measures
        5. Respect rate limits: {site_config.delay_between_requests} seconds between requests
        6. Use vendor-specific selectors and extraction patterns

        Data must be extracted in this exact StandardizedProduct format:
        {{
            "name": "Product title/name",
            "description": "Product description",
            "price": {{
                "current": 10.99,
                "currency": "GBP",
                "original": 15.99,
                "discount_percentage": 33.3
            }},
            "image_url": "Primary product image URL",
            "category": "{category}",
            "vendor": "{vendor}",
            "weight": "Product weight if available",
            "scraped_at": "ISO timestamp"
        }}

        Handle pagination by:
        1. Starting from the category page
        2. Extracting products from current page
        3. Navigating to next page if available and within max_pages limit
        4. Continuing until no more pages or max_pages reached
        5. Saving state after each page for resume capability
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A JSON object containing:
            - products: Array of StandardizedProduct objects
            - metadata: {{
                "vendor": vendor name,
                "category": category name,
                "session_id": session ID,
                "pages_processed": number of pages scraped,
                "total_products": total products extracted,
                "processing_time": time taken in seconds,
                "errors": any errors encountered
            }}
            """
        )

    def create_scraping_task(self, product_url: str, site_type: Optional[str] = None):
        """Create a task for scraping a specific product."""
        from crewai import Task
        
        task_description = f"""
        Scrape comprehensive product information from the following URL: {product_url}

        CRITICAL: You MUST use the Web Automation Tool (Stagehand) to actually navigate and extract data from the real website.
        DO NOT generate fake or mock data. Only return data that you actually extract from the live website.

        Your task is to:
        1. Use the Web Automation Tool to navigate to the product page: {product_url}
        2. Use the Web Automation Tool to extract all available product information including:
           - Product title and description
           - Current price and original price (if on sale)
           - Brand and model information
           - Product availability and stock status
           - Customer ratings and review count
           - Product images (all available URLs from the actual page)
           - Product specifications and features
           - Available variants (sizes, colors, etc.)
           - Shipping and delivery information
        3. Validate and clean the extracted data
        4. Return the data in a structured JSON format

        Site type: {site_type or 'Unknown - adapt accordingly'}

        Important guidelines:
        - ALWAYS use the Web Automation Tool for navigation and data extraction
        - Extract only real data from the actual website - never generate fake data
        - Be respectful of the website's resources (use appropriate delays)
        - Handle any CAPTCHAs or anti-bot measures gracefully
        - If you encounter errors, try alternative approaches
        - Ensure all extracted data is accurate and complete
        - Format prices consistently and handle different currencies
        - Resolve relative URLs to absolute URLs for images
        - If extraction fails, report the error rather than generating fake data
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A comprehensive JSON object containing all extracted product information,
            properly validated and formatted according to the Product schema.
            Include any warnings or notes about data quality issues encountered.
            """
        )
    
    def create_bulk_scraping_task(self, product_urls: List[str], site_type: Optional[str] = None):
        """Create a task for scraping multiple products."""
        from crewai import Task
        
        urls_list = "\n".join([f"- {url}" for url in product_urls])
        
        task_description = f"""
        Scrape comprehensive product information from the following URLs:
        {urls_list}
        
        For each product URL:
        1. Navigate to the product page
        2. Extract all available product information (same as single product scraping)
        3. Validate and clean the extracted data
        4. Continue to the next product
        
        Site type: {site_type or 'Unknown - adapt accordingly'}
        
        Important guidelines:
        - Maintain appropriate delays between requests (at least 2-3 seconds)
        - Handle errors gracefully and continue with remaining products
        - If a product page fails, note the error and move on
        - Collect all successful extractions into a single result
        - Provide a summary of success/failure rates
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A JSON array containing all successfully extracted product information,
            plus a summary object with statistics about the scraping process
            (total attempted, successful, failed, errors encountered).
            """
        )
    
    def create_search_and_scrape_task(self, search_query: str, site_url: str, max_products: int = 10):
        """Create a task for searching and scraping products."""
        from crewai import Task
        
        task_description = f"""
        Search for products and scrape information from: {site_url}

        Search query: "{search_query}"
        Maximum products to scrape: {max_products}

        CRITICAL: You MUST use the Web Automation Tool (Stagehand) to actually navigate and extract data from the real website.
        DO NOT generate fake or mock data. Only return data that you actually extract from the live website.

        Your task is to:
        1. Use the Web Automation Tool to navigate to: {site_url}
        2. Use the Web Automation Tool to perform a search for "{search_query}"
        3. Use the Web Automation Tool to identify product listings in the search results
        4. Select up to {max_products} relevant products from the actual search results
        5. For each selected product:
           - Use the Web Automation Tool to navigate to the product detail page
           - Use the Web Automation Tool to extract comprehensive product information from the actual page
           - Validate and clean the extracted data
        6. Compile all results into a structured format

        Important guidelines:
        - ALWAYS use the Web Automation Tool for navigation and data extraction
        - Extract only real data from the actual website - never generate fake data
        - Choose diverse and relevant products from search results
        - Prioritize products with good ratings and complete information
        - Handle pagination if needed to find enough products
        - Maintain respectful scraping practices with appropriate delays
        - Skip products that fail to load or have insufficient information
        - If extraction fails, report the error rather than generating fake data
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A JSON object containing:
            - search_query: The original search query
            - site_url: The site that was searched
            - products: Array of extracted product information
            - summary: Statistics about the search and scraping process
            """
        )
    
    def update_progress(self, vendor: str, category: str, products_scraped: int, pages_processed: int):
        """Update progress tracking if available."""
        if self.progress_tracker:
            self.progress_tracker.update_progress(vendor, category, pages_processed, products_scraped)

    def get_vendor_config(self, vendor: str) -> Optional[SiteConfig]:
        """Get site configuration for a specific vendor."""
        return get_site_config_by_vendor(vendor)

    def create_session(self) -> Optional[str]:
        """Create a new scraping session if state manager is available."""
        if self.state_manager:
            return self.state_manager.create_session()
        return None

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent
