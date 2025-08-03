#!/usr/bin/env python3
"""
Easy-to-use runner script for the ecommerce scraper.
This script provides simple commands to scrape products.
"""

import sys
import json
import os

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

# Import settings for enhanced configuration
from ecommerce_scraper.config.settings import settings

# Setup logging
settings.setup_logging()
import logging
logger = logging.getLogger(__name__)

# Set OpenAI API key directly from .env before any other imports
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key
    logger.info(f"✅ OpenAI API key loaded: {openai_key[:20]}...")
else:
    logger.error("❌ OpenAI API key not found in environment")
    print("❌ OpenAI API key not found in environment")

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

def show_help():
    """Show usage instructions."""
    console.print(Panel(
        """[bold blue]Ecommerce Scraper Usage[/bold blue]

[yellow]Interactive mode (recommended):[/yellow]
  python run_scraper.py interactive

[yellow]Test the system:[/yellow]
  python run_scraper.py test

[yellow]Scrape a single product:[/yellow]
  python run_scraper.py single <product_url>

[yellow]Scrape multiple products:[/yellow]
  python run_scraper.py multiple <url1> <url2> <url3>

[yellow]Search and scrape:[/yellow]
  python run_scraper.py search "<search_query>" <site_url>

[yellow]Examples:[/yellow]
  python run_scraper.py test
  python run_scraper.py single https://demo.vercel.store/products/acme-cup
  python run_scraper.py multiple https://demo.vercel.store/products/acme-cup https://demo.vercel.store/products/acme-mug
  python run_scraper.py search "cup" https://demo.vercel.store

[green]Note: Make sure your .env file is configured with API keys![/green]
        """,
        title="🛍️ Ecommerce Scraper",
        border_style="blue"
    ))

def run_test():
    """Run the test suite."""
    console.print("[bold blue]Running test suite...[/bold blue]")
    import subprocess
    result = subprocess.run([sys.executable, "test_ecommerce_simple.py"], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        console.print("[green]✅ Tests passed![/green]")
    else:
        console.print("[red]❌ Tests failed![/red]")
        console.print(result.stdout)
        console.print(result.stderr)

def scrape_single_product(product_url: str):
    """Scrape a single product using CrewAI agents."""
    console.print(f"[bold blue]Scraping single product:[/bold blue] {product_url}")

    try:
        # Import and use the actual EcommerceScraper
        from ecommerce_scraper import EcommerceScraper

        console.print("🤖 Initializing CrewAI agents...")

        # Use the real EcommerceScraper with CrewAI agents
        with EcommerceScraper(verbose=True) as scraper:
            result = scraper.scrape_product(product_url)

        # Save result
        filename = f"single_product_result.json"
        with open(filename, "w") as f:
            json.dump(result, f, indent=2)

        if result.get("success"):
            console.print("[green]✅ Product scraping completed successfully![/green]")
            console.print(f"📁 Results saved to: {filename}")

            # Show a preview of the extracted data
            if "data" in result and result["data"]:
                data = result["data"]
                console.print("\n[green]📊 Extracted Data Preview:[/green]")
                if isinstance(data, dict):
                    for key, value in list(data.items())[:5]:  # Show first 5 items
                        console.print(f"  {key}: {str(value)[:100]}...")
        else:
            console.print(f"[red]❌ Scraping failed: {result.get('error', 'Unknown error')}[/red]")

    except ImportError as e:
        console.print(f"[red]❌ Import error: {e}[/red]")
        console.print("[yellow]Make sure the ecommerce_scraper package is properly installed[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error during scraping: {e}[/red]")

def scrape_multiple_products(product_urls: list):
    """Scrape multiple products using CrewAI agents."""
    console.print(f"[bold blue]Scraping {len(product_urls)} products...[/bold blue]")

    try:
        # Import and use the actual EcommerceScraper
        from ecommerce_scraper import EcommerceScraper

        console.print("🤖 Initializing CrewAI agents...")

        # Use the real EcommerceScraper with CrewAI agents
        with EcommerceScraper(verbose=True) as scraper:
            results = scraper.scrape_products(product_urls)

        # Save results
        filename = "multiple_products_result.json"
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        # Show summary
        successful = sum(1 for r in results if r.get("success"))
        console.print(f"[green]✅ Completed: {successful}/{len(product_urls)} products scraped successfully![/green]")
        console.print(f"📁 Results saved to: {filename}")

        # Show preview of results
        if results:
            console.print("\n[green]📊 Results Summary:[/green]")
            for i, result in enumerate(results[:3], 1):  # Show first 3 results
                status = "✅" if result.get("success") else "❌"
                url = result.get("product_url", "Unknown URL")
                console.print(f"  {status} Product {i}: {url[:60]}...")

    except ImportError as e:
        console.print(f"[red]❌ Import error: {e}[/red]")
        console.print("[yellow]Make sure the ecommerce_scraper package is properly installed[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error during scraping: {e}[/red]")

def search_and_scrape(search_query: str, site_url: str):
    """Search for products and scrape them using CrewAI agents."""
    console.print(f"[bold blue]Searching for '{search_query}' on {site_url}[/bold blue]")

    try:
        # Import and use the actual EcommerceScraper
        from ecommerce_scraper import EcommerceScraper

        console.print("🤖 Initializing CrewAI agents...")

        # Use the real EcommerceScraper with CrewAI agents
        with EcommerceScraper(verbose=True) as scraper:
            result = scraper.search_and_scrape(search_query, site_url, max_products=5)

        # Save result
        filename = "search_and_scrape_result.json"
        with open(filename, "w") as f:
            json.dump(result, f, indent=2)

        if result.get("success"):
            console.print("[green]✅ Search and scrape completed successfully![/green]")
            console.print(f"📁 Results saved to: {filename}")

            # Show preview of found products
            if "data" in result and result["data"]:
                data = result["data"]
                console.print(f"\n[green]🔍 Found products for '{search_query}':[/green]")
                if isinstance(data, dict) and "products" in data:
                    products = data["products"]
                    for i, product in enumerate(products[:3], 1):  # Show first 3
                        title = product.get("title", "Unknown Product")
                        console.print(f"  {i}. {title[:60]}...")
        else:
            console.print(f"[red]❌ Search failed: {result.get('error', 'Unknown error')}[/red]")

    except ImportError as e:
        console.print(f"[red]❌ Import error: {e}[/red]")
        console.print("[yellow]Make sure the ecommerce_scraper package is properly installed[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error during search and scrape: {e}[/red]")

def interactive_mode():
    """Interactive mode that asks user for input."""
    console.print(Panel(
        """[bold blue]🤖 Interactive Ecommerce Scraper[/bold blue]

Welcome! I'll help you scrape ecommerce data.
Let me ask you a few questions to get started.""",
        title="🛍️ Scraper Assistant",
        border_style="blue"
    ))

    # Show available options
    table = Table(title="Available Scraping Options")
    table.add_column("Option", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("1", "Scrape a single product page")
    table.add_row("2", "Search and scrape multiple products")
    table.add_row("3", "Scrape multiple specific product URLs")
    table.add_row("4", "Test the system")

    console.print(table)

    # Get user choice
    choice = Prompt.ask(
        "\n[bold yellow]What would you like to do?[/bold yellow]",
        choices=["1", "2", "3", "4"],
        default="1"
    )

    if choice == "1":
        # Single product scraping
        console.print("\n[bold green]📦 Single Product Scraping[/bold green]")

        product_url = Prompt.ask(
            "[yellow]Enter the product URL you want to scrape[/yellow]",
            default="https://demo.vercel.store/products/acme-mug"
        )

        # Validate URL
        if not product_url.startswith(('http://', 'https://')):
            console.print("[red]❌ Please provide a valid URL starting with http:// or https://[/red]")
            return

        console.print(f"\n[blue]🚀 Starting to scrape: {product_url}[/blue]")
        scrape_single_product(product_url)

    elif choice == "2":
        # Search and scrape
        console.print("\n[bold green]🔍 Search and Scrape[/bold green]")

        search_query = Prompt.ask(
            "[yellow]What product are you looking for?[/yellow]",
            default="laptop"
        )

        site_url = Prompt.ask(
            "[yellow]Which site do you want to search on?[/yellow]",
            default="https://demo.vercel.store"
        )

        max_products = Prompt.ask(
            "[yellow]How many products should I scrape? (1-10)[/yellow]",
            default="5"
        )

        try:
            max_products = int(max_products)
            if max_products < 1 or max_products > 10:
                max_products = 5
        except ValueError:
            max_products = 5

        console.print(f"\n[blue]🚀 Searching for '{search_query}' on {site_url}[/blue]")
        console.print(f"[blue]📊 Will scrape up to {max_products} products[/blue]")
        search_and_scrape(search_query, site_url)

    elif choice == "3":
        # Multiple URLs
        console.print("\n[bold green]📋 Multiple Product URLs[/bold green]")

        urls = []
        console.print("[yellow]Enter product URLs (press Enter with empty input to finish):[/yellow]")

        while True:
            url = Prompt.ask(
                f"[cyan]URL #{len(urls) + 1}[/cyan]",
                default="" if urls else "https://demo.vercel.store/products/acme-mug"
            )

            if not url:
                break

            if not url.startswith(('http://', 'https://')):
                console.print("[red]❌ Please provide a valid URL starting with http:// or https://[/red]")
                continue

            urls.append(url)

            if len(urls) >= 5:
                if not Confirm.ask("[yellow]You've added 5 URLs. Add more?[/yellow]"):
                    break

        if urls:
            console.print(f"\n[blue]🚀 Starting to scrape {len(urls)} products[/blue]")
            scrape_multiple_products(urls)
        else:
            console.print("[red]❌ No valid URLs provided[/red]")

    elif choice == "4":
        # Test system
        console.print("\n[bold green]🧪 Testing System[/bold green]")
        console.print("[yellow]Running system tests...[/yellow]")
        run_test()

    # Ask if user wants to continue
    if Confirm.ask("\n[bold yellow]Would you like to perform another operation?[/bold yellow]"):
        interactive_mode()

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        # If no arguments provided, start interactive mode
        console.print("[bold blue]No command provided. Starting interactive mode...[/bold blue]")
        interactive_mode()
        return

    command = sys.argv[1].lower()

    if command == "help" or command == "-h" or command == "--help":
        show_help()

    elif command == "interactive" or command == "i":
        interactive_mode()

    elif command == "test":
        run_test()
    
    elif command == "single":
        if len(sys.argv) < 3:
            console.print("[red]❌ Error: Please provide a product URL[/red]")
            console.print("Usage: python run_scraper.py single <product_url>")
            return
        
        product_url = sys.argv[2]
        scrape_single_product(product_url)
    
    elif command == "multiple":
        if len(sys.argv) < 3:
            console.print("[red]❌ Error: Please provide at least one product URL[/red]")
            console.print("Usage: python run_scraper.py multiple <url1> <url2> ...")
            return
        
        product_urls = sys.argv[2:]
        scrape_multiple_products(product_urls)
    
    elif command == "search":
        if len(sys.argv) < 4:
            console.print("[red]❌ Error: Please provide search query and site URL[/red]")
            console.print('Usage: python run_scraper.py search "search query" <site_url>')
            return
        
        search_query = sys.argv[2]
        site_url = sys.argv[3]
        search_and_scrape(search_query, site_url)
    
    else:
        console.print(f"[red]❌ Unknown command: {command}[/red]")
        show_help()

if __name__ == "__main__":
    main()
