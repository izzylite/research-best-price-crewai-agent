#!/usr/bin/env python3
"""
Test CrewAI tool calling patterns with SimplifiedStagehandTool
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.tools.simplified_stagehand_tool import SimplifiedStagehandTool
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

def test_crewai_tool_calling():
    """Test how CrewAI calls the SimplifiedStagehandTool"""
    
    print("🧪 Testing CrewAI Tool Calling Patterns")
    print("=" * 60)
    
    # Create the tool
    tool = SimplifiedStagehandTool()
    
    # Create a simple agent
    agent = Agent(
        role="Test Agent",
        goal="Test tool calling",
        backstory="A test agent for debugging tool calls",
        tools=[tool],
        verbose=True
    )
    
    # Create a simple task
    task = Task(
        description="""
        Use the simplified_stagehand_tool to navigate to this URL:
        https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025
        
        Call the tool with operation="navigate" and url="https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/1215686352935-910000975210-1215666947025"
        """,
        agent=agent,
        expected_output="Navigation result"
    )
    
    # Create crew
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True
    )
    
    try:
        print("🚀 Starting CrewAI execution...")
        result = crew.kickoff()
        print(f"✅ CrewAI Result: {result}")
        
    except Exception as e:
        print(f"❌ CrewAI Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 Test Complete")

if __name__ == "__main__":
    test_crewai_tool_calling()
