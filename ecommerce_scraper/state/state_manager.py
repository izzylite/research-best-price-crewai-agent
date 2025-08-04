"""State management system for multi-vendor ecommerce scraping with pagination and resume functionality."""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class PaginationMethod(str, Enum):
    """Pagination method enumeration."""
    NUMBERED = "numbered"
    INFINITE_SCROLL = "infinite_scroll"
    LOAD_MORE = "load_more"
    OFFSET_BASED = "offset_based"
    UNKNOWN = "unknown"


@dataclass
class PaginationState:
    """Pagination state for a specific vendor/category combination."""
    
    session_id: str
    vendor: str
    category: str
    current_page: int = 1
    total_pages: Optional[int] = None
    products_scraped: int = 0
    last_product_url: Optional[str] = None
    pagination_method: PaginationMethod = PaginationMethod.UNKNOWN
    resume_url: Optional[str] = None
    started_at: datetime = None
    last_updated: datetime = None
    status: SessionStatus = SessionStatus.ACTIVE
    
    # Additional metadata
    max_pages: Optional[int] = None  # User-defined limit
    products_per_page: int = 0
    total_products_estimate: Optional[int] = None
    error_count: int = 0
    last_error: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['last_updated'] = self.last_updated.isoformat() if self.last_updated else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaginationState':
        """Create from dictionary with proper deserialization."""
        # Convert ISO strings back to datetime objects
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('last_updated'):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        # Convert string enums back to enum objects
        if 'status' in data:
            data['status'] = SessionStatus(data['status'])
        if 'pagination_method' in data:
            data['pagination_method'] = PaginationMethod(data['pagination_method'])
        
        return cls(**data)
    
    def update_progress(self, products_added: int, current_url: Optional[str] = None):
        """Update progress information."""
        self.products_scraped += products_added
        self.last_updated = datetime.now(timezone.utc)
        if current_url:
            self.last_product_url = current_url

    def advance_page(self):
        """Advance to next page."""
        self.current_page += 1
        self.last_updated = datetime.now(timezone.utc)
    
    def record_error(self, error_message: str):
        """Record an error."""
        self.error_count += 1
        self.last_error = error_message
        self.last_updated = datetime.now(timezone.utc)
    
    def is_complete(self) -> bool:
        """Check if pagination is complete."""
        if self.status in [SessionStatus.COMPLETED, SessionStatus.CANCELLED]:
            return True
        
        # Check if we've reached the maximum pages
        if self.max_pages and self.current_page >= self.max_pages:
            return True
        
        # Check if we've reached the total pages (if known)
        if self.total_pages and self.current_page >= self.total_pages:
            return True
        
        return False
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0.0 to 1.0)."""
        if self.total_pages:
            return min(self.current_page / self.total_pages, 1.0)
        elif self.max_pages:
            return min(self.current_page / self.max_pages, 1.0)
        else:
            # Unknown total, return based on products scraped
            return min(self.products_scraped / 1000, 1.0)  # Assume 1000 as rough estimate

    def mark_complete(self):
        """Mark this pagination state as completed."""
        self.status = SessionStatus.COMPLETED
        self.last_updated = datetime.now(timezone.utc)


class StateManager:
    """Manages scraping state with persistence and resume functionality."""
    
    def __init__(self, state_dir: str = "./scraping_state"):
        """Initialize state manager.
        
        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Dict[str, PaginationState]] = {}
        
        # Load existing sessions
        self._load_existing_sessions()
    
    def _get_state_filename(self, session_id: str, vendor: str, category: str) -> Path:
        """Get filename for state file."""
        # Clean vendor and category names for safe filenames
        safe_vendor = vendor.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        safe_category = category.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').replace(',', '_').replace('&', 'and').replace(' ', '_')
        return self.state_dir / f"{session_id}_{safe_vendor}_{safe_category}.json"
    
    def _load_existing_sessions(self):
        """Load existing session states from disk."""
        try:
            for state_file in self.state_dir.glob("*.json"):
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    
                    state = PaginationState.from_dict(data)
                    
                    if state.session_id not in self.sessions:
                        self.sessions[state.session_id] = {}
                    
                    key = f"{state.vendor}_{state.category}"
                    self.sessions[state.session_id][key] = state
                    
                    logger.info(f"Loaded session state: {state.session_id} - {state.vendor}/{state.category}")
                    
                except Exception as e:
                    logger.warning(f"Failed to load state file {state_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load existing sessions: {e}")
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new scraping session.
        
        Args:
            session_id: Optional session ID, will generate if not provided
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
            logger.info(f"Created new session: {session_id}")
        
        return session_id
    
    def create_pagination_state(self, session_id: str, vendor: str, category: str, 
                              max_pages: Optional[int] = None) -> PaginationState:
        """Create pagination state for vendor/category combination.
        
        Args:
            session_id: Session identifier
            vendor: Vendor identifier
            category: Category identifier
            max_pages: Maximum pages to scrape (optional)
            
        Returns:
            PaginationState instance
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        state = PaginationState(
            session_id=session_id,
            vendor=vendor,
            category=category,
            max_pages=max_pages
        )
        
        key = f"{vendor}_{category}"
        self.sessions[session_id][key] = state
        
        # Save to disk
        self._save_state(state)
        
        logger.info(f"Created pagination state: {session_id} - {vendor}/{category}")
        return state
    
    def get_pagination_state(self, session_id: str, vendor: str, category: str) -> Optional[PaginationState]:
        """Get pagination state for vendor/category combination.
        
        Args:
            session_id: Session identifier
            vendor: Vendor identifier
            category: Category identifier
            
        Returns:
            PaginationState instance or None if not found
        """
        if session_id not in self.sessions:
            return None
        
        key = f"{vendor}_{category}"
        return self.sessions[session_id].get(key)
    
    def update_pagination_state(self, state: PaginationState):
        """Update and persist pagination state.
        
        Args:
            state: Updated PaginationState instance
        """
        if state.session_id not in self.sessions:
            self.sessions[state.session_id] = {}
        
        key = f"{state.vendor}_{state.category}"
        self.sessions[state.session_id][key] = state
        
        # Save to disk
        self._save_state(state)
    
    def _save_state(self, state: PaginationState):
        """Save state to disk.
        
        Args:
            state: PaginationState to save
        """
        try:
            filename = self._get_state_filename(state.session_id, state.vendor, state.category)
            with open(filename, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of session progress.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary dictionary
        """
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        states = self.sessions[session_id]
        total_products = sum(state.products_scraped for state in states.values())
        total_pages = sum(state.current_page for state in states.values())
        
        completed_count = sum(1 for state in states.values() if state.is_complete())
        error_count = sum(state.error_count for state in states.values())
        
        return {
            "session_id": session_id,
            "total_vendor_categories": len(states),
            "completed_vendor_categories": completed_count,
            "total_products_scraped": total_products,
            "total_pages_processed": total_pages,
            "total_errors": error_count,
            "overall_status": self._get_session_status(session_id),
            "vendor_categories": [
                {
                    "vendor": state.vendor,
                    "category": state.category,
                    "products_scraped": state.products_scraped,
                    "current_page": state.current_page,
                    "status": state.status.value,
                    "progress_percentage": state.get_progress_percentage()
                }
                for state in states.values()
            ]
        }
    
    def _get_session_status(self, session_id: str) -> str:
        """Get overall session status.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Overall session status
        """
        if session_id not in self.sessions:
            return "not_found"
        
        states = list(self.sessions[session_id].values())
        if not states:
            return "empty"
        
        # If any are active, session is active
        if any(state.status == SessionStatus.ACTIVE for state in states):
            return "active"
        
        # If all are completed, session is completed
        if all(state.status == SessionStatus.COMPLETED for state in states):
            return "completed"
        
        # If any have errors, session has errors
        if any(state.status == SessionStatus.ERROR for state in states):
            return "error"
        
        # If any are paused, session is paused
        if any(state.status == SessionStatus.PAUSED for state in states):
            return "paused"
        
        return "unknown"
    
    def get_resumable_sessions(self) -> List[Dict[str, Any]]:
        """Get list of sessions that can be resumed.
        
        Returns:
            List of resumable session summaries
        """
        resumable = []
        
        for session_id in self.sessions:
            summary = self.get_session_summary(session_id)
            status = summary["overall_status"]
            
            # Sessions that can be resumed
            if status in ["active", "paused", "error"]:
                # Check if session is not too old (7 days)
                states = self.sessions[session_id].values()
                if states:
                    latest_update = max(state.last_updated for state in states)
                    if datetime.now(timezone.utc) - latest_update < timedelta(days=7):
                        resumable.append(summary)
        
        return resumable
    
    def cleanup_old_sessions(self, days: int = 7):
        """Clean up old completed sessions.
        
        Args:
            days: Number of days after which to clean up completed sessions
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        sessions_to_remove = []
        
        for session_id, states in self.sessions.items():
            # Check if all states in session are completed and old
            all_completed = all(state.status == SessionStatus.COMPLETED for state in states.values())
            all_old = all(state.last_updated < cutoff_date for state in states.values())
            
            if all_completed and all_old:
                sessions_to_remove.append(session_id)
        
        # Remove old sessions
        for session_id in sessions_to_remove:
            self._remove_session(session_id)
            logger.info(f"Cleaned up old session: {session_id}")
    
    def _remove_session(self, session_id: str):
        """Remove session and its state files.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            # Remove state files
            for state in self.sessions[session_id].values():
                try:
                    filename = self._get_state_filename(state.session_id, state.vendor, state.category)
                    if filename.exists():
                        filename.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove state file: {e}")
            
            # Remove from memory
            del self.sessions[session_id]
    
    def pause_session(self, session_id: str):
        """Pause all active states in a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            for state in self.sessions[session_id].values():
                if state.status == SessionStatus.ACTIVE:
                    state.status = SessionStatus.PAUSED
                    state.last_updated = datetime.now(timezone.utc)
                    self._save_state(state)
            logger.info(f"Paused session: {session_id}")
    
    def resume_session(self, session_id: str):
        """Resume all paused states in a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            for state in self.sessions[session_id].values():
                if state.status == SessionStatus.PAUSED:
                    state.status = SessionStatus.ACTIVE
                    state.last_updated = datetime.now(timezone.utc)
                    self._save_state(state)
            logger.info(f"Resumed session: {session_id}")
    
    def complete_pagination_state(self, session_id: str, vendor: str, category: str):
        """Mark a pagination state as completed.
        
        Args:
            session_id: Session identifier
            vendor: Vendor identifier
            category: Category identifier
        """
        state = self.get_pagination_state(session_id, vendor, category)
        if state:
            state.status = SessionStatus.COMPLETED
            state.last_updated = datetime.now(timezone.utc)
            self.update_pagination_state(state)
            logger.info(f"Completed pagination: {session_id} - {vendor}/{category}")


# Utility functions for progress tracking
def format_progress_message(state: PaginationState) -> str:
    """Format a progress message for display.
    
    Args:
        state: PaginationState instance
        
    Returns:
        Formatted progress message
    """
    if state.total_pages:
        page_info = f"Page {state.current_page} of {state.total_pages}"
    elif state.max_pages:
        page_info = f"Page {state.current_page} (max {state.max_pages})"
    else:
        page_info = f"Page {state.current_page}"
    
    return f"{state.vendor.title()}/{state.category} - {page_info} - Products: {state.products_scraped}"


def calculate_eta(state: PaginationState, avg_time_per_page: float) -> Optional[str]:
    """Calculate estimated time to completion.
    
    Args:
        state: PaginationState instance
        avg_time_per_page: Average time per page in seconds
        
    Returns:
        ETA string or None if cannot calculate
    """
    if state.total_pages:
        remaining_pages = state.total_pages - state.current_page
    elif state.max_pages:
        remaining_pages = state.max_pages - state.current_page
    else:
        return None
    
    if remaining_pages <= 0:
        return "Complete"
    
    eta_seconds = remaining_pages * avg_time_per_page
    
    if eta_seconds < 60:
        return f"{int(eta_seconds)}s"
    elif eta_seconds < 3600:
        return f"{int(eta_seconds / 60)}m"
    else:
        hours = int(eta_seconds / 3600)
        minutes = int((eta_seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
