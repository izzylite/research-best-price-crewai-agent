"""
CrewAI Integration Logger - Hooks into CrewAI to capture AI thoughts and tool calls.
"""

import json
import re
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from .ai_logger import get_ai_logger, AILogger


class CrewAILogger:
    """Logger that integrates with CrewAI to capture agent activities."""
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize the CrewAI logger."""
        self.ai_logger = get_ai_logger(session_id)
        self.current_agents = {}  # Track current agent contexts
        self.current_tasks = {}   # Track current task contexts
    
    def log_crew_start(self, crew_id: str, agents: List[str], tasks: List[str]):
        """Log the start of a crew execution."""
        self.ai_logger.log_task_event(
            task_id=crew_id,
            agent_name="CrewAI_System",
            event_type="crew_started",
            description=f"Crew execution started with {len(agents)} agents and {len(tasks)} tasks",
            metadata={
                "agents": agents,
                "tasks": tasks,
                "crew_id": crew_id
            }
        )
    
    def log_crew_end(self, crew_id: str, success: bool, result: Any = None):
        """Log the end of a crew execution."""
        self.ai_logger.log_task_event(
            task_id=crew_id,
            agent_name="CrewAI_System",
            event_type="crew_completed" if success else "crew_failed",
            description=f"Crew execution {'completed successfully' if success else 'failed'}",
            metadata={
                "crew_id": crew_id,
                "success": success,
                "result_length": len(str(result)) if result else 0
            }
        )
    
    def log_agent_start(self, agent_name: str, task_id: str, task_description: str):
        """Log when an agent starts working on a task."""
        self.current_agents[agent_name] = {
            "task_id": task_id,
            "start_time": time.time(),
            "task_description": task_description
        }
        
        self.ai_logger.log_task_event(
            task_id=task_id,
            agent_name=agent_name,
            event_type="started",
            description=f"Agent started working on task",
            metadata={
                "task_description": task_description[:200] + "..." if len(task_description) > 200 else task_description
            }
        )
    
    def log_agent_end(self, agent_name: str, task_id: str, success: bool, result: Any = None):
        """Log when an agent completes a task."""
        if agent_name in self.current_agents:
            start_time = self.current_agents[agent_name]["start_time"]
            execution_time = time.time() - start_time
            del self.current_agents[agent_name]
        else:
            execution_time = None
        
        self.ai_logger.log_task_event(
            task_id=task_id,
            agent_name=agent_name,
            event_type="completed" if success else "failed",
            description=f"Agent {'completed' if success else 'failed'} task",
            metadata={
                "success": success,
                "execution_time_seconds": execution_time,
                "result_length": len(str(result)) if result else 0
            }
        )
    
    def log_agent_thought(self, agent_name: str, thought: str, context: Optional[str] = None):
        """Log an agent's thought process."""
        task_id = None
        if agent_name in self.current_agents:
            task_id = self.current_agents[agent_name]["task_id"]
        
        self.ai_logger.log_thought(
            agent_name=agent_name,
            thought=thought,
            context=context,
            task_id=task_id
        )
    
    def log_tool_usage(self, agent_name: str, tool_name: str, tool_input: Dict[str, Any],
                      tool_output: str, execution_time_ms: Optional[float] = None,
                      success: bool = True, error: Optional[str] = None):
        """Log tool usage by an agent."""
        self.ai_logger.log_tool_call(
            agent_name=agent_name,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            execution_time_ms=execution_time_ms,
            success=success,
            error=error
        )
    
    def log_delegation(self, from_agent: str, to_agent: str, task_description: str):
        """Log when an agent delegates work to another agent."""
        self.ai_logger.log_task_event(
            task_id=f"delegation_{int(time.time())}",
            agent_name=from_agent,
            event_type="delegated",
            description=f"Delegated work to {to_agent}",
            metadata={
                "to_agent": to_agent,
                "task_description": task_description
            }
        )
    
    def parse_crew_output(self, output_text: str) -> List[Dict[str, Any]]:
        """Parse CrewAI terminal output to extract structured information."""
        events = []
        lines = output_text.split('\n')
        
        current_agent = None
        current_task = None
        
        for line in lines:
            line = line.strip()
            
            # Parse agent information
            agent_match = re.search(r'Agent: (.+)', line)
            if agent_match:
                current_agent = agent_match.group(1).strip()
            
            # Parse task information
            task_match = re.search(r'Task: (.+)', line)
            if task_match:
                current_task = task_match.group(1).strip()
            
            # Parse thoughts
            if "Thought:" in line and current_agent:
                thought = line.split("Thought:", 1)[1].strip()
                events.append({
                    "type": "thought",
                    "agent": current_agent,
                    "content": thought,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Parse tool usage
            tool_match = re.search(r'Using Tool: (.+)', line)
            if tool_match and current_agent:
                tool_name = tool_match.group(1).strip()
                events.append({
                    "type": "tool_start",
                    "agent": current_agent,
                    "tool": tool_name,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Parse tool results
            if "Tool Output" in line and current_agent:
                events.append({
                    "type": "tool_end",
                    "agent": current_agent,
                    "timestamp": datetime.now().isoformat()
                })
        
        return events
    
    def process_crew_output_stream(self, output_stream):
        """Process a stream of CrewAI output and log events in real-time."""
        buffer = ""
        
        for chunk in output_stream:
            buffer += chunk
            
            # Process complete lines
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                events = self.parse_crew_output(line)
                
                for event in events:
                    if event["type"] == "thought":
                        self.log_agent_thought(
                            agent_name=event["agent"],
                            thought=event["content"]
                        )
                    elif event["type"] == "tool_start":
                        # Tool start logged when we get the actual tool call
                        pass
                    elif event["type"] == "tool_end":
                        # Tool end logged when we get the actual result
                        pass
    
    def get_session_logs(self) -> Dict[str, Any]:
        """Get comprehensive session logs."""
        return {
            "summary": self.ai_logger.get_session_summary(),
            "recent_thoughts": [
                {
                    "timestamp": t.timestamp,
                    "agent": t.agent_name,
                    "thought": t.thought,
                    "task_id": t.task_id
                }
                for t in self.ai_logger.get_recent_thoughts(50)
            ],
            "recent_tool_calls": [
                {
                    "timestamp": t.timestamp,
                    "agent": t.agent_name,
                    "tool": t.tool_name,
                    "success": t.success,
                    "execution_time_ms": t.execution_time_ms,
                    "error": t.error
                }
                for t in self.ai_logger.get_recent_tool_calls(50)
            ]
        }
    
    def close(self):
        """Close the logger and save final summary."""
        self.ai_logger.close()


# Global CrewAI logger instance
_crew_logger: Optional[CrewAILogger] = None


def get_crew_logger(session_id: Optional[str] = None) -> CrewAILogger:
    """Get or create the global CrewAI logger instance."""
    global _crew_logger
    if _crew_logger is None:
        _crew_logger = CrewAILogger(session_id=session_id)
    return _crew_logger


def close_crew_logger():
    """Close the global CrewAI logger."""
    global _crew_logger
    if _crew_logger:
        _crew_logger.close()
        _crew_logger = None
