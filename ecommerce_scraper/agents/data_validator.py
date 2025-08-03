"""Data validation agent specialized in cleaning and validating extracted product data."""

from typing import List, Optional
from crewai import Agent, LLM


class DataValidatorAgent:
    """Agent specialized in validating, cleaning, and standardizing extracted product data."""
    
    def __init__(self, tools: List, llm: Optional[LLM] = None):
        """Initialize the data validator agent with required tools."""

        agent_config = {
            "role": "Product Data Quality Specialist",
            "goal": """
            Validate, clean, and standardize extracted product data to ensure
            high quality, consistency, and compliance with the defined schema.
            """,
            "backstory": """
            You are a data quality expert with extensive experience in ecommerce data
            standardization and validation. You understand the common issues that arise
            when extracting data from different websites and know how to clean and
            normalize data for consistency.

            Your expertise includes:
            - Data type validation and conversion
            - Price format standardization across currencies
            - URL validation and resolution
            - Text cleaning and normalization
            - Data completeness assessment
            - Duplicate detection and removal
            - Schema compliance validation
            - Data quality scoring and reporting
            - Handling missing or malformed data
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
    
    def create_validation_task(self, validation_level: str = "comprehensive"):
        """Create a task for validating extracted product data."""
        from crewai import Task
        
        if validation_level == "comprehensive":
            validation_description = "Perform comprehensive validation of all product data"
            validation_checks = """
            - Schema compliance validation
            - Data type validation and conversion
            - Price format standardization
            - URL validation and resolution
            - Text cleaning and normalization
            - Data completeness assessment
            - Logical consistency checks
            - Duplicate detection
            - Data quality scoring
            """
        elif validation_level == "basic":
            validation_description = "Perform basic validation focusing on critical fields"
            validation_checks = """
            - Required field validation
            - Basic data type checking
            - Price format validation
            - URL format validation
            - Text cleaning
            """
        elif validation_level == "pricing":
            validation_description = "Focus validation on pricing and financial data"
            validation_checks = """
            - Price format validation and conversion
            - Currency standardization
            - Discount calculation verification
            - Price range validation
            - Financial data consistency
            """
        else:
            validation_description = f"Custom validation focusing on: {validation_level}"
            validation_checks = f"- {validation_level}"
        
        task_description = f"""
        Validate and clean the extracted product data with focus on: {validation_description}
        
        Validation checks to perform:
        {validation_checks}
        
        Your task is to:
        1. Receive the raw extracted product data
        2. Validate the data against the Product schema
        3. Clean and standardize data formats
        4. Convert data types as needed
        5. Resolve relative URLs to absolute URLs
        6. Standardize price formats and currencies
        7. Clean and normalize text fields
        8. Assess data completeness and quality
        9. Generate a data quality report
        10. Return the cleaned and validated data
        
        Data cleaning strategies:
        - Remove extra whitespace and normalize text
        - Standardize price formats (handle different currencies)
        - Validate and resolve image URLs
        - Clean HTML tags from descriptions
        - Normalize product titles and descriptions
        - Validate email addresses and phone numbers
        - Check for logical inconsistencies
        - Handle missing or null values appropriately
        
        Provide detailed feedback on data quality issues found and resolved.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A JSON object containing:
            - validated_data: The cleaned and validated product data
            - quality_report: Assessment of data quality and completeness
            - issues_found: List of data quality issues discovered
            - issues_resolved: List of issues that were automatically fixed
            - recommendations: Suggestions for improving data extraction
            """
        )
    
    def create_schema_compliance_task(self):
        """Create a task for ensuring schema compliance."""
        from crewai import Task
        
        task_description = """
        Ensure the extracted product data complies with the defined Product schema.
        
        Your task is to:
        1. Validate the data structure against the Product schema
        2. Check for required fields and their data types
        3. Validate field constraints and formats
        4. Convert data types where possible
        5. Handle schema violations gracefully
        6. Generate a compliance report
        7. Suggest schema improvements if needed
        
        Schema compliance checks:
        - Required field presence
        - Data type validation (strings, numbers, dates, URLs)
        - Field format validation (emails, phone numbers, URLs)
        - Enum value validation (availability, condition)
        - Nested object validation (price, images, reviews)
        - Array field validation
        - Field length and range constraints
        
        For any schema violations, attempt to fix them automatically or
        provide clear guidance on how to resolve them.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A detailed compliance report including:
            - schema_compliant: Boolean indicating full compliance
            - compliance_score: Percentage of fields that comply
            - violations: List of schema violations found
            - auto_fixes: List of violations that were automatically corrected
            - manual_fixes_needed: List of issues requiring manual intervention
            - corrected_data: The schema-compliant version of the data
            """
        )
    
    def create_data_enrichment_task(self):
        """Create a task for enriching and enhancing product data."""
        from crewai import Task
        
        task_description = """
        Enrich and enhance the validated product data with additional insights.
        
        Your task is to:
        1. Calculate derived fields (discount percentages, price per unit)
        2. Enhance categorization and tagging
        3. Standardize brand and model names
        4. Generate product summaries or highlights
        5. Add data quality scores and confidence levels
        6. Identify potential data gaps or missing information
        7. Suggest additional data points that could be valuable
        
        Data enrichment strategies:
        - Calculate discount percentages from original and current prices
        - Standardize brand names (handle variations and misspellings)
        - Generate product categories from titles and descriptions
        - Extract key features from descriptions
        - Calculate price per unit where applicable
        - Identify seasonal or trending products
        - Add data freshness timestamps
        - Generate product quality scores
        
        Focus on adding value while maintaining data accuracy.
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            An enriched product data object containing:
            - original_data: The input data for reference
            - enriched_data: Enhanced product data with additional fields
            - derived_fields: List of calculated or derived data points
            - quality_scores: Data quality and confidence metrics
            - suggestions: Recommendations for additional data collection
            - metadata: Information about the enrichment process
            """
        )
    
    def create_duplicate_detection_task(self, product_list: List):
        """Create a task for detecting duplicate products in a list."""
        from crewai import Task
        
        task_description = f"""
        Detect and handle duplicate products in a list of {len(product_list)} products.
        
        Your task is to:
        1. Analyze the product list for potential duplicates
        2. Use multiple criteria for duplicate detection:
           - Exact title matches
           - Similar titles (fuzzy matching)
           - Matching SKUs or product IDs
           - Similar prices and descriptions
           - Matching image URLs
        3. Group potential duplicates together
        4. Determine the best representative for each duplicate group
        5. Provide recommendations for handling duplicates
        6. Generate a deduplicated product list
        
        Duplicate detection strategies:
        - Exact string matching for titles and SKUs
        - Fuzzy string matching for similar titles
        - Price range matching for similar products
        - Image URL comparison
        - Brand and model matching
        - Description similarity analysis
        
        When duplicates are found, prefer products with:
        - More complete information
        - Higher data quality scores
        - More recent scraping timestamps
        - Better image quality or more images
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A duplicate analysis report containing:
            - total_products: Original number of products
            - duplicates_found: Number of duplicate groups identified
            - duplicate_groups: Detailed information about each duplicate group
            - recommended_removals: Products recommended for removal
            - deduplicated_list: Clean list with duplicates resolved
            - deduplication_summary: Statistics about the process
            """
        )
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent
