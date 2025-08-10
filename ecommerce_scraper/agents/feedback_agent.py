"""FeedbackAgent - Decides feedback routing and generates targeted feedback.

This agent owns the responsibility of analyzing validation failures and deciding:
- Which agent should receive feedback first (Research or Confirmation)
- What actionable feedback each agent should get

It uses the AgentCapabilitiesReferenceTool to ensure feedback is aligned with
each agent's actual capabilities.
"""

from typing import Any, Dict, List, Optional
from crewai import Agent, LLM, Task
from ..config.settings import settings
from ..tools.agent_capabilities_reference_tool import AgentCapabilitiesReferenceTool
from ..ai_logging.error_logger import get_error_logger


class FeedbackAgent:
    """Agent that analyzes failures and produces targeted feedback + routing."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, llm: Optional[LLM] = None):
        tools = [AgentCapabilitiesReferenceTool()]

        agent_config = {
            "role": "Feedback Orchestrator",
            "goal": (
                "Analyze validation failures and generate targeted, capability-aligned feedback "
                "for ResearchAgent and ConfirmationAgent. Decide which agent should retry first."
            ),
            "backstory": (
                "You specialize in routing feedback between agents based on their documented "
                "capabilities. You do NOT validate products or research retailers yourself. "
                "Your only job is to map failures to agent capabilities and produce clear, "
                "actionable feedback with a retry strategy."
            ),
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": settings.enable_crew_memory,
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

        self.error_logger = get_error_logger("feedback_agent")
        self._agent = Agent(**agent_config)

    def get_agent(self) -> Agent:
        return self._agent

    def create_targeted_feedback_task(
        self,
        *,
        search_query: str,
        validation_failures: List[Dict[str, Any]],
        retailer: str,
        attempt_number: int = 1,
        max_attempts: int = 3,
        already_searched: Optional[List[Dict[str, Any]]] = None,
    ) -> Task:
        """Create a task that generates targeted feedback and routing using capabilities reference."""

        already_text = "None"
        if already_searched:
            try:
                names = [r.get("vendor", "Unknown") for r in already_searched]
                names_list = ", ".join([n for n in names if n])
                already_text = f"Vendors: {names_list}" if names_list else "Provided"
            except Exception:
                already_text = "Provided"

        description = f"""
        Analyze validation failures and generate targeted feedback aligned to agent capabilities.

        Search Query: {search_query}
        Retailer: {retailer}
        Attempt Number: {attempt_number} of {max_attempts}
        Validation Failures: {len(validation_failures)}
        Already Searched Retailers (avoid duplicates): {already_text}

        TASK OBJECTIVE:
        1. Use agent_capabilities_reference_tool to understand each agent's actionable feedback types.
        2. Categorize failures into research-related and confirmation-related.
        3. Produce actionable feedback for ResearchAgent and ConfirmationAgent strictly within their capabilities.
        4. Decide retry routing: research_first | confirmation_first | both_parallel | give_up and explain why.
        5. Prefer concise, structured output with only implementable actions.

        IMPORTANT: Do NOT include any steps that those agents cannot perform. Align with the capabilities tool.
        """

        expected_output = f"""
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
            "issues": ["..."],
            "retry_recommendations": ["..."],
            "alternative_retailers": ["..."],
            "search_refinements": ["..."]
          }},
          "confirmation_feedback": {{
            "target_agent": "ConfirmationAgent",
            "should_retry": <true/false>,
            "priority": "high|medium|low",
            "issues": ["..."],
            "retry_recommendations": ["..."],
            "confirmation_improvements": ["..."],
            "schema_fixes": ["..."]
          }},
          "retry_strategy": {{
            "recommended_approach": "research_first|confirmation_first|both_parallel|give_up",
            "success_probability": <0.0-1.0>,
            "reasoning": "...",
            "next_steps": ["..."]
          }}
        }}
        """

        return Task(
            description=description,
            agent=self._agent,
            expected_output=expected_output,
        )

    def create_empty_retailers_feedback_task(
        self,
        *,
        search_query: str,
        attempt_number: int,
        max_attempts: int,
        already_searched: Optional[List[Dict[str, Any]]] = None,
    ) -> Task:
        """Feedback task when there are no retailers; bias to research-first."""

        description = f"""
        No retailers found for search query: {search_query}.
        Use agent_capabilities_reference_tool to determine a minimal research-first plan and concise feedback payloads.

        Attempt Number: {attempt_number} of {max_attempts}
        """

        expected_output = f"""
        {{
          "research_feedback": {{"should_retry": true, "priority": "medium"}},
          "confirmation_feedback": {{"should_retry": false, "priority": "low"}},
          "retry_strategy": {{"recommended_approach": "research_first"}}
        }}
        """

        return Task(
            description=description,
            agent=self._agent,
            expected_output=expected_output,
        )


