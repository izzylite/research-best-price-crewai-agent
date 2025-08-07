"""ResearchAgent - Specialized agent for AI-powered retailer research."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from ..config.settings import settings
from ..tools.perplexity_retailer_research_tool import PerplexityRetailerResearchTool


class ResearchAgent:
    """Specialized agent for AI-powered retailer research and discovery."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the research agent with Perplexity research tool."""
        # Create Perplexity retailer research tool
        perplexity_tool = PerplexityRetailerResearchTool()

        # Use only the Perplexity research tool for retailer discovery
        tools = [perplexity_tool]
        
        agent_config = {
            "role": "AI-Powered Retailer Research Specialist",
            "goal": """
            Research UK retailers that sell specific products using AI-powered tools. Focus exclusively
            on retailer discovery and validation - identify legitimate UK retailers, find direct product
            URLs, and provide comprehensive retailer information for product searches.
            """,
            "backstory": """
            You are a specialized AI-powered retailer research expert with deep knowledge of UK retail
            platforms and product availability. Your primary responsibility is to research and identify
            UK retailers that sell specific products using AI-powered research tools.

            Your core expertise includes:
            - AI-powered retailer discovery using Perplexity research for product-specific searches
            - Identifying legitimate UK retailers (excluding price comparison sites and affiliate sites)
            - Finding direct product URLs and availability information
            - Verifying retailer legitimacy and product availability
            - Providing alternative retailer suggestions based on validation feedback
            - Refining search strategies based on feedback to improve research quality
            - Focusing on major UK retailers: ASDA, Tesco, Waitrose, Amazon UK, eBay UK, Argos, etc.

            TOOLS AVAILABLE:
            - perplexity_retailer_research_tool: Use this to research UK retailers that sell specific products

            CRITICAL: You focus ONLY on retailer research and discovery. You do NOT handle web navigation,
            popup dismissal, or page preparation - those are handled by other agents. Your job is to find
            the right retailers and provide accurate product URLs for the ExtractionAgent to work with.
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

    def create_retailer_research_task(self,
                                    product_query: str,
                                    max_retailers: int = 5,
                                    session_id: str = None):
        """Create a task for researching UK retailers that sell a specific product."""
        from crewai import Task

        task_description = f"""
        Research UK retailers that sell "{product_query}" using AI-powered research tools.

        Product Query: {product_query}
        Max Retailers: {max_retailers}
        Session ID: {session_id}

        RETAILER RESEARCH WORKFLOW:
        1. **Use the perplexity_retailer_research_tool to research UK retailers**
        2. **Call the tool with these exact parameters:**
           - product_query: "{product_query}"
           - max_retailers: {max_retailers}
           - search_instructions: (optional, for enhanced searches)
        3. **Focus on finding legitimate UK retailers that sell products directly**
        4. **Exclude price comparison sites and affiliate marketing sites**
        5. **Prioritize major UK retailers like ASDA, Tesco, Amazon UK, eBay UK, Argos, etc.**
        6. **Get direct product URLs where possible**

        TOOLS AVAILABLE:
        - perplexity_retailer_research_tool: Use this to research retailers that sell the specific product

        RESEARCH REQUIREMENTS:
        - Find retailers that actually sell the product, not just general retailers
        - Get direct product URLs when available
        - Include pricing information if found
        - Verify retailer legitimacy (exclude comparison sites, affiliate sites)
        - Focus on UK-based retailers with online presence

        IMPORTANT: Use the perplexity_retailer_research_tool to get comprehensive retailer information.
        Do not make assumptions - use the research tool to get real data about where this product is sold.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Retailer research result:
            {{
              "product_query": "{product_query}",
              "retailers": [
                {{
                  "name": "Retailer Name",
                  "website": "retailer-domain.co.uk",
                  "product_url": "direct URL to product page if found",
                  "price": "£XX.XX or 'Price not available'",
                  "availability": "In stock/Out of stock/Unknown",
                  "notes": "Any relevant information about this retailer's offering"
                }}
              ],
              "research_summary": "Brief summary of findings and recommendations",
              "total_found": <number_of_retailers>,
              "research_complete": true
            }}

            Provide comprehensive retailer research results with direct product URLs where possible.
            """
        )

    def create_feedback_enhanced_research_task(self,
                                             product_query: str,
                                             validation_feedback: Dict[str, Any],
                                             attempt_number: int = 1,
                                             max_retailers: int = 5,
                                             session_id: str = None):
        """Create a task for feedback-enhanced retailer research based on validation feedback."""
        from crewai import Task

        # Extract feedback components
        research_feedback = validation_feedback.get('research_feedback', {})
        issues = research_feedback.get('issues', [])
        retry_recommendations = research_feedback.get('retry_recommendations', [])
        alternative_retailers = research_feedback.get('alternative_retailers', [])
        search_refinements = research_feedback.get('search_refinements', [])

        # Format feedback for task description
        issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "- No specific research issues identified"
        recommendations_text = "\n".join(f"- {rec}" for rec in retry_recommendations) if retry_recommendations else "- Use standard research approach"
        alternatives_text = "\n".join(f"- {alt}" for alt in alternative_retailers) if alternative_retailers else "- Focus on major UK retailers"
        refinements_text = "\n".join(f"- {ref}" for ref in search_refinements) if search_refinements else "- Use original search query"

        task_description = f"""
        Conduct improved retailer research for "{product_query}" using validation feedback to address previous issues.
        This is retry attempt #{attempt_number} with targeted feedback to improve research quality.

        **RESEARCH PARAMETERS:**
        Product Query: {product_query}
        Max Retailers: {max_retailers}
        Retry Attempt: {attempt_number}
        Session ID: {session_id}

        **VALIDATION FEEDBACK FROM PREVIOUS ATTEMPT:**

        Research Issues Identified:
        {issues_text}

        Retry Recommendations:
        {recommendations_text}

        Alternative Retailers to Consider:
        {alternatives_text}

        Search Query Refinements:
        {refinements_text}

        **FEEDBACK-ENHANCED RESEARCH PROCESS:**
        1. **Apply Search Refinements:** Use improved search terms based on feedback
        2. **Focus on Alternative Retailers:** Prioritize the suggested alternative retailers
        3. **Address Previous Issues:** Specifically resolve the research issues identified
        4. **Enhanced Validation:** Ensure retailers actually sell the product directly
        5. **Quality Verification:** Double-check retailer legitimacy and product availability

        **IMPROVED RESEARCH REQUIREMENTS:**
        - Address all research issues identified in the feedback
        - Focus on legitimate UK retailers that actually sell "{product_query}"
        - Avoid price comparison sites and affiliate marketing sites
        - Get direct product URLs where possible, not search result pages
        - Verify retailer websites are accessible and functional
        - Ensure product availability and pricing information accuracy

        **TOOLS AVAILABLE:**
        - perplexity_retailer_research_tool: Use this with enhanced search_instructions parameter

        **TOOL USAGE WITH FEEDBACK:**
        Call the perplexity_retailer_research_tool with these parameters:
        - product_query: "{product_query}"
        - max_retailers: {max_retailers}
        - search_instructions: "Find UK retailers that sell {product_query}. {' '.join(retry_recommendations) if retry_recommendations else 'Focus on major UK retailers.'} {' Prioritize: ' + ', '.join(alternative_retailers) if alternative_retailers else ''} {' Search terms: ' + ', '.join(search_refinements) if search_refinements else ''} {' Avoid: ' + ', '.join(issues) if issues else ''}"

        IMPORTANT: Use the search_instructions parameter to pass all feedback recommendations to the tool for enhanced search quality.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Improved retailer research result addressing validation feedback:
            {{
              "product_query": "{product_query}",
              "retry_attempt": {attempt_number},
              "feedback_applied": true,
              "retailers": [
                {{
                  "name": "Improved Retailer Name",
                  "website": "verified-retailer-domain.co.uk",
                  "product_url": "direct URL to product page (verified)",
                  "price": "£XX.XX or 'Price not available'",
                  "availability": "In stock/Out of stock/Unknown",
                  "legitimacy_verified": true,
                  "notes": "Why this retailer is better than previous attempts"
                }}
              ],
              "research_improvements": {{
                "issues_addressed": {issues},
                "recommendations_applied": {retry_recommendations},
                "search_refinements_used": {search_refinements},
                "alternative_retailers_found": <number>,
                "quality_improvements": [
                  "List of specific improvements made based on feedback"
                ]
              }},
              "research_summary": "Brief summary of improved findings and how feedback was addressed",
              "total_found": <number_of_retailers>,
              "research_complete": true
            }}

            Show clear improvement over previous research attempt by addressing all validation feedback.
            """
        )
