"""ConfirmationAgent - Uses Perplexity to confirm retailer product availability and return minimal fields."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from ..config.settings import settings
from ..config.settings import settings 
from ..schemas.agent_outputs import ConfirmationResult
from ..ai_logging.error_logger import get_error_logger
from ..tools.perplexity_retailer_product_tool import PerplexityRetailerProductTool

# No browser tools required for this agent; it uses Perplexity exclusively
_SELENIUM_AVAILABLE = False


class ConfirmationAgent:
    """Agent that confirms product availability via Perplexity and returns name, url, price."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the confirmation agent with the Perplexity product confirmation tool only."""
        # Ignore browser tools; use only the Perplexity product tool
        product_tool = PerplexityRetailerProductTool()
        tools = [product_tool]
        
        agent_config = {
            "role": "Perplexity Product Confirmation Specialist",
            "goal": """
            Confirm if a specific retailer sells a given product using Perplexity and, when purchasable,
            return the product name, direct URL, and price in GBP.
            """,
            "backstory": """
            You use an AI research tool (Perplexity) to verify whether a retailer has a product available to buy.
            If available, you return minimal fields: name, url, price. You do not browse or scrape; you only call
            the Perplexity product confirmation tool to obtain verified details.
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": settings.enable_crew_memory,
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

        self.error_logger = get_error_logger("confirmation_agent")
        self.agent = Agent(**agent_config)

    def _tools_summary(self) -> Dict[str, str]:
        """Summarize available tool names for clarity."""
        names: List[str] = []
        product_tool = "perplexity_retailer_product_tool"
        try:
            for tool in getattr(self.agent, "tools", []) or []:
                name = getattr(tool, "name", type(tool).__name__)
                names.append(name)
                if name.lower() == "perplexity_retailer_product_tool":
                    product_tool = name
        except Exception:
            pass
        others = ", ".join([n for n in names if n != product_tool])
        return {"product_tool": product_tool, "others": others}

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    
 
     
    def create_product_search_confirmation_task(self,
                                            product_query: str,
                                            retailer: str,
                                            retailer_url: str):
        """
        Create a task for targeted product confirmation focusing on core fields.

        Uses custom schema for confirmation:
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
            retailer_url: URL to navigate to for confirmation
            session_id: Optional session identifier for tracking

        Returns:
            CrewAI Task configured for product confirmation with schema validation
        """
        from crewai import Task
        from urllib.parse import urlparse

        names = self._tools_summary()
        try:
            retailer_domain = urlparse(retailer_url).netloc if isinstance(retailer_url, str) else ""
        except Exception:
            retailer_domain = ""

        task_description = f"""
        Goal: Confirm if {retailer} sells "{product_query}" using {names["product_tool"]} and, if purchasable,
        return the minimal product fields: name, url, price.

        Inputs: product_query, retailer, retailer_domain={retailer_domain}, retailer_url={retailer_url}

        TOOL USAGE:
        - Call {names["product_tool"]} with:
          - product_query: "{product_query}"
          - retailer: "{retailer}"
          - retailer_domain: "{retailer_domain}"
          - keywords: true
          - search_instructions: "Allow keywords related to the product to be used in the search"

        DECISION:
        - If the tool returns exists=false, output product=null and confirmation_successful=false.
        - If exists=true, output a single object in 'product' with fields name, url, price from the tool.

        Constraints:
        - Do NOT browse or scrape; ONLY use {names["product_tool"]}.
        - URLs must be direct product pages.
        - Prices should be GBP (e.g., £XX.XX) when available.

        Output JSON only per contract below.
        """

        try:
            return Task(
                description=task_description,
                agent=self.agent,
                expected_output=f"""
            Return a valid JSON object only (no extra text):
            {{
              "product": {{
                "name": "Exact product name",
                "url": "direct product page url",
                "price": "£XX.XX"
              }},
              "errors": [
                "Any error messages encountered during confirmation"
              ],
              "confirmation_summary": {{
                "search_query": "{product_query}",
                "retailer": "{retailer}", 
                "confirmation_successful": <true/false>
              }}
            }}

            IMPORTANT:
            - Output JSON only, no wrappers or tags
            - If the tool returns exists=false, return product=null and confirmation_successful=false
            - Ensure URL is a direct product page and price is GBP when available
            - Handle any errors gracefully and include them in the errors array
            """,
                output_pydantic=ConfirmationResult
            )
        except Exception as e:
            self.error_logger.error(f"Failed to create confirmation task: {e}", exc_info=True)
            raise

    
    def create_feedback_enhanced_confirmation_task(self,
                                               product_query: str,
                                               retailer: str,
                                               retailer_url: str,
                                               validation_feedback: Dict[str, Any],
                                                attempt_number: int = 1):
        """
        Create a task for feedback-enhanced product confirmation that uses validation feedback to improve results.

        Uses validation feedback to guide confirmation improvements:
        - Primary issues from previous attempt
        - Retry recommendations for better confirmation
        - Confirmation improvements suggested by validation
        - Alternative search strategies

        Uses custom schema for confirmation:
        {
          "fields": {
            "name": "str",           // Product name as displayed
            "url": "str",            // direct product page url
            "price": "str"           // Product price in GBP format (£XX.XX)
          },
          "name": "Product",
          "is_list": true
        }

        Args:
            product_query: Specific product to search for
            retailer: Name of the retailer website
            retailer_url: URL to navigate to for confirmation
            validation_feedback: Feedback from previous validation attempt
            attempt_number: Current retry attempt number

        Returns:
            CrewAI Task configured for feedback-enhanced confirmation
        """
        from crewai import Task
        from urllib.parse import urlparse

        # Build domain constraint from retailer_url when available
        try:
            retailer_domain = urlparse(retailer_url).netloc if isinstance(retailer_url, str) else ""
        except Exception:
            retailer_domain = ""

        # Optional guidance
        issues = validation_feedback.get('primary_issues', []) or []
        recommendations = validation_feedback.get('retry_recommendations', []) or []
        refinements = validation_feedback.get('search_refinements', []) or []

        feedback_hint = " ".join([
            " ".join(issues[:3]),
            " ".join(recommendations[:3]),
            " ".join(refinements[:3]),
        ]).strip()

        names = self._tools_summary()
        task_description = f"""
        Retry #{attempt_number}: Confirm if {retailer} sells "{product_query}" using {names["product_tool"]}.
        If purchasable, return minimal fields: name, url, price.

        Inputs: product_query, retailer, retailer_domain={retailer_domain}, retailer_url={retailer_url}

        TOOL USAGE:
        - Call {names["product_tool"]} with:
          - product_query: "{product_query}"
          - retailer: "{retailer}"
          - retailer_domain: "{retailer_domain}"
          - keywords: true
          - search_instructions: "{feedback_hint} Allow keywords related to the product to be used in the search"

        HINTS FROM FEEDBACK (optional context for better disambiguation): {feedback_hint} | Target URL: {retailer_url}

        DECISION:
        - If the tool returns exists=false, output product=null and confirmation_successful=false.
        - If exists=true, output a single object in 'product' with fields name, url, price from the tool.

        Constraints: 
        - URLs must be direct product pages.
        - Prices should be GBP when available.

        Output JSON only per contract below.
        """

        try:
            return Task(
                description=task_description,
                agent=self.agent,
                expected_output=f"""
            Return a valid JSON object only (no extra text):
            {{
              "product": {{
                "url": "direct product page url",
                "name": "Exact product name", 
                "price": "£XX.XX"
              }},
              "errors": [
                "Any error messages encountered during confirmation"
              ],
              "confirmation_summary": {{
                "search_query": "{product_query}",
                "retailer": "{retailer}",
                "retry_attempt": {attempt_number},
                "feedback_applied": true,
                "confirmation_successful": <true/false>
              }}
            }}

            IMPORTANT:
            - Output JSON only, no wrappers or tags
            - If the tool returns exists=false, return product=null and confirmation_successful=false
            - Ensure URL is a direct product page and price is GBP when available
            - Handle any errors gracefully and include them in the errors array
            """,
                output_pydantic=ConfirmationResult
            )
        except Exception as e:
            self.error_logger.error(f"Failed to create feedback-enhanced confirmation task: {e}", exc_info=True)
            raise
