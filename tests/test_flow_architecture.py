"""Tests specifically for the CrewAI Flow architecture implementation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ecommerce_scraper.workflows.ecommerce_flow import EcommerceScrapingFlow, EcommerceScrapingState
from ecommerce_scraper.workflows.flow_utils import FlowResultProcessor, FlowStateManager, FlowPerformanceMonitor
from ecommerce_scraper.workflows.flow_routing import FlowRouter, FlowAction, ValidationResult
from ecommerce_scraper.main import EcommerceScraper


class TestFlowArchitecture:
    """Test suite for CrewAI Flow architecture components."""

    def test_flow_state_creation(self):
        """Test EcommerceScrapingState creation and validation."""
        state = EcommerceScrapingState(
            category_url="https://test.com/category",
            vendor="test_vendor",
            category_name="test_category",
            max_pages=5
        )
        
        assert state.category_url == "https://test.com/category"
        assert state.vendor == "test_vendor"
        assert state.category_name == "test_category"
        assert state.max_pages == 5
        assert state.current_page == 1
        assert state.products == []
        assert state.extraction_attempts == 0
        assert state.success is False

    def test_flow_state_manager(self):
        """Test FlowStateManager utilities."""
        state = EcommerceScrapingState(
            category_url="https://test.com/category",
            vendor="test_vendor",
            category_name="test_category"
        )
        
        # Test statistics extraction
        stats = FlowStateManager.get_flow_statistics(state)
        assert "vendor" in stats
        assert "category" in stats
        assert stats["pages_processed"] == 0
        assert stats["current_page"] == 1
        
        # Test progress extraction
        progress = FlowStateManager.get_flow_progress(state)
        assert "current_page" in progress
        assert "pages_processed" in progress
        assert progress["products_found"] == 0

    def test_flow_router_initialization(self):
        """Test FlowRouter initialization and configuration."""
        router = FlowRouter(max_retries=5, max_pages=10)
        
        assert router.max_retries == 5
        assert router.max_pages == 10
        assert "extraction_failed" in router.routing_rules
        assert "validation_failed" in router.routing_rules

    def test_flow_router_successful_validation(self):
        """Test FlowRouter handling of successful validation."""
        router = FlowRouter(max_retries=3, max_pages=5)
        
        # Mock state
        mock_state = Mock()
        mock_state.current_page = 2
        mock_state.max_pages = 5
        
        validation_result = {"validation_passed": True}
        
        # Should route to next page since we're not at max pages
        next_action = router.route_after_validation(mock_state, validation_result)
        assert next_action in [FlowAction.NEXT_PAGE.value, FlowAction.COMPLETE.value]

    def test_flow_router_failed_validation(self):
        """Test FlowRouter handling of failed validation."""
        router = FlowRouter(max_retries=3, max_pages=5)
        
        # Mock state with no previous attempts
        mock_state = Mock()
        mock_state.extraction_attempts = 0
        mock_state.max_extraction_attempts = 3
        
        validation_result = {
            "validation_passed": False,
            "feedback": "Improve data quality"
        }
        
        # Should route to re-extraction
        next_action = router.route_after_validation(mock_state, validation_result)
        assert next_action == FlowAction.RE_EXTRACT.value

    def test_flow_performance_monitor(self):
        """Test FlowPerformanceMonitor functionality."""
        monitor = FlowPerformanceMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.start_time is not None
        
        # Add checkpoint
        monitor.checkpoint("test_checkpoint")
        assert "test_checkpoint" in monitor.checkpoints
        
        # Get summary
        summary = monitor.get_performance_summary()
        assert "total_duration_seconds" in summary
        assert "start_time" in summary
        assert "checkpoints" in summary

    def test_flow_result_processor(self):
        """Test FlowResultProcessor utilities."""
        # Mock flow result
        flow_result = {
            "success": True,
            "products": [{"name": "Test Product", "price": "10.00"}],
            "session_id": "test_session",
            "vendor": "test_vendor",
            "category": "test_category",
            "statistics": {"total_pages_processed": 2}
        }
        
        # Convert to DynamicScrapingResult
        result = FlowResultProcessor.create_dynamic_scraping_result(flow_result)
        
        assert result.success is True
        assert len(result.products) == 1
        assert result.session_id == "test_session"
        assert result.vendor == "test_vendor"
        assert result.category == "test_category"

    @patch('ecommerce_scraper.workflows.ecommerce_flow.EcommerceScrapingFlow.kickoff')
    def test_ecommerce_scraper_flow_integration(self, mock_kickoff):
        """Test EcommerceScraper integration with Flow architecture."""
        # Mock successful flow result
        mock_kickoff.return_value = {
            "success": True,
            "products": [{"name": "Test Product", "price": "10.00"}],
            "session_id": "test_session",
            "vendor": "test_vendor",
            "category": "test_category"
        }
        
        scraper = EcommerceScraper(verbose=False)
        
        # Test architecture info
        info = scraper.get_architecture_info()
        assert info["architecture_type"] == "crewai_flow"
        assert "flow_router" in info["components"]
        
        # Test scraping method
        result = scraper.scrape_category(
            category_url="https://test.com/category",
            vendor="test_vendor",
            category_name="test_category",
            max_pages=2
        )
        
        assert result.success is True
        assert len(result.products) == 1
        mock_kickoff.assert_called_once()

    def test_flow_plot_creation(self):
        """Test Flow plot creation functionality."""
        scraper = EcommerceScraper(verbose=False)
        
        # Test plot creation
        plot_file = scraper.create_flow_plot("test_plot")
        assert plot_file == "test_plot.html"

    def test_flow_session_statistics(self):
        """Test Flow session statistics when no active flow."""
        scraper = EcommerceScraper(verbose=False)
        
        # Should return message when no active flow
        stats = scraper.get_session_statistics()
        assert "No active Flow session" in stats["status"]
        assert stats["architecture"] == "crewai_flow"

    def test_flow_performance_metrics(self):
        """Test Flow performance metrics."""
        scraper = EcommerceScraper(verbose=False)
        
        # Should return performance monitor summary
        metrics = scraper.get_performance_metrics()
        # Empty metrics when no monitoring started
        assert isinstance(metrics, dict)

    def test_flow_cleanup(self):
        """Test Flow cleanup functionality."""
        scraper = EcommerceScraper(verbose=False)
        
        # Mock active flow
        mock_flow = Mock()
        scraper._current_flow = mock_flow
        
        # Test cleanup
        scraper.cleanup()
        
        # Flow cleanup should have been called
        mock_flow.cleanup.assert_called_once()
        assert scraper._current_flow is None

    def test_flow_context_manager(self):
        """Test Flow-based scraper as context manager."""
        with EcommerceScraper(verbose=False) as scraper:
            assert scraper is not None
            assert hasattr(scraper, 'flow_router')
            assert hasattr(scraper, 'performance_monitor')
        
        # Cleanup should have been called automatically

    def test_validation_result_enum(self):
        """Test ValidationResult enum values."""
        assert ValidationResult.PASSED.value == "passed"
        assert ValidationResult.FAILED.value == "failed"
        assert ValidationResult.PARTIAL.value == "partial"
        assert ValidationResult.RETRY_NEEDED.value == "retry_needed"
        assert ValidationResult.SKIP_RECOMMENDED.value == "skip_recommended"

    def test_flow_action_enum(self):
        """Test FlowAction enum values."""
        assert FlowAction.NAVIGATE.value == "navigate"
        assert FlowAction.EXTRACT.value == "extract"
        assert FlowAction.VALIDATE.value == "validate"
        assert FlowAction.RE_EXTRACT.value == "re_extract"
        assert FlowAction.NEXT_PAGE.value == "next_page"
        assert FlowAction.COMPLETE.value == "complete"
        assert FlowAction.ERROR.value == "handle_error"

    def test_flow_state_validation(self):
        """Test Flow state validation utilities."""
        from ecommerce_scraper.workflows.flow_utils import FlowDebugger
        
        # Valid state
        valid_state = EcommerceScrapingState(
            category_url="https://test.com/category",
            vendor="test_vendor",
            category_name="test_category"
        )
        
        validation = FlowDebugger.validate_flow_state(valid_state)
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        
        # Invalid state (missing required fields)
        invalid_state = EcommerceScrapingState()
        
        validation = FlowDebugger.validate_flow_state(invalid_state)
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
