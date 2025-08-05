"""Utilities for CrewAI Flow-based ecommerce scraping."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..schemas.standardized_product import StandardizedProduct

logger = logging.getLogger(__name__)


class FlowResultProcessor:
    """Process and format Flow results for compatibility with existing code."""
    
    @staticmethod
    def create_dynamic_scraping_result(flow_result: Dict[str, Any]) -> 'DynamicScrapingResult':
        """Convert Flow result to DynamicScrapingResult for backward compatibility."""
        from ..main import DynamicScrapingResult
        
        return DynamicScrapingResult(
            success=flow_result.get("success", False),
            products=flow_result.get("products", []),
            error=flow_result.get("error"),
            session_id=flow_result.get("session_id"),
            vendor=flow_result.get("vendor"),
            category=flow_result.get("category"),
            raw_crew_result=flow_result,
            statistics=flow_result.get("statistics", {})
        )
    
    @staticmethod
    def save_flow_results(
        flow_result: Dict[str, Any], 
        vendor: str, 
        category_name: str
    ) -> Optional[Path]:
        """Save Flow results to organized directory structure."""
        if not flow_result.get("success") or not flow_result.get("products"):
            logger.info("No products to save from Flow result")
            return None
        
        # Create directory structure: scrapped-result/vendor/category/
        base_dir = Path("scrapped-result")
        vendor_dir = base_dir / vendor.lower()
        
        # Clean category name for directory
        clean_category = (category_name.replace(" > ", "_")
                         .replace(" ", "_")
                         .replace(",", "")
                         .replace("&", "and"))
        category_dir = vendor_dir / clean_category
        
        # Create directories
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"products_flow_{timestamp}.json"
        filepath = category_dir / filename
        
        # Prepare data for saving
        products_data = {
            "scraping_info": {
                "vendor": vendor,
                "category": category_name,
                "scraped_at": datetime.now().isoformat(),
                "session_id": flow_result.get("session_id"),
                "total_products": len(flow_result["products"]),
                "success": flow_result["success"],
                "architecture": "crewai_flow",
                "statistics": flow_result.get("statistics", {})
            },
            "products": [
                product.model_dump() if hasattr(product, 'model_dump') 
                else product.to_dict() if hasattr(product, 'to_dict')
                else product
                for product in flow_result["products"]
            ]
        }
        
        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Flow results saved to: {filepath}")
            logger.info(f"Saved {len(flow_result['products'])} products")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save Flow results: {e}")
            return None


class FlowStateManager:
    """Manage Flow state and provide utilities for state inspection."""
    
    @staticmethod
    def get_flow_statistics(flow_state: Any) -> Dict[str, Any]:
        """Extract comprehensive statistics from Flow state."""
        try:
            return {
                "session_id": getattr(flow_state, 'id', 'unknown'),
                "vendor": getattr(flow_state, 'vendor', 'unknown'),
                "category": getattr(flow_state, 'category_name', 'unknown'),
                "pages_processed": getattr(flow_state, 'pages_processed', 0),
                "current_page": getattr(flow_state, 'current_page', 1),
                "max_pages": getattr(flow_state, 'max_pages', None),
                "total_products_found": getattr(flow_state, 'total_products_found', 0),
                "successful_extractions": getattr(flow_state, 'successful_extractions', 0),
                "failed_extractions": getattr(flow_state, 'failed_extractions', 0),
                "extraction_attempts": getattr(flow_state, 'extraction_attempts', 0),
                "max_extraction_attempts": getattr(flow_state, 'max_extraction_attempts', 3),
                "success": getattr(flow_state, 'success', False),
                "error_message": getattr(flow_state, 'error_message', None),
                "validation_feedback": getattr(flow_state, 'validation_feedback', None)
            }
        except Exception as e:
            logger.error(f"Failed to extract Flow statistics: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_flow_progress(flow_state: Any) -> Dict[str, Any]:
        """Get current progress information from Flow state."""
        try:
            pages_processed = getattr(flow_state, 'pages_processed', 0)
            max_pages = getattr(flow_state, 'max_pages', None)
            
            if max_pages:
                progress_percentage = (pages_processed / max_pages) * 100
            else:
                progress_percentage = None
            
            return {
                "current_page": getattr(flow_state, 'current_page', 1),
                "pages_processed": pages_processed,
                "max_pages": max_pages,
                "progress_percentage": progress_percentage,
                "products_found": getattr(flow_state, 'total_products_found', 0),
                "successful_extractions": getattr(flow_state, 'successful_extractions', 0),
                "failed_extractions": getattr(flow_state, 'failed_extractions', 0),
                "is_complete": getattr(flow_state, 'success', False)
            }
        except Exception as e:
            logger.error(f"Failed to get Flow progress: {e}")
            return {"error": str(e)}


class FlowDebugger:
    """Debug and inspect Flow execution."""
    
    @staticmethod
    def create_flow_plot(flow_instance, plot_name: str = "ecommerce_flow_plot"):
        """Create a visual plot of the Flow for debugging."""
        try:
            flow_instance.plot(plot_name)
            logger.info(f"Flow plot created: {plot_name}.html")
            return f"{plot_name}.html"
        except Exception as e:
            logger.error(f"Failed to create Flow plot: {e}")
            return None
    
    @staticmethod
    def log_flow_state(flow_state: Any, stage: str = "unknown"):
        """Log current Flow state for debugging."""
        try:
            stats = FlowStateManager.get_flow_statistics(flow_state)
            logger.info(f"Flow State at {stage}: {stats}")
        except Exception as e:
            logger.error(f"Failed to log Flow state: {e}")
    
    @staticmethod
    def validate_flow_state(flow_state: Any) -> Dict[str, Any]:
        """Validate Flow state and return validation results."""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check required fields
            required_fields = ['vendor', 'category_name', 'category_url']
            for field in required_fields:
                if not getattr(flow_state, field, None):
                    validation_results["errors"].append(f"Missing required field: {field}")
                    validation_results["valid"] = False
            
            # Check logical constraints
            current_page = getattr(flow_state, 'current_page', 1)
            max_pages = getattr(flow_state, 'max_pages', None)
            
            if current_page < 1:
                validation_results["errors"].append("current_page must be >= 1")
                validation_results["valid"] = False
            
            if max_pages is not None and current_page > max_pages:
                validation_results["warnings"].append(
                    f"current_page ({current_page}) exceeds max_pages ({max_pages})"
                )
            
            # Check extraction attempts
            extraction_attempts = getattr(flow_state, 'extraction_attempts', 0)
            max_attempts = getattr(flow_state, 'max_extraction_attempts', 3)
            
            if extraction_attempts > max_attempts:
                validation_results["warnings"].append(
                    f"extraction_attempts ({extraction_attempts}) exceeds max ({max_attempts})"
                )
            
        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Validation error: {str(e)}")
        
        return validation_results


class FlowPerformanceMonitor:
    """Monitor Flow performance and resource usage."""
    
    def __init__(self):
        self.start_time = None
        self.checkpoints = {}
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = datetime.now()
        self.checkpoints = {"start": self.start_time}
    
    def checkpoint(self, name: str):
        """Add a performance checkpoint."""
        if self.start_time:
            self.checkpoints[name] = datetime.now()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.start_time:
            return {"error": "Monitoring not started"}
        
        current_time = datetime.now()
        total_duration = (current_time - self.start_time).total_seconds()
        
        checkpoint_durations = {}
        prev_time = self.start_time
        
        for name, checkpoint_time in self.checkpoints.items():
            if name != "start":
                duration = (checkpoint_time - prev_time).total_seconds()
                checkpoint_durations[name] = duration
                prev_time = checkpoint_time
        
        return {
            "total_duration_seconds": total_duration,
            "start_time": self.start_time.isoformat(),
            "current_time": current_time.isoformat(),
            "checkpoint_durations": checkpoint_durations,
            "checkpoints": {
                name: time.isoformat() 
                for name, time in self.checkpoints.items()
            }
        }
