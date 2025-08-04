"""Data validation agent specialized in cleaning and validating extracted product data."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Pydantic model for validation task output."""
    validated_products: List[Dict[str, Any]]
    validation_summary: Dict[str, Any]


class DataValidatorAgent:
    """Agent specialized in validating, cleaning, and standardizing extracted product data using StandardizedProduct schema."""

    def __init__(self, tools: List, llm: Optional[LLM] = None):
        """Initialize the data validator agent with required tools."""

        agent_config = {
            "role": "StandardizedProduct Data Validation Expert",
            "goal": """
            Validate, clean, and standardize extracted product data to ensure compliance with
            the StandardizedProduct schema and maintain high quality across all UK retail vendors.
            """,
            "backstory": """
            You are a data quality specialist with extensive experience in multi-vendor ecommerce
            data validation and StandardizedProduct schema compliance. You understand the specific
            data quality challenges when extracting from UK retail platforms.

            Your enhanced expertise includes:
            - StandardizedProduct schema validation and compliance
            - UK retail data standardization (GBP pricing, weights, etc.)
            - Multi-vendor data consistency across ASDA, Tesco, Waitrose, etc.
            - Price format validation and GBP currency standardization
            - Product weight validation and unit standardization
            - URL validation and image link verification
            - Text cleaning and normalization for UK product data
            - Category standardization across different vendor taxonomies
            - Duplicate detection across multiple vendors
            - Data completeness assessment for required schema fields
            - Quality scoring and vendor-specific data reporting
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

    def create_standardized_validation_task(self, vendor: str, category: str, session_id: str):
        """Create a task for validating extracted data against StandardizedProduct schema."""
        from crewai import Task

        task_description = f"""
        Validate and clean extracted product data to ensure StandardizedProduct schema compliance.

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}

        VALIDATION REQUIREMENTS:
        Validate each product against the StandardizedProduct schema:

        CRITICAL: You MUST convert all data to exact StandardizedProduct schema format:

        REQUIRED STANDARDIZATION CONVERSIONS:
        - price.current → price.amount (required field)
        - price.original → ignore (not in StandardizedProduct schema)
        - price.discount_percentage → ignore (not in StandardizedProduct schema)
        - Any other price fields → convert to price.amount

        REQUIRED FIELDS (exact StandardizedProduct schema):
        - name: Non-empty string, min 1 character
        - description: Non-empty string, min 1 character
        - price.amount: Valid float/number > 0 (converted from price.current)
        - price.currency: Must be "GBP" for UK retailers
        - image_url: Valid URL format
        - category: Must match provided category "{category}"
        - vendor: Must match provided vendor "{vendor}"
        - scraped_at: Valid ISO timestamp

        OPTIONAL FIELDS (exact StandardizedProduct schema):
        - weight: Valid weight string with units (null if not available)

        VALIDATION ACTIONS:
        1. Check all required fields are present and valid
        2. Validate data types and formats
        3. Standardize price formats to GBP
        4. Clean and normalize text fields
        5. Validate URL formats for images
        6. Remove products with missing required fields
        7. Calculate discount percentages if original price exists
        8. Standardize weight units and formats
        9. Ensure category and vendor consistency
        10. Generate validation report with statistics

        STANDARDIZATION RULES (CRITICAL - MUST FOLLOW EXACTLY):
        1. Convert price.current to price.amount (required)
        2. Remove any non-StandardizedProduct price fields (original, discount_percentage, etc.)
        3. Ensure price object only has: {{amount: number, currency: string}}
        4. Trim whitespace from all text fields
        5. Validate and fix image URLs
        6. Standardize weight units (g, kg, ml, l) or set to null
        7. Remove HTML tags from descriptions
        8. Ensure exact schema compliance

        VALIDATION FAILURE HANDLING:
        If the output fails StandardizedProduct validation, you MUST retry with corrections.
        The final output MUST pass StandardizedProduct(**item) validation.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="""
            A validation result containing:
            - validated_products: Array of StandardizedProduct objects with EXACT schema:
              [{{
                "name": "string",
                "description": "string",
                "price": {{"amount": number, "currency": "string"}},
                "image_url": "string",
                "category": "string",
                "vendor": "string",
                "scraped_at": "ISO timestamp",
                "weight": "string or null"
              }}]
            - validation_summary: {{
                "total_input": number of input products,
                "valid_products": number of products that passed validation,
                "invalid_products": number of products removed,
                "validation_errors": list of validation issues found,
                "vendor": vendor name,
                "category": category name,
                "session_id": session identifier
            }}

            CRITICAL: Each product in validated_products MUST pass StandardizedProduct(**product) validation.
            If validation fails, retry with corrections until it passes.
            """,
            output_json=ValidationResult
        )

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
