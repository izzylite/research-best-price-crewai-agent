"""
AI Activity Logger - Tracks AI thoughts, tool calls, and debugging information.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import threading


@dataclass
class ToolCall:
    """Represents a tool call made by an AI agent."""
    timestamp: str
    agent_name: str
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: str
    execution_time_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentThought:
    """Represents an AI agent's thought process."""
    timestamp: str
    agent_name: str
    thought: str
    context: Optional[str] = None
    task_id: Optional[str] = None


@dataclass
class TaskEvent:
    """Represents a task lifecycle event."""
    timestamp: str
    task_id: str
    agent_name: str
    event_type: str  # started, completed, failed, delegated
    description: str
    metadata: Optional[Dict[str, Any]] = None


class AILogger:
    """Comprehensive logger for AI agent activities, thoughts, and tool calls."""
    
    def __init__(self, log_dir: str = "logs", session_id: Optional[str] = None):
        """Initialize the AI logger."""
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create session-specific log directory
        self.session_dir = self.log_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)
        
        # Initialize log files
        self.thoughts_file = self.session_dir / "ai_thoughts.jsonl"
        self.tools_file = self.session_dir / "tool_calls.jsonl"
        self.tasks_file = self.session_dir / "task_events.jsonl"
        self.summary_file = self.session_dir / "session_summary.json"
        
        # Thread-safe logging
        self._lock = threading.Lock()
        
        # Setup standard logger
        self.logger = self._setup_logger()
        
        # Session statistics
        self.stats = {
            "session_start": datetime.now().isoformat(),
            "total_thoughts": 0,
            "total_tool_calls": 0,
            "total_tasks": 0,
            "successful_tool_calls": 0,
            "failed_tool_calls": 0,
            "agents_used": set(),
            "tools_used": set()
        }
        
        self.logger.info(f"AI Logger initialized for session: {self.session_id}")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup the standard logger."""
        logger = logging.getLogger(f"ai_logger_{self.session_id}")
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(self.session_dir / "ai_activity.log")
        file_handler.setLevel(logging.INFO)
        
        # Console handler for important events
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_thought(self, agent_name: str, thought: str, context: Optional[str] = None, 
                   task_id: Optional[str] = None):
        """Log an AI agent's thought."""
        with self._lock:
            thought_entry = AgentThought(
                timestamp=datetime.now().isoformat(),
                agent_name=agent_name,
                thought=thought,
                context=context,
                task_id=task_id
            )
            
            # Write to JSONL file
            with open(self.thoughts_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(thought_entry)) + '\n')
            
            # Update stats
            self.stats["total_thoughts"] += 1
            self.stats["agents_used"].add(agent_name)
            
            # Log to standard logger
            self.logger.info(f"THOUGHT [{agent_name}]: {thought[:100]}...")
    
    def log_tool_call(self, agent_name: str, tool_name: str, tool_input: Dict[str, Any],
                     tool_output: str, execution_time_ms: Optional[float] = None,
                     success: bool = True, error: Optional[str] = None):
        """Log a tool call made by an AI agent."""
        with self._lock:
            tool_call = ToolCall(
                timestamp=datetime.now().isoformat(),
                agent_name=agent_name,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                execution_time_ms=execution_time_ms,
                success=success,
                error=error
            )
            
            # Write to JSONL file
            with open(self.tools_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(tool_call)) + '\n')
            
            # Update stats
            self.stats["total_tool_calls"] += 1
            self.stats["agents_used"].add(agent_name)
            self.stats["tools_used"].add(tool_name)
            
            if success:
                self.stats["successful_tool_calls"] += 1
            else:
                self.stats["failed_tool_calls"] += 1
            
            # Log to standard logger
            status = "SUCCESS" if success else "FAILED"
            self.logger.info(f"TOOL [{agent_name}] {tool_name}: {status}")
            if error:
                self.logger.error(f"TOOL ERROR [{agent_name}] {tool_name}: {error}")
    
    def log_task_event(self, task_id: str, agent_name: str, event_type: str,
                      description: str, metadata: Optional[Dict[str, Any]] = None):
        """Log a task lifecycle event."""
        with self._lock:
            task_event = TaskEvent(
                timestamp=datetime.now().isoformat(),
                task_id=task_id,
                agent_name=agent_name,
                event_type=event_type,
                description=description,
                metadata=metadata
            )
            
            # Write to JSONL file
            with open(self.tasks_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(task_event)) + '\n')
            
            # Update stats
            if event_type == "started":
                self.stats["total_tasks"] += 1
            self.stats["agents_used"].add(agent_name)
            
            # Log to standard logger
            self.logger.info(f"TASK [{agent_name}] {task_id}: {event_type.upper()} - {description}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        with self._lock:
            summary = self.stats.copy()
            summary["session_end"] = datetime.now().isoformat()
            summary["agents_used"] = list(summary["agents_used"])
            summary["tools_used"] = list(summary["tools_used"])
            
            # Calculate success rate
            total_calls = summary["total_tool_calls"]
            if total_calls > 0:
                summary["tool_success_rate"] = summary["successful_tool_calls"] / total_calls
            else:
                summary["tool_success_rate"] = 0.0
            
            return summary
    
    def save_session_summary(self):
        """Save the session summary to file."""
        summary = self.get_session_summary()
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Session summary saved: {self.summary_file}")
    
    def get_recent_thoughts(self, limit: int = 10) -> List[AgentThought]:
        """Get recent AI thoughts."""
        thoughts = []
        if self.thoughts_file.exists():
            with open(self.thoughts_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    data = json.loads(line.strip())
                    thoughts.append(AgentThought(**data))
        return thoughts
    
    def get_recent_tool_calls(self, limit: int = 10) -> List[ToolCall]:
        """Get recent tool calls."""
        tool_calls = []
        if self.tools_file.exists():
            with open(self.tools_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    data = json.loads(line.strip())
                    tool_calls.append(ToolCall(**data))
        return tool_calls
    
    def close(self):
        """Close the logger and save final summary."""
        self.save_session_summary()
        self.logger.info(f"AI Logger session closed: {self.session_id}")
        
        # Close handlers
        for handler in self.logger.handlers:
            handler.close()


# Global logger instance
_global_logger: Optional[AILogger] = None


def get_ai_logger(session_id: Optional[str] = None) -> AILogger:
    """Get or create the global AI logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = AILogger(session_id=session_id)
    return _global_logger


def close_ai_logger():
    """Close the global AI logger."""
    global _global_logger
    if _global_logger:
        _global_logger.close()
        _global_logger = None
