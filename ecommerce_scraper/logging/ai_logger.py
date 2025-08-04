"""Logging utilities for AI operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_ai_logger(session_id: str) -> logging.Logger:
    """Get logger for AI operations.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_dir = Path("logs") / session_id
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logger
    logger_name = f"ai_logger_{session_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Add file handler
    log_file = log_dir / "ai_activity.log"
    handler = logging.FileHandler(log_file)
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)
    
    # Log initialization
    logger.info(f"AI Logger initialized for session: {session_id}")
    
    return logger


def close_ai_logger(session_id: str):
    """Close and cleanup AI logger.
    
    Args:
        session_id: Session identifier
    """
    logger_name = f"ai_logger_{session_id}"
    logger = logging.getLogger(logger_name)
    
    try:
        # Save session summary
        log_dir = Path("logs") / session_id
        summary_file = log_dir / "session_summary.json"
        
        summary = {
            "session_start": None,  # Will be set from first log entry
            "total_thoughts": 0,
            "total_tool_calls": 0,
            "total_tasks": 0,
            "successful_tool_calls": 0,
            "failed_tool_calls": 0,
            "agents_used": set(),
            "tools_used": set(),
            "session_end": datetime.now().isoformat(),
            "tool_success_rate": 0.0
        }
        
        # Parse log file to build summary
        log_file = log_dir / "ai_activity.log"
        if log_file.exists():
            with open(log_file) as f:
                for line in f:
                    try:
                        # Extract timestamp from log line
                        if summary["session_start"] is None:
                            timestamp = line.split(',', 1)[0]
                            summary["session_start"] = datetime.strptime(
                                timestamp, "%Y-%m-%d %H:%M:%S"
                            ).isoformat()
                        
                        # Count different log types
                        if "THOUGHT" in line:
                            summary["total_thoughts"] += 1
                        elif "TOOL_CALL" in line:
                            summary["total_tool_calls"] += 1
                            if "success=True" in line:
                                summary["successful_tool_calls"] += 1
                            else:
                                summary["failed_tool_calls"] += 1
                        elif "TASK" in line:
                            summary["total_tasks"] += 1
                        
                        # Extract agent names
                        if "[" in line and "]" in line:
                            agent = line.split('[', 1)[1].split(']')[0]
                            summary["agents_used"].add(agent)
                        
                        # Extract tool names
                        if "tool_name=" in line:
                            tool = line.split("tool_name=")[1].split()[0]
                            summary["tools_used"].add(tool)
                            
                    except Exception as e:
                        logger.warning(f"Error parsing log line: {e}")
        
        # Calculate success rate
        if summary["total_tool_calls"] > 0:
            summary["tool_success_rate"] = (
                summary["successful_tool_calls"] / summary["total_tool_calls"]
            ) * 100
        
        # Convert sets to lists for JSON serialization
        summary["agents_used"] = list(summary["agents_used"])
        summary["tools_used"] = list(summary["tools_used"])
        
        # Save summary
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Session summary saved: {summary_file}")
        
    except Exception as e:
        logger.error(f"Error saving session summary: {e}")
    
    finally:
        # Remove handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        
        logger.info(f"AI Logger session closed: {session_id}")