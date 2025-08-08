"""ExtractionAgent - Specialized agent for StandardizedProduct data extraction with re-extraction support."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from ..config.settings import settings
from ..config.settings import settings
from ..config.sites import get_site_config_by_vendor, SiteConfig
from ..schemas.agent_outputs import ExtractionResult


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
            You are a specialized product data extraction expert. Your primary responsibility is to
            extract high-quality product data that matches the search goal. When needed to complete
            extraction successfully, you may also perform lightweight navigation (goto a URL) and
            dismiss blocking popups before searching on the site or extracting data using the provided tool.

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
            
            CRITICAL: Prefer extracting from pages prepared by research and validation.
            If the page is not directly extractable, you may navigate to the target URL,
            handle simple popups, and proceed with schema-aligned extraction.
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": settings.enable_crew_memory
        }

        if llm:
            agent_config["llm"] = llm

        # If no LLM provided, respect configured model for consistency
        if llm is None and settings.openai_api_key:
            try:
                from crewai import LLM as CrewLLM
                model_name = settings.agent_model_name
                agent_config["llm"] = CrewLLM(model=model_name)
            except Exception:
                pass

        self.agent = Agent(**agent_config)

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    
 
     
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
         Your goal is to navigate to the provided URL and extract product name, website, url, and price using the simplified_stagehand_tool.

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
        3. **Classify Page (OBSERVE):** Use simplified_stagehand_tool with operation "observe" (set return_action=true) to determine if current page is a direct product page vs a general site/search page.
           - Direct product page indicators: single product title, price, primary CTA (Add to basket/Buy now)
           - Non-product page indicators: search/home/category pages, product grids/lists
        4. **If NOT a direct product page → SEARCH ON THE SITE:**
           - Use "observe" (return_action=true) to locate the site search input and search button/icon
           - Use "act" to execute the returned action(s) to focus the input, then type "{product_query}" and submit (Enter or click search icon)
           - After results load, use "observe" (return_action=true) to identify the most relevant product card/link (closest title match to "{product_query}")
           - If a match is found, use "act" to click it to open the product page. If no match is found, stop and return an empty products array with extraction_successful=false (the Flow will move to the next URL)
           - Verify arrival on a product page (see indicators above) before extracting
        5. **Extract Product Data:** Use simplified_stagehand_tool with operation "extract" and custom schema to get:
           - name (exact product name as displayed)
           - website (retailer website URL or domain)
           - url (direct product page URL)
           - price (in GBP format with £ symbol)

        **CUSTOM EXTRACTION SCHEMA:**
        Use this exact schema definition for extraction:
        {{
          "fields": {{
            "name": "str",
            "website": "optional_url",
            "url": "optional_url",
            "price": "str"
          }},
          "name": "Product",
          "is_list": true
        }}

        **EXTRACTION REQUIREMENTS:**
        - Focus on products that match or closely relate to "{product_query}"
        - Ensure prices are in GBP format (£XX.XX)
        - Get direct product page URLs when possible
        - Include retailer website domain when available
        - Handle errors gracefully and document any issues

        **ERROR HANDLING:**
        - If navigation fails, document the error
        - If product information is incomplete, extract what's available
        - If no matching products found, report this clearly
        - Include error details in the response for debugging

        **DIRECT PRODUCT CHECK & CRITERIA:**
        - Treat URLs containing /search, /category, /categories, or pages showing grids/lists as NOT product pages
        - Treat pages with a single product title, price, and primary action (Add to basket/Buy now) as product pages
        - Always confirm using an "observe" step before extraction

        **CRITICAL INSTRUCTIONS:**
        1. Always use the exact tool name "simplified_stagehand_tool"
        2. Use appropriate operation parameters: "navigate", "act", or "extract"
        3. For extraction, include the custom schema parameter:
           Tool: simplified_stagehand_tool
           Action Input: {{
             "operation": "extract",
             "instruction": "Extract product information for {product_query}",
             "schema": {{
               "fields": {{"name": "str", "website": "optional_url", "url": "optional_url", "price": "str"}},
               "name": "Product",
               "is_list": true
             }}
           }}
        4. Use "observe" with return_action=true and pass returned actions to "act" whenever interacting (typing/clicking) to avoid DOM drift
        5. Focus on extracting complete product information (name, website, url, price)
        6. If no product can be found via on-site search, return products=[] and set extraction_successful=false
        7. Validate that extracted data is relevant to "{product_query}"
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Return a valid JSON object only (no extra text):
            {{
              "products": [
                {{
                  "name": "Exact product name from site",
                  "website": "https://{retailer}.com",
                  "url": "{retailer_url}",
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

            IMPORTANT:
            - Output JSON only, no wrappers or tags
            - If no errors occur, you may omit the "errors" key
            - Ensure all URLs, names, images, and prices are accurately extracted
            - Handle any extraction errors gracefully and include them in the errors array
            """,
            output_pydantic=ExtractionResult
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
        4. If the provided URL is not a product page, perform the on-site search workflow described above before extracting
        5. Apply all feedback recommendations to improve extraction quality
        5. Focus on resolving the specific issues identified in previous attempt
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Return a valid JSON object only (no extra text):
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

            IMPORTANT:
            - Output JSON only, no wrappers or tags
            - Address all validation feedback from the previous attempt
            - If no errors occur, you may omit the "errors" key
            - Ensure all URLs, names, images, and prices are accurately extracted
            - Document what improvements were made based on the feedback
            """,
            output_pydantic=ExtractionResult
        )
