"""Advanced routing and conditional logic for CrewAI Flow-based ecommerce scraping."""

import logging
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class FlowAction(Enum):
    """Enumeration of possible Flow actions."""
    NAVIGATE = "navigate"
    EXTRACT = "extract"
    VALIDATE = "validate"
    RE_EXTRACT = "re_extract"
    NEXT_PAGE = "next_page"
    COMPLETE = "complete"
    ERROR = "handle_error"
    RETRY = "retry"
    SKIP_PAGE = "skip_page"


class ValidationResult(Enum):
    """Enumeration of validation results."""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    RETRY_NEEDED = "retry_needed"
    SKIP_RECOMMENDED = "skip_recommended"


class FlowRouter:
    """Advanced routing logic for ecommerce scraping flows."""
    
    def __init__(self, max_retries: int = 3, max_pages: Optional[int] = None):
        self.max_retries = max_retries
        self.max_pages = max_pages
        self.routing_rules = {}
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default routing rules."""
        self.routing_rules = {
            "validation_failed": self._handle_validation_failure,
            "pagination_check": self._handle_pagination,
            "error_recovery": self._handle_error_recovery,
            "completion_check": self._handle_completion
        }
    
    def route_after_validation(
        self, 
        flow_state: Any, 
        validation_result: Dict[str, Any]
    ) -> str:
        """
        Determine next action after validation based on complex routing logic.
        
        This replaces the simple @router logic with more sophisticated decision making.
        """
        try:
            # Parse validation result
            validation_status = self._parse_validation_status(validation_result)
            
            # Apply routing rules in order of priority
            if validation_status == ValidationResult.PASSED:
                return self._handle_successful_validation(flow_state)
            
            elif validation_status == ValidationResult.FAILED:
                return self._handle_validation_failure(flow_state, validation_result)
            
            elif validation_status == ValidationResult.PARTIAL:
                return self._handle_partial_validation(flow_state, validation_result)
            
            elif validation_status == ValidationResult.RETRY_NEEDED:
                return self._handle_retry_needed(flow_state, validation_result)
            
            elif validation_status == ValidationResult.SKIP_RECOMMENDED:
                return self._handle_skip_recommendation(flow_state, validation_result)
            
            else:
                logger.warning(f"Unknown validation status: {validation_status}")
                return FlowAction.ERROR.value
                
        except Exception as e:
            logger.error(f"Routing failed: {str(e)}")
            return FlowAction.ERROR.value
    
    def _parse_validation_status(self, validation_result: Dict[str, Any]) -> ValidationResult:
        """Parse validation result to determine status."""
        try:
            if validation_result.get("validation_passed", False):
                return ValidationResult.PASSED
            
            # Check for specific failure types
            error_type = validation_result.get("error_type", "").lower()
            confidence = validation_result.get("confidence", 0)
            
            if "network" in error_type or "timeout" in error_type:
                return ValidationResult.RETRY_NEEDED
            
            if "partial" in error_type or confidence > 0.5:
                return ValidationResult.PARTIAL
            
            if "skip" in error_type or "block" in error_type:
                return ValidationResult.SKIP_RECOMMENDED
            
            return ValidationResult.FAILED
            
        except Exception as e:
            logger.error(f"Failed to parse validation status: {e}")
            return ValidationResult.FAILED
    
    def _handle_successful_validation(self, flow_state: Any) -> str:
        """Handle successful validation - decide whether to continue or complete."""
        try:
            current_page = getattr(flow_state, 'current_page', 1)
            max_pages = getattr(flow_state, 'max_pages', self.max_pages)
            
            # Check if we should continue to next page
            if max_pages is None or current_page < max_pages:
                # Check if more pages are available (this would use NavigationAgent)
                if self._has_more_pages_available(flow_state):
                    return FlowAction.NEXT_PAGE.value
            
            return FlowAction.COMPLETE.value
            
        except Exception as e:
            logger.error(f"Failed to handle successful validation: {e}")
            return FlowAction.ERROR.value
    
    def _handle_validation_failure(
        self, 
        flow_state: Any, 
        validation_result: Dict[str, Any]
    ) -> str:
        """Handle validation failure with retry logic."""
        try:
            extraction_attempts = getattr(flow_state, 'extraction_attempts', 0)
            max_attempts = getattr(flow_state, 'max_extraction_attempts', self.max_retries)
            
            if extraction_attempts < max_attempts:
                # Store feedback for re-extraction
                feedback = validation_result.get("feedback", "Please improve extraction quality")
                setattr(flow_state, 'validation_feedback', feedback)
                
                return FlowAction.RE_EXTRACT.value
            else:
                # Max attempts reached - decide whether to skip or complete
                skip_on_failure = validation_result.get("skip_on_max_attempts", True)
                
                if skip_on_failure:
                    return self._handle_skip_page(flow_state)
                else:
                    return FlowAction.COMPLETE.value
                    
        except Exception as e:
            logger.error(f"Failed to handle validation failure: {e}")
            return FlowAction.ERROR.value
    
    def _handle_partial_validation(
        self, 
        flow_state: Any, 
        validation_result: Dict[str, Any]
    ) -> str:
        """Handle partial validation - some products valid, some not."""
        try:
            confidence = validation_result.get("confidence", 0)
            partial_threshold = validation_result.get("partial_threshold", 0.7)
            
            if confidence >= partial_threshold:
                # Accept partial results and continue
                return self._handle_successful_validation(flow_state)
            else:
                # Treat as failure and retry
                return self._handle_validation_failure(flow_state, validation_result)
                
        except Exception as e:
            logger.error(f"Failed to handle partial validation: {e}")
            return FlowAction.ERROR.value
    
    def _handle_retry_needed(
        self, 
        flow_state: Any, 
        validation_result: Dict[str, Any]
    ) -> str:
        """Handle cases where retry is needed (network issues, etc.)."""
        try:
            retry_attempts = getattr(flow_state, 'retry_attempts', 0)
            max_retries = validation_result.get("max_retries", 2)
            
            if retry_attempts < max_retries:
                setattr(flow_state, 'retry_attempts', retry_attempts + 1)
                return FlowAction.RETRY.value
            else:
                # Max retries reached - skip or fail
                return self._handle_skip_page(flow_state)
                
        except Exception as e:
            logger.error(f"Failed to handle retry: {e}")
            return FlowAction.ERROR.value
    
    def _handle_skip_recommendation(
        self, 
        flow_state: Any, 
        validation_result: Dict[str, Any]
    ) -> str:
        """Handle cases where skipping is recommended."""
        try:
            skip_reason = validation_result.get("skip_reason", "Unknown")
            logger.info(f"Skipping page due to: {skip_reason}")
            
            return self._handle_skip_page(flow_state)
            
        except Exception as e:
            logger.error(f"Failed to handle skip recommendation: {e}")
            return FlowAction.ERROR.value
    
    def _handle_skip_page(self, flow_state: Any) -> str:
        """Skip current page and move to next or complete."""
        try:
            current_page = getattr(flow_state, 'current_page', 1)
            max_pages = getattr(flow_state, 'max_pages', self.max_pages)
            
            # Reset attempts for next page
            setattr(flow_state, 'extraction_attempts', 0)
            setattr(flow_state, 'retry_attempts', 0)
            
            # Check if we can move to next page
            if max_pages is None or current_page < max_pages:
                if self._has_more_pages_available(flow_state):
                    return FlowAction.NEXT_PAGE.value
            
            return FlowAction.COMPLETE.value
            
        except Exception as e:
            logger.error(f"Failed to handle page skip: {e}")
            return FlowAction.ERROR.value
    
    def _has_more_pages_available(self, flow_state: Any) -> bool:
        """Check if more pages are available for processing."""
        try:
            # This would integrate with NavigationAgent to check pagination
            # For now, return True if we haven't hit the limit
            current_page = getattr(flow_state, 'current_page', 1)
            max_pages = getattr(flow_state, 'max_pages', self.max_pages)
            
            if max_pages is None:
                return True  # Assume more pages available
            
            return current_page < max_pages
            
        except Exception as e:
            logger.error(f"Failed to check for more pages: {e}")
            return False
    
    def add_custom_rule(self, rule_name: str, rule_function: Callable):
        """Add a custom routing rule."""
        self.routing_rules[rule_name] = rule_function
    
    def apply_custom_rule(
        self, 
        rule_name: str, 
        flow_state: Any, 
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Apply a custom routing rule."""
        try:
            if rule_name in self.routing_rules:
                return self.routing_rules[rule_name](flow_state, context)
            else:
                logger.warning(f"Unknown routing rule: {rule_name}")
                return None
        except Exception as e:
            logger.error(f"Failed to apply custom rule {rule_name}: {e}")
            return None

    def _handle_pagination(self, flow_state: Any) -> str:
        """Handle pagination logic."""
        try:
            current_page = getattr(flow_state, 'current_page', 1)
            max_pages = getattr(flow_state, 'max_pages', self.max_pages)

            if max_pages and current_page >= max_pages:
                return FlowAction.COMPLETE.value
            else:
                return FlowAction.NEXT_PAGE.value

        except Exception as e:
            logger.error(f"Failed to handle pagination: {e}")
            return FlowAction.ERROR.value

    def _handle_error_recovery(self, flow_state: Any, error: str = None) -> str:
        """Handle error recovery logic."""
        try:
            extraction_attempts = getattr(flow_state, 'extraction_attempts', 0)

            if extraction_attempts < self.max_retries:
                return FlowAction.RETRY.value
            else:
                return FlowAction.SKIP_PAGE.value

        except Exception as e:
            logger.error(f"Failed to handle error recovery: {e}")
            return FlowAction.ERROR.value

    def _handle_completion(self, flow_state: Any) -> str:
        """Handle completion logic."""
        try:
            # Check if we have any products or if we should complete
            products = getattr(flow_state, 'products', [])
            current_page = getattr(flow_state, 'current_page', 1)
            max_pages = getattr(flow_state, 'max_pages', self.max_pages)

            if max_pages and current_page >= max_pages:
                return FlowAction.COMPLETE.value
            elif len(products) > 0:
                return FlowAction.COMPLETE.value
            else:
                return FlowAction.NEXT_PAGE.value

        except Exception as e:
            logger.error(f"Failed to handle completion: {e}")
            return FlowAction.COMPLETE.value


class ConditionalFlowLogic:
    """Implement complex conditional logic for Flow routing."""
    
    @staticmethod
    def should_continue_extraction(
        flow_state: Any, 
        extraction_result: Dict[str, Any]
    ) -> bool:
        """Determine if extraction should continue based on results."""
        try:
            products_found = len(extraction_result.get("extracted_products", []))
            min_products_threshold = getattr(flow_state, 'min_products_per_page', 1)
            
            return products_found >= min_products_threshold
            
        except Exception as e:
            logger.error(f"Failed to check extraction continuation: {e}")
            return False
    
    @staticmethod
    def should_apply_feedback(
        flow_state: Any, 
        validation_result: Dict[str, Any]
    ) -> bool:
        """Determine if validation feedback should be applied."""
        try:
            feedback_quality = validation_result.get("feedback_quality", 0)
            feedback_threshold = getattr(flow_state, 'feedback_threshold', 0.5)
            
            return feedback_quality >= feedback_threshold
            
        except Exception as e:
            logger.error(f"Failed to check feedback application: {e}")
            return False
    
    @staticmethod
    def calculate_success_rate(flow_state: Any) -> float:
        """Calculate current success rate for decision making."""
        try:
            successful = getattr(flow_state, 'successful_extractions', 0)
            failed = getattr(flow_state, 'failed_extractions', 0)
            total = successful + failed
            
            if total == 0:
                return 1.0  # No attempts yet, assume success
            
            return successful / total
            
        except Exception as e:
            logger.error(f"Failed to calculate success rate: {e}")
            return 0.0


