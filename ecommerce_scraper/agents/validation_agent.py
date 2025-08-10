"""Product Search Validation Agent - Validates confirmation results using Perplexity URL legitimacy check."""

import json
import logging
from typing import Dict, Any, List, Optional
from crewai import Agent, LLM, Task
from ..config.settings import settings
from pydantic import BaseModel, Field
from ..config.settings import settings 
from ..tools.agent_capabilities_reference_tool import AgentCapabilitiesReferenceTool
from ..tools.perplexity_url_legitimacy_tool import PerplexityUrlLegitimacyTool
from ..schemas.agent_outputs import TargetedFeedbackResult
from ..ai_logging.error_logger import get_error_logger

logger = logging.getLogger(__name__)

_SELENIUM_AVAILABLE = False


class ProductSearchValidationResult(BaseModel):
    """Pydantic model for product search validation task output (single product)."""
    validation_passed: bool = False
    validated_product: Optional[Dict[str, Any]] = None
    validation_feedback: Optional[Dict[str, Any]] = None
    retry_recommendations: Optional[List[str]] = None
    processing_complete: bool = True


class ProductSearchValidationAgent:
    """Agent for validating product search results with feedback loops."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the product search validation agent."""
        # Tools: capabilities reference + Perplexity URL legitimacy; no browser tools
        capabilities_tool = AgentCapabilitiesReferenceTool()
        url_tool = PerplexityUrlLegitimacyTool()
        tools = [capabilities_tool, url_tool]

        agent_config = {
            "role": "AI-Powered Validation Specialist (Perplexity URL Check)",
            "goal": """
            Validate confirmation outputs by ensuring minimal required fields (name, url, price) are present, and
            confirm the URL is a direct, purchasable product page from a legitimate retailer using Perplexity.
            Provide targeted feedback for retries when validation fails.
            """,
            "backstory": """
            You are a specialized product search validation expert with deep knowledge of UK retail
            websites and product matching algorithms. Your responsibility is to validate that confirmed
            products match the user's original search query and come from legitimate UK retailers.
            
            Your core expertise includes:
            - Semantic product name matching and similarity analysis
            - UK retailer legitimacy verification (excluding price comparison sites)
            - Product URL validation and purchasability verification
            - Feedback generation for failed validations
            - Retry strategy recommendations for alternative retailers
            - Quality scoring and confidence assessment
            
            VALIDATION CRITERIA:
            1. Confirmation minimal fields present: name, url, price (GBP preferred)
            2. URL legitimacy via Perplexity: direct product page, not comparison/affiliate site
            3. Purchasability likely (Perplexity indicates purchasable)

            FEEDBACK LOOP PROCESS:
            - When validation fails, determine root cause and route feedback:
              - Research-related: illegitimate retailer/comparison URL, not a product page
            - Confirmation-related: missing fields or price format issues
            - Use agent capabilities reference tool to structure actionable feedback

            TOOLS AVAILABLE:
            - perplexity_url_legitimacy_tool: Validate URL legitimacy and purchasability via Perplexity
            - agent_capabilities_reference_tool: Reference updated agent capabilities and routing guidelines
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
        """Summarize available tool names for prompt clarity."""
        names: List[str] = []
        url_tool = "perplexity_url_legitimacy_tool"
        capabilities_tool = "agent_capabilities_reference_tool"
        try:
            for tool in getattr(self.agent, "tools", []) or []:
                name = getattr(tool, "name", type(tool).__name__)
                names.append(name)
                if name.lower() == "perplexity_url_legitimacy_tool":
                    url_tool = name
                if name.lower() == "agent_capabilities_reference_tool":
                    capabilities_tool = name
        except Exception:
            pass
        others = ", ".join([n for n in names if n not in {url_tool, capabilities_tool}])
        return {"url_tool": url_tool, "capabilities_tool": capabilities_tool, "others": others}

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    def create_product_search_validation_task(self,
                                            search_query: str, 
                                            retailer: str,
                                            retailer_url: str,
                                            retailer_price: str,
                                            attempt_number: int = 1,
                                            max_attempts: int = 3):
        """Create a task for validating product search results."""

        names = self._tools_summary()
        task_description = f"""
        Validate the confirmed product for "{search_query}" from {retailer} (source URL: {retailer_url}).

        Attempt Number: {attempt_number} of {max_attempts}
        Search Query: {search_query}
        Retailer Name: {retailer}
        Retailer URL: {retailer_url}
        Retailer Price: {retailer_price}

        VALIDATION WORKFLOW (Perplexity-based):
        1) Minimal fields check: For each confirmed product, verify required fields exist: name (non-empty), url (http/https), price (prefer GBP with £).
        2) URL legitimacy: For products passing step 1, call {names["url_tool"]} with:
           - url: the product's url
           - retailer: "{retailer}"
           - product_name: the product's name
           - keywords: keywords are not needed for this tool
        3) Pass criteria:
           - is_product_page == true
           - is_purchasable == true
           - is_comparison_site == false
        4) For failures, classify root cause and prepare feedback:
            - Research-related: comparison/affiliate site, not a product page, retailer mismatch
            - Confirmation-related: missing fields, price format issues

        TOOLS AVAILABLE:
        - {names["url_tool"]}: Validate URL is a direct, purchasable product page (not comparison/affiliate)
        - {names["capabilities_tool"]}: Use when generating targeted feedback to ensure actionable guidance

        PRICE VALIDATION:
        - Prefer GBP (with £). Normalize or flag otherwise.

        FEEDBACK GENERATION (if validation fails):
        - Identify specific issues with each failed product
            - Determine if issues are research-related or confirmation-related
        - Generate targeted feedback payloads for ResearchAgent and ConfirmationAgent
        - Provide retry guidance and priorities based on capabilities
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
              "validated_product": {{
                "product_name": "Validated product name",
                "price": "£XX.XX",
                "url": "direct product page URL",
                "retailer": "{retailer}",
                "validation_score": <0.0-1.0>,
                "validation_notes": "Why this product passed validation"
              }},
              "validation_summary": {{ 
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
                    "Comparison/affiliate site or not a product page"
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
              "confirmation_feedback": {{
                "target_agent": "ConfirmationAgent",
                  "issues": [
                    "Missing minimal fields (name, url, price) or GBP price format"
                  ],
                  "retry_recommendations": [
                    "Provide clearer search_instructions to disambiguate variants"
                  ],
                  "confirmation_improvements": [
                    "Ensure minimal fields and GBP normalization"
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
                                    already_searched: Optional[List[Dict[str, Any]]] = None):
        """Create a task for generating targeted feedback for both ResearchAgent and ConfirmationAgent."""

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
        Generate targeted feedback for both ResearchAgent and ConfirmationAgent based on validation failures.

        Search Query: {search_query}
        Retailer: {retailer}
        Attempt Number: {attempt_number} of {max_attempts}
         
        Validation Failures: {len(validation_failures)}
        Already Searched Retailers (avoid duplicates): {already_text}

        STEP 1: CAPABILITIES REFERENCE (AT MOST ONCE PER ATTEMPT)
        - If you need capabilities context, you may call agent_capabilities_reference_tool at most once per validation attempt.
        - Prefer using your existing knowledge; avoid repeated calls that do not change the outcome.

        STEP 2: TARGETED FEEDBACK ANALYSIS
        Based on the agent capabilities information:
        1. **Categorize validation failures by root cause**
        2. **Map failures to agent capabilities** (what each agent can actually address)
        3. **Generate specific, actionable feedback for ResearchAgent**
        4. **Generate specific, actionable feedback for ConfirmationAgent**
        5. **Determine which agent should retry first based on capabilities**

        STEP 3: CAPABILITY-BASED FEEDBACK GENERATION
        Generate feedback that each agent can actually act upon. Do not call the capabilities tool more than once.

        FOR RESEARCHAGENT:
        - Only suggest feedback types listed in its "feedback_types_actionable"
        - Focus on issues it can address with its perplexity_retailer_research_tool
        - Provide search_instructions that utilize its feedback_response_capabilities
        - Consider its limitations when making recommendations
        - IMPORTANT: Avoid suggesting retailers that were already searched in this session. Use the list above to exclude duplicates.

        FOR CONFIRMATIONAGENT:
        - Only suggest feedback types listed in its "feedback_types_actionable"
        - Focus on issues it can address with its perplexity_retailer_product_tool
        - Provide improvements via search_instructions that utilize its feedback_response_capabilities
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
                "confirmation_related_failures": <number>,
                "primary_failure_type": "research|confirmation|mixed"
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
              "confirmation_feedback": {{
                "target_agent": "ConfirmationAgent",
                "should_retry": <true/false>,
                "priority": "high|medium|low",
                "issues": [
                  "Specific confirmation-related issues identified"
                ],
                "retry_recommendations": [
                  "Specific actions for ConfirmationAgent to improve"
                ],
                "confirmation_improvements": [
                  "Better confirmation strategies or approaches"
                ],
                "schema_fixes": [
                  "Specific schema compliance improvements needed"
                ]
              }},
              "retry_strategy": {{
                "recommended_approach": "research_first|confirmation_first|both_parallel|give_up",
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
