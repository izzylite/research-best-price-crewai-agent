"""
Agent Capabilities Reference Tool

Provides detailed information about the roles, capabilities, and responsibilities
of ResearchAgent and ExtractionAgent to enable targeted feedback generation.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class AgentCapabilitiesInput(BaseModel):
    """Input schema for agent capabilities reference."""
    agent_name: str = Field(..., description="Name of the agent to get capabilities for ('ResearchAgent' or 'ExtractionAgent' or 'both')")
    capability_type: Optional[str] = Field(None, description="Specific capability type to focus on ('tools', 'feedback_types', 'limitations', 'all')")


class AgentCapabilitiesReferenceTool(BaseTool):
    """Tool that provides structured information about agent capabilities for targeted feedback generation."""
    
    name: str = "agent_capabilities_reference_tool"
    description: str = """
    Get detailed information about ResearchAgent and ExtractionAgent capabilities, tools, 
    and feedback requirements. Use this to understand what each agent can do and what 
    types of feedback they can effectively act upon for retry improvements.
    
    Parameters:
    - agent_name: 'ResearchAgent', 'ExtractionAgent', or 'both'
    - capability_type: 'tools', 'feedback_types', 'limitations', or 'all' (optional)
    
    Returns structured information about agent roles, tools, capabilities, and feedback requirements.
    """
    args_schema: type[BaseModel] = AgentCapabilitiesInput

    def _run(self, agent_name: str, capability_type: Optional[str] = None) -> str:
        """
        Get agent capabilities information.
        
        Args:
            agent_name: Which agent(s) to get information about
            capability_type: Specific type of capability information to focus on
            
        Returns:
            JSON string with detailed agent capabilities information
        """
        try:
            if agent_name.lower() == "both":
                research_info = self._get_research_agent_capabilities()
                extraction_info = self._get_extraction_agent_capabilities()
                
                capabilities_data = {
                    "ResearchAgent": research_info,
                    "ExtractionAgent": extraction_info,
                    "feedback_routing_guidelines": self._get_feedback_routing_guidelines()
                }
            elif agent_name.lower() in ["researchagent", "research_agent", "research"]:
                capabilities_data = {
                    "ResearchAgent": self._get_research_agent_capabilities()
                }
            elif agent_name.lower() in ["extractionagent", "extraction_agent", "extraction"]:
                capabilities_data = {
                    "ExtractionAgent": self._get_extraction_agent_capabilities()
                }
            else:
                return f"Error: Unknown agent name '{agent_name}'. Use 'ResearchAgent', 'ExtractionAgent', or 'both'."
            
            # Filter by capability type if specified
            if capability_type and capability_type.lower() != "all":
                capabilities_data = self._filter_by_capability_type(capabilities_data, capability_type)
            
            import json
            return json.dumps(capabilities_data, indent=2)
            
        except Exception as e:
            return f"Error getting agent capabilities: {str(e)}"

    def _get_research_agent_capabilities(self) -> Dict[str, Any]:
        """Get detailed ResearchAgent capabilities."""
        return {
            "role": "AI-Powered Retailer Research Specialist",
            "primary_responsibility": "Research and identify UK retailers that sell specific products using AI-powered tools",
            "core_capabilities": [
                "AI-powered retailer discovery using Perplexity research",
                "Identifying legitimate UK retailers (excluding price comparison sites)",
                "Finding direct product URLs and availability information",
                "Verifying retailer legitimacy and product availability",
                "Providing alternative retailer suggestions based on feedback",
                "Refining search strategies based on validation feedback"
            ],
            "tools_available": {
                "perplexity_retailer_research_tool": {
                    "description": "AI-powered retailer research using Perplexity API",
                    "parameters": {
                        "product_query": "Specific product to search for",
                        "max_retailers": "Maximum number of retailers to find",
                        "search_instructions": "Enhanced search instructions based on feedback (NEW)"
                    },
                    "capabilities": [
                        "Research UK retailers for specific products",
                        "Find direct product URLs",
                        "Get pricing information",
                        "Apply feedback-enhanced search strategies"
                    ]
                }
            },
            "feedback_types_actionable": {
                "retailer_discovery_issues": [
                    "Wrong or illegitimate retailers discovered",
                    "Price comparison sites instead of direct retailers",
                    "International retailers instead of UK-only stores",
                    "Affiliate marketing sites instead of direct sellers"
                ],
                "url_quality_issues": [
                    "Invalid or inaccessible product URLs",
                    "URLs leading to search pages instead of product pages",
                    "URLs leading to category pages instead of specific products"
                ],
                "search_strategy_issues": [
                    "Search query too broad or narrow",
                    "Missing key search terms or product identifiers",
                    "Not focusing on official brand retailers"
                ],
                "retailer_legitimacy_issues": [
                    "Retailers that don't actually sell the product",
                    "Retailers with poor reputation or reliability",
                    "Retailers that don't ship to UK addresses"
                ]
            },
            "feedback_response_capabilities": {
                "alternative_retailers": "Can prioritize specific UK retailers in research",
                "search_refinements": "Can use improved search terms and strategies",
                "retailer_filtering": "Can exclude problematic retailer types",
                "url_validation": "Can focus on finding direct product URLs",
                "legitimacy_verification": "Can verify retailer authenticity and UK availability"
            },
            "limitations": [
                "Cannot perform web navigation or page interaction",
                "Cannot extract product data from web pages",
                "Cannot handle popups or dynamic content loading",
                "Cannot validate actual product availability in real-time",
                "Relies on Perplexity API for research (requires API key)"
            ],
            "retry_scenarios": [
                "When validation finds wrong retailer types",
                "When product URLs are invalid or inaccessible",
                "When retailers don't actually sell the product",
                "When search strategy needs refinement",
                "When alternative retailers need to be explored"
            ]
        }

    def _get_extraction_agent_capabilities(self) -> Dict[str, Any]:
        """Get detailed ExtractionAgent capabilities."""
        return {
            "role": "AI-Powered Product Data Extraction Specialist",
            "primary_responsibility": "Extract structured product data from retailer websites using AI-powered web automation",
            "core_capabilities": [
                "Navigate to retailer websites and product pages",
                "Extract structured product data using AI-powered tools",
                "Handle dynamic content loading and page interactions",
                "Apply schema-based data extraction with validation",
                "Implement feedback-enhanced extraction strategies",
                "Ensure data quality and completeness"
            ],
            "tools_available": {
                "simplified_stagehand_tool": {
                    "description": "AI-powered web automation and data extraction tool",
                    "operations": {
                        "navigate": "Navigate to specific URLs",
                        "extract": "Extract structured data from web pages",
                        "act": "Perform actions like clicking buttons",
                        "observe": "Observe page elements and content"
                    },
                    "parameters": {
                        "operation": "Type of operation to perform",
                        "url": "URL to navigate to (for navigate operation)",
                        "instruction": "Natural language instruction for extraction/observation",
                        "action": "Specific action to perform (for act operation)"
                    },
                    "capabilities": [
                        "Schema-based product data extraction",
                        "Dynamic content handling",
                        "Popup dismissal and page preparation",
                        "Multi-field data extraction with validation"
                    ]
                }
            },
            "extraction_schema": {
                "StandardizedProduct": {
                    "required_fields": ["name", "price", "url"],
                    "optional_fields": ["image_url", "description", "availability", "brand", "model"],
                    "validation_rules": [
                        "Price must be in GBP format (£X.XX)",
                        "URL must be valid HTTP/HTTPS link",
                        "Name must be non-empty string",
                        "Image URL must be valid if provided"
                    ]
                }
            },
            "feedback_types_actionable": {
                "data_quality_issues": [
                    "Missing or incomplete product data",
                    "Incorrect price formatting or currency",
                    "Poor quality or missing product images",
                    "Inaccurate product names or descriptions"
                ],
                "extraction_strategy_issues": [
                    "Extraction instructions too vague or specific",
                    "Schema compliance failures",
                    "Dynamic content not properly loaded",
                    "Page elements not properly identified"
                ],
                "navigation_issues": [
                    "Unable to access product pages",
                    "Popups blocking content access",
                    "Page loading timeouts or errors",
                    "Invalid or broken URLs from research"
                ],
                "schema_compliance_issues": [
                    "Data doesn't match expected schema format",
                    "Required fields missing from extracted data",
                    "Data type mismatches (string vs number)",
                    "Validation rules not met"
                ]
            },
            "feedback_response_capabilities": {
                "extraction_improvements": "Can modify extraction strategies and instructions",
                "schema_fixes": "Can adjust data formatting to meet schema requirements",
                "navigation_enhancements": "Can improve page navigation and popup handling",
                "data_validation": "Can implement additional data quality checks",
                "retry_strategies": "Can apply different extraction approaches"
            },
            "limitations": [
                "Cannot research or discover new retailers",
                "Cannot modify or validate retailer URLs before extraction",
                "Cannot determine if retailers actually sell products without visiting",
                "Depends on ResearchAgent for retailer discovery and URLs",
                "Requires valid, accessible URLs to perform extraction"
            ],
            "retry_scenarios": [
                "When extracted data is incomplete or poor quality",
                "When schema validation fails",
                "When navigation or page access issues occur",
                "When extraction strategy needs refinement",
                "When data formatting doesn't meet requirements"
            ]
        }

    def _get_feedback_routing_guidelines(self) -> Dict[str, Any]:
        """Get guidelines for routing feedback to appropriate agents."""
        return {
            "research_agent_priority": {
                "conditions": [
                    "More than 50% of validation failures are retailer-related",
                    "URLs are invalid, inaccessible, or lead to wrong pages",
                    "Wrong retailer types discovered (comparison sites, affiliates)",
                    "Retailers don't actually sell the product",
                    "International retailers instead of UK stores"
                ],
                "feedback_focus": [
                    "Alternative retailer suggestions",
                    "Search strategy refinements",
                    "Retailer legitimacy requirements",
                    "URL quality improvements"
                ]
            },
            "extraction_agent_priority": {
                "conditions": [
                    "More than 50% of validation failures are data quality related",
                    "Schema compliance issues",
                    "Missing or incomplete product information",
                    "Data formatting problems",
                    "Navigation or page access issues with valid URLs"
                ],
                "feedback_focus": [
                    "Extraction strategy improvements",
                    "Schema compliance fixes",
                    "Data quality enhancements",
                    "Navigation improvements"
                ]
            },
            "both_agents_needed": {
                "conditions": [
                    "Mixed failure types (both research and extraction issues)",
                    "Validation failures span multiple categories",
                    "Previous single-agent retries have failed"
                ],
                "recommended_approach": "Research first, then extraction",
                "reasoning": "Better retailers lead to better extraction opportunities"
            }
        }

    def _filter_by_capability_type(self, data: Dict[str, Any], capability_type: str) -> Dict[str, Any]:
        """Filter capabilities data by specific type."""
        type_mapping = {
            "tools": ["tools_available"],
            "feedback_types": ["feedback_types_actionable", "feedback_response_capabilities"],
            "limitations": ["limitations", "retry_scenarios"]
        }
        
        if capability_type.lower() not in type_mapping:
            return data
        
        filtered_data = {}
        keys_to_include = type_mapping[capability_type.lower()]
        
        for agent_name, agent_data in data.items():
            if isinstance(agent_data, dict):
                filtered_agent_data = {}
                for key in keys_to_include:
                    if key in agent_data:
                        filtered_agent_data[key] = agent_data[key]
                filtered_data[agent_name] = filtered_agent_data
            else:
                filtered_data[agent_name] = agent_data
        
        return filtered_data
