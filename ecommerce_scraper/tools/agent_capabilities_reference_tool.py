"""
Agent Capabilities Reference Tool

Provides detailed information about the roles, capabilities, and responsibilities
of ResearchAgent and ConfirmationAgent to enable targeted feedback generation.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class AgentCapabilitiesInput(BaseModel):
    """Input schema for agent capabilities reference."""
    agent_name: str = Field(..., description="Name of the agent to get capabilities for ('ResearchAgent' or 'ConfirmationAgent' or 'both')")
    capability_type: Optional[str] = Field(None, description="Specific capability type to focus on ('tools', 'feedback_types', 'limitations', 'all')")


class AgentCapabilitiesReferenceTool(BaseTool):
    """Tool that provides structured information about agent capabilities for targeted feedback generation."""
    
    name: str = "agent_capabilities_reference_tool"
    description: str = """
    Get detailed information about ResearchAgent and ConfirmationAgent capabilities, tools, 
    and feedback requirements. Use this to understand what each agent can do and what 
    types of feedback they can effectively act upon for retry improvements.
    
    Parameters:
    - agent_name: 'ResearchAgent', 'ConfirmationAgent', or 'both'
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
                confirmation_info = self._get_confirmation_agent_capabilities()
                
                capabilities_data = {
                    "ResearchAgent": research_info,
                    "ConfirmationAgent": confirmation_info,
                    "feedback_routing_guidelines": self._get_feedback_routing_guidelines()
                }
            elif agent_name.lower() in ["researchagent", "research_agent", "research"]:
                capabilities_data = {
                    "ResearchAgent": self._get_research_agent_capabilities()
                }
            elif agent_name.lower() in ["confirmationagent", "confirmation_agent", "confirmation", "confirmationagent", "confirmation_agent", "confirmation"]:
                capabilities_data = {
                    "ConfirmationAgent": self._get_confirmation_agent_capabilities()
                }
            else:
                return f"Error: Unknown agent name '{agent_name}'. Use 'ResearchAgent', 'ConfirmationAgent', or 'both'."
            
            # Filter by capability type if specified
            if capability_type and capability_type.lower() != "all":
                capabilities_data = self._filter_by_capability_type(capabilities_data, capability_type)
            
            import json
            # Add a small note to discourage repeated calls in the same attempt
            return json.dumps({
                "capabilities": capabilities_data,
                "advisory": "Use this reference at most once per validation attempt to avoid loops."
            }, indent=2)
            
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
                        "search_instructions": "Enhanced search instructions based on feedback",
                        "exclude_urls": "List of exact product URLs to exclude from results",
                        "exclude_domains": "List of retailer domains to exclude (e.g., 'example.com')",
                        "vendor_name": "Optional vendor to scope search (feedback retries)",
                        "vendor_url": "Optional vendor base URL/domain to constrain site",
                        "keywords": "Optional related keywords to match variants within the vendor site",
                        "amount": "Optional number of vendor-scoped results (capped by max_retailers)"
                    },
                    "capabilities": [
                        "Research UK retailers for specific products",
                        "Find direct product URLs",
                        "Get pricing information",
                        "Apply feedback-enhanced search strategies",
                        "Vendor-scoped search: find up to N matching products within a specific vendor site using provided keywords",
                        "Honor explicit URL/domain exclusions with defensive post-filtering"
                    ]
                }
                ,
                "perplexity_vendor_scoped_research_tool": {
                    "description": "Search within a specific vendor site using related keywords and return direct product-page URLs.",
                    "parameters": {
                        "product_query": "Product to find",
                        "vendor_name": "Vendor/Retailer name",
                        "vendor_url": "Vendor base URL/domain (optional but recommended)",
                        "keywords": "Related keywords or list of keywords",
                        "amount": "How many results to return (cap externally if needed)",
                        "exclude_urls": "Exact URLs to exclude"
                    },
                    "capabilities": [
                        "Vendor-scoped research using Perplexity",
                        "Find direct product URLs on a single site",
                        "Allow closely related keywords and minor naming variants",
                        "Return results compatible with research flow"
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
                "Cannot confirm product data from web pages",
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

    def _get_confirmation_agent_capabilities(self) -> Dict[str, Any]:
        """Get detailed ConfirmationAgent capabilities."""
        return {
            "role": "Perplexity Product Confirmation Specialist",
            "primary_responsibility": "Confirm if a specific retailer sells a product via Perplexity and return name, url, price",
            "core_capabilities": [
                "Confirm product availability via Perplexity",
                "Return minimal fields: name, url, price",
                "Use feedback-driven search_instructions for disambiguation",
                "Report unavailable when retailer does not sell the product"
            ],
            "tools_available": {
                "perplexity_retailer_product_tool": {
                    "description": "Confirm retailer sells product and return name, url, price",
                    "parameters": {
                        "product_query": "Product to confirm",
                        "retailer": "Retailer name",
                        "retailer_url": "Optional candidate direct product URL to prefer if valid",
                        "retailer_domain": "Optional official retailer domain to constrain results (e.g., 'tesco.com')",
                        "keywords": "Allow using keywords related to the product in confirmation",
                        "search_instructions": "Feedback-guided disambiguation"
                    },
                    "capabilities": [
                        "Confirm purchasability",
                        "Provide direct product URL",
                        "Provide GBP price when available",
                        "Respect domain constraints and leverage provided candidate URLs when supplied"
                    ]
                }
            },
            "confirmation_schema": {
                "MinimalProduct": {
                    "required_fields": ["name", "price", "url"],
                    "optional_fields": [],
                    "validation_rules": [
                        "Price must be in GBP format (£X.XX)",
                        "URL must be valid HTTP/HTTPS link",
                        "Name must be non-empty string"
                    ]
                }
            },
            "feedback_types_actionable": {
                "data_quality_issues": [
                    "Missing minimal fields (name, url, price)",
                    "Incorrect price formatting or currency",
                    "Inaccurate product name"
                ],
                "confirmation_strategy_issues": [
                    "Ambiguous product query",
                    "Retailer has multiple variants",
                    "Needs feedback-driven search_instructions"
                ],
                "schema_compliance_issues": [
                    "MinimalProduct schema not satisfied"
                ]
            },
            "feedback_response_capabilities": {
                "confirmation_improvements": "Can refine product confirmation via search_instructions",
                "schema_fixes": "Can adjust minimal field formatting",
                "retry_strategies": "Can re-confirm with refined hints"
            },
            "limitations": [
                "Does not browse or scrape",
                "Depends on ResearchAgent for retailer discovery and URLs",
                "Relies on Perplexity API availability"
            ],
            "retry_scenarios": [
                "When minimal fields are missing or invalid",
                "When disambiguation is needed for variants",
                "When GBP price was not returned and is required"
            ]
        }

    def _get_feedback_routing_guidelines(self) -> Dict[str, Any]:
        """Get guidelines for routing feedback to appropriate agents."""
        return {
            "research_agent_priority": {
                "conditions": [
                    "More than 50% of validation failures are retailer-related",
                    "URLs lead to comparison/affiliate sites",
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
            "confirmation_agent_priority": {
                "conditions": [
                    "More than 50% of validation failures are data quality related",
                    "Minimal fields missing (name, url, price)",
                    "Price formatting not GBP",
                    "Ambiguous product confirmation requiring hints"
                ],
                "feedback_focus": [
                    "Refine search_instructions",
                    "Ensure minimal fields",
                    "Price normalization to GBP"
                ]
            },
            "both_agents_needed": {
                "conditions": [
                    "Mixed failure types (both research and confirmation issues)",
                    "Validation failures span multiple categories",
                    "Previous single-agent retries have failed"
                ],
                "recommended_approach": "Research first, then confirmation",
                "reasoning": "Better retailers lead to better confirmation opportunities"
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
