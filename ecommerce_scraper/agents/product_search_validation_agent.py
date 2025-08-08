"""Product Search Validation Agent - Validates product search results with feedback loops."""

import json
import logging
from typing import Dict, Any, List, Optional
from crewai import Agent, LLM, Task
from pydantic import BaseModel
from ..config.settings import settings
from ..schemas.product_search_extraction import ProductSearchExtraction
from ..tools.agent_capabilities_reference_tool import AgentCapabilitiesReferenceTool

logger = logging.getLogger(__name__)


class ProductSearchValidationResult(BaseModel):
    """Pydantic model for product search validation task output."""
    validation_passed: bool
    validated_products: List[Dict[str, Any]]
    validation_feedback: Optional[Dict[str, Any]] = None
    retry_recommendations: Optional[List[str]] = None
    processing_complete: bool = True


class ProductSearchValidationAgent:
    """Agent for validating product search results with feedback loops."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the product search validation agent."""
        # Create agent capabilities reference tool
        capabilities_tool = AgentCapabilitiesReferenceTool()

        # Handle both old (tools, llm) and new (stagehand_tool, verbose) calling patterns
        if stagehand_tool is not None:
            # New Flow-based calling pattern - add capabilities tool
            tools = [stagehand_tool, capabilities_tool] if stagehand_tool else [capabilities_tool]
        elif tools is None:
            tools = [capabilities_tool]
        else:
            # Add capabilities tool to existing tools
            tools.append(capabilities_tool)

        agent_config = {
            "role": "Product Search Validation and Quality Assurance Specialist",
            "goal": """
            Validate product search results to ensure they match the original search query,
            come from legitimate UK retailers, and lead to actual purchasable product pages.
            Provide feedback for retry attempts when validation fails.
            """,
            "backstory": """
            You are a specialized product search validation expert with deep knowledge of UK retail
            websites and product matching algorithms. Your responsibility is to validate that extracted
            products match the user's original search query and come from legitimate UK retailers.
            
            Your core expertise includes:
            - Semantic product name matching and similarity analysis
            - UK retailer legitimacy verification (excluding price comparison sites)
            - Product URL validation and purchasability verification
            - Feedback generation for failed validations
            - Retry strategy recommendations for alternative retailers
            - Quality scoring and confidence assessment
            
            VALIDATION CRITERIA:
            1. Product name must match or be semantically similar to the search query
            2. URL must be from a legitimate UK retailer (not price comparison sites)
            3. URL must lead to an actual product page, not search results or categories
            4. Price must be in valid GBP format
            5. Product must be available for purchase (not out of stock permanently)
            
            FEEDBACK LOOP PROCESS:
            - When validation fails, provide specific feedback for retry attempts
            - Use agent capabilities reference tool to understand what each agent can address
            - Generate targeted feedback based on agent capabilities and limitations
            - Suggest alternative retailers or search strategies
            - Limit retry attempts to maximum 3 per product search
            - Track validation success rates and improvement over retries

            TOOLS AVAILABLE:
            - agent_capabilities_reference_tool: Get detailed information about ResearchAgent and ExtractionAgent capabilities for targeted feedback generation
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 3,
            "memory": settings.enable_crew_memory
        }

        if llm:
            agent_config["llm"] = llm

        self.agent = Agent(**agent_config)

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    def create_product_search_validation_task(self,
                                            search_query: str,
                                            extracted_products: List[Dict[str, Any]],
                                            retailer: str,
                                            attempt_number: int = 1,
                                            max_attempts: int = 3,
                                            session_id: str = None):
        """Create a task for validating product search results."""
        
        task_description = f"""
        Validate product search results for "{search_query}" from {retailer}.

        Search Query: {search_query}
        Retailer: {retailer}
        Attempt Number: {attempt_number} of {max_attempts}
        Session ID: {session_id}
        Products to Validate: {len(extracted_products)}

        VALIDATION WORKFLOW:
        1. **Validate each extracted product against the search query**
        2. **Check product name similarity to "{search_query}"**
        3. **Verify retailer legitimacy and URL validity**
        4. **Assess product availability and purchasability**
        5. **Generate feedback for failed validations**
        6. **Recommend retry strategies if needed**

        VALIDATION CRITERIA:
        
        PRODUCT NAME MATCHING:
        - Exact match: Product name contains all key words from "{search_query}"
        - Semantic match: Product name is semantically similar (e.g., "iPhone 15 Pro" matches "Apple iPhone 15 Pro Max")
        - Brand/model match: Core brand and model identifiers are present
        - Reject: Generic terms, unrelated products, or completely different items
        
        UK RETAILER LEGITIMACY:
        - ACCEPT: asda.com, tesco.com, waitrose.com, sainsburys.co.uk, amazon.co.uk, ebay.co.uk, 
                 argos.co.uk, currys.co.uk, johnlewis.com, next.co.uk, marksandspencer.com, etc.
        - REJECT: Price comparison sites (pricerunner, shopping.com, google shopping, kelkoo)
        - REJECT: Affiliate sites that redirect to other retailers
        - REJECT: Unknown or suspicious domains
        
        URL VALIDATION:
        - Must be direct product page URL, not search results or category pages
        - Must be accessible and lead to actual product information
        - Must not be a redirect to price comparison or affiliate sites
        
        PRICE VALIDATION:
        - Must be in GBP format with £ symbol
        - Must be reasonable price for the product type
        - Must not be placeholder or obviously incorrect prices
        
        FEEDBACK GENERATION (if validation fails):
        - Identify specific issues with each failed product
        - Determine if issues are research-related (wrong retailers, bad URLs) or extraction-related (data quality)
        - Generate targeted feedback for ResearchAgent (retailer discovery, URL validation)
        - Generate targeted feedback for ExtractionAgent (data extraction improvements)
        - Suggest alternative search terms or retailers
        - Recommend different extraction strategies
        - Provide retry guidance for both ResearchAgent and ExtractionAgent
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Product search validation result:
            {{
              "validation_passed": <true/false>,
              "search_query": "{search_query}",
              "retailer": "{retailer}",
              "attempt_number": {attempt_number},
              "validated_products": [
                {{
                  "product_name": "Validated product name",
                  "price": "£XX.XX",
                  "url": "validated product URL",
                  "retailer": "{retailer}",
                  "validation_score": <0.0-1.0>,
                  "validation_notes": "Why this product passed validation"
                }}
              ],
              "validation_summary": {{
                "total_products_received": {len(extracted_products)},
                "products_passed": <number>,
                "products_failed": <number>,
                "overall_success_rate": <percentage>,
                "validation_complete": true
              }},
              "feedback": {{
                "issues_found": [
                  "Specific validation issues"
                ],
                "research_feedback": {{
                  "target_agent": "ResearchAgent",
                  "issues": [
                    "Research-related issues (wrong retailers, bad URLs, etc.)"
                  ],
                  "retry_recommendations": [
                    "Specific suggestions for ResearchAgent retry attempts"
                  ],
                  "alternative_retailers": [
                    "Suggested alternative retailers to try"
                  ],
                  "search_refinements": [
                    "Suggested search query refinements"
                  ]
                }},
                "extraction_feedback": {{
                  "target_agent": "ExtractionAgent",
                  "issues": [
                    "Extraction-related issues (data quality, missing fields, etc.)"
                  ],
                  "retry_recommendations": [
                    "Specific suggestions for ExtractionAgent retry attempts"
                  ],
                  "extraction_improvements": [
                    "Suggested changes to extraction approach"
                  ]
                }}
              }}
            }}
            
            Provide detailed validation results with specific feedback for retry attempts.
            Only include products that pass all validation criteria in validated_products.
            """
        )

    def create_feedback_generation_task(self,
                                      validation_failures: List[Dict[str, Any]],
                                      search_query: str,
                                      current_attempt: int,
                                      max_attempts: int):
        """Create a task for generating feedback for failed validations."""
        
        task_description = f"""
        Generate specific feedback and retry recommendations for failed product search validation.

        Search Query: {search_query}
        Current Attempt: {current_attempt} of {max_attempts}
        Validation Failures: {len(validation_failures)}

        FEEDBACK GENERATION REQUIREMENTS:
        1. **Analyze specific validation failure reasons**
        2. **Generate actionable retry recommendations**
        3. **Suggest alternative retailers or search strategies**
        4. **Provide search query refinements if needed**
        5. **Assess if retry attempts are worthwhile**

        FAILURE ANALYSIS:
        - Product name mismatches: Suggest search term refinements
        - Invalid retailers: Recommend legitimate UK retailers
        - URL issues: Suggest different extraction approaches
        - Price problems: Recommend price validation improvements
        - Availability issues: Suggest alternative retailers

        RETRY STRATEGY:
        - If attempt < {max_attempts}: Provide specific retry guidance
        - If attempt = {max_attempts}: Provide final recommendations or suggest giving up
        - Focus on most promising retry approaches first
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Feedback generation result:
            {{
              "search_query": "{search_query}",
              "current_attempt": {current_attempt},
              "max_attempts": {max_attempts},
              "retry_worthwhile": <true/false>,
              "feedback": {{
                "primary_issues": [
                  "Main reasons for validation failures"
                ],
                "retry_recommendations": [
                  "Specific actions for next retry attempt"
                ],
                "alternative_retailers": [
                  "UK retailers to try instead"
                ],
                "search_refinements": [
                  "Suggested modifications to search query"
                ],
                "extraction_improvements": [
                  "Suggested changes to extraction approach"
                ]
              }},
              "confidence_assessment": {{
                "retry_success_probability": <0.0-1.0>,
                "recommended_action": "retry|try_alternatives|give_up",
                "reasoning": "Why this recommendation was made"
              }}
            }}
            
            Provide actionable feedback for improving validation success on retry attempts.
            """
        )

    def validate_product_match(self, product_name: str, search_query: str) -> float:
        """Validate if a product name matches the search query (0.0-1.0 score)."""
        import re
        
        # Normalize both strings
        def normalize_text(text: str) -> str:
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            return ' '.join(text.split())
        
        normalized_product = normalize_text(product_name)
        normalized_query = normalize_text(search_query)
        
        # Simple keyword matching
        query_words = set(normalized_query.split())
        product_words = set(normalized_product.split())
        
        if not query_words:
            return 0.0
        
        # Calculate overlap ratio
        overlap = len(query_words.intersection(product_words))
        return overlap / len(query_words)

    def is_legitimate_uk_retailer(self, url: str) -> bool:
        """Check if URL is from a legitimate UK retailer."""
        uk_retailer_domains = [
            'asda.com', 'tesco.com', 'waitrose.com', 'sainsburys.co.uk',
            'amazon.co.uk', 'ebay.co.uk', 'argos.co.uk', 'currys.co.uk',
            'johnlewis.com', 'next.co.uk', 'marksandspencer.com',
            'boots.com', 'superdrug.com', 'wilko.com', 'b&q.co.uk'
        ]
        
        # Price comparison sites to exclude
        comparison_sites = [
            'pricerunner', 'shopping.com', 'google.com/shopping',
            'kelkoo', 'pricegrabber', 'nextag', 'bizrate'
        ]
        
        url_lower = url.lower()
        
        # Check for comparison sites first (exclude)
        if any(site in url_lower for site in comparison_sites):
            return False
        
        # Check for legitimate UK retailers
        return any(domain in url_lower for domain in uk_retailer_domains)

    def create_targeted_feedback_task(self,
                                    search_query: str,
                                    validation_failures: List[Dict[str, Any]],
                                    retailer: str,
                                    attempt_number: int = 1,
                                    max_attempts: int = 3,
                                    session_id: str = None):
        """Create a task for generating targeted feedback for both ResearchAgent and ExtractionAgent."""

        task_description = f"""
        Generate targeted feedback for both ResearchAgent and ExtractionAgent based on validation failures.

        Search Query: {search_query}
        Retailer: {retailer}
        Attempt Number: {attempt_number} of {max_attempts}
        Session ID: {session_id}
        Validation Failures: {len(validation_failures)}

        STEP 1: GET AGENT CAPABILITIES INFORMATION
        First, use the agent_capabilities_reference_tool to understand what each agent can do:

        Tool: agent_capabilities_reference_tool
        Action Input: {{"agent_name": "both", "capability_type": "all"}}

        This will provide detailed information about:
        - ResearchAgent capabilities, tools, and feedback types it can act upon
        - ExtractionAgent capabilities, tools, and feedback types it can act upon
        - Guidelines for routing feedback to the appropriate agent

        STEP 2: TARGETED FEEDBACK ANALYSIS
        Based on the agent capabilities information:
        1. **Categorize validation failures by root cause**
        2. **Map failures to agent capabilities** (what each agent can actually address)
        3. **Generate specific, actionable feedback for ResearchAgent**
        4. **Generate specific, actionable feedback for ExtractionAgent**
        5. **Determine which agent should retry first based on capabilities**

        STEP 3: CAPABILITY-BASED FEEDBACK GENERATION
        Using the agent capabilities information, generate feedback that each agent can actually act upon:

        FOR RESEARCHAGENT:
        - Only suggest feedback types listed in its "feedback_types_actionable"
        - Focus on issues it can address with its perplexity_retailer_research_tool
        - Provide search_instructions that utilize its feedback_response_capabilities
        - Consider its limitations when making recommendations

        FOR EXTRACTIONAGENT:
        - Only suggest feedback types listed in its "feedback_types_actionable"
        - Focus on issues it can address with its simplified_stagehand_tool
        - Provide extraction improvements that utilize its feedback_response_capabilities
        - Consider its limitations when making recommendations

        STEP 4: INTELLIGENT FEEDBACK ROUTING
        Use the feedback_routing_guidelines from the capabilities tool to determine:
        - Which agent should retry first based on failure patterns
        - What priority level to assign to each agent's feedback
        - Whether both agents need to retry or just one
        - Success probability assessment based on agent capabilities

        CRITICAL: Only generate feedback that agents can actually implement based on their documented capabilities and tools.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Targeted feedback analysis result:
            {{
              "search_query": "{search_query}",
              "retailer": "{retailer}",
              "attempt_number": {attempt_number},
              "max_attempts": {max_attempts},
              "failure_analysis": {{
                "total_failures": {len(validation_failures)},
                "research_related_failures": <number>,
                "extraction_related_failures": <number>,
                "primary_failure_type": "research|extraction|mixed"
              }},
              "research_feedback": {{
                "target_agent": "ResearchAgent",
                "should_retry": <true/false>,
                "priority": "high|medium|low",
                "issues": [
                  "Specific research-related issues identified"
                ],
                "retry_recommendations": [
                  "Specific actions for ResearchAgent to improve"
                ],
                "alternative_retailers": [
                  "Better UK retailers to research and try"
                ],
                "search_refinements": [
                  "Improved search queries or strategies"
                ]
              }},
              "extraction_feedback": {{
                "target_agent": "ExtractionAgent",
                "should_retry": <true/false>,
                "priority": "high|medium|low",
                "issues": [
                  "Specific extraction-related issues identified"
                ],
                "retry_recommendations": [
                  "Specific actions for ExtractionAgent to improve"
                ],
                "extraction_improvements": [
                  "Better extraction strategies or approaches"
                ],
                "schema_fixes": [
                  "Specific schema compliance improvements needed"
                ]
              }},
              "retry_strategy": {{
                "recommended_approach": "research_first|extraction_first|both_parallel|give_up",
                "success_probability": <0.0-1.0>,
                "reasoning": "Why this approach is recommended",
                "next_steps": [
                  "Ordered list of recommended retry steps"
                ]
              }}
            }}

            Provide comprehensive targeted feedback for both agents with clear retry priorities.
            """
        )
