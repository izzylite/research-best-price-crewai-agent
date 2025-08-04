#!/usr/bin/env python3
"""Test script to demonstrate popup handling functionality."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool
from ecommerce_scraper.utils.popup_handler import PopupHandler, handle_common_popups
from rich.console import Console
from rich.panel import Panel

console = Console()

def test_popup_handling():
    """Test popup handling on ASDA website."""
    
    console.print(Panel(
        "[bold blue]🚫 Testing Popup Handling Functionality[/bold blue]\n\n"
        "This test will:\n"
        "1. Navigate to ASDA website\n"
        "2. Automatically handle popups and banners\n"
        "3. Verify main content is accessible\n"
        "4. Report on popup handling success",
        title="Popup Handling Test"
    ))
    
    # Check environment variables
    if not os.getenv("BROWSERBASE_API_KEY"):
        console.print("[red]❌ BROWSERBASE_API_KEY not found in environment[/red]")
        return False
    
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[red]❌ No LLM API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY)[/red]")
        return False
    
    try:
        console.print("\n🚀 Creating Stagehand session...")
        
        # Create Stagehand tool with context manager
        with EcommerceStagehandTool.create_with_context() as tool:
            console.print("✅ Stagehand session created")
            
            # Navigate to ASDA (this will trigger automatic popup handling)
            console.print("\n🌐 Navigating to ASDA website...")
            result = tool._run(
                instruction="Navigate to ASDA website",
                url="https://www.asda.com/",
                command_type="act"
            )
            console.print(f"Navigation result: {result}")
            
            # Check if main content is accessible
            console.print("\n🔍 Verifying main content accessibility...")
            verification = tool._run(
                instruction="Check if the main ASDA website content is visible, including navigation menu, search box, and product categories",
                command_type="observe"
            )
            console.print(f"Content verification: {verification}")
            
            # Test vendor-specific popup instructions
            console.print("\n📋 Getting ASDA-specific popup instructions...")
            asda_instructions = PopupHandler.get_vendor_specific_instructions("asda")
            console.print(f"ASDA instructions: {asda_instructions}")
            
            # Test manual popup handling if needed
            console.print("\n🛠️ Testing manual popup handling...")
            actions = handle_common_popups(tool, vendor="asda")
            console.print(f"Manual popup actions: {actions}")
            
            console.print("\n✅ Popup handling test completed successfully!")
            return True
            
    except Exception as e:
        console.print(f"\n❌ Test failed with error: {str(e)}")
        return False

def test_popup_strategies():
    """Test popup handling strategies."""
    
    console.print(Panel(
        "[bold green]📋 Popup Handling Strategies[/bold green]",
        title="Available Strategies"
    ))
    
    # Display popup strategies
    for strategy in PopupHandler.POPUP_STRATEGIES:
        console.print(f"\n[bold]{strategy['name']}[/bold]")
        console.print(f"Keywords: {', '.join(strategy['keywords'])}")
        console.print("Actions:")
        for action in strategy['actions']:
            console.print(f"  • {action}")
    
    # Test command generation
    console.print("\n[bold]Generated Commands:[/bold]")
    popup_types = ["cookie", "newsletter", "age", "location", "promotion", "app"]
    
    for popup_type in popup_types:
        command = PopupHandler.create_popup_dismissal_command(popup_type)
        console.print(f"[cyan]{popup_type.title()}:[/cyan] {command}")

def main():
    """Main test function."""
    
    console.print(Panel(
        "[bold magenta]🚫 Popup Handling Test Suite[/bold magenta]\n\n"
        "Testing automatic popup dismissal functionality for ecommerce scraping.",
        title="Test Suite"
    ))
    
    # Test 1: Popup strategies
    console.print("\n" + "="*60)
    console.print("[bold]Test 1: Popup Handling Strategies[/bold]")
    console.print("="*60)
    test_popup_strategies()
    
    # Test 2: Live popup handling (optional)
    console.print("\n" + "="*60)
    console.print("[bold]Test 2: Live Popup Handling[/bold]")
    console.print("="*60)
    
    user_input = console.input("\n[yellow]Do you want to test live popup handling on ASDA? (y/N): [/yellow]")
    
    if user_input.lower() in ['y', 'yes']:
        success = test_popup_handling()
        if success:
            console.print("\n[bold green]🎉 All tests passed![/bold green]")
        else:
            console.print("\n[bold red]❌ Some tests failed![/bold red]")
    else:
        console.print("\n[yellow]Skipping live test. Strategy test completed.[/yellow]")

if __name__ == "__main__":
    main()
