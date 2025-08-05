"""Integration tests for the CrewAI Flow-based workflow."""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ecommerce_scraper.workflows.ecommerce_flow import EcommerceScrapingFlow, EcommerceScrapingState
from ecommerce_scraper.workflows.flow_utils import FlowResultProcessor, FlowStateManager
from ecommerce_scraper.workflows.flow_routing import FlowRouter


class TestFlowWorkflowIntegration:
    """Integration tests for the complete CrewAI Flow workflow."""

    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_crew_results(self):
        """Mock CrewAI results for different workflow steps."""
        return {
            "navigation": Mock(raw='{"status": "page_ready", "page_info": {"products_visible": 24}}'),
            "extraction": Mock(raw='{"extraction_batch": [{"name": "Test Product", "description": "Test", "price": {"amount": 10.99, "currency": "GBP"}, "image_url": "https://test.com/img.jpg", "category": "test", "vendor": "test", "scraped_at": "2025-01-04T12:00:00Z"}], "extraction_metadata": {"products_found": 1}}'),
            "validation": Mock(raw='{"validation_complete": true, "products_saved": 1, "products_failed": 0, "feedback_required": false}'),
            "pagination": Mock(raw='{"status": "no_more_pages", "pagination_info": {"has_more_pages": false}}')
        }

    @patch('ecommerce_scraper.workflows.cyclical_processor.Crew')
    def test_single_page_workflow(self, mock_crew_class, mock_crew_results, temp_directory):
        """Test complete workflow for a single page."""
        # Setup mock crew instances
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        # Configure crew to return different results based on call order
        call_count = 0
        def mock_kickoff():
            nonlocal call_count
            results = [
                mock_crew_results["navigation"],
                mock_crew_results["extraction"], 
                mock_crew_results["validation"],
                mock_crew_results["pagination"]
            ]
            result = results[call_count % len(results)]
            call_count += 1
            return result
        
        mock_crew_instance.kickoff.side_effect = mock_kickoff

        # Initialize processor
        processor = CyclicalProcessor(verbose=False, session_id="test_integration")
        
        # Execute workflow
        result = processor.process_category(
            vendor="test_vendor",
            category="test_category", 
            category_url="https://test.com/category",
            max_pages=1
        )
        
        # Verify results
        assert result["success"] is True
        assert result["vendor"] == "test_vendor"
        assert result["category"] == "test_category"
        assert result["pages_processed"] == 1
        
        # Verify crew was called for each step
        assert mock_crew_instance.kickoff.call_count >= 4  # Navigation, Extraction, Validation, Pagination

    @patch('ecommerce_scraper.workflows.cyclical_processor.Crew')
    def test_multi_page_workflow(self, mock_crew_class, mock_crew_results, temp_directory):
        """Test workflow with multiple pages."""
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        # Configure pagination to return more pages initially, then stop
        call_count = 0
        def mock_kickoff():
            nonlocal call_count
            step = call_count % 4  # 4 steps per page cycle
            
            if step == 0:  # Navigation
                result = mock_crew_results["navigation"]
            elif step == 1:  # Extraction
                result = mock_crew_results["extraction"]
            elif step == 2:  # Validation
                result = mock_crew_results["validation"]
            else:  # Pagination
                page_num = call_count // 4 + 1
                if page_num < 3:  # First 2 pages have more content
                    result = Mock(raw='{"status": "next_page_ready", "pagination_info": {"has_more_pages": true}}')
                else:  # Last page
                    result = mock_crew_results["pagination"]
            
            call_count += 1
            return result
        
        mock_crew_instance.kickoff.side_effect = mock_kickoff

        processor = CyclicalProcessor(verbose=False, session_id="test_multi_page")
        
        result = processor.process_category(
            vendor="test_vendor",
            category="test_category",
            category_url="https://test.com/category",
            max_pages=3
        )
        
        assert result["success"] is True
        assert result["pages_processed"] == 3

    @patch('ecommerce_scraper.workflows.cyclical_processor.Crew')
    def test_workflow_with_feedback_loop(self, mock_crew_class, mock_crew_results, temp_directory):
        """Test workflow with validation feedback and re-extraction."""
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        call_count = 0
        def mock_kickoff():
            nonlocal call_count
            step_type = call_count % 6  # Extended cycle with feedback
            
            if step_type == 0:  # Navigation
                result = mock_crew_results["navigation"]
            elif step_type == 1:  # Initial extraction
                result = mock_crew_results["extraction"]
            elif step_type == 2:  # Validation (fails first time)
                result = Mock(raw='{"validation_complete": false, "products_saved": 0, "products_failed": 1, "feedback_required": true, "feedback_data": {"issues": ["Missing description"], "suggestions": ["Look for product details"], "retry_count": 1, "max_retries": 3}}')
            elif step_type == 3:  # Re-extraction
                result = Mock(raw='{"extraction_batch": [{"name": "Test Product", "description": "Improved description", "price": {"amount": 10.99, "currency": "GBP"}, "image_url": "https://test.com/img.jpg", "category": "test", "vendor": "test", "scraped_at": "2025-01-04T12:00:00Z"}], "extraction_metadata": {"products_found": 1, "retry_count": 1}}')
            elif step_type == 4:  # Validation (succeeds)
                result = mock_crew_results["validation"]
            else:  # Pagination
                result = mock_crew_results["pagination"]
            
            call_count += 1
            return result
        
        mock_crew_instance.kickoff.side_effect = mock_kickoff

        processor = CyclicalProcessor(verbose=False, session_id="test_feedback")
        
        result = processor.process_category(
            vendor="test_vendor",
            category="test_category",
            category_url="https://test.com/category",
            max_pages=1
        )
        
        assert result["success"] is True
        # Should have more calls due to re-extraction
        assert mock_crew_instance.kickoff.call_count >= 6

    def test_json_storage_integration(self, temp_directory):
        """Test integration between workflow and JSON storage."""
        json_manager = JSONManager(base_directory=temp_directory)
        
        # Create session file
        session_file = json_manager.create_session_file(
            vendor="integration_vendor",
            category="integration_category",
            session_id="integration_test",
            category_url="https://test.com/integration"
        )
        
        # Simulate multiple page updates
        for page in range(1, 4):
            products = [
                {
                    "name": f"Product {page}-{i}",
                    "description": f"Description for product {page}-{i}",
                    "price": {"amount": 10.99 + i, "currency": "GBP"},
                    "image_url": f"https://test.com/img{page}-{i}.jpg",
                    "category": "integration_category",
                    "vendor": "integration_vendor",
                    "scraped_at": datetime.now().isoformat()
                }
                for i in range(1, 6)  # 5 products per page
            ]
            
            update_result = json_manager.update_session_products(
                filepath=session_file,
                new_products=products,
                page_number=page,
                validation_info={"products_saved": len(products), "products_failed": 0}
            )
            
            assert update_result["success"] is True
        
        # Verify final state
        session_data = json_manager.load_session_data(session_file)
        assert len(session_data["products"]) == 15  # 3 pages × 5 products
        assert session_data["session_statistics"]["pages_processed"] == 3

    def test_progress_tracking_integration(self):
        """Test integration between workflow and progress tracking."""
        tracker = EnhancedProgressTracker()
        
        # Start session
        session = tracker.start_session("integration_session", "test_vendor", "test_category")
        
        # Simulate multi-page processing
        for page_num in range(1, 4):
            # Start page
            page = tracker.start_page("integration_session", page_num)
            
            # Simulate workflow steps
            tracker.update_page_status("integration_session", page_num, "navigation")
            tracker.update_page_status("integration_session", page_num, "extraction", products_found=10)
            tracker.update_page_status("integration_session", page_num, "validation", products_validated=9)
            tracker.update_page_status("integration_session", page_num, "complete")
        
        # Complete session
        tracker.complete_session("integration_session", success=True)
        
        # Verify session statistics
        stats = tracker.get_session_stats("integration_session")
        assert stats["pages_processed"] == 3
        assert stats["total_products"] == 30  # 3 pages × 10 products
        assert stats["total_validated"] == 27  # 3 pages × 9 validated

    @patch('ecommerce_scraper.workflows.cyclical_processor.Crew')
    def test_error_handling_integration(self, mock_crew_class):
        """Test error handling throughout the workflow."""
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        # Simulate navigation failure
        mock_crew_instance.kickoff.side_effect = Exception("Navigation failed")
        
        processor = CyclicalProcessor(verbose=False, session_id="test_error")
        
        result = processor.process_category(
            vendor="test_vendor",
            category="test_category",
            category_url="https://test.com/category",
            max_pages=1
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Navigation failed" in result["error"]

    def test_performance_monitoring_integration(self):
        """Test integration with performance monitoring."""
        from ecommerce_scraper.monitoring.performance_metrics import PerformanceMetrics
        
        metrics = PerformanceMetrics(enable_auto_collection=False)
        
        # Add custom metrics for workflow tracking
        metrics.add_custom_metric("pages_processed", lambda: 3)
        metrics.add_custom_metric("products_extracted", lambda: 25)
        
        # Get snapshot
        snapshot = metrics.get_current_snapshot()
        assert "pages_processed" in snapshot.custom_metrics
        assert "products_extracted" in snapshot.custom_metrics
        assert snapshot.custom_metrics["pages_processed"] == 3
        assert snapshot.custom_metrics["products_extracted"] == 25
        
        # Get performance window
        window = metrics.get_performance_window(duration_minutes=1)
        assert window is not None

    def test_backup_integration(self, temp_directory):
        """Test backup integration with workflow."""
        from ecommerce_scraper.storage.backup_manager import BackupManager
        
        json_manager = JSONManager(base_directory=temp_directory)
        backup_manager = BackupManager(base_directory=temp_directory)
        
        # Create and populate session file
        session_file = json_manager.create_session_file(
            vendor="backup_test",
            category="backup_category",
            session_id="backup_session",
            category_url="https://test.com/backup"
        )
        
        # Create backup
        backup_path = backup_manager.create_backup(session_file, backup_type="integration_test")
        
        # Verify backup exists and is valid
        assert backup_manager.verify_backup_integrity(backup_path)["valid"] is True
        
        # List backups
        backups = backup_manager.list_backups("backup_test*")
        assert len(backups) >= 1
        assert any("integration_test" in backup["backup_type"] for backup in backups)
