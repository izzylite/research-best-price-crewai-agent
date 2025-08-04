"""Site navigation agent specialized in navigating different ecommerce platforms."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM

from ..config.sites import get_site_config_by_vendor, SiteConfig


class SiteNavigatorAgent:
    """Agent specialized in navigating ecommerce sites and handling site-specific challenges."""

    def __init__(self,
                 tools: List,
                 llm: Optional[LLM] = None,
                 site_configs: Optional[Dict[str, SiteConfig]] = None):
        """Initialize the site navigator agent with required tools and site configurations."""

        # Store site configurations
        self.site_configs = site_configs or {}

        agent_config = {
            "role": "Multi-Vendor Ecommerce Site Navigation Expert",
            "goal": """
            Navigate multiple UK ecommerce websites efficiently using vendor-specific configurations.
            Handle site-specific challenges, cookie banners, age verification, and complex navigation
            structures while maintaining optimal performance across different retail platforms.
            """,
            "backstory": """
            You are a multi-vendor web navigation specialist with extensive experience across UK retail
            platforms including ASDA, Tesco, Waitrose, Costco, Hamleys, and other major retailers.
            You understand vendor-specific navigation patterns and can adapt to different site architectures.

            Your enhanced expertise includes:
            - Vendor-specific cookie consent and GDPR compliance handling
            - UK retail site navigation patterns and category structures
            - Location-based delivery area selection for UK postcodes
            - Age verification for restricted products (alcohol, etc.)
            - Anti-bot evasion strategies tailored to each vendor
            - Mobile vs desktop layout differences across UK retailers
            - Site-specific search functionality and filtering systems
            - Handling vendor-specific popups and promotional banners
            - Managing rate limits and respectful crawling per vendor
            """,
            "verbose": True,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 3,
            "memory": False
        }

        if llm:
            agent_config["llm"] = llm

        self.agent = Agent(**agent_config)

    def create_vendor_navigation_task(self, vendor: str, category: str, session_id: str):
        """Create a task for navigating to a specific vendor's category page."""
        from crewai import Task

        # Get vendor-specific configuration
        site_config = get_site_config_by_vendor(vendor)
        if not site_config:
            raise ValueError(f"No configuration found for vendor: {vendor}")

        task_description = f"""
        Navigate to {vendor}'s {category} category page and prepare for product extraction.

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}
        Base URL: {site_config.base_url}

        NAVIGATION STEPS:
        1. Navigate to the vendor's base URL: {site_config.base_url}
        2. Handle initial popups and consent banners using vendor-specific patterns
        3. Navigate to the {category} category section
        4. Verify the category page loaded correctly
        5. Handle any additional popups or age verification if needed
        6. Prepare the page for product extraction

        VENDOR-SPECIFIC REQUIREMENTS:
        - Rate limit: Wait {site_config.delay_between_requests} seconds between actions
        - Cookie consent: Handle GDPR compliance appropriately
        - Location selection: Set to UK if prompted
        - Age verification: Handle for restricted categories
        - Anti-bot measures: Use natural interaction patterns

        CRITICAL: Report any navigation failures or obstacles encountered.
        The page must be ready for product extraction when this task completes.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A navigation report containing:
            - success: boolean indicating if navigation was successful
            - current_url: the final URL reached
            - category_verified: boolean indicating if correct category page was reached
            - obstacles_encountered: list of any popups, banners, or challenges handled
            - ready_for_extraction: boolean indicating if page is ready for product scraping
            - error_message: any error details if navigation failed
            """
        )

    def create_navigation_task(self, target_url: str, navigation_goal: str):
        """Create a task for navigating to a specific page or section."""
        from crewai import Task
        
        task_description = f"""
        Navigate to the target URL and accomplish the navigation goal.
        
        Target URL: {target_url}
        Navigation Goal: {navigation_goal}
        
        Your task is to:
        1. Navigate to the target URL
        2. **IMMEDIATELY handle any blocking popups, banners, or consent requests:**
           - Look for cookie consent banners and click "Accept All" or "I Accept"
           - Dismiss privacy policy dialogs by clicking "Accept" or "Continue"
           - Close newsletter signup popups with "No Thanks", "Close", or "X"
           - Handle age verification by clicking "Yes" or entering appropriate age
           - Select "United Kingdom" or "UK" for location prompts
           - Accept GDPR compliance by clicking "Accept" or "Continue"
           - Dismiss promotional offers with "Close" or "No Thanks"
           - Handle app download prompts with "Continue in Browser"
        3. **VERIFY the main content is visible and not blocked by overlays**
        4. Accomplish the specific navigation goal
        5. Verify that you've reached the correct page/section
        6. Report on any obstacles encountered and how they were resolved
        
        Common challenges to watch for and MUST handle immediately:
        - **Cookie consent banners** (click "Accept All", "I Accept", "Accept Cookies", "Continue")
        - **Privacy policy dialogs** (click "Accept", "I Agree", "Continue")
        - **Age verification prompts** (enter appropriate age or click "Yes", "I am 18+")
        - **Location/country selection dialogs** (select "United Kingdom", "UK", or "Continue")
        - **Newsletter signup popups** (click "Close", "No Thanks", "Skip", "X" button, "Maybe Later")
        - **GDPR compliance banners** (click "Accept", "Accept All", "Continue")
        - **Promotional banners/offers** (click "Close", "Dismiss", "No Thanks", "Continue Shopping")
        - **Mobile app download prompts** (click "Continue in Browser", "Not Now", "Stay on Web")
        - **Loading delays and dynamic content** (wait for elements to appear)
        - **Mobile vs desktop layout differences** (adapt to different layouts)
        
        Be patient and allow pages to fully load before taking actions.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A report confirming successful navigation with details about:
            - Whether the navigation goal was achieved
            - Any obstacles encountered and how they were resolved
            - Current page status and readiness for further actions
            - Any warnings or notes about the site's behavior
            """
        )
    
    def create_search_task(self, site_url: str, search_query: str):
        """Create a task for performing a search on an ecommerce site."""
        from crewai import Task
        
        task_description = f"""
        Navigate to the ecommerce site and perform a product search.

        Site URL: {site_url}
        Search Query: "{search_query}"

        CRITICAL: You MUST use the Web Automation Tool (Stagehand) to actually navigate and interact with the real website.
        DO NOT generate fake responses. Only report what you actually observe on the live website.

        Your task is to:
        1. Use the Web Automation Tool to navigate to the site and handle any initial popups/banners
        2. Use the Web Automation Tool to locate the search functionality (search box, search button)
        3. Use the Web Automation Tool to enter the search query and execute the search
        4. Wait for search results to load completely
        5. Verify that relevant search results are displayed
        6. Report on the search results page structure and content

        Search strategies to try:
        - ALWAYS use the Web Automation Tool for navigation and interaction
        - Look for main search box (usually in header)
        - Try category-specific search if main search isn't obvious
        - Handle search suggestions/autocomplete if they appear
        - Wait for dynamic loading of results
        - Check if filters or sorting options are available
        - Only report what you actually see on the real website

        If the search fails, try alternative approaches or report the issue.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A detailed report about the search process including:
            - Whether the search was successful
            - Number of results found (if visible)
            - Structure of the search results page
            - Available filters, sorting options, or pagination
            - Any issues encountered during the search process
            """
        )
    
    def create_category_navigation_task(self, site_url: str, category_path: str):
        """Create a task for navigating to a specific product category."""
        from crewai import Task
        
        task_description = f"""
        Navigate to a specific product category on the ecommerce site.
        
        Site URL: {site_url}
        Category Path: {category_path}
        
        Your task is to:
        1. Navigate to the site and handle initial popups/banners
        2. Locate the main navigation menu or category structure
        3. Navigate through the category hierarchy to reach the target category
        4. Verify that you've reached the correct category page
        5. Report on the category page structure and available products
        
        Navigation strategies:
        - Look for main navigation menu (usually in header)
        - Check for mega menus or dropdown categories
        - Try breadcrumb navigation if available
        - Look for category filters or subcategory options
        - Handle any category-specific popups or promotions
        
        Category path examples:
        - "Electronics > Computers > Laptops"
        - "Clothing > Men > Shoes"
        - "Home & Garden > Furniture"
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A report about the category navigation including:
            - Whether the target category was reached successfully
            - Structure of the category page (grid, list, filters available)
            - Number of products visible in the category
            - Available subcategories or filters
            - Any navigation challenges encountered
            """
        )
    
    def create_product_page_access_task(self, product_url: str):
        """Create a task for accessing a specific product page."""
        from crewai import Task
        
        task_description = f"""
        Navigate to a specific product page and ensure it's fully loaded.
        
        Product URL: {product_url}
        
        Your task is to:
        1. Navigate directly to the product URL
        2. Handle any popups, banners, or access restrictions
        3. Wait for the product page to fully load (including images and dynamic content)
        4. Verify that this is indeed a product page with product information
        5. Check for any access restrictions or errors
        6. Report on the page readiness for data extraction
        
        Things to watch for:
        - Product page loading completely (images, prices, descriptions)
        - Variant selection options (size, color, etc.)
        - Dynamic pricing or availability updates
        - Related products or recommendations loading
        - Any login requirements or access restrictions
        - Mobile vs desktop layout differences
        
        If the page doesn't load properly, try refreshing or report the issue.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A status report about the product page including:
            - Whether the page loaded successfully
            - Confirmation that it's a valid product page
            - Readiness for data extraction (all elements loaded)
            - Any access restrictions or errors encountered
            - Notes about the page structure and layout
            """
        )
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent
