"""Progress tracking and resume functionality for multi-vendor ecommerce scraping."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

from ecommerce_scraper.state.state_manager import StateManager, PaginationState, format_progress_message, calculate_eta

console = Console()


@dataclass
class ProgressSnapshot:
    """Snapshot of scraping progress at a point in time."""
    
    timestamp: datetime
    session_id: str
    total_vendors: int
    active_vendors: int
    completed_vendors: int
    total_products: int
    total_pages: int
    estimated_completion: Optional[str] = None
    vendor_progress: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.vendor_progress is None:
            self.vendor_progress = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressSnapshot':
        """Create from dictionary with proper deserialization."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ProgressTracker:
    """Tracks and displays progress for multi-vendor scraping operations."""
    
    def __init__(self, state_manager: StateManager, update_interval: float = 2.0):
        """Initialize progress tracker.
        
        Args:
            state_manager: State manager instance
            update_interval: How often to update progress (seconds)
        """
        self.state_manager = state_manager
        self.update_interval = update_interval
        
        # Progress tracking
        self.snapshots: List[ProgressSnapshot] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Display components
        self.progress_display: Optional[Progress] = None
        self.live_display: Optional[Live] = None
        self.progress_tasks: Dict[str, int] = {}  # vendor_category -> task_id
        
        # Callbacks
        self.progress_callbacks: List[Callable] = []
        
        # Performance tracking
        self.page_times: List[float] = []
        self.product_rates: List[float] = []
    
    def start_tracking(self, session_id: str):
        """Start tracking progress for a session.
        
        Args:
            session_id: Session to track
        """
        self.start_time = datetime.utcnow()
        self.session_id = session_id
        
        # Initialize progress display
        self.progress_display = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        )
        
        console.print(f"[green]Started tracking session: {session_id}[/green]")
    
    def stop_tracking(self):
        """Stop tracking progress."""
        self.end_time = datetime.utcnow()
        
        if self.live_display:
            self.live_display.stop()
        
        # Generate final summary
        self._generate_final_summary()
        
        console.print("[green]Progress tracking stopped[/green]")
    
    def add_vendor_category(self, vendor: str, category: str, estimated_pages: Optional[int] = None):
        """Add a vendor/category combination to track.
        
        Args:
            vendor: Vendor identifier
            category: Category identifier
            estimated_pages: Estimated number of pages (optional)
        """
        if not self.progress_display:
            return
        
        key = f"{vendor}_{category}"
        description = f"{vendor.title()}/{category}"
        
        total = estimated_pages if estimated_pages else 100  # Default estimate
        
        task_id = self.progress_display.add_task(
            description=description,
            total=total
        )
        
        self.progress_tasks[key] = task_id
    
    def update_progress(self, vendor: str, category: str, current_page: int, 
                       products_scraped: int, total_pages: Optional[int] = None):
        """Update progress for a vendor/category.
        
        Args:
            vendor: Vendor identifier
            category: Category identifier
            current_page: Current page number
            products_scraped: Number of products scraped
            total_pages: Total pages (if known)
        """
        if not self.progress_display:
            return
        
        key = f"{vendor}_{category}"
        
        if key in self.progress_tasks:
            task_id = self.progress_tasks[key]
            
            # Update task
            if total_pages:
                self.progress_display.update(
                    task_id,
                    completed=current_page,
                    total=total_pages,
                    description=f"{vendor.title()}/{category} - {products_scraped} products"
                )
            else:
                self.progress_display.advance(task_id, 1)
                self.progress_display.update(
                    task_id,
                    description=f"{vendor.title()}/{category} - Page {current_page} - {products_scraped} products"
                )
    
    def create_live_display(self) -> Live:
        """Create a live display for real-time progress monitoring.
        
        Returns:
            Rich Live display instance
        """
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=10),
            Layout(name="summary", size=8),
            Layout(name="footer", size=3)
        )
        
        self.live_display = Live(layout, refresh_per_second=1, console=console)
        return self.live_display
    
    def update_live_display(self, session_id: str):
        """Update the live display with current progress.
        
        Args:
            session_id: Session ID to display
        """
        if not self.live_display:
            return
        
        layout = self.live_display.renderable
        
        # Update header
        elapsed = datetime.utcnow() - self.start_time if self.start_time else timedelta(0)
        layout["header"].update(
            Panel(
                f"[bold blue]Multi-Vendor Ecommerce Scraping Progress[/bold blue]\n"
                f"Session: {session_id} | Elapsed: {elapsed}",
                style="blue"
            )
        )
        
        # Update progress bars
        if self.progress_display:
            layout["progress"].update(self.progress_display)
        
        # Update summary
        summary = self._create_summary_table(session_id)
        layout["summary"].update(summary)
        
        # Update footer
        layout["footer"].update(
            Panel(
                "[dim]Press Ctrl+C to pause | 'q' to quit | 'r' to resume[/dim]",
                style="dim"
            )
        )
    
    def _create_summary_table(self, session_id: str) -> Table:
        """Create a summary table of current progress.
        
        Args:
            session_id: Session ID
            
        Returns:
            Rich Table with summary information
        """
        table = Table(title="Session Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Get session summary
        summary = self.state_manager.get_session_summary(session_id)
        
        if "error" not in summary:
            table.add_row("Total Vendor/Categories", str(summary["total_vendor_categories"]))
            table.add_row("Completed", str(summary["completed_vendor_categories"]))
            table.add_row("Total Products", str(summary["total_products_scraped"]))
            table.add_row("Total Pages", str(summary["total_pages_processed"]))
            table.add_row("Errors", str(summary["total_errors"]))
            table.add_row("Status", summary["overall_status"].title())
            
            # Calculate rates
            if self.start_time:
                elapsed_minutes = (datetime.utcnow() - self.start_time).total_seconds() / 60
                if elapsed_minutes > 0:
                    products_per_minute = summary["total_products_scraped"] / elapsed_minutes
                    pages_per_minute = summary["total_pages_processed"] / elapsed_minutes
                    
                    table.add_row("Products/min", f"{products_per_minute:.1f}")
                    table.add_row("Pages/min", f"{pages_per_minute:.1f}")
        else:
            table.add_row("Error", summary["error"])
        
        return table
    
    def take_snapshot(self, session_id: str) -> ProgressSnapshot:
        """Take a snapshot of current progress.
        
        Args:
            session_id: Session ID
            
        Returns:
            Progress snapshot
        """
        summary = self.state_manager.get_session_summary(session_id)
        
        if "error" in summary:
            # Create empty snapshot on error
            snapshot = ProgressSnapshot(
                timestamp=datetime.utcnow(),
                session_id=session_id,
                total_vendors=0,
                active_vendors=0,
                completed_vendors=0,
                total_products=0,
                total_pages=0
            )
        else:
            # Calculate ETA
            eta = self._calculate_eta(summary)
            
            snapshot = ProgressSnapshot(
                timestamp=datetime.utcnow(),
                session_id=session_id,
                total_vendors=summary["total_vendor_categories"],
                active_vendors=summary["total_vendor_categories"] - summary["completed_vendor_categories"],
                completed_vendors=summary["completed_vendor_categories"],
                total_products=summary["total_products_scraped"],
                total_pages=summary["total_pages_processed"],
                estimated_completion=eta,
                vendor_progress=summary.get("vendor_categories", [])
            )
        
        self.snapshots.append(snapshot)
        
        # Notify callbacks
        for callback in self.progress_callbacks:
            callback(snapshot)
        
        return snapshot
    
    def _calculate_eta(self, summary: Dict[str, Any]) -> Optional[str]:
        """Calculate estimated time to completion.
        
        Args:
            summary: Session summary
            
        Returns:
            ETA string or None
        """
        if not self.start_time or summary["completed_vendor_categories"] == 0:
            return None
        
        elapsed = datetime.utcnow() - self.start_time
        completed = summary["completed_vendor_categories"]
        total = summary["total_vendor_categories"]
        
        if completed >= total:
            return "Complete"
        
        remaining = total - completed
        avg_time_per_vendor = elapsed.total_seconds() / completed
        eta_seconds = remaining * avg_time_per_vendor
        
        eta_time = datetime.utcnow() + timedelta(seconds=eta_seconds)
        return eta_time.strftime("%H:%M:%S")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        if not self.snapshots:
            return {}
        
        latest = self.snapshots[-1]
        
        metrics = {
            "total_runtime": None,
            "average_products_per_minute": 0,
            "average_pages_per_minute": 0,
            "peak_products_per_minute": 0,
            "peak_pages_per_minute": 0,
            "efficiency_score": 0
        }
        
        if self.start_time:
            if self.end_time:
                runtime = self.end_time - self.start_time
            else:
                runtime = datetime.utcnow() - self.start_time
            
            metrics["total_runtime"] = str(runtime)
            
            # Calculate rates
            minutes = runtime.total_seconds() / 60
            if minutes > 0:
                metrics["average_products_per_minute"] = latest.total_products / minutes
                metrics["average_pages_per_minute"] = latest.total_pages / minutes
        
        # Calculate peak rates from snapshots
        if len(self.snapshots) > 1:
            product_rates = []
            page_rates = []
            
            for i in range(1, len(self.snapshots)):
                prev = self.snapshots[i-1]
                curr = self.snapshots[i]
                
                time_diff = (curr.timestamp - prev.timestamp).total_seconds() / 60
                if time_diff > 0:
                    product_rate = (curr.total_products - prev.total_products) / time_diff
                    page_rate = (curr.total_pages - prev.total_pages) / time_diff
                    
                    product_rates.append(product_rate)
                    page_rates.append(page_rate)
            
            if product_rates:
                metrics["peak_products_per_minute"] = max(product_rates)
            if page_rates:
                metrics["peak_pages_per_minute"] = max(page_rates)
        
        return metrics
    
    def save_progress_log(self, filepath: str):
        """Save progress log to file.
        
        Args:
            filepath: Path to save log file
        """
        log_data = {
            "session_id": getattr(self, 'session_id', None),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "performance_metrics": self.get_performance_metrics()
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        console.print(f"[green]Progress log saved to: {filepath}[/green]")
    
    def load_progress_log(self, filepath: str):
        """Load progress log from file.
        
        Args:
            filepath: Path to log file
        """
        with open(filepath, 'r') as f:
            log_data = json.load(f)
        
        if log_data.get("start_time"):
            self.start_time = datetime.fromisoformat(log_data["start_time"])
        if log_data.get("end_time"):
            self.end_time = datetime.fromisoformat(log_data["end_time"])
        
        self.snapshots = [
            ProgressSnapshot.from_dict(snapshot_data)
            for snapshot_data in log_data.get("snapshots", [])
        ]
        
        console.print(f"[green]Progress log loaded from: {filepath}[/green]")
    
    def _generate_final_summary(self):
        """Generate and display final summary."""
        if not self.snapshots:
            return
        
        final_snapshot = self.snapshots[-1]
        metrics = self.get_performance_metrics()
        
        # Create summary table
        table = Table(title="Final Scraping Summary", show_header=True, header_style="bold green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Session ID", final_snapshot.session_id)
        table.add_row("Total Runtime", metrics.get("total_runtime", "Unknown"))
        table.add_row("Vendors Processed", f"{final_snapshot.completed_vendors}/{final_snapshot.total_vendors}")
        table.add_row("Total Products", str(final_snapshot.total_products))
        table.add_row("Total Pages", str(final_snapshot.total_pages))
        table.add_row("Avg Products/min", f"{metrics.get('average_products_per_minute', 0):.1f}")
        table.add_row("Avg Pages/min", f"{metrics.get('average_pages_per_minute', 0):.1f}")
        table.add_row("Peak Products/min", f"{metrics.get('peak_products_per_minute', 0):.1f}")
        table.add_row("Peak Pages/min", f"{metrics.get('peak_pages_per_minute', 0):.1f}")
        
        console.print(table)
        
        # Save automatic log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"progress_log_{final_snapshot.session_id}_{timestamp}.json"
        self.save_progress_log(log_path)
    
    def add_progress_callback(self, callback: Callable):
        """Add a progress callback function.
        
        Args:
            callback: Function to call on progress updates
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable):
        """Remove a progress callback function.
        
        Args:
            callback: Function to remove
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)


class ResumeManager:
    """Manages resume functionality for interrupted scraping sessions."""
    
    def __init__(self, state_manager: StateManager):
        """Initialize resume manager.
        
        Args:
            state_manager: State manager instance
        """
        self.state_manager = state_manager
    
    def get_resumable_sessions(self) -> List[Dict[str, Any]]:
        """Get list of sessions that can be resumed.
        
        Returns:
            List of resumable session information
        """
        return self.state_manager.get_resumable_sessions()
    
    def display_resumable_sessions(self) -> Optional[str]:
        """Display resumable sessions and let user choose.
        
        Returns:
            Selected session ID or None
        """
        resumable = self.get_resumable_sessions()
        
        if not resumable:
            console.print("[yellow]No resumable sessions found[/yellow]")
            return None
        
        # Create table of resumable sessions
        table = Table(title="Resumable Sessions", show_header=True, header_style="bold blue")
        table.add_column("Session ID", style="cyan")
        table.add_column("Vendors", style="green")
        table.add_column("Completed", style="yellow")
        table.add_column("Products", style="magenta")
        table.add_column("Status", style="red")
        
        for session in resumable:
            table.add_row(
                session["session_id"][:12] + "...",
                str(session["total_vendor_categories"]),
                str(session["completed_vendor_categories"]),
                str(session["total_products_scraped"]),
                session["overall_status"].title()
            )
        
        console.print(table)
        
        # Let user choose
        from rich.prompt import Prompt
        choices = [str(i) for i in range(len(resumable))]
        choice = Prompt.ask(
            "Select session to resume",
            choices=choices + ["n"],
            default="n"
        )
        
        if choice == "n":
            return None
        
        return resumable[int(choice)]["session_id"]
    
    def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Resume a specific session.
        
        Args:
            session_id: Session ID to resume
            
        Returns:
            Resume information
        """
        # Get session summary
        summary = self.state_manager.get_session_summary(session_id)
        
        if "error" in summary:
            console.print(f"[red]Error resuming session: {summary['error']}[/red]")
            return {}
        
        # Resume all paused states
        self.state_manager.resume_session(session_id)
        
        console.print(f"[green]Resumed session: {session_id}[/green]")
        console.print(f"Vendors to complete: {summary['total_vendor_categories'] - summary['completed_vendor_categories']}")
        
        return summary
