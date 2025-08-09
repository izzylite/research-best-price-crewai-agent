"""Product Search Validation Agent - Validates product search results with feedback loops."""

import json
import logging
from typing import Dict, Any, List, Optional
from crewai import Agent, LLM, Task
from ..config.settings import settings
from pydantic import BaseModel, Field
from ..config.settings import settings
from ..schemas.product_search_extraction import ProductSearchExtraction
from ..tools.agent_capabilities_reference_tool import AgentCapabilitiesReferenceTool
from ..schemas.agent_outputs import TargetedFeedbackResult
from ..ai_logging.error_logger import get_error_logger

logger = logging.getLogger(__name__)

# Optional Selenium fallback from crewai-tools for verification tasks
try:
    from crewai_tools import SeleniumScrapingTool  # type: ignore
    _SELENIUM_AVAILABLE = True
except Exception:
    SeleniumScrapingTool = None  # type: ignore
    _SELENIUM_AVAILABLE = False


class ProductSearchValidationResult(BaseModel):
    """Pydantic model for product search validation task output.

    Be tolerant to partial outputs by providing defaults for required fields.
    """
    validation_passed: bool = False
    validated_products: List[Dict[str, Any]] = Field(default_factory=list)
    validation_feedback: Optional[Dict[str, Any]] = None
    retry_recommendations: Optional[List[str]] = None
    processing_complete: bool = True


class ProductSearchValidationAgent:
    """Agent for validating product search results with feedback loops."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the product search validation agent."""
        # Create agent capabilities reference tool
        capabilities_tool = AgentCapabilitiesReferenceTool()
        
        # Selenium fallback to help validate product pages when Stagehand struggles
        supplemental_tools: List[Any] = []
        if _SELENIUM_AVAILABLE and SeleniumScrapingTool is not None:
            try:
                supplemental_tools.append(SeleniumScrapingTool())
            except Exception:
                pass

        # Handle both old (tools, llm) and new (stagehand_tool, verbose) calling patterns
        # Build final tool list ensuring consistent naming so Crew shows them to the agent
        final_tools: List[Any] = []
        if stagehand_tool:
            final_tools.append(stagehand_tool)
        # Add supplemental tools first so the UI lists them clearly
        final_tools.extend(supplemental_tools)
        # Always include capabilities tool
        final_tools.append(capabilities_tool)

        # If caller provided explicit tools, merge uniquely (preserve order)
        if tools:
            names = {getattr(t, "name", str(type(t))) for t in final_tools}
            for t in tools:
                n = getattr(t, "name", str(type(t)))
                if n not in names:
                    final_tools.append(t)
                    names.add(n)

        tools = final_tools

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
            - simplified_stagehand_tool: Navigate/observe/act/extract to open pages and verify product-page indicators
            - SeleniumScrapingTool: Fallback browser automation to load pages and interact when Stagehand observation/act is unreliable
            - agent_capabilities_reference_tool: Get detailed information about ResearchAgent and ExtractionAgent capabilities for targeted feedback generation
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": settings.enable_crew_memory
        }

        if llm:
            agent_config["llm"] = llm

        # If no LLM provided, align with configured model
        if llm is None and settings.openai_api_key:
            try:
                from crewai import LLM as CrewLLM
                model_name = settings.agent_model_name
                agent_config["llm"] = CrewLLM(model=model_name)
            except Exception:
                pass

        self.error_logger = get_error_logger("validation_agent")
        self.agent = Agent(**agent_config)

    def _tools_summary(self) -> Dict[str, str]:
        """Summarize available tool names so prompts reference real names.
        Returns dict with keys: stagehand, others, selenium (may be empty)."""
        names: List[str] = []
        stagehand = "simplified_stagehand_tool"
        selenium = ""
        try:
            for tool in getattr(self.agent, "tools", []) or []:
                name = getattr(tool, "name", type(tool).__name__)
                names.append(name)
                if name.lower() == "simplified_stagehand_tool":
                    stagehand = name
                if "selenium" in name.lower():
                    selenium = name
        except Exception:
            pass
        others = ", ".join([n for n in names if n != stagehand])
        return {"stagehand": stagehand, "others": others, "selenium": selenium}

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    def create_product_search_validation_task(self,
                                            search_query: str,
                                            extracted_products: List[Dict[str, Any]],
                                            retailer: str,
                                            retailer_url: str,
                                            attempt_number: int = 1,
                                            max_attempts: int = 3,
                                            session_id: str = None):
        """Create a task for validating product search results."""
        
        names = self._tools_summary()
        task_description = f"""
        Validate product search results for "{search_query}" from {retailer} at {retailer_url}.

  
        Attempt Number: {attempt_number} of {max_attempts}
        Session ID: {session_id} 
        Products to Validate: {len(extracted_products)}

        TOOLS:
        - Primary: {names["stagehand"]} (navigate → observe → act → extract)
        - Fallback (only if present): {names["selenium"]} for loading and interactions when observe/act is unreliable
       
        VALIDATION WORKFLOW:
        **MANDATORY TOOL USAGE**: You MUST attempt to load and inspect the page using tools. Do NOT claim a URL is inaccessible or invalid without attempting the following with {names["stagehand"]}; if two attempts fail, use {names["selenium"]} when available.
      
        PROCEDURE:
        1. **Navigate**: Use {names["stagehand"]} with operation="navigate" to open {retailer_url} if not already at the target URL.
        2. **Handle popups (allowed actions only)**: If cookie/consent/geo banners block the page (common on Amazon UK), use operation="act" to accept/close, then continue. You may also scroll or expand collapsed sections. 
        3. **Observe**: Use operation="observe" to confirm product-page indicators: distinct title, GBP price (with £), and a primary CTA (e.g., Add to Basket).
        4. **Optional extract**: If needed, use operation="extract" with a simple schema to read name and price.
        5. **Validate** each product against the search query.
        6. **Verify** retailer legitimacy and URL validity based on observed/extracted DOM.
        7. **Assess** product availability and purchasability.
        8. **Generate feedback** for failed validations and **recommend retry strategies**.

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
        - Must be accessible and lead to actual product information (CONFIRM via tool usage)
        - Confirm product-page indicators (unique title, price, primary CTA) using observe/extract
        - Must not be a redirect to price comparison or affiliate sites
        
        NON-NAVIGATION REQUIREMENT (CRITICAL):
        - NEVER navigate away from the provided Target URL during validation. Do NOT perform on-site searches, do NOT click links that change the page location, and do NOT follow cross-sells/related items.
        - The ONLY allowed actions are: accepting/closing blocking popups, scrolling, and expanding in-page UI elements. If the site performs a server-side redirect from the provided URL to its canonical product URL on first load, record the final URL but do not trigger any further navigation.
        - If the provided URL is not a product page or is invalid, return a failed validation with precise reasons instead of navigating to another page.

        HARD CONSTRAINTS:
        - You are REQUIRED to use the available tools to verify accessibility and content. Returning a failure like "Unable to access" without a tool attempt is not permitted.
        - If tool calls fail, include the specific tool errors in the feedback so the system can route retries correctly.
        
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
                  "url": "{retailer_url}",
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
            """,
            output_pydantic=ProductSearchValidationResult
        )

  
    
   
    def create_targeted_feedback_task(self,
                                    search_query: str,
                                    validation_failures: List[Dict[str, Any]],
                                    retailer: str,
                                    attempt_number: int = 1,
                                    max_attempts: int = 3,
                                    session_id: str = None,
                                    already_searched: Optional[List[Dict[str, Any]]] = None):
        """Create a task for generating targeted feedback for both ResearchAgent and ExtractionAgent."""

        # Summarize already searched retailers to steer ResearchAgent away from duplicates
        already_text = "None"
        if already_searched:
            try:
                names = [r.get("vendor", "Unknown") for r in already_searched]
                domains = []
                for r in already_searched:
                    url = r.get("url") or ""
                    if url:
                        try:
                            from urllib.parse import urlparse
                            netloc = urlparse(url).netloc
                            if netloc:
                                domains.append(netloc)
                        except Exception:
                            pass
                names_list = ", ".join([n for n in names if n])
                domains_list = ", ".join(sorted(set([d for d in domains if d])))
                already_text = f"Vendors: {names_list} | Domains: {domains_list}"
            except Exception:
                already_text = "Provided"

        task_description = f"""
        Generate targeted feedback for both ResearchAgent and ExtractionAgent based on validation failures.

        Search Query: {search_query}
        Retailer: {retailer}
        Attempt Number: {attempt_number} of {max_attempts}
        Session ID: {session_id}
        Validation Failures: {len(validation_failures)}
        Already Searched Retailers (avoid duplicates): {already_text}

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
        - IMPORTANT: Avoid suggesting retailers that were already searched in this session. Use the list above to exclude duplicates.

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
