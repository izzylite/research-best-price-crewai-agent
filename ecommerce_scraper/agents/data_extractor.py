"""Data extraction agent specialized in extracting structured product information."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM

from ..config.sites import get_site_config_by_vendor, SiteConfig


class DataExtractorAgent:
    """Agent specialized in extracting structured product data from ecommerce pages using StandardizedProduct schema."""

    def __init__(self,
                 tools: List,
                 llm: Optional[LLM] = None,
                 site_configs: Optional[Dict[str, SiteConfig]] = None):
        """Initialize the data extractor agent with required tools and site configurations."""

        # Store site configurations
        self.site_configs = site_configs or {}

        agent_config = {
            "role": "Multi-Vendor Product Data Extraction Specialist",
            "goal": """
            Extract comprehensive and accurate product information from multiple UK ecommerce vendors,
            ensuring all data is captured in the StandardizedProduct schema format for consistency
            across different retail platforms.
            """,
            "backstory": """
            You are a multi-vendor data extraction expert with deep knowledge of UK retail platforms
            and their specific product data structures. You understand how different vendors organize
            product information and can adapt extraction strategies accordingly.

            Your enhanced expertise includes:
            - StandardizedProduct schema compliance for all extractions
            - UK retail platform product structures (ASDA, Tesco, Waitrose, etc.)
            - Vendor-specific pricing formats and currency handling (GBP)
            - Product weight extraction for grocery and retail items
            - Category standardization across different vendor taxonomies
            - Handling vendor-specific product variants and options
            - Extracting product images with proper URL resolution
            - Managing dynamic content and JavaScript-rendered data per vendor
            - Recognizing vendor-specific structured data markup
            - Dealing with UK-specific product information (weights, sizes, etc.)
            """,
            "verbose": True,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": False
        }

        if llm:
            agent_config["llm"] = llm

        self.agent = Agent(**agent_config)

    def create_standardized_extraction_task(self, vendor: str, category: str, session_id: str):
        """Create a task for extracting products using the StandardizedProduct schema."""
        from crewai import Task

        # Get vendor-specific configuration
        site_config = get_site_config_by_vendor(vendor)
        if not site_config:
            raise ValueError(f"No configuration found for vendor: {vendor}")

        task_description = f"""
        Extract product data from {vendor} using the StandardizedProduct schema format.

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}

        CRITICAL: Extract data in this EXACT StandardizedProduct format:
        {{
            "name": "Product title/name (string, required, min 1 char)",
            "description": "Product description (string, required, min 1 char)",
            "price": {{
                "current": 10.99,  // Current price as float
                "currency": "GBP",  // Always GBP for UK retailers
                "original": 15.99,  // Original price if on sale (optional)
                "discount_percentage": 33.3  // Calculated discount % (optional)
            }},
            "image_url": "Primary product image URL (string, required)",
            "category": "{category}",  // Use the provided category
            "vendor": "{vendor}",      // Use the provided vendor
            "weight": "Product weight if available (string, optional)",
            "scraped_at": "ISO timestamp (auto-generated)"
        }}

        EXTRACTION REQUIREMENTS:
        1. Extract ALL products visible on the current page
        2. Use vendor-specific selectors and patterns when available
        3. Ensure all required fields are populated
        4. Handle missing data gracefully (skip products with missing required fields)
        5. Extract accurate pricing information in GBP
        6. Get the primary/main product image URL
        7. Clean and normalize product names and descriptions
        8. Extract weight information for grocery items when available

        VENDOR-SPECIFIC CONSIDERATIONS:
        - Respect {vendor}'s specific HTML structure and CSS selectors
        - Handle {vendor}'s specific pricing display formats
        - Extract {vendor}'s specific product information layout
        - Use appropriate delays between extractions
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A JSON array of StandardizedProduct objects, each containing:
            - name: Product title (required)
            - description: Product description (required)
            - price: Pricing object with current, currency, and optional original/discount
            - image_url: Primary product image URL (required)
            - category: Product category (required)
            - vendor: Source vendor (required)
            - weight: Product weight if available (optional)
            - scraped_at: ISO timestamp (auto-generated)
            """
        )

    def create_basic_extraction_task(self, extraction_focus: str = "complete"):
        """Create a task for basic product data extraction."""
        from crewai import Task
        
        if extraction_focus == "complete":
            focus_description = "Extract all available product information comprehensively"
            extraction_list = """
            - Product title and full description
            - Current price, original price, and any discounts
            - Brand, model, and SKU information
            - Product availability and stock status
            - All product images and media
            - Customer ratings and review statistics
            - Product specifications and features
            - Available variants (sizes, colors, models, etc.)
            - Shipping and delivery information
            - Product categories and tags
            """
        elif extraction_focus == "pricing":
            focus_description = "Focus primarily on pricing and availability information"
            extraction_list = """
            - Current selling price
            - Original/MSRP price
            - Discount percentage and savings
            - Currency information
            - Price variations for different variants
            - Availability status
            - Stock quantity if visible
            """
        elif extraction_focus == "media":
            focus_description = "Focus on extracting product images and media content"
            extraction_list = """
            - All product images (main and additional)
            - Product videos if available
            - 360-degree views or interactive media
            - Variant-specific images
            - Image alt text and descriptions
            """
        else:
            focus_description = f"Focus on extracting: {extraction_focus}"
            extraction_list = f"- {extraction_focus}"
        
        task_description = f"""
        Extract product information from the current page with focus on: {focus_description}

        CRITICAL: You MUST use the Web Automation Tool (Stagehand) to actually extract data from the real website.
        DO NOT generate fake or mock data. Only return data that you actually extract from the live website.

        Extraction targets:
        {extraction_list}

        Your task is to:
        1. Use the Web Automation Tool to analyze the current page structure and identify product information sections
        2. Use the Web Automation Tool to extract the specified information using appropriate selectors and methods
        3. Handle dynamic content that may load after initial page load
        4. Ensure all extracted data is accurate and complete
        5. Format the data in a structured JSON format
        6. Handle any extraction errors gracefully

        Extraction strategies:
        - ALWAYS use the Web Automation Tool for data extraction
        - Extract only real data from the actual website - never generate fake data
        - Use semantic HTML elements and common class names
        - Look for structured data markup (JSON-LD, microdata)
        - Handle JavaScript-rendered content appropriately
        - Extract from multiple sources if information is scattered
        - Validate extracted data for consistency
        - Handle different formats and layouts gracefully
        - If extraction fails, report the error rather than generating fake data

        Return the extracted data in a clean, structured format.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A structured JSON object containing all successfully extracted product information.
            Include confidence levels or notes about data quality where appropriate.
            If any extraction fails, note the issue and continue with other data points.
            """
        )
    
    def create_variant_extraction_task(self):
        """Create a task specifically for extracting product variants."""
        from crewai import Task
        
        task_description = """
        Extract detailed information about product variants (sizes, colors, models, etc.).
        
        Your task is to:
        1. Identify all available product variants on the page
        2. For each variant, extract:
           - Variant name and type (size, color, model, etc.)
           - Variant-specific pricing if different
           - Availability status for each variant
           - Variant-specific images if available
           - SKU or identifier for each variant
        3. Handle interactive variant selectors (dropdowns, buttons, swatches)
        4. Test variant selection to see if it changes page content
        5. Capture any variant-specific information that appears
        
        Variant extraction strategies:
        - Look for size charts, color swatches, model selectors
        - Test clicking/selecting different variants to see content changes
        - Extract from variant selection dropdowns or radio buttons
        - Check for variant-specific URLs or parameters
        - Look for inventory status per variant
        - Capture variant images that change with selection
        
        Be thorough but efficient in testing different variant combinations.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A detailed JSON structure containing all product variants with their
            specific attributes, pricing, availability, and any variant-specific content.
            Include information about how variants are organized and selected on the page.
            """
        )
    
    def create_review_extraction_task(self):
        """Create a task for extracting customer review information."""
        from crewai import Task
        
        task_description = """
        Extract comprehensive customer review and rating information.
        
        Your task is to:
        1. Find the customer review section on the product page
        2. Extract overall rating information:
           - Average rating (stars/score)
           - Total number of reviews
           - Rating distribution (5-star, 4-star, etc.)
        3. Extract individual review details if accessible:
           - Review text snippets
           - Individual ratings
           - Review dates
           - Reviewer information (if available)
           - Helpful/unhelpful votes
        4. Look for review filters and sorting options
        5. Check if there are links to full review pages
        
        Review extraction strategies:
        - Look for star ratings, numerical scores, or percentage ratings
        - Find review count indicators
        - Extract rating histograms or distributions
        - Look for review summary statistics
        - Check for verified purchase indicators
        - Handle paginated reviews if accessible
        
        Focus on aggregate statistics rather than individual review content.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A JSON object containing comprehensive review information including
            overall ratings, review counts, rating distributions, and any
            additional review metadata available on the product page.
            """
        )
    
    def create_specification_extraction_task(self):
        """Create a task for extracting detailed product specifications."""
        from crewai import Task
        
        task_description = """
        Extract detailed product specifications and technical information.
        
        Your task is to:
        1. Locate product specification sections (specs, details, features)
        2. Extract technical specifications in key-value format
        3. Capture product features and highlights
        4. Extract dimension, weight, and physical attributes
        5. Capture compatibility information if relevant
        6. Extract warranty and support information
        7. Look for downloadable manuals or documentation links
        
        Specification extraction strategies:
        - Look for specification tables or lists
        - Extract from product description sections
        - Find technical details tabs or accordions
        - Look for feature bullet points or highlights
        - Extract from product comparison tables
        - Check for expandable specification sections
        - Look for manufacturer specifications
        
        Organize specifications into logical categories when possible.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A structured JSON object containing all product specifications
            organized by category (technical specs, physical attributes,
            features, compatibility, etc.). Include any additional technical
            information or documentation links found.
            """
        )
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent
