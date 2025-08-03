"""Main product scraper agent that coordinates the scraping process."""

from typing import List, Optional
from crewai import Agent, LLM


class ProductScraperAgent:
    """Main agent that coordinates product scraping across different ecommerce sites."""
    
    def __init__(self, tools: List, llm: Optional[LLM] = None):
        """Initialize the product scraper agent with required tools."""

        agent_config = {
            "role": "Product Scraping Coordinator",
            "goal": """
            Coordinate the extraction of comprehensive product information from ecommerce websites.
            Ensure data quality, handle errors gracefully, and maintain respectful scraping practices.
            """,
            "backstory": """
            You are an expert ecommerce data analyst with deep knowledge of online retail platforms.
            You understand the structure of product pages across different sites and can adapt your
            approach based on the specific ecommerce platform. You prioritize data accuracy and
            completeness while respecting website terms of service and rate limits.

            Your expertise includes:
            - Navigating complex ecommerce site structures
            - Identifying and extracting product information
            - Handling dynamic content and JavaScript-heavy sites
            - Dealing with anti-bot measures and CAPTCHAs
            - Ensuring data quality and consistency
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
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent
