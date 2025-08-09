"""Utility functions for CrewAI setup and configuration."""

import os
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_crewai_directories(project_root: str = None):
    """Ensure all required CrewAI memory directories exist.
    
    Args:
        project_root: Optional project root directory name
    """
    # Base CrewAI directory
    base_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "CrewAI"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Project directory
    if project_root:
        project_dir = base_dir / project_root
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory directories
        memory_dirs = [
            project_dir / "short_term",
            project_dir / "entities",
            project_dir / "tasks",
            project_dir / "tools"
        ]
        
        for directory in memory_dirs:
            directory.mkdir(parents=True, exist_ok=True)
    # Info logging removed
    
    # Info logging removed


def clear_crewai_memory(project_root: str = None):
    """Clear all CrewAI memory data.

    Args:
        project_root: Optional project root directory name
    """
    # Base CrewAI directory
    base_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "CrewAI"

    if project_root:
        project_dir = base_dir / project_root
        if project_dir.exists():
            try:
                shutil.rmtree(project_dir)
            except Exception as e:
                logger.error(f"Failed to clear CrewAI memory: {e}")
        else:
            # No project directory found; nothing to clear
            pass
    else:
        # Clear all CrewAI memory
        if base_dir.exists():
            try:
                shutil.rmtree(base_dir)
            except Exception as e:
                logger.error(f"Failed to clear all CrewAI memory: {e}")
        else:
            # No base directory found; nothing to clear
            pass


def list_crewai_memory_projects():
    """List all CrewAI memory projects.

    Returns:
        List of project names with memory data
    """
    base_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "CrewAI"

    if not base_dir.exists():
        return []

    projects = []
    for item in base_dir.iterdir():
        if item.is_dir():
            projects.append(item.name)

    return projects