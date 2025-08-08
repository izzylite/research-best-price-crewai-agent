#!/usr/bin/env python3
"""
Demonstration of the Enhanced ValidationAgent with Agent Capabilities Reference Tool

This script shows how the ValidationAgent now uses the AgentCapabilitiesReferenceTool
to generate more targeted and effective feedback for both ResearchAgent and ExtractionAgent.
"""

import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.tools.agent_capabilities_reference_tool import AgentCapabilitiesReferenceTool


def demonstrate_agent_capabilities_tool():
    """Demonstrate the AgentCapabilitiesReferenceTool functionality."""
    
    print("🔧 Agent Capabilities Reference Tool Demonstration")
    print("=" * 60)
    print()
    
    tool = AgentCapabilitiesReferenceTool()
    
    # Test 1: Get both agents' capabilities
    print("📋 Test 1: Get Both Agents' Capabilities")
    print("-" * 50)
    
    result = tool._run(agent_name="both", capability_type="all")
    capabilities_data = json.loads(result)
    
    print("ResearchAgent Capabilities:")
    research_agent = capabilities_data["ResearchAgent"]
    print(f"  Role: {research_agent['role']}")
    print(f"  Tools: {list(research_agent['tools_available'].keys())}")
    print(f"  Actionable Feedback Types: {len(research_agent['feedback_types_actionable'])}")
    print()
    
    print("ExtractionAgent Capabilities:")
    extraction_agent = capabilities_data["ExtractionAgent"]
    print(f"  Role: {extraction_agent['role']}")
    print(f"  Tools: {list(extraction_agent['tools_available'].keys())}")
    print(f"  Actionable Feedback Types: {len(extraction_agent['feedback_types_actionable'])}")
    print()
    
    # Test 2: Get specific capability types
    print("📋 Test 2: Get Specific Capability Types")
    print("-" * 50)
    
    tools_result = tool._run(agent_name="both", capability_type="tools")
    tools_data = json.loads(tools_result)
    
    print("Tools Available:")
    for agent_name, agent_data in tools_data.items():
        if "tools_available" in agent_data:
            print(f"  {agent_name}:")
            for tool_name, tool_info in agent_data["tools_available"].items():
                print(f"    - {tool_name}: {tool_info['description']}")
    print()
    
    # Test 3: Get feedback routing guidelines
    print("📋 Test 3: Feedback Routing Guidelines")
    print("-" * 50)
    
    routing_guidelines = capabilities_data["feedback_routing_guidelines"]
    
    print("ResearchAgent Priority Conditions:")
    for condition in routing_guidelines["research_agent_priority"]["conditions"]:
        print(f"  - {condition}")
    print()
    
    print("ExtractionAgent Priority Conditions:")
    for condition in routing_guidelines["extraction_agent_priority"]["conditions"]:
        print(f"  - {condition}")
    print()


def simulate_enhanced_feedback_generation():
    """Simulate how the ValidationAgent would use the capabilities tool for feedback generation."""
    
    print("🎯 Enhanced Feedback Generation Simulation")
    print("=" * 60)
    print()
    
    # Simulate validation failures
    validation_failures = [
        {
            "issue": "Found price comparison sites instead of direct retailers",
            "type": "research_related",
            "severity": "high"
        },
        {
            "issue": "Product URLs lead to search pages rather than product pages",
            "type": "research_related", 
            "severity": "medium"
        },
        {
            "issue": "Missing product descriptions in extracted data",
            "type": "extraction_related",
            "severity": "low"
        }
    ]
    
    print("Validation Failures to Address:")
    for i, failure in enumerate(validation_failures, 1):
        print(f"  {i}. {failure['issue']} ({failure['type']}, {failure['severity']})")
    print()
    
    # Get agent capabilities
    tool = AgentCapabilitiesReferenceTool()
    capabilities_result = tool._run(agent_name="both", capability_type="all")
    capabilities_data = json.loads(capabilities_result)
    
    # Analyze failures against agent capabilities
    print("📊 Failure Analysis Against Agent Capabilities")
    print("-" * 50)
    
    research_failures = [f for f in validation_failures if f["type"] == "research_related"]
    extraction_failures = [f for f in validation_failures if f["type"] == "extraction_related"]
    
    print(f"Research-related failures: {len(research_failures)}")
    print(f"Extraction-related failures: {len(extraction_failures)}")
    
    # Determine priority based on capabilities
    research_agent_caps = capabilities_data["ResearchAgent"]["feedback_types_actionable"]
    extraction_agent_caps = capabilities_data["ExtractionAgent"]["feedback_types_actionable"]
    
    print()
    print("🎯 Capability-Based Feedback Generation")
    print("-" * 50)
    
    # Generate ResearchAgent feedback
    print("ResearchAgent Feedback:")
    research_actionable_issues = []
    for failure in research_failures:
        issue = failure["issue"]
        if "price comparison sites" in issue.lower():
            research_actionable_issues.append("retailer_discovery_issues")
        elif "search pages" in issue.lower():
            research_actionable_issues.append("url_quality_issues")
    
    print(f"  Actionable Issue Categories: {research_actionable_issues}")
    print(f"  Can Address: {len(research_actionable_issues)} out of {len(research_failures)} research issues")
    
    # Generate specific feedback based on capabilities
    research_feedback = {
        "target_agent": "ResearchAgent",
        "should_retry": True,
        "priority": "high",
        "issues": [f["issue"] for f in research_failures],
        "retry_recommendations": [
            "Focus on major UK electronics retailers",
            "Search for official brand retailers",
            "Verify URLs lead to actual product pages"
        ],
        "alternative_retailers": ["Currys", "John Lewis", "Amazon UK"],
        "search_refinements": ["iPhone 15 Pro official UK retailers"]
    }
    
    print(f"  Generated Feedback: {json.dumps(research_feedback, indent=4)}")
    print()
    
    # Generate ExtractionAgent feedback
    print("ExtractionAgent Feedback:")
    extraction_actionable_issues = []
    for failure in extraction_failures:
        issue = failure["issue"]
        if "missing" in issue.lower() and "description" in issue.lower():
            extraction_actionable_issues.append("data_quality_issues")
    
    print(f"  Actionable Issue Categories: {extraction_actionable_issues}")
    print(f"  Can Address: {len(extraction_actionable_issues)} out of {len(extraction_failures)} extraction issues")
    
    extraction_feedback = {
        "target_agent": "ExtractionAgent",
        "should_retry": True,
        "priority": "low",
        "issues": [f["issue"] for f in extraction_failures],
        "retry_recommendations": [
            "Improve extraction instructions to include product descriptions",
            "Verify all schema fields are being extracted"
        ],
        "extraction_improvements": [
            "Use more comprehensive extraction instructions",
            "Add specific focus on product description fields"
        ]
    }
    
    print(f"  Generated Feedback: {json.dumps(extraction_feedback, indent=4)}")
    print()
    
    # Determine retry strategy using routing guidelines
    routing_guidelines = capabilities_data["feedback_routing_guidelines"]
    
    print("🔄 Retry Strategy Determination")
    print("-" * 50)
    
    research_failure_percentage = len(research_failures) / len(validation_failures) * 100
    extraction_failure_percentage = len(extraction_failures) / len(validation_failures) * 100
    
    print(f"Research failures: {research_failure_percentage:.1f}%")
    print(f"Extraction failures: {extraction_failure_percentage:.1f}%")
    
    if research_failure_percentage > 50:
        recommended_approach = "research_first"
        reasoning = "More than 50% of failures are research-related"
    elif extraction_failure_percentage > 50:
        recommended_approach = "extraction_first"
        reasoning = "More than 50% of failures are extraction-related"
    else:
        recommended_approach = "research_first"
        reasoning = "Mixed failures - research improvements enable better extraction"
    
    retry_strategy = {
        "recommended_approach": recommended_approach,
        "success_probability": 0.8,
        "reasoning": reasoning,
        "next_steps": [
            f"1. Retry with {recommended_approach.replace('_', ' ')}",
            "2. Apply capability-based feedback",
            "3. Validate improvements"
        ]
    }
    
    print(f"Recommended Strategy: {json.dumps(retry_strategy, indent=2)}")


def demonstrate_before_after_comparison():
    """Show the before/after comparison of feedback generation."""
    
    print("\n📊 Before vs After Comparison")
    print("=" * 60)
    print()
    
    print("❌ BEFORE: Generic Feedback (Without Capabilities Tool)")
    print("-" * 55)
    print("- Generic suggestions not tailored to agent capabilities")
    print("- May suggest actions agents cannot perform")
    print("- No understanding of tool limitations")
    print("- Ineffective retry strategies")
    print()
    
    print("✅ AFTER: Targeted Feedback (With Capabilities Tool)")
    print("-" * 55)
    print("- Feedback precisely tailored to what each agent can do")
    print("- Only suggests actionable improvements")
    print("- Considers tool capabilities and limitations")
    print("- Intelligent retry strategy based on agent strengths")
    print("- Higher success probability for retries")


def main():
    """Run the complete demonstration."""
    demonstrate_agent_capabilities_tool()
    print("\n" + "=" * 60)
    simulate_enhanced_feedback_generation()
    demonstrate_before_after_comparison()
    
    print("\n🎉 CONCLUSION")
    print("=" * 60)
    print("The enhanced ValidationAgent with AgentCapabilitiesReferenceTool")
    print("generates more targeted, effective feedback by understanding exactly")
    print("what each agent can do and what types of feedback they can act upon.")
    print("This leads to higher success rates and more efficient retry cycles.")


if __name__ == "__main__":
    main()
