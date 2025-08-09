"""ExtractionAgent - Specialized agent for StandardizedProduct data extraction with re-extraction support."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from ..config.settings import settings
from ..config.settings import settings 
from ..schemas.agent_outputs import ExtractionResult
from ..ai_logging.error_logger import get_error_logger

# Optional Selenium fallback from crewai-tools
try:
    from crewai_tools import SeleniumScrapingTool  # type: ignore
    _SELENIUM_AVAILABLE = True
except Exception:
    SeleniumScrapingTool = None  # type: ignore
    _SELENIUM_AVAILABLE = False


class ExtractionAgent:
    """Specialized agent for StandardizedProduct data extraction with feedback loop support."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the extraction agent with StagehandTool + SeleniumScrapingTool."""
        # Handle both old (tools, llm) and new (stagehand_tool, verbose) calling patterns
        supplemental_tools: List[Any] = []
        if _SELENIUM_AVAILABLE:
            try:
                if SeleniumScrapingTool is not None:
                    supplemental_tools.append(SeleniumScrapingTool())
            except Exception:
                pass

        # Build final tool list to ensure Crew surfaces all supplemental tools
        final_tools: List[Any] = []
        if stagehand_tool:
            final_tools.append(stagehand_tool)
        final_tools.extend(supplemental_tools)
        if tools:
            names = {getattr(t, "name", str(type(t))) for t in final_tools}
            for t in tools:
                n = getattr(t, "name", str(type(t)))
                if n not in names:
                    final_tools.append(t)
                    names.add(n)
        tools = final_tools
        
        agent_config = {
            "role": "Data Extraction Specialist",
            "goal": """
            Extract comprehensive and accurate product information from prepared ecommerce pages,
            ensuring strict schema compliance. Process re-extraction requests
            from ValidationAgent to improve data quality through feedback loops.
            """,
            "backstory": """
            You are a specialized product data extraction expert. Your primary responsibility is to
            extract high-quality product data that matches the search goal. When needed to complete
            extraction successfully, you may also perform lightweight navigation (goto a URL) and
            dismiss blocking popups before searching on the site or extracting data using the provided tool.

            Your core expertise includes:
           
            - UK retail platform product data structures (ASDA, Tesco, Waitrose, etc.)
            - Vendor-specific pricing formats and GBP currency handling 
            - Re-extraction based on ValidationAgent feedback
            - Managing dynamic content and JavaScript-rendered data
            - Quality improvement through iterative extraction
            
            CRITICAL: Prefer extracting from pages prepared by research and validation.
            If the page is not directly extractable, you may navigate to the target URL,
            handle simple popups and banners by dismissing them, and proceed with schema-aligned extraction.
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

        self.error_logger = get_error_logger("extraction_agent")
        self.agent = Agent(**agent_config)

    def _tools_summary(self) -> Dict[str, str]:
        """Summarize available tool names to avoid name mismatches at runtime.

        Returns a dict with keys:
        - stagehand: the exact name for Stagehand tool
        - others: comma-separated list of other scraping tools available
        - selenium: the exact Selenium tool name if present, else empty string
        """
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

        names = self._tools_summary()
        task_description = f"""
        Goal: Extract name, website, url, price for "{product_query}" from {retailer} at {retailer_url}.

        Inputs: product_query, retailer, retailer_url, session_id={session_id}

        Tools:
        - Primary: {names["stagehand"]} (navigate → observe → act → extract)
        - Fallback (only if present): {names["selenium"]}

        Procedure:
        1) Navigate to {retailer_url}. If the page is an error/soft-404/404/5xx (e.g., "Looking for something?", "Page not found", "not a functioning page"), immediately return products=[] and extraction_successful=false.
        2) Observe to classify page. If not a product page, perform one on-site search for "{product_query}" and open the best match; if none found, return empty products.
        3) On a product page, extract fields. Prefer {names["stagehand"]} extract then use the product page url for the url field; if observe/act cannot locate elements or the page is highly dynamic, use Selenium fallback to perform the interaction and complete extraction.

        Constraints:
        - One on-site search attempt; no crawling multiple pages
        - Prices must be GBP (e.g., £XX.XX); URLs must be direct product pages

        Output JSON only per contract below.
        """

        try:
            return Task(
                description=task_description,
                agent=self.agent,
                expected_output=f"""
            Return a valid JSON object only (no extra text):
            {{
              "products": [
                {{
                  "name": "Exact product name from site",
                  "website": "website url",
                  "url": "direct product page url",
                  "price": "£XX.XX"
                }}
              ],
              "errors": [
                "Any error messages encountered during extraction"
              ],
              "extraction_summary": {{
                "search_query": "{product_query}",
                "retailer": "{retailer}", 
                "extraction_successful": <true/false>
              }}
            }}

            IMPORTANT:
            - Output JSON only, no wrappers or tags
            - If no errors occur, you may omit the "errors" key
            - Ensure all URLs, names, and prices are accurately extracted
            - Handle any extraction errors gracefully and include them in the errors array
            """,
                output_pydantic=ExtractionResult
            )
        except Exception as e:
            self.error_logger.error(f"Failed to create extraction task: {e}", exc_info=True)
            raise

    
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
            "url": "str",            // direct product page url
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
        Goal (retry #{attempt_number}): Extract product fields for "{product_query}" from {retailer} at {retailer_url}, applying prior feedback.

        Feedback summary:
        - Issues: {issues_text}
        - Recommendations: {recommendations_text}
        - Improvements: {improvements_text}
        - Search refinements: {refinements_text}

        Tools (order): Stagehand → SeleniumScrapingTool (fallback only if needed).

        Procedure:
        1) Navigate to {retailer_url}. If error/soft-404/404/5xx (“Looking for something?”, “Page not found”, “not a functioning page”), return products=[] and extraction_successful=false.
        2) Apply the feedback above while classifying/searching:
           - If not a product page, perform one on-site search for "{product_query}" (using refined terms if given).
           - Open the best match; if none, return empty products.
        3) Extract fields on product page and use the product page url for the url field. Prefer Stagehand extract; use Selenium only if observe/act is unreliable or the page is highly dynamic.

        Constraints: one on-site search attempt; GBP pricing; direct product URL required.

        Output JSON only per contract below.
        """

        try:
            return Task(
                description=task_description,
                agent=self.agent,
                expected_output=f"""
            Return a valid JSON object only (no extra text):
            {{
              "products": [
                {{
                  "url": "Direct product page url",
                  "name": "Exact product name from site", 
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
            - Ensure all URLs, names, and prices are accurately extracted
            - Document what improvements were made based on the feedback
            """,
                output_pydantic=ExtractionResult
            )
        except Exception as e:
            self.error_logger.error(f"Failed to create feedback-enhanced extraction task: {e}", exc_info=True)
            raise
