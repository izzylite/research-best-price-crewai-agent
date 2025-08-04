#!/usr/bin/env python3
"""
Script to manage CrewAI memory for the ecommerce scraper.
"""

import sys
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.utils.crewai_setup import (
    clear_crewai_memory, 
    list_crewai_memory_projects
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

console = Console()

def show_memory_status():
    """Show current CrewAI memory status."""
    projects = list_crewai_memory_projects()
    
    if not projects:
        console.print("[green]✅ No CrewAI memory found[/green]")
        return
    
    console.print(f"[yellow]📁 Found CrewAI memory for {len(projects)} project(s):[/yellow]")
    
    table = Table(title="CrewAI Memory Projects")
    table.add_column("Project Name", style="cyan")
    table.add_column("Memory Path", style="dim")
    
    base_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "CrewAI"
    
    for project in projects:
        project_path = base_dir / project
        table.add_row(project, str(project_path))
    
    console.print(table)

def clear_all_memory():
    """Clear all CrewAI memory."""
    if Confirm.ask("⚠️  Are you sure you want to clear ALL CrewAI memory?"):
        clear_crewai_memory()
        console.print("[green]✅ All CrewAI memory cleared[/green]")
    else:
        console.print("[yellow]❌ Operation cancelled[/yellow]")

def clear_project_memory():
    """Clear memory for a specific project."""
    projects = list_crewai_memory_projects()
    
    if not projects:
        console.print("[green]✅ No CrewAI memory found[/green]")
        return
    
    console.print("[yellow]Available projects:[/yellow]")
    for i, project in enumerate(projects, 1):
        console.print(f"  {i}. {project}")
    
    try:
        choice = int(input("\nEnter project number to clear (0 to cancel): "))
        if choice == 0:
            console.print("[yellow]❌ Operation cancelled[/yellow]")
            return
        
        if 1 <= choice <= len(projects):
            project = projects[choice - 1]
            if Confirm.ask(f"⚠️  Clear memory for project '{project}'?"):
                clear_crewai_memory(project)
                console.print(f"[green]✅ Memory cleared for project: {project}[/green]")
            else:
                console.print("[yellow]❌ Operation cancelled[/yellow]")
        else:
            console.print("[red]❌ Invalid choice[/red]")
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]❌ Operation cancelled[/yellow]")

def main():
    """Main function."""
    console.print(Panel(
        """[bold blue]CrewAI Memory Manager[/bold blue]

This tool helps you manage CrewAI memory for the ecommerce scraper.

[yellow]Commands:[/yellow]
  status  - Show current memory status
  clear   - Clear all memory
  project - Clear memory for specific project
  help    - Show this help message
""",
        title="Memory Manager",
        border_style="blue"
    ))
    
    if len(sys.argv) < 2:
        console.print("[red]❌ Please specify a command[/red]")
        console.print("Usage: python clear_memory.py [status|clear|project|help]")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        show_memory_status()
    elif command == "clear":
        clear_all_memory()
    elif command == "project":
        clear_project_memory()
    elif command == "help":
        console.print("Available commands:")
        console.print("  status  - Show current memory status")
        console.print("  clear   - Clear all CrewAI memory")
        console.print("  project - Clear memory for specific project")
        console.print("  help    - Show this help message")
    else:
        console.print(f"[red]❌ Unknown command: {command}[/red]")
        console.print("Use 'help' to see available commands")

if __name__ == "__main__":
    main()
