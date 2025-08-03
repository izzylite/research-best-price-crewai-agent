#!/usr/bin/env python3
"""
Interactive Ecommerce Scraper - User-friendly interface for the CrewAI scraping system.
This script guides users through the scraping process with questions and prompts.
"""

import os
import sys
import json
from typing import List, Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv()

console = Console()

def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        "BROWSERBASE_API_KEY",
        "BROWSERBASE_PROJECT_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        console.print(Panel(
            f"""[bold red]❌ Missing Environment Variables[/bold red]

The following required environment variables are not set:
{chr(10).join(f'  • {var}' for var in missing_vars)}

Please check your .env file and ensure these variables are configured.
            """,
            title="⚠️ Configuration Error",
            border_style="red"
        ))
        return False
    
    # Check if at least one LLM API key is available
    llm_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    has_llm = any(os.getenv(key) for key in llm_keys)
    
    if not has_llm:
        console.print(Panel(
            """[bold yellow]⚠️ No LLM API Key Found[/bold yellow]

You need at least one of these API keys:
  • OPENAI_API_KEY (for GPT models)
  • ANTHROPIC_API_KEY (for Claude models)

The scraper may not work properly without an LLM API key.
            """,
            title="⚠️ LLM Configuration Warning",
            border_style="yellow"
        ))
        
        if not Confirm.ask("Continue anyway?"):
            return False
    
    return True

def show_welcome():
    """Show welcome message and system info."""
    console.print(Panel(
        """[bold blue]🤖 Welcome to the Interactive Ecommerce Scraper![/bold blue]

This tool uses CrewAI agents with Stagehand browser automation to scrape
ecommerce websites intelligently. The system can:

✨ [green]Scrape individual product pages[/green]
🔍 [green]Search and scrape multiple products[/green]
🧠 [green]Adapt to different ecommerce site structures[/green]
📊 [green]Extract structured product data[/green]
✅ [green]Validate and clean extracted data[/green]

[yellow]Supported sites include Amazon, eBay, Shopify stores, and generic ecommerce sites.[/yellow]
        """,
        title="🛍️ Ecommerce Scraper",
        border_style="blue"
    ))

def get_scraping_mode():
    """Ask user what type of scraping they want to do."""
    table = Table(title="🎯 Scraping Options")
    table.add_column("Option", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Best For", style="green")
    
    table.add_row("1", "Single Product", "Getting detailed info about one specific product")
    table.add_row("2", "Product Search", "Finding and scraping products by search term")
    table.add_row("3", "Multiple URLs", "Scraping several specific product pages")
    table.add_row("4", "Test System", "Verifying the scraper is working correctly")
    
    console.print(table)
    
    choice = Prompt.ask(
        "\n[bold yellow]What would you like to do?[/bold yellow]",
        choices=["1", "2", "3", "4"],
        default="1"
    )
    
    return choice

def get_single_product_details():
    """Get details for single product scraping."""
    console.print("\n[bold green]📦 Single Product Scraping[/bold green]")
    
    # Show some example URLs
    console.print("\n[dim]Example URLs you can try:[/dim]")
    examples = [
        "https://demo.vercel.store/product/acme-geometric-circles-t-shirt",
        "https://demo.vercel.store/search",
        "https://www.amazon.com/dp/[product-id]",
        "https://www.ebay.com/itm/[item-id]"
    ]
    
    for i, example in enumerate(examples, 1):
        console.print(f"[dim]  {i}. {example}[/dim]")
    
    product_url = Prompt.ask(
        "\n[yellow]Enter the product URL you want to scrape[/yellow]",
        default="https://demo.vercel.store/products/acme-mug"
    )
    
    # Validate URL
    if not product_url.startswith(('http://', 'https://')):
        console.print("[red]❌ Please provide a valid URL starting with http:// or https://[/red]")
        return None
    
    return {"url": product_url}

def get_search_details():
    """Get details for search and scrape operation."""
    console.print("\n[bold green]🔍 Product Search & Scrape[/bold green]")
    
    search_query = Prompt.ask(
        "[yellow]What product are you looking for?[/yellow]",
        default="laptop"
    )
    
    # Show example sites
    console.print("\n[dim]Example sites you can search:[/dim]")
    examples = [
        "https://demo.vercel.store",
        "https://www.amazon.com",
        "https://www.ebay.com",
        "https://shopify-store.com"
    ]
    
    for i, example in enumerate(examples, 1):
        console.print(f"[dim]  {i}. {example}[/dim]")
    
    site_url = Prompt.ask(
        "\n[yellow]Which site do you want to search on?[/yellow]",
        default="https://demo.vercel.store"
    )
    
    max_products = IntPrompt.ask(
        "[yellow]How many products should I scrape?[/yellow]",
        default=5,
        show_default=True
    )
    
    if max_products < 1:
        max_products = 1
    elif max_products > 20:
        console.print("[yellow]⚠️ Limiting to 20 products for performance[/yellow]")
        max_products = 20
    
    return {
        "search_query": search_query,
        "site_url": site_url,
        "max_products": max_products
    }

def get_multiple_urls():
    """Get multiple URLs for batch scraping."""
    console.print("\n[bold green]📋 Multiple Product URLs[/bold green]")
    
    urls = []
    console.print("[yellow]Enter product URLs (press Enter with empty input to finish):[/yellow]")
    
    while True:
        prompt_text = f"[cyan]URL #{len(urls) + 1}[/cyan]" if urls else "[cyan]First URL[/cyan]"
        default_url = "" if urls else "https://demo.vercel.store/products/acme-mug"
        
        url = Prompt.ask(prompt_text, default=default_url)
        
        if not url:
            break
            
        if not url.startswith(('http://', 'https://')):
            console.print("[red]❌ Please provide a valid URL starting with http:// or https://[/red]")
            continue
            
        urls.append(url)
        console.print(f"[green]✅ Added: {url}[/green]")
        
        if len(urls) >= 10:
            if not Confirm.ask("[yellow]You've added 10 URLs. Add more?[/yellow]"):
                break
    
    return {"urls": urls} if urls else None

def execute_scraping(mode: str, details: dict):
    """Execute the scraping based on mode and details."""
    try:
        if mode == "1":  # Single product
            console.print(f"\n[blue]🚀 Scraping product: {details['url']}[/blue]")
            from ecommerce_scraper import EcommerceScraper

            with EcommerceScraper(verbose=True) as scraper:
                result = scraper.scrape_product(details['url'])

            # Save and display results
            filename = "single_product_result.json"
            with open(filename, "w") as f:
                json.dump(result, f, indent=2)

            if result.get("success"):
                console.print("[green]✅ Product scraping completed![/green]")
                console.print(f"📁 Results saved to: {filename}")
            else:
                console.print(f"[red]❌ Scraping failed: {result.get('error')}[/red]")

        elif mode == "2":  # Search and scrape
            console.print(f"\n[blue]🚀 Searching for '{details['search_query']}' on {details['site_url']}[/blue]")
            from ecommerce_scraper import EcommerceScraper

            with EcommerceScraper(verbose=True) as scraper:
                result = scraper.search_and_scrape(
                    details['search_query'],
                    details['site_url'],
                    details['max_products']
                )

            # Save and display results
            filename = "search_and_scrape_result.json"
            with open(filename, "w") as f:
                json.dump(result, f, indent=2)

            if result.get("success"):
                console.print("[green]✅ Search and scrape completed![/green]")
                console.print(f"📁 Results saved to: {filename}")
            else:
                console.print(f"[red]❌ Search failed: {result.get('error')}[/red]")

        elif mode == "3":  # Multiple URLs
            console.print(f"\n[blue]🚀 Scraping {len(details['urls'])} products[/blue]")
            from ecommerce_scraper import EcommerceScraper

            with EcommerceScraper(verbose=True) as scraper:
                results = scraper.scrape_products(details['urls'])

            # Save and display results
            filename = "multiple_products_result.json"
            with open(filename, "w") as f:
                json.dump(results, f, indent=2)

            successful = sum(1 for r in results if r.get("success"))
            console.print(f"[green]✅ Completed: {successful}/{len(details['urls'])} products![/green]")
            console.print(f"📁 Results saved to: {filename}")

        elif mode == "4":  # Test system
            console.print("\n[blue]🧪 Running system tests[/blue]")
            from run_scraper import run_test
            run_test()

    except ImportError as e:
        console.print(f"[red]❌ Import error: {e}[/red]")
        console.print("[yellow]Make sure all dependencies are installed: pip install -r requirements.txt[/yellow]")
        console.print("[yellow]Also ensure the ecommerce_scraper package is in your Python path[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error during scraping: {e}[/red]")
        import traceback
        console.print(f"[dim]Full error: {traceback.format_exc()}[/dim]")

def main():
    """Main interactive function."""
    try:
        # Show welcome
        show_welcome()
        
        # Check environment
        if not check_environment():
            return
        
        console.print("[green]✅ Environment check passed![/green]")
        
        while True:
            # Get scraping mode
            mode = get_scraping_mode()
            
            # Get details based on mode
            details = None
            if mode == "1":
                details = get_single_product_details()
            elif mode == "2":
                details = get_search_details()
            elif mode == "3":
                details = get_multiple_urls()
            elif mode == "4":
                details = {}  # No additional details needed for test
            
            if details is None and mode != "4":
                console.print("[red]❌ Invalid input. Please try again.[/red]")
                continue
            
            # Execute scraping
            execute_scraping(mode, details)
            
            # Ask if user wants to continue
            if not Confirm.ask("\n[bold yellow]Would you like to perform another operation?[/bold yellow]"):
                break
        
        console.print("\n[bold green]🎉 Thank you for using the Interactive Ecommerce Scraper![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⏹️ Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")

if __name__ == "__main__":
    main()
