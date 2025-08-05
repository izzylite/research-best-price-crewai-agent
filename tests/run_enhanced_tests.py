"""Test runner for the enhanced architecture test suite."""

import sys
import subprocess
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table


def run_tests(test_type="all", verbose=False, coverage=False):
    """Run the enhanced architecture test suite."""
    console = Console()
    
    # Test configurations
    test_configs = {
        "unit": {
            "path": "tests/test_enhanced_architecture.py",
            "description": "Unit tests for individual components"
        },
        "integration": {
            "path": "tests/integration/",
            "description": "Integration tests for component interactions"
        },
        "e2e": {
            "path": "tests/e2e/",
            "description": "End-to-end tests for complete workflows"
        },
        "all": {
            "path": "tests/",
            "description": "All tests"
        }
    }
    
    if test_type not in test_configs:
        console.print(f"[red]Invalid test type: {test_type}[/red]")
        console.print(f"Available types: {', '.join(test_configs.keys())}")
        return False
    
    config = test_configs[test_type]
    
    console.print(f"[bold blue]🧪 Running {test_type} tests[/bold blue]")
    console.print(f"[cyan]{config['description']}[/cyan]")
    console.print(f"[cyan]Path: {config['path']}[/cyan]\n")
    
    # Build pytest command
    cmd = ["python", "-m", "pytest", config["path"]]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if coverage:
        cmd.extend([
            "--cov=ecommerce_scraper",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Add additional pytest options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "-W", "ignore::DeprecationWarning"
    ])
    
    try:
        # Run tests
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Display results
        if result.returncode == 0:
            console.print(f"[bold green]✅ {test_type.title()} tests passed![/bold green]")
        else:
            console.print(f"[bold red]❌ {test_type.title()} tests failed![/bold red]")
        
        # Show output
        if result.stdout:
            console.print("\n[bold]Test Output:[/bold]")
            console.print(result.stdout)
        
        if result.stderr:
            console.print("\n[bold red]Test Errors:[/bold red]")
            console.print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        console.print(f"[red]Failed to run tests: {str(e)}[/red]")
        return False


def display_test_summary():
    """Display a summary of available tests."""
    console = Console()
    
    table = Table(title="Enhanced Architecture Test Suite")
    table.add_column("Test Type", style="cyan")
    table.add_column("Description", style="yellow")
    table.add_column("Coverage", style="green")
    
    test_info = [
        ("unit", "Individual component tests", "Agents, Storage, Communication, Monitoring"),
        ("integration", "Component interaction tests", "Cyclical Workflow, JSON Storage, Progress Tracking"),
        ("e2e", "End-to-end workflow tests", "Complete Scraping Workflows, Error Handling"),
        ("all", "Complete test suite", "All components and workflows")
    ]
    
    for test_type, description, coverage in test_info:
        table.add_row(test_type, description, coverage)
    
    console.print(table)
    
    console.print("\n[bold]Test Components:[/bold]")
    console.print("[cyan]• NavigationAgent - Site navigation and popup handling[/cyan]")
    console.print("[cyan]• ExtractionAgent - Product data extraction with feedback[/cyan]")
    console.print("[cyan]• ValidationAgent - Data validation and storage[/cyan]")
    console.print("[cyan]• CyclicalProcessor - Workflow orchestration[/cyan]")
    console.print("[cyan]• JSONManager - Persistent storage with atomic updates[/cyan]")
    console.print("[cyan]• BackupManager - Backup creation and recovery[/cyan]")
    console.print("[cyan]• EnhancedProgressTracker - Real-time progress monitoring[/cyan]")
    console.print("[cyan]• PerformanceMetrics - System performance tracking[/cyan]")
    console.print("[cyan]• MessageProtocol - Inter-agent communication[/cyan]")
    console.print("[cyan]• FeedbackSystem - Validation feedback and re-extraction[/cyan]")


def check_test_dependencies():
    """Check if test dependencies are installed."""
    console = Console()
    
    required_packages = [
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "rich"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        console.print("[red]Missing test dependencies:[/red]")
        for package in missing_packages:
            console.print(f"[red]  • {package}[/red]")
        console.print(f"\n[yellow]Install with: pip install {' '.join(missing_packages)}[/yellow]")
        return False
    
    console.print("[green]✅ All test dependencies are installed[/green]")
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Enhanced Architecture Test Runner")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["unit", "integration", "e2e", "all"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Display test summary and exit"
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check test dependencies and exit"
    )
    
    args = parser.parse_args()
    
    console = Console()
    
    if args.summary:
        display_test_summary()
        return
    
    if args.check_deps:
        check_test_dependencies()
        return
    
    # Check dependencies before running tests
    if not check_test_dependencies():
        console.print("[red]Please install missing dependencies before running tests[/red]")
        sys.exit(1)
    
    # Run tests
    success = run_tests(
        test_type=args.test_type,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    if success:
        console.print(f"\n[bold green]🎉 All {args.test_type} tests completed successfully![/bold green]")
        if args.coverage:
            console.print("[cyan]📊 Coverage report generated in htmlcov/[/cyan]")
    else:
        console.print(f"\n[bold red]💥 {args.test_type.title()} tests failed![/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
