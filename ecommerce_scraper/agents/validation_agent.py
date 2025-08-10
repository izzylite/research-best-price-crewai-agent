"""Product Search Validation Agent - Validates confirmation results using Perplexity URL legitimacy check."""

import json
import logging
from typing import Dict, Any, List, Optional
from crewai import Agent, LLM, Task
from ..config.settings import settings
from pydantic import BaseModel, Field
from ..config.settings import settings 
from ..tools.perplexity_url_legitimacy_tool import PerplexityUrlLegitimacyTool
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
        # Tools: ONLY Perplexity URL legitimacy; feedback routing handled by FeedbackAgent
        url_tool = PerplexityUrlLegitimacyTool()
        tools = [url_tool]

        agent_config = {
            "role": "AI-Powered Validation Specialist (Perplexity URL Check)",
            "goal": """
            Validate confirmation outputs by ensuring minimal required fields (name, url, price) are present, and
            confirm the URL is a direct, purchasable product page from a legitimate retailer using Perplexity.
            You do NOT generate or route feedback. Feedback is owned by FeedbackAgent.
            """,
            "backstory": """
            You are a specialized product search validation expert with deep knowledge of UK retail
            websites and product matching algorithms. Your responsibility is to validate that confirmed
            products match the user's original search query and come from legitimate UK retailers.
            
            Your core expertise includes:
            - Semantic product name matching and similarity analysis
            - UK retailer legitimacy verification (excluding price comparison sites)
            - Product URL validation and purchasability verification
            - Quality scoring and confidence assessment
            
            VALIDATION CRITERIA:
            1. Confirmation minimal fields present: name, url, price (GBP preferred)
            2. URL legitimacy via Perplexity: direct product page, not comparison/affiliate site
            3. Purchasability likely (Perplexity indicates purchasable)

            FEEDBACK LOOP PROCESS:
            - When validation fails, STOP. Another agent (FeedbackAgent) will decide routing and generate feedback.

            TOOLS AVAILABLE:
            - perplexity_url_legitimacy_tool: Validate URL legitimacy and purchasability via Perplexity
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": settings.enable_crew_memory
        }

        if llm:
            agent_config["llm"] = llm

        # If no LLM provided, configure one based on available provider keys
        if llm is None:
            try:
                from crewai import LLM as CrewLLM
                model_name = settings.agent_model_name
                if settings.openai_api_key:
                    agent_config["llm"] = CrewLLM(model=model_name)
                elif settings.perplexity_api_key:
                    agent_config["llm"] = CrewLLM(model="perplexity/llama-3.1-sonar-small-128k-online")
                elif settings.google_api_key:
                    agent_config["llm"] = CrewLLM(model="gemini/gemini-1.5-flash")
            except Exception:
                pass

        self.error_logger = get_error_logger("validation_agent")
        self.agent = Agent(**agent_config)

    def _tools_summary(self) -> Dict[str, str]:
        """Summarize available tool names for prompt clarity."""
        url_tool = "perplexity_url_legitimacy_tool"
        try:
            for tool in getattr(self.agent, "tools", []) or []:
                name = getattr(tool, "name", type(tool).__name__)
                if name.lower() == "perplexity_url_legitimacy_tool":
                    url_tool = name
        except Exception:
            pass
        return {"url_tool": url_tool}

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    def create_product_search_validation_task(self,
                                            search_query: str, 
                                            retailer: str,
                                            retailer_url: str,
                                            retailer_price: str,
                                            product_name: Optional[str] = None,
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
        Candidate product name: {product_name or ''}

        VALIDATION WORKFLOW (Perplexity-based):
        1) Minimal fields check: For each confirmed product, verify required fields exist: name (non-empty), url (http/https), price (prefer GBP with £).
        2) URL legitimacy: For products passing step 1, call {names["url_tool"]} with:
           - url: the product's url
           - retailer: "{retailer}"
            - product_name: "{product_name or ''}"
            - retailer_url: "{retailer_url}"
           - keywords: keywords are not needed for this tool
        3) Pass criteria:
           - is_product_page == true
           - is_comparison_site == false
           - is_purchasable may be false due to out-of-stock or sign-in gating; treat as pass if page is the official product detail page on a legitimate retailer domain.
         4) For failures, classify root cause for logging only. Do NOT generate feedback.

        TOOLS AVAILABLE:
        - {names["url_tool"]}: Validate URL is a direct, purchasable product page (not comparison/affiliate)

        PRICE VALIDATION:
        - Prefer GBP (with £). Normalize or flag otherwise.

        FEEDBACK GENERATION:
        - Not your responsibility. Another agent will handle feedback.
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

    # Feedback task creation removed. Feedback is now owned by FeedbackAgent.
