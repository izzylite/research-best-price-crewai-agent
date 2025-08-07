#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced feedback system for the Perplexity Retailer Research Tool.

This script shows how the tool now accepts feedback-enhanced search instructions
and how the ResearchAgent can provide targeted search guidance based on validation feedback.
"""

import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.tools.perplexity_retailer_research_tool import PerplexityRetailerResearchTool


def test_basic_research():
    """Test basic research without feedback (original functionality)."""
    print("🔍 Testing Basic Research (No Feedback)")
    print("=" * 50)
    
    tool = PerplexityRetailerResearchTool()
    
    # Test basic research
    result = tool._run(
        product_query="iPhone 15 Pro",
        max_retailers=3
    )
    
    print("Basic Research Result:")
    print(result)
    print("\n")


def test_feedback_enhanced_research():
    """Test feedback-enhanced research with specific instructions."""
    print("🎯 Testing Feedback-Enhanced Research")
    print("=" * 50)
    
    tool = PerplexityRetailerResearchTool()
    
    # Simulate validation feedback that would come from the ValidationAgent
    feedback_instructions = """Find UK retailers that sell iPhone 15 Pro with the following requirements:
- Focus on major UK electronics retailers like Currys, John Lewis, Amazon UK
- Avoid price comparison sites and affiliate marketing sites  
- Prioritize retailers that offer direct product URLs and verified pricing
- Search specifically for official Apple retailers in the UK
- Ensure retailers actually have the product in stock, not just listings"""
    
    # Test feedback-enhanced research
    result = tool._run(
        product_query="iPhone 15 Pro",
        max_retailers=3,
        search_instructions=feedback_instructions
    )
    
    print("Feedback-Enhanced Research Result:")
    print(result)
    print("\n")


def test_validation_feedback_simulation():
    """Simulate how the ResearchAgent would use validation feedback."""
    print("🔄 Simulating Validation Feedback Loop")
    print("=" * 50)
    
    # Simulate validation feedback from ValidationAgent
    validation_feedback = {
        "research_feedback": {
            "issues": [
                "Found price comparison sites instead of direct retailers",
                "Some URLs led to search pages rather than product pages"
            ],
            "retry_recommendations": [
                "Focus on major UK electronics retailers",
                "Search for official Apple authorized retailers",
                "Verify URLs lead to actual product pages"
            ],
            "alternative_retailers": [
                "Currys",
                "John Lewis", 
                "Amazon UK",
                "Argos"
            ],
            "search_refinements": [
                "iPhone 15 Pro official UK retailers",
                "iPhone 15 Pro buy online UK authorized"
            ]
        }
    }
    
    # Extract feedback components (as ResearchAgent would do)
    research_feedback = validation_feedback.get('research_feedback', {})
    issues = research_feedback.get('issues', [])
    retry_recommendations = research_feedback.get('retry_recommendations', [])
    alternative_retailers = research_feedback.get('alternative_retailers', [])
    search_refinements = research_feedback.get('search_refinements', [])
    
    # Build enhanced search instructions (as ResearchAgent would do)
    enhanced_instructions = f"""Find UK retailers that sell iPhone 15 Pro. 
{' '.join(retry_recommendations) if retry_recommendations else 'Focus on major UK retailers.'}
{' Prioritize: ' + ', '.join(alternative_retailers) if alternative_retailers else ''}
{' Search terms: ' + ', '.join(search_refinements) if search_refinements else ''}
{' Avoid: ' + ', '.join(issues) if issues else ''}

Ensure all retailers are legitimate UK-based stores with direct product URLs."""
    
    print("Generated Enhanced Search Instructions:")
    print(enhanced_instructions)
    print("\n")
    
    # Use the enhanced instructions with the tool
    tool = PerplexityRetailerResearchTool()
    result = tool._run(
        product_query="iPhone 15 Pro",
        max_retailers=5,
        search_instructions=enhanced_instructions
    )
    
    print("Result with Validation Feedback Applied:")
    print(result)
    print("\n")


def main():
    """Run all tests to demonstrate the enhanced feedback system."""
    print("🚀 Enhanced Feedback System Test Suite")
    print("=" * 60)
    print("This demonstrates how the Perplexity tool now supports")
    print("feedback-enhanced search instructions from the ResearchAgent.")
    print("=" * 60)
    print("\n")
    
    try:
        # Test 1: Basic research (backward compatibility)
        test_basic_research()
        
        # Test 2: Feedback-enhanced research
        test_feedback_enhanced_research()
        
        # Test 3: Full validation feedback simulation
        test_validation_feedback_simulation()
        
        print("✅ All tests completed successfully!")
        print("\n🎯 Key Improvements:")
        print("- Tool now accepts search_instructions parameter")
        print("- Base guidelines moved to system role")
        print("- ResearchAgent can provide targeted feedback")
        print("- Validation feedback drives search improvements")
        print("- Backward compatibility maintained")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Note: This test requires PERPLEXITY_API_KEY to be set for full functionality.")
        print("Without the API key, the tool will raise an exception as designed.")


if __name__ == "__main__":
    main()
