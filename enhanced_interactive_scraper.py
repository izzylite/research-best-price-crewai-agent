#!/usr/bin/env python3
"""Enhanced interactive CLI for multi-vendor ecommerce scraping with category discovery."""

import json
import os
import signal
import sys
import threading
import time
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is available for CrewAI
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import our scraper components
from ecommerce_scraper.config.sites import get_site_config_by_vendor, get_supported_uk_vendors

# Try to import keyboard library for ESC detection (optional)
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

console = Console()

# Global flag for graceful termination
_termination_requested = False
_scraper_instance = None

def signal_handler(signum, frame):
    """Handle Ctrl+C (SIGINT) gracefully."""
    global _termination_requested, _scraper_instance
    console.print("\n[STOP] [red]Termination requested (Ctrl+C detected)...[/red]")
    _termination_requested = True

    # Try to gracefully close the scraper if it exists
    if _scraper_instance:
        try:
            console.print("[CLOSING] [yellow]Attempting to close scraper gracefully...[/yellow]")
            _scraper_instance.close()
            console.print("[SUCCESS] [green]Scraper closed successfully[/green]")
        except Exception as e:
            console.print(f"[WARNING] [yellow]Error closing scraper: {e}[/yellow]")

    console.print("[EXIT] [blue]Exiting gracefully...[/blue]")
    sys.exit(0)

def esc_key_listener():
    """Listen for ESC key press in a separate thread."""
    global _termination_requested
    if not KEYBOARD_AVAILABLE:
        return

    try:
        while not _termination_requested:
            if keyboard.is_pressed('esc'):
                console.print("\n🛑 [red]ESC key detected - requesting termination...[/red]")
                _termination_requested = True
                break
            time.sleep(0.1)  # Small delay to prevent high CPU usage
    except Exception:
        # Silently handle any keyboard detection errors
        pass

def start_esc_listener():
    """Start ESC key listener in a daemon thread."""
    if KEYBOARD_AVAILABLE:
        listener_thread = threading.Thread(target=esc_key_listener, daemon=True)
        listener_thread.start()
        return listener_thread
    return None

def check_termination():
    """Check if termination was requested."""
    return _termination_requested

# UK Retail Vendor Configuration
UK_VENDORS = {
    "asda": {
        "name": "ASDA",
        "url": "https://www.asda.com/",
        "type": "groceries",
        "description": "UK supermarket chain - groceries and general merchandise"
    },
    "costco": {
        "name": "Costco UK", 
        "url": "https://www.costco.com/",
        "type": "wholesale",
        "description": "Wholesale retailer - bulk groceries and merchandise"
    },
    "waitrose": {
        "name": "Waitrose",
        "url": "https://www.waitrose.com/",
        "type": "groceries",
        "description": "Premium UK supermarket - high-quality groceries"
    },
    "tesco": {
        "name": "Tesco",
        "url": "https://www.tesco.com/groceries/en-GB",
        "type": "groceries", 
        "description": "UK's largest supermarket chain - groceries online"
    },
    "hamleys": {
        "name": "Hamleys",
        "url": "https://www.hamleys.com/",
        "type": "toys",
        "description": "World-famous toy store - toys and games"
    },
    "mamasandpapas": {
        "name": "Mamas & Papas",
        "url": "https://www.mamasandpapas.com/",
        "type": "baby",
        "description": "Baby and children's products specialist"
    },
    "selfridges": {
        "name": "Selfridges",
        "url": "https://www.selfridges.com/GB/en/",
        "type": "luxury",
        "description": "Luxury department store - fashion, beauty, lifestyle"
    },
    "next": {
        "name": "Next",
        "url": "https://www.next.co.uk/",
        "type": "fashion",
        "description": "Fashion and home retailer - clothing and homeware"
    },
    "primark": {
        "name": "Primark",
        "url": "https://www.primark.com/en-gb",
        "type": "fashion",
        "description": "Fast fashion retailer - affordable clothing"
    },
    "thetoyshop": {
        "name": "The Toy Shop",
        "url": "https://www.thetoyshop.com/",
        "type": "toys",
        "description": "Specialist toy retailer - toys and games"
    }
}

SCRAPING_SCOPES = {
    "recent": {
        "name": "Recent products only",
        "description": "First 2-3 pages per category (faster, good for testing)",
        "max_pages": 3
    },
    "all": {
        "name": "All products", 
        "description": "Complete category scraping with pagination (comprehensive)",
        "max_pages": None
    }
}

def show_welcome():
    """Display welcome message and system overview."""
    console.print(Panel(
        """[bold blue]🛍️ Enhanced Multi-Vendor Ecommerce Scraper[/bold blue]

Welcome to the comprehensive UK retail scraping system!

This tool will help you:
• Select from 10 major UK retail websites
• Discover available product categories dynamically
• Choose scraping scope (recent vs complete)
• Track progress with resume functionality
• Export standardized JSON data

[green]🔍 AI Activity Logging: All agent thoughts and tool calls will be logged for debugging[/green]
[cyan]📁 View logs with: python view_logs.py[/cyan]

[yellow]⚠️  Please ensure you have valid API keys configured in your .env file[/yellow]""",
        title="🤖 Scraper Assistant v2.0",
        border_style="blue"
    ))

def display_vendor_table():
    """Display available vendors in a formatted table."""
    table = Table(title="Available UK Retail Vendors", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True, width=12)
    table.add_column("Vendor", style="green", width=20)
    table.add_column("Type", style="yellow", width=12)
    table.add_column("Description", style="white")

    for vendor_id, vendor_info in UK_VENDORS.items():
        table.add_row(
            vendor_id,
            vendor_info["name"],
            vendor_info["type"].title(),
            vendor_info["description"]
        )
    
    console.print(table)

def select_vendors() -> List[str]:
    """Allow user to select multiple vendors for scraping."""
    console.print("\n[bold yellow]Step 1: Vendor Selection[/bold yellow]")
    display_vendor_table()
    
    console.print("\n[cyan]You can select multiple vendors by entering their IDs separated by commas.[/cyan]")
    console.print("[cyan]Example: asda,tesco,next[/cyan]")
    
    while True:
        vendor_input = Prompt.ask(
            "\n[bold]Enter vendor IDs to scrape from[/bold]",
            default="asda,tesco"
        )
        
        # Parse and validate vendor selection
        selected_vendors = [v.strip().lower() for v in vendor_input.split(",")]
        invalid_vendors = [v for v in selected_vendors if v not in UK_VENDORS]
        
        if invalid_vendors:
            console.print(f"[red]❌ Invalid vendor IDs: {', '.join(invalid_vendors)}[/red]")
            console.print(f"[yellow]Valid options: {', '.join(UK_VENDORS.keys())}[/yellow]")
            continue
            
        # Confirm selection
        console.print(f"\n[green]✅ Selected vendors:[/green]")
        for vendor_id in selected_vendors:
            vendor_info = UK_VENDORS[vendor_id]
            console.print(f"  • {vendor_info['name']} ({vendor_info['type']})")
            
        if Confirm.ask("\nProceed with these vendors?", default=True):
            return selected_vendors

def discover_categories_for_vendor(vendor_id: str) -> List[Dict[str, Any]]:
    """Get real categories for a specific vendor extracted from their websites."""
    vendor_info = UK_VENDORS[vendor_id]
    console.print(f"\n[blue]🔍 Loading categories for {vendor_info['name']}...[/blue]")

    # Load categories from vendor-specific JSON file
    categories_file = Path(__file__).parent / "categories" / f"{vendor_id}.json"

    try:
        with open(categories_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]❌ Categories file not found: {categories_file}[/red]")
        return []
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Error parsing categories file: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]❌ Error loading categories: {e}[/red]")
        return []

    if not categories:
        console.print(f"[yellow]⚠️ No categories found for {vendor_info['name']}[/yellow]")
        return []

    console.print(f"[green]✅ Loaded {len(categories)} real categories for {vendor_info['name']}[/green]")
    return categories

def select_subcategories(category: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Allow user to select subcategories for a category that has them."""
    subcategories = category.get('subcategories', [])

    if not subcategories:
        return [category]  # Return the main category if no subcategories

    console.print(f"\n[bold blue]📂 Select subcategories for {category['name']}[/bold blue]")

    # Display subcategories table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True, width=15)
    table.add_column("Subcategory", style="green", width=30)

    for subcategory in subcategories:
        table.add_row(
            str(subcategory["id"]),
            subcategory["name"]
        )

    console.print(table)
    console.print("\n[cyan]Enter subcategory IDs separated by commas, or 'all' for all subcategories.[/cyan]")

    while True:
        subcategory_input = Prompt.ask(
            f"\n[bold]Select subcategories for {category['name']}[/bold]",
            default="all"
        )

        if subcategory_input.lower() == "all":
            return subcategories

        # Parse and validate subcategory selection
        try:
            selected_subcategory_ids = [int(c.strip()) for c in subcategory_input.split(",")]
        except ValueError:
            console.print(f"[red]❌ Invalid input. Please enter numeric IDs separated by commas.[/red]")
            continue

        valid_subcategory_ids = [subcat["id"] for subcat in subcategories]
        invalid_subcategories = [c for c in selected_subcategory_ids if c not in valid_subcategory_ids]

        if invalid_subcategories:
            console.print(f"[red]❌ Invalid subcategory IDs: {', '.join(map(str, invalid_subcategories))}[/red]")
            console.print(f"[yellow]Valid options: {', '.join(map(str, valid_subcategory_ids))}[/yellow]")
            continue

        # Get selected subcategories
        selected_subcategories = [subcat for subcat in subcategories if subcat["id"] in selected_subcategory_ids]
        selected_names = [subcat["name"] for subcat in selected_subcategories]
        console.print(f"\n[green]✅ Selected subcategories: {', '.join(selected_names)}[/green]")

        if Confirm.ask("Proceed with these subcategories?", default=True):
            return selected_subcategories


def select_categories_for_vendor(vendor_id: str, categories: List[Dict[str, Any]]) -> List[str]:
    """Allow user to select categories for a specific vendor."""
    vendor_info = UK_VENDORS[vendor_id]
    console.print(f"\n[bold yellow]Select categories for {vendor_info['name']}:[/bold yellow]")
    
    # Display categories table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True, width=15)
    table.add_column("Category", style="green", width=30)
    table.add_column("Subcategories", style="blue", width=12)

    for category in categories:
        has_subcategories = "subcategories" in category and category["subcategories"]
        subcategory_indicator = "📁 Yes" if has_subcategories else "No"
        table.add_row(
            str(category["id"]),
            category["name"],
            subcategory_indicator
        )
    
    console.print(table)
    
    console.print("\n[cyan]Enter category IDs separated by commas, or 'all' for all categories.[/cyan]")
    
    while True:
        category_input = Prompt.ask(
            f"\n[bold]Select categories for {vendor_info['name']}[/bold]",
            default="all"
        )
        
        if category_input.lower() == "all":
            return [cat["id"] for cat in categories]
        
        # Parse and validate category selection
        try:
            selected_categories = [int(c.strip()) for c in category_input.split(",")]
        except ValueError:
            console.print(f"[red]❌ Invalid input. Please enter numeric IDs separated by commas.[/red]")
            continue

        valid_category_ids = [cat["id"] for cat in categories]
        invalid_categories = [c for c in selected_categories if c not in valid_category_ids]
        
        if invalid_categories:
            console.print(f"[red]❌ Invalid category IDs: {', '.join(map(str, invalid_categories))}[/red]")
            console.print(f"[yellow]Valid options: {', '.join(map(str, valid_category_ids))}[/yellow]")
            continue
            
        # Confirm selection
        selected_names = [cat["name"] for cat in categories if cat["id"] in selected_categories]
        console.print(f"\n[green]✅ Selected categories: {', '.join(selected_names)}[/green]")
        
        if Confirm.ask("Proceed with these categories?", default=True):
            return selected_categories

def select_scraping_scope() -> str:
    """Allow user to select scraping scope (recent vs all products)."""
    console.print(f"\n[bold yellow]Step 3: Scraping Scope Selection[/bold yellow]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", no_wrap=True, width=10)
    table.add_column("Scope", style="green", width=20)
    table.add_column("Description", style="white")
    
    for scope_id, scope_info in SCRAPING_SCOPES.items():
        table.add_row(
            scope_id,
            scope_info["name"],
            scope_info["description"]
        )
    
    console.print(table)
    
    scope = Prompt.ask(
        "\n[bold]Select scraping scope[/bold]",
        choices=list(SCRAPING_SCOPES.keys()),
        default="recent"
    )
    
    scope_info = SCRAPING_SCOPES[scope]
    console.print(f"\n[green]✅ Selected scope: {scope_info['name']}[/green]")
    console.print(f"[blue]📄 {scope_info['description']}[/blue]")
    
    return scope

def create_scraping_plan(vendors: List[str], vendor_categories: Dict[str, List[Dict]], scope: str) -> Dict[str, Any]:
    """Create a comprehensive scraping plan based on user selections."""
    plan = {
        "session_id": f"scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "scope": scope,
        "vendors": {},
        "total_estimated_products": 0,
        "estimated_duration_minutes": 0,
        "total_urls": 0
    }

    # Extract URLs to get accurate counts
    scraping_urls = extract_urls_from_selections(vendors, vendor_categories)

    # Group URLs by vendor for planning
    vendor_url_counts = {}
    for url_info in scraping_urls:
        vendor_id = url_info["vendor"]
        if vendor_id not in vendor_url_counts:
            vendor_url_counts[vendor_id] = 0
        vendor_url_counts[vendor_id] += 1

    for vendor_id in vendors:
        vendor_info = UK_VENDORS[vendor_id]
        categories = vendor_categories[vendor_id]
        url_count = vendor_url_counts.get(vendor_id, 0)

        # Estimate products per URL (more realistic)
        estimated_products_per_url = 25 if scope == "recent" else 100
        total_vendor_products = url_count * estimated_products_per_url

        plan["vendors"][vendor_id] = {
            "name": vendor_info["name"],
            "url": vendor_info["url"],
            "categories": [cat["name"] for cat in categories],
            "url_count": url_count,
            "estimated_products": total_vendor_products
        }

        plan["total_estimated_products"] += total_vendor_products
        plan["total_urls"] += url_count

    # Estimate duration (rough calculation: 2 minutes per URL)
    plan["estimated_duration_minutes"] = plan["total_urls"] * 2

    return plan

def extract_urls_from_selections(vendors: List[str], vendor_categories: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
    """Extract URLs from user selections for direct scraping."""
    scraping_urls = []

    for vendor_id in vendors:
        vendor_info = UK_VENDORS[vendor_id]
        selected_categories = vendor_categories[vendor_id]

        # Extract URLs for selected categories (now with full context)
        for category_info in selected_categories:
            if category_info["type"] == "category":
                # Main category
                scraping_urls.append({
                    "vendor": vendor_id,
                    "vendor_name": vendor_info["name"],
                    "category_id": category_info["id"],
                    "category_name": category_info["name"],
                    "url": category_info["url"],
                    "type": "category"
                })
            else:
                # Subcategory
                scraping_urls.append({
                    "vendor": vendor_id,
                    "vendor_name": vendor_info["name"],
                    "category_id": category_info["id"],
                    "category_name": f"{category_info['parent_category_name']} > {category_info['name']}",
                    "url": category_info["url"],
                    "type": "subcategory",
                    "parent_category": category_info["parent_category_name"]
                })

    return scraping_urls

def display_scraping_plan(plan: Dict[str, Any]):
    """Display the final scraping plan for user confirmation."""
    console.print(f"\n[bold yellow]📋 Scraping Plan Summary[/bold yellow]")

    # Plan overview
    overview_table = Table(show_header=False, box=None)
    overview_table.add_column("Field", style="cyan", width=25)
    overview_table.add_column("Value", style="white")

    overview_table.add_row("Session ID", plan["session_id"])
    overview_table.add_row("Scope", SCRAPING_SCOPES[plan["scope"]]["name"])
    overview_table.add_row("Total Vendors", str(len(plan["vendors"])))
    overview_table.add_row("Total URLs", str(plan.get("total_urls", 0)))
    overview_table.add_row("Estimated Products", str(plan["total_estimated_products"]))
    overview_table.add_row("Estimated Duration", f"{plan['estimated_duration_minutes']} minutes")

    console.print(overview_table)

    # Vendor details
    console.print(f"\n[bold]Vendor Details:[/bold]")
    for vendor_id, vendor_plan in plan["vendors"].items():
        console.print(f"\n[green]• {vendor_plan['name']}[/green]")
        console.print(f"  Categories: {', '.join(map(str, vendor_plan['categories']))}")
        console.print(f"  URLs to scrape: {vendor_plan.get('url_count', 0)}")
        console.print(f"  Estimated products: {vendor_plan['estimated_products']}")

def execute_scraping_plan(plan: Dict[str, Any], scraping_urls: List[Dict[str, Any]], scope: str):
    """Execute the scraping plan using CrewAI's dynamic multi-agent orchestration."""
    global _scraper_instance

    # Check for termination before starting
    if check_termination():
        console.print("[yellow]🛑 Termination requested before starting scraping plan[/yellow]")
        return

    console.print(f"\n[bold blue]🤖 Initializing dynamic multi-agent scraping...[/bold blue]")
    console.print(f"[cyan]📋 Session ID: {plan['session_id']}[/cyan]")
    console.print(f"[cyan]🎯 Scope: {SCRAPING_SCOPES[scope]['name']}[/cyan]")
    console.print(f"[cyan]📄 Max pages per category: {SCRAPING_SCOPES[scope]['max_pages'] or 'All'}[/cyan]")

    # Use CrewAI's enhanced multi-agent orchestration from main.py
    from ecommerce_scraper.main import EcommerceScraper

    # Prepare categories for dynamic agent scraping with scope configuration
    console.print(f"[blue]📋 Preparing {len(scraping_urls)} categories for dynamic agent scraping...[/blue]")

    # Group URLs by vendor for better organization
    vendor_categories = {}
    for url_info in scraping_urls:
        vendor = url_info["vendor"]
        if vendor not in vendor_categories:
            vendor_categories[vendor] = []
        vendor_categories[vendor].append({
            "url": url_info["url"],
            "category_name": url_info["category_name"]
        })

    # Configure enhanced scraper with scope settings
    max_pages = SCRAPING_SCOPES[scope]['max_pages']

    console.print(f"[blue]🤖 Using CrewAI enhanced multi-agent orchestration[/blue]")
    console.print(f"[blue]📄 Pages per category: {max_pages or 'All available'}[/blue]")

    # Start dynamic scraping
    console.print(f"\n[bold green]🚀 Starting dynamic multi-agent scraping...[/bold green]")

    all_results = []
    total_products = 0
    successful_categories = 0
    failed_categories = 0

    # Use context manager for proper resource cleanup
    try:
        with EcommerceScraper(verbose=True) as ecommerce_scraper:
            _scraper_instance = ecommerce_scraper  # Store reference for signal handler

            # Process each vendor's categories
            for vendor, categories in vendor_categories.items():
                # Check for termination before processing each vendor
                if check_termination():
                    console.print(f"[yellow]🛑 Termination requested while processing {vendor}[/yellow]")
                    break

                console.print(f"\n[cyan]🏪 Processing {vendor.upper()} ({len(categories)} categories)[/cyan]")

                for category in categories:
                    # Check for termination before processing each category
                    if check_termination():
                        console.print(f"[yellow]🛑 Termination requested while processing {category['category_name']}[/yellow]")
                        break

                    console.print(f"[blue]📂 Scraping: {category['category_name']}[/blue]")

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console
                    ) as progress:
                        task = progress.add_task(
                            f"Scraping {vendor}/{category['category_name']}...",
                            total=None
                        )

                        # Execute enhanced scraping for this category URL
                        result = ecommerce_scraper.scrape_category(
                            category_url=category["url"],
                            vendor=vendor,
                            category_name=category["category_name"],
                            max_pages=max_pages
                        )

                        progress.update(task, completed=1, total=1)

                    # Check for termination after scraping
                    if check_termination():
                        console.print(f"[yellow]🛑 Termination requested after scraping {category['category_name']}[/yellow]")
                        break

                    # Process result
                    all_results.append(result)

                    if result.success:
                        successful_categories += 1
                        category_products = len(result.products)
                        total_products += category_products

                        console.print(f"[green]✅ {vendor}/{category['category_name']}: {category_products} products[/green]")

                        # Show agent breakdown
                        if result.agent_results:
                            for agent_result in result.agent_results:
                                status = "✅" if agent_result['success'] else "❌"
                                console.print(f"[dim]   {status} Agent {agent_result['agent_id']}: {agent_result['subcategory']} ({agent_result['products_found']} products)[/dim]")
                    else:
                        failed_categories += 1
                        console.print(f"[red]❌ {vendor}/{category['category_name']}: {result.error}[/red]")

            # Display final results
            console.print(f"\n[bold green]🎉 Dynamic scraping completed![/bold green]")
            console.print(f"[cyan]📊 Final Results:[/cyan]")
            console.print(f"  • Total categories: {len(scraping_urls)}")
            console.print(f"  • Successful: {successful_categories}")
            console.print(f"  • Failed: {failed_categories}")
            console.print(f"  • Total products: {total_products}")
            console.print(f"  • Average products per category: {total_products/successful_categories if successful_categories > 0 else 0:.1f}")

            # Show vendor breakdown
            if len(vendor_categories) > 1:
                console.print(f"\n[cyan]🏪 Vendor Breakdown:[/cyan]")
                for vendor in vendor_categories:
                    vendor_results = [r for r in all_results if any(cat['url'] in str(r) for cat in vendor_categories[vendor])]
                    vendor_products = sum(len(r.products) for r in vendor_results if r.success)
                    console.print(f"  • {vendor.upper()}: {vendor_products} products")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Scraping interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Dynamic scraping error: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")

    console.print(f"\n[cyan]💾 Results processed by individual agents with detailed logging[/cyan]")

def main():
    """Main enhanced interactive scraping workflow."""
    global _scraper_instance

    try:
        # Welcome and setup
        show_welcome()

        # Check for termination before starting
        if check_termination():
            console.print("[yellow]🛑 Termination requested before starting[/yellow]")
            return

        # Step 1: Vendor Selection
        selected_vendors = select_vendors()

        # Check for termination after vendor selection
        if check_termination():
            console.print("[yellow]🛑 Termination requested during vendor selection[/yellow]")
            return

        # Step 2: Category Discovery and Selection
        console.print(f"\n[bold yellow]Step 2: Category Discovery[/bold yellow]")
        vendor_categories = {}

        for vendor_id in selected_vendors:
            # Check for termination in the loop
            if check_termination():
                console.print("[yellow]🛑 Termination requested during category discovery[/yellow]")
                return
            categories = discover_categories_for_vendor(vendor_id)
            selected_category_ids = select_categories_for_vendor(vendor_id, categories)

            # Process subcategories for selected categories
            final_categories = []
            for category_id in selected_category_ids:
                # Find the category object
                category = next((cat for cat in categories if cat["id"] == category_id), None)
                if category:
                    if "subcategories" in category and category["subcategories"]:
                        # Category has subcategories, let user select them
                        selected_subcategories = select_subcategories(category)
                        # Store subcategory info with parent context to avoid ID collisions
                        for subcat in selected_subcategories:
                            final_categories.append({
                                "id": subcat["id"],
                                "name": subcat["name"],
                                "url": subcat["url"],
                                "parent_category_id": category["id"],
                                "parent_category_name": category["name"],
                                "type": "subcategory"
                            })
                    else:
                        # Category has no subcategories, add it directly
                        final_categories.append({
                            "id": category_id,
                            "name": category["name"],
                            "url": category["url"],
                            "type": "category"
                        })

            vendor_categories[vendor_id] = final_categories
        
        # Check for termination before scope selection
        if check_termination():
            console.print("[yellow]🛑 Termination requested before scope selection[/yellow]")
            return

        # Step 3: Scraping Scope
        scope = select_scraping_scope()

        # Check for termination after scope selection
        if check_termination():
            console.print("[yellow]🛑 Termination requested after scope selection[/yellow]")
            return

        # Step 4: Create and Display Plan
        plan = create_scraping_plan(selected_vendors, vendor_categories, scope)
        display_scraping_plan(plan)

        # Check for termination before final confirmation
        if check_termination():
            console.print("[yellow]🛑 Termination requested before confirmation[/yellow]")
            return

        # Final confirmation
        if not Confirm.ask("\n[bold]Start scraping with this plan?[/bold]", default=True):
            console.print("[yellow]❌ Scraping cancelled by user.[/yellow]")
            return

        # Check for termination before starting scraping
        if check_termination():
            console.print("[yellow]🛑 Termination requested before starting scraping[/yellow]")
            return

        # Execute scraping plan
        console.print(f"\n[green]🚀 Starting scraping session: {plan['session_id']}[/green]")

        # Extract URLs from selections
        console.print("[blue]🔗 Extracting URLs from category selections...[/blue]")
        scraping_urls = extract_urls_from_selections(selected_vendors, vendor_categories)

        if not scraping_urls:
            console.print("[red]❌ No URLs found for scraping. Please check your selections.[/red]")
            return

        console.print(f"[green]✅ Found {len(scraping_urls)} URLs to scrape[/green]")

        # Execute the scraping
        execute_scraping_plan(plan, scraping_urls, scope)

        # Save plan for future reference
        plan_file = f"scraping_plans/{plan['session_id']}.json"
        os.makedirs("scraping_plans", exist_ok=True)
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        console.print(f"[blue]📄 Plan saved to: {plan_file}[/blue]")

    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Scraping interrupted by user (Ctrl+C).[/yellow]")
    except Exception as e:
        if check_termination():
            console.print("\n[yellow]🛑 Scraping terminated gracefully[/yellow]")
        else:
            console.print(f"\n[red]❌ Error: {e}[/red]")
    finally:
        # Clear the scraper instance reference
        _scraper_instance = None

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Start ESC key listener if available
    esc_thread = start_esc_listener()

    # Display startup message
    console.print("[bold blue]🚀 Enhanced Interactive Ecommerce Scraper[/bold blue]")
    if KEYBOARD_AVAILABLE:
        console.print("[dim]💡 Press Ctrl+C or ESC at any time to gracefully terminate[/dim]")
    else:
        console.print("[dim]💡 Press Ctrl+C at any time to gracefully terminate[/dim]")
        console.print("[dim]ℹ️ Install 'keyboard' package for ESC key support: pip install keyboard[/dim]")
    console.print()

    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Scraper interrupted by user[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT
