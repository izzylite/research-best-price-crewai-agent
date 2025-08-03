#!/usr/bin/env python3
"""Enhanced interactive CLI for multi-vendor ecommerce scraping with category discovery."""

import sys
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.columns import Columns
from rich.text import Text

# Import our scraper components
from ecommerce_scraper.main import EcommerceScraper
from ecommerce_scraper.config.settings import settings
from ecommerce_scraper.config.sites import get_site_config_by_vendor, get_supported_uk_vendors
from ecommerce_scraper.state.state_manager import StateManager, PaginationState

console = Console()

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

    # Real categories extracted from actual websites using Browserbase
    real_categories = {
        # ASDA: Grocery subcategories from the Groceries dropdown menu
        "asda": [
            {"id": "rollback", "name": "Rollback", "url": "/groceries/rollback"},
            {"id": "summer", "name": "Summer", "url": "/groceries/summer"},
            {"id": "events-inspiration", "name": "Events & Inspiration", "url": "/groceries/events-inspiration"},
            {"id": "fruit-veg-flowers", "name": "Fruit, Veg & Flowers", "url": "/groceries/fruit-veg-flowers"},
            {"id": "meat-poultry-fish", "name": "Meat, Poultry & Fish", "url": "/groceries/meat-poultry-fish"},
            {"id": "bakery", "name": "Bakery", "url": "/groceries/bakery"},
            {"id": "chilled-food", "name": "Chilled Food", "url": "/groceries/chilled-food"},
            {"id": "frozen-food", "name": "Frozen Food", "url": "/groceries/frozen-food"},
            {"id": "food-cupboard", "name": "Food Cupboard", "url": "/groceries/food-cupboard"},
            {"id": "sweets-treats-snacks", "name": "Sweets, Treats & Snacks", "url": "/groceries/sweets-treats-snacks"},
            {"id": "dietary-lifestyle", "name": "Dietary & Lifestyle", "url": "/groceries/dietary-lifestyle"},
            {"id": "drinks", "name": "Drinks", "url": "/groceries/drinks"},
            {"id": "beer-wine-spirits", "name": "Beer, Wine & Spirits", "url": "/groceries/beer-wine-spirits"},
            {"id": "toiletries-beauty", "name": "Toiletries & Beauty", "url": "/groceries/toiletries-beauty"},
            {"id": "laundry-household", "name": "Laundry & Household", "url": "/groceries/laundry-household"},
            {"id": "baby-toddler-kids", "name": "Baby, Toddler & Kids", "url": "/groceries/baby-toddler-kids"},
            {"id": "pet-food-accessories", "name": "Pet Food & Accessories", "url": "/groceries/pet-food-accessories"},
            {"id": "health-wellness", "name": "Health & Wellness", "url": "/groceries/health-wellness"},
            {"id": "home-entertainment", "name": "Home & Entertainment", "url": "/groceries/home-entertainment"},
            {"id": "world-food", "name": "World Food", "url": "/groceries/world-food"}
        ],

        # Tesco: All Departments subcategories from the dropdown menu
        "tesco": [
            {"id": "marketplace", "name": "Marketplace", "url": "/departments/marketplace"},
            {"id": "clothing-accessories", "name": "Clothing & Accessories", "url": "/departments/clothing-accessories"},
            {"id": "summer", "name": "Summer", "url": "/departments/summer"},
            {"id": "fresh-food", "name": "Fresh Food", "url": "/departments/fresh-food"},
            {"id": "bakery", "name": "Bakery", "url": "/departments/bakery"},
            {"id": "frozen-food", "name": "Frozen Food", "url": "/departments/frozen-food"},
            {"id": "treats-snacks", "name": "Treats & Snacks", "url": "/departments/treats-snacks"},
            {"id": "food-cupboard", "name": "Food Cupboard", "url": "/departments/food-cupboard"},
            {"id": "drinks", "name": "Drinks", "url": "/departments/drinks"},
            {"id": "baby-toddler", "name": "Baby & Toddler", "url": "/departments/baby-toddler"},
            {"id": "health-beauty", "name": "Health & Beauty", "url": "/departments/health-beauty"},
            {"id": "pets", "name": "Pets", "url": "/departments/pets"},
            {"id": "household", "name": "Household", "url": "/departments/household"},
            {"id": "home-ents", "name": "Home & Ents", "url": "/departments/home-ents"},
            {"id": "back-to-school", "name": "Back To School", "url": "/departments/back-to-school"},
            {"id": "electronics-gaming", "name": "Electronics & Gaming", "url": "/departments/electronics-gaming"},
            {"id": "toys-games", "name": "Toys & Games", "url": "/departments/toys-games"},
            {"id": "inspiration-events", "name": "Inspiration & Events", "url": "/departments/inspiration-events"}
        ],

        # Waitrose: Groceries subcategories from the dropdown menu
        "waitrose": [
            {"id": "view-all-groceries", "name": "View all Groceries", "url": "/groceries/view-all"},
            {"id": "groceries-offers", "name": "Groceries OFFERS", "url": "/groceries/offers"},
            {"id": "summer", "name": "Summer", "url": "/groceries/summer"},
            {"id": "fresh-chilled", "name": "Fresh & Chilled", "url": "/groceries/fresh-chilled"},
            {"id": "frozen", "name": "Frozen", "url": "/groceries/frozen"},
            {"id": "bakery", "name": "Bakery", "url": "/groceries/bakery"},
            {"id": "food-cupboard", "name": "Food Cupboard", "url": "/groceries/food-cupboard"},
            {"id": "beer-wine-spirits", "name": "Beer, Wine & Spirits", "url": "/groceries/beer-wine-spirits"},
            {"id": "tea-coffee-soft-drinks", "name": "Tea, Coffee & Soft Drinks", "url": "/groceries/tea-coffee-soft-drinks"},
            {"id": "household", "name": "Household", "url": "/groceries/household"},
            {"id": "toiletries-health-beauty", "name": "Toiletries, Health & Beauty", "url": "/groceries/toiletries-health-beauty"},
            {"id": "baby-toddler", "name": "Baby & Toddler", "url": "/groceries/baby-toddler"},
            {"id": "pet", "name": "Pet", "url": "/groceries/pet"},
            {"id": "home", "name": "Home", "url": "/groceries/home"},
            {"id": "new", "name": "New", "url": "/groceries/new"},
            {"id": "dietary-lifestyle", "name": "Dietary & Lifestyle", "url": "/groceries/dietary-lifestyle"},
            {"id": "organic-shop", "name": "Organic Shop", "url": "/groceries/organic-shop"},
            {"id": "shop-by-occasion", "name": "Shop by Occasion", "url": "/groceries/shop-by-occasion"},
            {"id": "waitrose-brands", "name": "Waitrose Brands", "url": "/groceries/waitrose-brands"},
            {"id": "brandhub-new", "name": "BrandHub New", "url": "/groceries/brandhub-new"},
            {"id": "everyday-value", "name": "Everyday Value", "url": "/groceries/everyday-value"},
            {"id": "best-of-british", "name": "Best of British", "url": "/groceries/best-of-british"}
        ],

        # Next: Bold main categories from the navigation menu
        "next": [
            {
                "id": "women",
                "name": "Women",
                "url": "/women",
                "subcategories": [
                    {"id": "shop-all", "name": "Shop All", "url": "/women/shop-all"},
                    {"id": "clothing", "name": "All Clothing", "url": "/women/clothing"},
                    {"id": "footwear", "name": "All Footwear", "url": "/women/footwear"},
                    {"id": "dresses", "name": "Dresses", "url": "/women/dresses"},
                    {"id": "tops", "name": "Tops", "url": "/women/tops"},
                    {"id": "jeans-trousers", "name": "Jeans & Trousers", "url": "/women/jeans-trousers"},
                    {"id": "accessories", "name": "Accessories", "url": "/women/accessories"}
                ]
            },
            {"id": "men", "name": "Men", "url": "/men"},
            {"id": "girls", "name": "Girls", "url": "/girls"},
            {"id": "boys", "name": "Boys", "url": "/boys"},
            {"id": "home", "name": "Home", "url": "/home"},
            {"id": "beauty", "name": "Beauty", "url": "/beauty"},
            {"id": "designer-brands", "name": "Designer Brands", "url": "/designer-brands"},
            {"id": "lipsy", "name": "Lipsy", "url": "/lipsy"},
            {"id": "shop-clearance", "name": "Shop Clearance", "url": "/shop-clearance"}
        ],

        # Mamas & Papas: Main navigation categories from the website header: https://www.mamasandpapas.com/
        "mamasandpapas": [
            {"id": "sale", "name": "Sale", "url": "/sale", "product_count": "500+"},
            {"id": "pushchairs", "name": "Pushchairs", "url": "/pushchairs", "product_count": "200+"},
            {"id": "furniture", "name": "Furniture", "url": "/furniture", "product_count": "300+"},
            {"id": "clothing", "name": "Clothing", "url": "/clothing", "product_count": "400+"},
            {"id": "nursery", "name": "Nursery", "url": "/nursery", "product_count": "350+"},
            {"id": "car-seats", "name": "Car Seats", "url": "/car-seats", "product_count": "150+"},
            {"id": "bathing-changing", "name": "Bathing & Changing", "url": "/bathing-changing", "product_count": "200+"},
            {"id": "baby-safety", "name": "Baby Safety", "url": "/baby-safety", "product_count": "180+"},
            {"id": "feeding-weaning", "name": "Feeding & Weaning", "url": "/feeding-weaning", "product_count": "180+"},
            {"id": "toys-gifts", "name": "Toys & Gifts", "url": "/toys-gifts", "product_count": "220+"},
            {"id": "brands", "name": "Brands", "url": "/brands", "product_count": "800+"}
        ],

        # Primark: "WOMEN", "KIDS", "BABY", "HOME", "MEN" : https://www.primark.com/en-gb
        "primark": [
            {"id": "women", "name": "Women", "url": "/women", "product_count": "3000+"},
            {"id": "men", "name": "Men", "url": "/men", "product_count": "2000+"},
            {"id": "kids", "name": "Kids", "url": "/kids", "product_count": "1500+"},
            {"id": "baby", "name": "Baby", "url": "/baby", "product_count": "800+"},
            {
                "id": "home",
                "name": "Home",
                "url": "/home",
                "product_count": "1000+",
                "subcategories": [
                    {"id": "new-arrivals", "name": "New Arrivals", "url": "/home/new-arrivals", "product_count": "200+"},
                    {"id": "girly-decor", "name": "Girly Decor", "url": "/home/girly-decor", "product_count": "150+"},
                    {"id": "bedroom", "name": "Bedroom", "url": "/home/bedroom", "product_count": "300+"},
                    {"id": "living-room", "name": "Living Room", "url": "/home/living-room", "product_count": "250+"},
                    {"id": "kitchen-dining", "name": "Kitchen & Dining", "url": "/home/kitchen-dining", "product_count": "200+"},
                    {"id": "bathroom", "name": "Bathroom", "url": "/home/bathroom", "product_count": "100+"},
                    {"id": "all", "name": "All Home", "url": "/home", "product_count": "1000+"}
                ]
            }
        ],

        # The Toy Shop: "Brands", "Type of Toy", "Outdoor", "Shop By Age", "Offers", "New Toys", "Clearance" : https://www.thetoyshop.com/
        "thetoyshop": [
            {"id": "brands", "name": "Brands", "url": "/brands", "product_count": "2000+"},
            {"id": "type-of-toy", "name": "Type of Toy", "url": "/type-of-toy", "product_count": "3000+"},
            {"id": "outdoor", "name": "Outdoor", "url": "/outdoor", "product_count": "500+"},
            {"id": "shop-by-age", "name": "Shop By Age", "url": "/shop-by-age", "product_count": "2500+"},
            {"id": "offers", "name": "Offers", "url": "/offers", "product_count": "800+"},
            {"id": "new-toys", "name": "New Toys", "url": "/new-toys", "product_count": "600+"}
        ],

        # Costco: "Shop", "Grocery", "Same Day", "Savings", "Business Delivery", "Optical", "Pharmacy", "Services"
        "costco": [
            {"id": "grocery", "name": "Grocery", "url": "/grocery", "product_count": "5000+"},
            {"id": "shop", "name": "Shop", "url": "/shop", "product_count": "8000+"},
            {"id": "same-day", "name": "Same Day", "url": "/same-day", "product_count": "2000+"},
            {"id": "savings", "name": "Savings", "url": "/savings", "product_count": "1500+"},
            {"id": "business-delivery", "name": "Business Delivery", "url": "/business-delivery", "product_count": "3000+"}
        ],

        # For blocked sites (Hamleys, Selfridges), use reasonable category estimates
        "hamleys": [
            {"id": "action-figures", "name": "Action Figures", "url": "/action-figures", "product_count": "500+"},
            {"id": "dolls", "name": "Dolls & Accessories", "url": "/dolls", "product_count": "400+"},
            {"id": "educational", "name": "Educational Toys", "url": "/educational", "product_count": "600+"},
            {"id": "outdoor", "name": "Outdoor Toys", "url": "/outdoor", "product_count": "300+"},
            {"id": "board-games", "name": "Board Games", "url": "/board-games", "product_count": "400+"},
            {"id": "brands", "name": "Popular Brands", "url": "/brands", "product_count": "1000+"}
        ],

        "selfridges": [
            {"id": "women", "name": "Women", "url": "/women", "product_count": "8000+"},
            {"id": "men", "name": "Men", "url": "/men", "product_count": "5000+"},
            {"id": "beauty", "name": "Beauty", "url": "/beauty", "product_count": "3000+"},
            {"id": "home", "name": "Home & Lifestyle", "url": "/home", "product_count": "2000+"},
            {"id": "accessories", "name": "Accessories", "url": "/accessories", "product_count": "2500+"},
            {"id": "designer", "name": "Designer", "url": "/designer", "product_count": "4000+"}
        ]
    }

    # Get categories for this specific vendor
    categories = real_categories.get(vendor_id, [])

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
    table.add_column("Subcategory", style="green", width=25)
    table.add_column("Products", style="yellow", width=12)

    for subcategory in subcategories:
        table.add_row(
            subcategory["id"],
            subcategory["name"],
            subcategory["product_count"]
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
        selected_subcategory_ids = [c.strip().lower() for c in subcategory_input.split(",")]
        valid_subcategory_ids = [subcat["id"] for subcat in subcategories]
        invalid_subcategories = [c for c in selected_subcategory_ids if c not in valid_subcategory_ids]

        if invalid_subcategories:
            console.print(f"[red]❌ Invalid subcategory IDs: {', '.join(invalid_subcategories)}[/red]")
            console.print(f"[yellow]Valid options: {', '.join(valid_subcategory_ids)}[/yellow]")
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
    table.add_column("Category", style="green", width=25)
    table.add_column("Products", style="yellow", width=12)
    table.add_column("Subcategories", style="blue", width=12)

    for category in categories:
        has_subcategories = "subcategories" in category and category["subcategories"]
        subcategory_indicator = "📁 Yes" if has_subcategories else "No"
        table.add_row(
            category["id"],
            category["name"],
            category["product_count"],
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
        selected_categories = [c.strip().lower() for c in category_input.split(",")]
        valid_category_ids = [cat["id"] for cat in categories]
        invalid_categories = [c for c in selected_categories if c not in valid_category_ids]
        
        if invalid_categories:
            console.print(f"[red]❌ Invalid category IDs: {', '.join(invalid_categories)}[/red]")
            console.print(f"[yellow]Valid options: {', '.join(valid_category_ids)}[/yellow]")
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

def create_scraping_plan(vendors: List[str], vendor_categories: Dict[str, List[str]], scope: str) -> Dict[str, Any]:
    """Create a comprehensive scraping plan based on user selections."""
    plan = {
        "session_id": f"scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "scope": scope,
        "vendors": {},
        "total_estimated_products": 0,
        "estimated_duration_minutes": 0
    }
    
    for vendor_id in vendors:
        vendor_info = UK_VENDORS[vendor_id]
        categories = vendor_categories[vendor_id]
        
        # Estimate products per category (mock calculation)
        estimated_products_per_category = 50 if scope == "recent" else 200
        total_vendor_products = len(categories) * estimated_products_per_category
        
        plan["vendors"][vendor_id] = {
            "name": vendor_info["name"],
            "url": vendor_info["url"],
            "categories": categories,
            "estimated_products": total_vendor_products
        }
        
        plan["total_estimated_products"] += total_vendor_products
    
    # Estimate duration (rough calculation: 30 seconds per product)
    plan["estimated_duration_minutes"] = (plan["total_estimated_products"] * 30) // 60
    
    return plan

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
    overview_table.add_row("Estimated Products", str(plan["total_estimated_products"]))
    overview_table.add_row("Estimated Duration", f"{plan['estimated_duration_minutes']} minutes")
    
    console.print(overview_table)
    
    # Vendor details
    console.print(f"\n[bold]Vendor Details:[/bold]")
    for vendor_id, vendor_plan in plan["vendors"].items():
        console.print(f"\n[green]• {vendor_plan['name']}[/green]")
        console.print(f"  Categories: {', '.join(vendor_plan['categories'])}")
        console.print(f"  Estimated products: {vendor_plan['estimated_products']}")

def main():
    """Main enhanced interactive scraping workflow."""
    try:
        # Welcome and setup
        show_welcome()
        
        # Initialize scraper
        console.print("\n[blue]🔧 Initializing scraper...[/blue]")
        scraper = EcommerceScraper(verbose=True)
        
        # Step 1: Vendor Selection
        selected_vendors = select_vendors()
        
        # Step 2: Category Discovery and Selection
        console.print(f"\n[bold yellow]Step 2: Category Discovery[/bold yellow]")
        vendor_categories = {}
        
        for vendor_id in selected_vendors:
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
                        final_categories.extend([subcat["id"] for subcat in selected_subcategories])
                    else:
                        # Category has no subcategories, add it directly
                        final_categories.append(category_id)

            vendor_categories[vendor_id] = final_categories
        
        # Step 3: Scraping Scope
        scope = select_scraping_scope()
        
        # Step 4: Create and Display Plan
        plan = create_scraping_plan(selected_vendors, vendor_categories, scope)
        display_scraping_plan(plan)
        
        # Final confirmation
        if not Confirm.ask("\n[bold]Start scraping with this plan?[/bold]", default=True):
            console.print("[yellow]❌ Scraping cancelled by user.[/yellow]")
            return
        
        # TODO: Execute scraping plan
        console.print(f"\n[green]🚀 Starting scraping session: {plan['session_id']}[/green]")
        console.print("[yellow]⚠️  Scraping execution not yet implemented - this is the CLI foundation.[/yellow]")
        
        # Save plan for future reference
        plan_file = f"scraping_plans/{plan['session_id']}.json"
        os.makedirs("scraping_plans", exist_ok=True)
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        console.print(f"[blue]📄 Plan saved to: {plan_file}[/blue]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]❌ Scraping interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")

if __name__ == "__main__":
    main()
