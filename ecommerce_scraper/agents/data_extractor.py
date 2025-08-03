"""Data extraction agent specialized in extracting structured product information."""

from typing import List
from crewai import Agent


class DataExtractorAgent:
    """Agent specialized in extracting structured product data from ecommerce pages."""
    
    def __init__(self, tools: List):
        """Initialize the data extractor agent with required tools."""
        
        self.agent = Agent(
            role="Product Data Extraction Specialist",
            goal="""
            Extract comprehensive and accurate product information from ecommerce pages,
            ensuring all relevant data is captured in a structured format.
            """,
            backstory="""
            You are a data extraction expert with deep knowledge of ecommerce product structures
            across different platforms. You understand how product information is typically
            organized and can adapt your extraction strategies based on the site layout.
            
            Your expertise includes:
            - Identifying product titles, descriptions, and specifications
            - Extracting pricing information including sales and discounts
            - Capturing product images and media content
            - Understanding product variants and options
            - Extracting customer reviews and ratings
            - Handling dynamic content and JavaScript-rendered data
            - Recognizing structured data markup (JSON-LD, microdata)
            - Dealing with different currency formats and international sites
            """,
            verbose=True,
            allow_delegation=False,
            tools=tools,
            max_iter=4,
            memory=True
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
