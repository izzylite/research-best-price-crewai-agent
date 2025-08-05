"""Logging utilities for CrewAI operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_crew_logger(session_id: str) -> logging.Logger:
    """Get logger for CrewAI operations.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_dir = Path("logs") / session_id
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logger
    logger_name = f"crew_logger_{session_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Add file handler
    log_file = log_dir / "crew_activity.log"
    handler = logging.FileHandler(log_file)
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)
    
    # Add JSON handler for structured logging
    json_file = log_dir / "task_events.jsonl"
    json_handler = JsonFileHandler(json_file)
    logger.addHandler(json_handler)
    
    return logger


def close_crew_logger(session_id: str):
    """Close and cleanup CrewAI logger.
    
    Args:
        session_id: Session identifier
    """
    logger_name = f"crew_logger_{session_id}"
    logger = logging.getLogger(logger_name)
    
    # Remove handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


class JsonFileHandler(logging.Handler):
    """Custom handler for JSON line-delimited logging."""
    
    def __init__(self, filename: str):
        """Initialize JSON file handler.
        
        Args:
            filename: Path to log file
        """
        super().__init__()
        self.filename = filename
    
    def emit(self, record: logging.LogRecord):
        """Write log record as JSON.
        
        Args:
            record: Log record to write
        """
        try:
            # Extract task info from message
            task_info = self._parse_task_info(record.msg)
            
            # Create JSON entry
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "task_id": task_info.get("task_id"),
                "agent_name": task_info.get("agent_name"),
                "event_type": task_info.get("event_type"),
                "description": task_info.get("description"),
                "metadata": task_info.get("metadata", {})
            }
            
            # Write to file
            with open(self.filename, 'a') as f:
                json.dump(entry, f)
                f.write('\n')
                
        except Exception as e:
            # Log error but don't raise to avoid handler loops
            logger.error(f"Error writing JSON log: {e}")
    
    def _parse_task_info(self, message: str) -> Dict[str, Any]:
        """Parse task information from log message.
        
        Args:
            message: Log message to parse
            
        Returns:
            Dictionary containing parsed task information
        """
        try:
            # Try to parse as JSON first
            if isinstance(message, str) and message.startswith('{'):
                return json.loads(message)
            
            # Otherwise parse structured message format:
            # TASK [agent] task_id: event - description
            parts = message.split(' - ', 1)
            if len(parts) != 2:
                return {"description": message}
            
            header, description = parts
            header_parts = header.split(' ', 2)
            
            if len(header_parts) != 3:
                return {"description": message}
            
            _, agent, task_id = header_parts
            agent = agent.strip('[]')
            task_id = task_id.strip(':')
            
            return {
                "task_id": task_id,
                "agent_name": agent,
                "event_type": "task_event",
                "description": description
            }
            
        except Exception:
            # Return raw message if parsing fails
            return {"description": message}