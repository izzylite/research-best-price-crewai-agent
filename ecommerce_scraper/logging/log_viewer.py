"""
Log Viewer - CLI tool to view and analyze AI activity logs.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree


class LogViewer:
    """CLI tool for viewing and analyzing AI activity logs."""
    
    def __init__(self, logs_dir: str = "logs"):
        """Initialize the log viewer."""
        self.logs_dir = Path(logs_dir)
        self.console = Console()
    
    def list_sessions(self) -> List[str]:
        """List all available log sessions."""
        if not self.logs_dir.exists():
            return []
        
        sessions = []
        for session_dir in self.logs_dir.iterdir():
            if session_dir.is_dir() and session_dir.name != ".gitkeep":
                sessions.append(session_dir.name)
        
        return sorted(sessions, reverse=True)  # Most recent first
    
    def load_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session summary."""
        summary_file = self.logs_dir / session_id / "session_summary.json"
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def load_thoughts(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load AI thoughts from session."""
        thoughts_file = self.logs_dir / session_id / "ai_thoughts.jsonl"
        thoughts = []
        
        if thoughts_file.exists():
            with open(thoughts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    thoughts.append(json.loads(line.strip()))
        
        if limit:
            thoughts = thoughts[-limit:]
        
        return thoughts
    
    def load_tool_calls(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load tool calls from session."""
        tools_file = self.logs_dir / session_id / "tool_calls.jsonl"
        tool_calls = []
        
        if tools_file.exists():
            with open(tools_file, 'r', encoding='utf-8') as f:
                for line in f:
                    tool_calls.append(json.loads(line.strip()))
        
        if limit:
            tool_calls = tool_calls[-limit:]
        
        return tool_calls
    
    def load_task_events(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load task events from session."""
        tasks_file = self.logs_dir / session_id / "task_events.jsonl"
        task_events = []
        
        if tasks_file.exists():
            with open(tasks_file, 'r', encoding='utf-8') as f:
                for line in f:
                    task_events.append(json.loads(line.strip()))
        
        if limit:
            task_events = task_events[-limit:]
        
        return task_events
    
    def show_sessions_list(self):
        """Display list of available sessions."""
        sessions = self.list_sessions()
        
        if not sessions:
            self.console.print("[yellow]No log sessions found.[/yellow]")
            return
        
        table = Table(title="Available Log Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Summary", style="white")
        table.add_column("Duration", style="green")
        table.add_column("Success Rate", style="magenta")
        
        for session_id in sessions:
            summary = self.load_session_summary(session_id)
            if summary:
                start_time = datetime.fromisoformat(summary.get("session_start", ""))
                end_time = datetime.fromisoformat(summary.get("session_end", ""))
                duration = str(end_time - start_time).split('.')[0]  # Remove microseconds
                
                success_rate = f"{summary.get('tool_success_rate', 0):.1%}"
                summary_text = f"{summary.get('total_tasks', 0)} tasks, {summary.get('total_tool_calls', 0)} tool calls"
                
                table.add_row(session_id, summary_text, duration, success_rate)
            else:
                table.add_row(session_id, "No summary available", "-", "-")
        
        self.console.print(table)
    
    def show_session_details(self, session_id: str):
        """Display detailed information about a session."""
        summary = self.load_session_summary(session_id)
        
        if not summary:
            self.console.print(f"[red]Session {session_id} not found or no summary available.[/red]")
            return
        
        # Session overview
        self.console.print(Panel(
            f"[bold]Session: {session_id}[/bold]\n"
            f"Start: {summary.get('session_start', 'Unknown')}\n"
            f"End: {summary.get('session_end', 'Unknown')}\n"
            f"Total Thoughts: {summary.get('total_thoughts', 0)}\n"
            f"Total Tool Calls: {summary.get('total_tool_calls', 0)}\n"
            f"Total Tasks: {summary.get('total_tasks', 0)}\n"
            f"Success Rate: {summary.get('tool_success_rate', 0):.1%}\n"
            f"Agents Used: {', '.join(summary.get('agents_used', []))}\n"
            f"Tools Used: {', '.join(summary.get('tools_used', []))}",
            title="Session Overview"
        ))
    
    def show_thoughts(self, session_id: str, limit: int = 10):
        """Display AI thoughts from a session."""
        thoughts = self.load_thoughts(session_id, limit)
        
        if not thoughts:
            self.console.print("[yellow]No thoughts found for this session.[/yellow]")
            return
        
        self.console.print(f"\n[bold]Recent AI Thoughts (last {len(thoughts)})[/bold]")
        
        for thought in thoughts:
            timestamp = datetime.fromisoformat(thought['timestamp']).strftime('%H:%M:%S')
            agent_name = thought['agent_name']
            thought_text = thought['thought']
            
            self.console.print(Panel(
                f"[dim]{timestamp}[/dim] [bold cyan]{agent_name}[/bold cyan]\n{thought_text}",
                border_style="blue"
            ))
    
    def show_tool_calls(self, session_id: str, limit: int = 10):
        """Display tool calls from a session."""
        tool_calls = self.load_tool_calls(session_id, limit)
        
        if not tool_calls:
            self.console.print("[yellow]No tool calls found for this session.[/yellow]")
            return
        
        table = Table(title=f"Recent Tool Calls (last {len(tool_calls)})")
        table.add_column("Time", style="dim")
        table.add_column("Agent", style="cyan")
        table.add_column("Tool", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Duration (ms)", style="magenta")
        table.add_column("Output", style="white")
        
        for call in tool_calls:
            timestamp = datetime.fromisoformat(call['timestamp']).strftime('%H:%M:%S')
            agent_name = call['agent_name']
            tool_name = call['tool_name'].split('.')[-1]  # Get just the method name
            status = "✅" if call['success'] else "❌"
            duration = f"{call.get('execution_time_ms', 0):.1f}" if call.get('execution_time_ms') else "-"
            output = call['tool_output'][:50] + "..." if len(call['tool_output']) > 50 else call['tool_output']
            
            table.add_row(timestamp, agent_name, tool_name, status, duration, output)
        
        self.console.print(table)
    
    def show_task_events(self, session_id: str, limit: int = 10):
        """Display task events from a session."""
        task_events = self.load_task_events(session_id, limit)
        
        if not task_events:
            self.console.print("[yellow]No task events found for this session.[/yellow]")
            return
        
        table = Table(title=f"Recent Task Events (last {len(task_events)})")
        table.add_column("Time", style="dim")
        table.add_column("Agent", style="cyan")
        table.add_column("Event", style="yellow")
        table.add_column("Description", style="white")
        
        for event in task_events:
            timestamp = datetime.fromisoformat(event['timestamp']).strftime('%H:%M:%S')
            agent_name = event['agent_name']
            event_type = event['event_type'].upper()
            description = event['description']
            
            table.add_row(timestamp, agent_name, event_type, description)
        
        self.console.print(table)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="View AI activity logs")
    parser.add_argument("--logs-dir", default="logs", help="Directory containing log files")
    parser.add_argument("--session", help="Session ID to view")
    parser.add_argument("--thoughts", action="store_true", help="Show AI thoughts")
    parser.add_argument("--tools", action="store_true", help="Show tool calls")
    parser.add_argument("--tasks", action="store_true", help="Show task events")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of entries to show")
    
    args = parser.parse_args()
    
    viewer = LogViewer(args.logs_dir)
    
    if not args.session:
        viewer.show_sessions_list()
        return
    
    # Show session details
    viewer.show_session_details(args.session)
    
    # Show specific log types if requested
    if args.thoughts:
        viewer.show_thoughts(args.session, args.limit)
    
    if args.tools:
        viewer.show_tool_calls(args.session, args.limit)
    
    if args.tasks:
        viewer.show_task_events(args.session, args.limit)
    
    # If no specific log type requested, show a summary of recent activity
    if not any([args.thoughts, args.tools, args.tasks]):
        viewer.show_thoughts(args.session, 5)
        viewer.show_tool_calls(args.session, 5)
        viewer.show_task_events(args.session, 5)


if __name__ == "__main__":
    main()
