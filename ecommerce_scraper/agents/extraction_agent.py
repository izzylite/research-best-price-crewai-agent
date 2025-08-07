"""ExtractionAgent - Specialized agent for StandardizedProduct data extraction with re-extraction support."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from ..config.settings import settings
from ..config.sites import get_site_config_by_vendor, SiteConfig


class ExtractionAgent:
    """Specialized agent for StandardizedProduct data extraction with feedback loop support."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the extraction agent with StagehandTool + PriceExtractor + ImageExtractor."""
        # Handle both old (tools, llm) and new (stagehand_tool, verbose) calling patterns
        if stagehand_tool is not None:
            # New Flow-based calling pattern
            tools = [stagehand_tool] if stagehand_tool else []
        elif tools is None:
            tools = []
        
        agent_config = {
            "role": "StandardizedProduct Data Extraction Specialist",
            "goal": """
            Extract comprehensive and accurate product information from prepared ecommerce pages,
            ensuring strict StandardizedProduct schema compliance. Process re-extraction requests
            from ValidationAgent to improve data quality through feedback loops.
            """,
            "backstory": """
            You are a specialized data extraction expert focused purely on extracting product data
            from web pages that have been prepared by the NavigationAgent. You never navigate or
            handle popups - you only extract data from pages that are ready for extraction.
            
            Your core expertise includes:
            - StandardizedProduct schema compliance for all extractions
            - UK retail platform product data structures (ASDA, Tesco, Waitrose, etc.)
            - Vendor-specific pricing formats and GBP currency handling
            - Product weight extraction for grocery and retail items
            - Category standardization across different vendor taxonomies
            - High-resolution product image URL extraction
            - Re-extraction based on ValidationAgent feedback
            - Handling vendor-specific product variants and options
            - Managing dynamic content and JavaScript-rendered data
            - Recognizing vendor-specific structured data markup
            - Quality improvement through iterative extraction
            
            CRITICAL: You NEVER navigate pages or handle popups. You only extract data from
            pages that are already prepared and ready. You focus purely on data extraction
            accuracy and StandardizedProduct schema compliance.
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": settings.enable_crew_memory
        }

        if llm:
            agent_config["llm"] = llm

        self.agent = Agent(**agent_config)

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    def create_extraction_task(self, vendor: str, category: str, page_number: int = 1, feedback=None, **kwargs):
        """Alias for create_product_extraction_task to match Flow calling pattern."""
        return self.create_product_extraction_task(
            vendor=vendor,
            category=category,
            page_number=page_number,
            session_id=kwargs.get('session_id'),
            feedback=feedback
        )

    def create_product_extraction_task(self,
                                     vendor: str,
                                     category: str,
                                     page_number: int = 1,
                                     session_id: str = None,
                                     feedback: Dict[str, Any] = None):
        """Create a task for extracting products from a prepared page."""
        from crewai import Task
        from ..schemas.standardized_product import StandardizedProduct

        # Get vendor-specific configuration
        site_config = get_site_config_by_vendor(vendor)
        
        # Handle re-extraction feedback
        feedback_instructions = ""
        if feedback:
            feedback_instructions = f"""
            RE-EXTRACTION FEEDBACK FROM VALIDATION:
            Issues to address: {feedback.get('issues', [])}
            Suggestions: {feedback.get('suggestions', [])}
            Retry attempt: {feedback.get('retry_count', 1)} of {feedback.get('max_retries', 3)}
            
            FOCUS ON FIXING THESE SPECIFIC ISSUES:
            {chr(10).join(f"- {issue}" for issue in feedback.get('issues', []))}
            
            APPLY THESE SUGGESTIONS:
            {chr(10).join(f"- {suggestion}" for suggestion in feedback.get('suggestions', []))}
            """

        task_description = f"""
        Extract all products from the {vendor} {category} page.

        The page is already prepared - just extract the product data.

        Use simplified_stagehand_tool with:
        - operation: "extract"
        - instruction: "Extract all products from this page. For each product get: name, description, price, image URL from img src attribute, weight, category, and vendor"

        {feedback_instructions}

        Extract all products from the page. Return valid JSON array only.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Valid JSON array of products extracted from the page.

            Example format:
            [
              {{
                "name": "Product Name",
                "description": "Product Description",
                "price": {{"amount": 10.99, "currency": "GBP"}},
                "image_url": "https://example.com/image.jpg",
                "category": "{category}",
                "vendor": "{vendor}",
                "weight": "optional weight",
                "scraped_at": "2025-01-04T12:34:56Z"
              }}
            ]

            TOOL USAGE:
            Tool: simplified_stagehand_tool
            Action Input: {{"operation": "extract", "instruction": "Extract all products from this page. For each product get the name, description, price, image URL, and weight. Return as JSON array with no comments."}}

            SIMPLE EXTRACTION PROCESS:
            1. Call simplified_stagehand_tool with {{"operation": "extract", "instruction": "Extract all products from this page. For each product get the name, description, price, image URL, and weight. Return as JSON array with no comments."}}
            2. Return the extracted data as valid JSON
            3. Use only real data from the page

            REMEMBER: Always use "simplified_stagehand_tool" as the tool name, never use "extract", "observe" as tool names.

            EXPECTED RESULTS:
            - Navigation Agent has prepared the page with all products visible
            - ASDA fruit pages typically show 60+ products after preparation
            - Extract ALL products found on the prepared page using schema-based extraction
            - Return structured JSON data matching StandardizedProduct schema

            CRITICAL REQUIREMENTS:
            - NEVER generate fake data like "Banana" with "https://example.com" URLs
            - ONLY extract real product data from the prepared page
            - DO NOT navigate - the Navigation Agent has already prepared the page
            - Return valid JSON array without comments or additional text
            - Extract ALL products on the page, not just 1-2 products
            - Use product name as description if no description available
            - Return only products that meet StandardizedProduct schema requirements
            - Skip any products missing required fields rather than including incomplete data

            CRITICAL: Return valid JSON only - no comments, no explanations, no truncation.
            """
        )

    def create_re_extraction_task(self, 
                                vendor: str, 
                                category: str, 
                                feedback: Dict[str, Any],
                                page_number: int = 1,
                                session_id: str = None):
        """Create a task for re-extracting products based on ValidationAgent feedback."""
        from crewai import Task

        issues = feedback.get('issues', [])
        suggestions = feedback.get('suggestions', [])
        retry_count = feedback.get('retry_count', 1)
        max_retries = feedback.get('max_retries', 3)

        task_description = f"""
        Re-extract product data from {vendor} {category} page based on validation feedback.
        
        Vendor: {vendor}
        Category: {category}
        Page Number: {page_number}
        Session ID: {session_id}
        Retry Attempt: {retry_count} of {max_retries}

        VALIDATION FEEDBACK TO ADDRESS:
        Issues Found:
        {chr(10).join(f"- {issue}" for issue in issues)}
        
        Improvement Suggestions:
        {chr(10).join(f"- {suggestion}" for suggestion in suggestions)}

        RE-EXTRACTION STRATEGY:
        1. **Focus specifically on the identified issues**
        2. **Apply the suggested improvements**
        3. **Use alternative selectors if previous ones failed**
        4. **Look for additional data sources on the page**
        5. **Improve data cleaning and normalization**
        6. **Verify all required fields are properly extracted**

        ENHANCED EXTRACTION APPROACH:
        - Try multiple selector strategies for missing data
        - Look for alternative product information sources
        - Improve text cleaning and normalization
        - Verify image URLs are accessible and high-quality
        - Double-check price extraction and formatting
        - Ensure descriptions are meaningful and complete

        QUALITY IMPROVEMENT FOCUS:
        - Address each specific issue mentioned in feedback
        - Implement suggested extraction improvements
        - Verify data completeness and accuracy
        - Ensure StandardizedProduct schema compliance
        - Improve overall extraction quality

        CRITICAL: This is a focused re-extraction to fix specific issues.
        Apply the feedback suggestions and improve upon the previous extraction attempt.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Improved extraction result addressing validation feedback:
            {{
              "extraction_batch": [
                {{
                  "name": "Improved Product Name",
                  "description": "Complete Product Description",
                  "price": {{"current": 10.99, "currency": "GBP", "original": 12.99}},
                  "image_url": "https://high-quality-image-url",
                  "category": "{category}",
                  "vendor": "{vendor}",
                  "weight": "extracted weight if available",
                  "scraped_at": "2025-01-04T12:34:56Z"
                }}
              ],
              "extraction_metadata": {{
                "page_number": {page_number},
                "products_found": <number_of_products>,
                "extraction_method": "re_extraction",
                "retry_count": {retry_count},
                "issues_addressed": {issues},
                "suggestions_applied": {suggestions},
                "improvement_notes": "Description of improvements made"
              }}
            }}
            
            Show clear improvement over previous extraction attempt.
            Address all validation feedback issues and apply suggested improvements.
            """
        )

    def create_batch_extraction_task(self,
                                   vendor: str,
                                   category: str,
                                   batch_size: int = 50,
                                   page_number: int = 1,
                                   session_id: str = None):
        """Create a task for batch extraction of products with size limits."""
        from crewai import Task

        task_description = f"""
        Extract products in batches to optimize memory usage and processing efficiency.

        Vendor: {vendor}
        Category: {category}
        Batch Size: {batch_size} products maximum
        Page Number: {page_number}
        Session ID: {session_id}

        BATCH EXTRACTION STRATEGY:
        1. **Identify all products on the prepared page**
        2. **Process products in batches of {batch_size} maximum**
        3. **Extract complete StandardizedProduct data for each batch**
        4. **Ensure consistent quality across all batches**
        5. **Handle memory efficiently by processing in chunks**

        BATCH PROCESSING REQUIREMENTS:
        - Extract up to {batch_size} products per batch
        - Maintain StandardizedProduct schema compliance
        - Ensure all required fields are present
        - Process products in logical order (top to bottom, left to right)
        - Handle incomplete products gracefully

        MEMORY OPTIMIZATION:
        - Process products incrementally
        - Clear intermediate data between products
        - Optimize image URL extraction
        - Minimize memory footprint during extraction

        QUALITY CONSISTENCY:
        - Apply same extraction standards to all products
        - Maintain consistent data formatting
        - Ensure uniform field population
        - Verify batch completeness before returning

        CRITICAL: Focus on extraction efficiency while maintaining data quality.
        Process only the prepared page content without navigation.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Batch extraction result:
            {{
              "extraction_batch": [

              ],
              "batch_metadata": {{
                "batch_size": <actual_products_in_batch>,
                "max_batch_size": {batch_size},
                "page_number": {page_number},
                "total_products_on_page": <total_products_detected>,
                "batch_complete": <true/false>,
                "processing_notes": "Any relevant processing information"
              }}
            }}

            Ensure efficient processing while maintaining StandardizedProduct compliance.
            """
        )

    def create_quality_focused_extraction_task(self,
                                             vendor: str,
                                             category: str,
                                             quality_requirements: Dict[str, Any] = None,
                                             session_id: str = None):
        """Create a task for high-quality extraction with specific requirements."""
        from crewai import Task

        quality_requirements = quality_requirements or {
            "min_description_length": 10,
            "require_weight": False,
            "require_original_price": False,
            "image_quality": "high"
        }

        task_description = f"""
        Extract products with enhanced quality standards and specific requirements.

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}
        Quality Requirements: {quality_requirements}

        ENHANCED QUALITY STANDARDS:
        - Minimum description length: {quality_requirements.get('min_description_length', 10)} characters
        - Weight extraction required: {quality_requirements.get('require_weight', False)}
        - Original price required: {quality_requirements.get('require_original_price', False)}
        - Image quality level: {quality_requirements.get('image_quality', 'standard')}

        QUALITY EXTRACTION PROCESS:
        1. **Apply enhanced data validation during extraction**
        2. **Verify all quality requirements are met**
        3. **Use multiple extraction strategies for better coverage**
        4. **Implement advanced text cleaning and normalization**
        5. **Ensure high-quality image URL extraction**
        6. **Skip products that don't meet quality standards**

        ADVANCED EXTRACTION TECHNIQUES:
        - Multiple selector strategies for robust data capture
        - Enhanced text processing and cleaning
        - Advanced price parsing and validation
        - High-resolution image URL prioritization
        - Comprehensive product description extraction
        - Weight and measurement extraction for applicable products

        QUALITY VALIDATION:
        - Verify each product meets specified quality requirements
        - Ensure data completeness and accuracy
        - Validate image URLs are accessible
        - Check price formatting and currency consistency
        - Confirm description quality and relevance

        CRITICAL: Only return products that meet the enhanced quality standards.
        Skip products that don't meet requirements rather than lowering standards.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            High-quality extraction result:
            {{
              "extraction_batch": [

              ],
              "quality_metadata": {{
                "products_extracted": <number_of_quality_products>,
                "products_skipped": <number_skipped_for_quality>,
                "quality_requirements": {quality_requirements},
                "quality_score": <average_quality_score>,
                "extraction_notes": "Quality-focused extraction details"
              }}
            }}

            All products meet enhanced quality standards and requirements.
            """
        )

    def create_product_search_extraction_task(self,
                                            product_query: str,
                                            retailer: str,
                                            retailer_url: str,
                                            session_id: str = None):
        """
        Create a task for targeted product search extraction focusing on core fields.

        Uses custom schema for extraction:
        {
          "fields": {
            "name": "str",           // Product name as displayed
            "image": "optional_url", // Main product image URL (HttpUrl validation)
            "price": "str"           // Product price in GBP format (£XX.XX)
          },
          "name": "Product",
          "is_list": true
        }

        Args:
            product_query: Specific product to search for
            retailer: Name of the retailer website
            retailer_url: URL to navigate to for extraction
            session_id: Optional session identifier for tracking

        Returns:
            CrewAI Task configured for product extraction with schema validation
        """
        from crewai import Task

        task_description = f"""
        You are tasked with extracting product information from the {retailer} website for "{product_query}".
         Your goal is to navigate to the provided URL and extract product name, image URL, and price using the simplified_stagehand_tool function.

        **EXTRACTION PARAMETERS:**
        Product Query: {product_query}
        Retailer: {retailer}
        Target URL: {retailer_url}
        Session ID: {session_id}

        **AVAILABLE TOOL:**
        - simplified_stagehand_tool: Use this for all navigation and extraction operations

        **STEP-BY-STEP PROCESS:**
        1. **Navigate to URL:** Use simplified_stagehand_tool with operation "navigate" to go to {retailer_url}
        2. **Handle Popups:** Use simplified_stagehand_tool with operation "act" to dismiss any popups, cookie banners, or overlays
        3. **Search if needed:** If the URL is not a direct product page, use simplified_stagehand_tool with operation "act" to search for "{product_query}"
        4. **Extract Product Data:** Use simplified_stagehand_tool with operation "extract" and custom schema to get:
           - Product name (exact name as displayed)
           - Product image URL (main product image)
           - Product price (in GBP format with £ symbol)

        **CUSTOM EXTRACTION SCHEMA:**
        Use this exact schema definition for extraction:
        {{
          "fields": {{
            "name": "str",
            "image": "optional_url",
            "price": "str"
          }},
          "name": "Product",
          "is_list": true
        }}

        **EXTRACTION REQUIREMENTS:**
        - Focus on products that match or closely relate to "{product_query}"
        - Extract main product image URLs (not thumbnails or icons)
        - Ensure prices are in GBP format (£XX.XX)
        - Get direct product page URLs when possible
        - Handle errors gracefully and document any issues

        **ERROR HANDLING:**
        - If navigation fails, document the error
        - If product information is incomplete, extract what's available
        - If no matching products found, report this clearly
        - Include error details in the response for debugging

        **CRITICAL INSTRUCTIONS:**
        1. Always use the exact tool name "simplified_stagehand_tool"
        2. Use appropriate operation parameters: "navigate", "act", or "extract"
        3. For extraction, include the custom schema parameter:
           Tool: simplified_stagehand_tool
           Action Input: {{
             "operation": "extract",
             "instruction": "Extract product information for {product_query}",
             "schema": {{
               "fields": {{"name": "str", "image": "optional_url", "price": "str"}},
               "name": "Product",
               "is_list": true
             }}
           }}
        4. Focus on extracting complete product information (name, image, price)
        5. Validate that extracted data is relevant to "{product_query}"
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Your final output should be a valid JSON string containing product information. Enclose your entire response within <json_output> tags.

            Expected JSON structure:
            <json_output>
            {{
              "products": [
                {{
                  "url": "{retailer_url}",
                  "name": "Exact product name from site",
                  "image": "https://example.com/images/product.jpg",
                  "price": "£XX.XX"
                }}
              ],
              "errors": [
                "Any error messages encountered during extraction"
              ],
              "extraction_summary": {{
                "search_query": "{product_query}",
                "retailer": "{retailer}",
                "total_products_found": <number>,
                "extraction_successful": <true/false>
              }}
            }}
            </json_output>

            **IMPORTANT:**
            - Include the <json_output> tags around your JSON response
            - If no errors occur, you may omit the "errors" key
            - Ensure all URLs, names, images, and prices are accurately extracted
            - Handle any extraction errors gracefully and include them in the errors array
            """
        )

    def create_multi_url_extraction_task(self,
                                       urls: List[str],
                                       product_query: str = "",
                                       session_id: str = None):
        """
        Create a task for extracting product information from multiple URLs.

        Uses custom schema for each URL extraction:
        {
          "fields": {
            "name": "str",           // Product name as displayed
            "image": "optional_url", // Main product image URL (HttpUrl validation)
            "price": "str"           // Product price in GBP format (£XX.XX)
          },
          "name": "Product",
          "is_list": false          // Single product per URL
        }

        Expected output format:
        {
          "products": [
            {
              "url": "https://example.com/product1",
              "name": "Product Name",
              "image": "https://example.com/image.jpg",
              "price": "£19.99"
            }
          ],
          "errors": ["Error messages if any"],
          "extraction_summary": {
            "total_urls_processed": N,
            "successful_extractions": N,
            "failed_extractions": N
          }
        }

        Args:
            urls: List of product URLs to extract information from
            product_query: Optional context about what product to look for
            session_id: Optional session identifier for tracking

        Returns:
            CrewAI Task configured for multi-URL extraction with error handling
        """
        from crewai import Task

        urls_formatted = "\n".join(f"- {url}" for url in urls)

        task_description = f"""
        You are tasked with extracting product information from a list of URLs. Your goal is to navigate to each provided URL and extract the product name, image URL, and price using the simplified_stagehand_tool function. You will then compile this information into a JSON format.

        **EXTRACTION PARAMETERS:**
        Product Query Context: {product_query if product_query else "General product extraction"}
        Session ID: {session_id}
        Total URLs to Process: {len(urls)}

        **AVAILABLE TOOL:**
        - simplified_stagehand_tool: Use this for all navigation and extraction operations

        **STEP-BY-STEP PROCESS FOR EACH URL:**
        1. **Navigate to URL:** Use simplified_stagehand_tool with operation "navigate" to go to the URL
        2. **Handle Popups:** Use simplified_stagehand_tool with operation "act" to dismiss any popups, cookie banners, or overlays
        3. **Extract Product Data:** Use simplified_stagehand_tool with operation "extract" and custom schema:
           Tool: simplified_stagehand_tool
           Action Input: {{
             "operation": "extract",
             "instruction": "Extract product name, image URL, and price from this page",
             "schema": {{
               "fields": {{"name": "str", "image": "optional_url", "price": "str"}},
               "name": "Product",
               "is_list": false
             }}
           }}
        4. **Handle Errors:** If extraction fails for any URL, document the error and continue with next URL

        **EXTRACTION REQUIREMENTS:**
        - Extract main product image URLs (full-size images, not thumbnails or icons)
        - Ensure prices are in GBP format (£XX.XX) or note if different currency
        - Get exact product names as displayed on the site
        - Handle errors gracefully and document any issues
        - Process all URLs even if some fail

        **ERROR HANDLING:**
        - If navigation fails for a URL, document the error and continue
        - If product information is incomplete, extract what's available
        - If a page doesn't contain product information, note this
        - Include all error details in the response for debugging

        **CRITICAL INSTRUCTIONS:**
        1. Always use the exact tool name "simplified_stagehand_tool"
        2. Use appropriate operation parameters: "navigate", "act", or "extract"
        3. Process each URL independently
        4. Compile results into the specified JSON format

        **URLs TO PROCESS:**
        {urls_formatted}
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Your final output should be a valid JSON string containing an array of product objects and any error messages. Enclose your entire response within <json_output> tags.

            Expected JSON structure:
            <json_output>
            {{
              "products": [
                {{
                  "url": "https://example.com/product1",
                  "name": "Example Product 1",
                  "image": "https://example.com/images/product1.jpg",
                  "price": "£19.99"
                }},
                {{
                  "url": "https://example.com/product2",
                  "name": "Example Product 2",
                  "image": "https://example.com/images/product2.jpg",
                  "price": "£29.99"
                }}
              ],
              "errors": [
                "Unable to extract information from https://example.com/product3: Page not found",
                "Navigation failed for https://example.com/product4: Timeout"
              ],
              "extraction_summary": {{
                "total_urls_processed": {len(urls)},
                "successful_extractions": <number>,
                "failed_extractions": <number>,
                "extraction_complete": true
              }}
            }}
            </json_output>

            **IMPORTANT:**
            - Include the <json_output> tags around your JSON response
            - If no errors occur, you may omit the "errors" key from the JSON output
            - Ensure all URLs, names, images, and prices are accurately extracted
            - Handle any extraction errors gracefully and include them in the errors array
            - Process all {len(urls)} URLs provided in the list
            """
        )

    def create_feedback_enhanced_extraction_task(self,
                                               product_query: str,
                                               retailer: str,
                                               retailer_url: str,
                                               validation_feedback: Dict[str, Any],
                                               attempt_number: int = 1,
                                               session_id: str = None):
        """
        Create a task for feedback-enhanced product extraction that uses validation feedback to improve results.

        Uses validation feedback to guide extraction improvements:
        - Primary issues from previous attempt
        - Retry recommendations for better extraction
        - Extraction improvements suggested by validation
        - Alternative search strategies

        Uses custom schema for extraction:
        {
          "fields": {
            "name": "str",           // Product name as displayed
            "image": "optional_url", // Main product image URL (HttpUrl validation)
            "price": "str"           // Product price in GBP format (£XX.XX)
          },
          "name": "Product",
          "is_list": true
        }

        Args:
            product_query: Specific product to search for
            retailer: Name of the retailer website
            retailer_url: URL to navigate to for extraction
            validation_feedback: Feedback from previous validation attempt
            attempt_number: Current retry attempt number
            session_id: Optional session identifier for tracking

        Returns:
            CrewAI Task configured for feedback-enhanced extraction
        """
        from crewai import Task

        # Extract feedback components
        primary_issues = validation_feedback.get('primary_issues', [])
        retry_recommendations = validation_feedback.get('retry_recommendations', [])
        extraction_improvements = validation_feedback.get('extraction_improvements', [])
        search_refinements = validation_feedback.get('search_refinements', [])

        # Format feedback for task description
        issues_text = "\n".join(f"- {issue}" for issue in primary_issues) if primary_issues else "- No specific issues identified"
        recommendations_text = "\n".join(f"- {rec}" for rec in retry_recommendations) if retry_recommendations else "- Use standard extraction approach"
        improvements_text = "\n".join(f"- {imp}" for imp in extraction_improvements) if extraction_improvements else "- Focus on core product fields"
        refinements_text = "\n".join(f"- {ref}" for ref in search_refinements) if search_refinements else "- Use original search query"

        task_description = f"""
        You are tasked with extracting product information from the {retailer} website for "{product_query}".
        This is retry attempt #{attempt_number} with validation feedback to improve extraction quality.

        **EXTRACTION PARAMETERS:**
        Product Query: {product_query}
        Retailer: {retailer}
        Target URL: {retailer_url}
        Retry Attempt: {attempt_number}
        Session ID: {session_id}

        **VALIDATION FEEDBACK FROM PREVIOUS ATTEMPT:**

        Primary Issues Identified:
        {issues_text}

        Retry Recommendations:
        {recommendations_text}

        Extraction Improvements Needed:
        {improvements_text}

        Search Query Refinements:
        {refinements_text}

        **FEEDBACK-ENHANCED EXTRACTION PROCESS:**
        1. **Navigate to URL:** Use simplified_stagehand_tool with operation "navigate" to go to {retailer_url}
        2. **Handle Popups:** Use simplified_stagehand_tool with operation "act" to dismiss any popups, cookie banners, or overlays
        3. **Apply Feedback:** Implement the retry recommendations and extraction improvements listed above
        4. **Enhanced Search:** If search refinements are suggested, try alternative search terms or approaches
        5. **Improved Extraction:** Use simplified_stagehand_tool with operation "extract" and custom schema, focusing on the identified issues

        **CUSTOM EXTRACTION SCHEMA:**
        Use this exact schema definition for extraction:
        {{
          "fields": {{
            "name": "str",
            "image": "optional_url",
            "price": "str"
          }},
          "name": "Product",
          "is_list": true
        }}

        **EXTRACTION REQUIREMENTS:**
        - Address all primary issues identified in the feedback
        - Focus on products that closely match "{product_query}"
        - Ensure product names are relevant and accurate
        - Get high-quality product image URLs (main images, not thumbnails)
        - Ensure prices are in GBP format with £ symbol
        - Validate that extracted data addresses previous validation failures

        **CRITICAL INSTRUCTIONS:**
        1. Always use the exact tool name "simplified_stagehand_tool"
        2. Use appropriate operation parameters: "navigate", "act", or "extract"
        3. For extraction, include the custom schema parameter:
           Tool: simplified_stagehand_tool
           Action Input: {{
             "operation": "extract",
             "instruction": "Extract product information for {product_query}, addressing previous validation issues",
             "schema": {{
               "fields": {{"name": "str", "image": "optional_url", "price": "str"}},
               "name": "Product",
               "is_list": true
             }}
           }}
        4. Apply all feedback recommendations to improve extraction quality
        5. Focus on resolving the specific issues identified in previous attempt
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Your final output should be a valid JSON string containing improved product information. Enclose your entire response within <json_output> tags.

            Expected JSON structure:
            <json_output>
            {{
              "products": [
                {{
                  "url": "{retailer_url}",
                  "name": "Exact product name from site",
                  "image": "https://example.com/images/product.jpg",
                  "price": "£XX.XX"
                }}
              ],
              "errors": [
                "Any error messages encountered during extraction"
              ],
              "extraction_summary": {{
                "search_query": "{product_query}",
                "retailer": "{retailer}",
                "retry_attempt": {attempt_number},
                "feedback_applied": true,
                "total_products_found": <number>,
                "extraction_successful": <true/false>,
                "improvements_made": [
                  "List of specific improvements made based on feedback"
                ]
              }}
            }}
            </json_output>

            **IMPORTANT:**
            - Include the <json_output> tags around your JSON response
            - Address all validation feedback from the previous attempt
            - If no errors occur, you may omit the "errors" key
            - Ensure all URLs, names, images, and prices are accurately extracted
            - Document what improvements were made based on the feedback
            """
        )
