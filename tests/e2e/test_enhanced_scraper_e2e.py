"""End-to-end tests for the CrewAI Flow-based scraper architecture."""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from ecommerce_scraper.main import EcommerceScraper
from ecommerce_scraper.workflows.ecommerce_flow import EcommerceScrapingFlow


class TestFlowScraperE2E:
    """End-to-end tests for the complete enhanced scraper system."""

    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_complete_workflow(self):
        """Mock a complete successful workflow."""
        def mock_process_category(*args, **kwargs):
            return {
                "success": True,
                "vendor": "test_vendor",
                "category": "test_category",
                "category_url": "https://test.com/category",
                "session_id": "test_session",
                "pages_processed": 2,
                "total_products": 15,
                "error": None,
                "session_stats": {
                    "total_pages_processed": 2,
                    "total_products_extracted": 15,
                    "total_products_validated": 14,
                    "validation_success_rate": 93.3
                }
            }
        return mock_process_category

    @pytest.fixture
    def sample_session_data(self):
        """Sample session data for testing."""
        return {
            "scraping_session": {
                "session_id": "test_session_e2e",
                "vendor": "test_vendor",
                "category": "test_category",
                "category_url": "https://test.com/category",
                "started_at": "2025-01-04T12:00:00Z",
                "status": "completed"
            },
            "products": [
                {
                    "name": "E2E Test Product 1",
                    "description": "End-to-end test product description",
                    "price": {"amount": 19.99, "currency": "GBP"},
                    "image_url": "https://test.com/e2e-product1.jpg",
                    "category": "test_category",
                    "vendor": "test_vendor",
                    "scraped_at": "2025-01-04T12:05:00Z"
                },
                {
                    "name": "E2E Test Product 2",
                    "description": "Another test product for e2e testing",
                    "price": {"amount": 24.99, "currency": "GBP"},
                    "image_url": "https://test.com/e2e-product2.jpg",
                    "category": "test_category",
                    "vendor": "test_vendor",
                    "scraped_at": "2025-01-04T12:06:00Z"
                }
            ],
            "session_statistics": {
                "total_products_found": 2,
                "total_products_validated": 2,
                "validation_success_rate": 100.0,
                "pages_processed": 1
            }
        }

    @patch('ecommerce_scraper.workflows.cyclical_processor.CyclicalProcessor.process_category')
    @patch('ecommerce_scraper.storage.json_manager.JSONManager.create_session_file')
    @patch('ecommerce_scraper.storage.json_manager.JSONManager.load_session_data')
    def test_complete_enhanced_scraping_workflow(self, 
                                               mock_load_session, 
                                               mock_create_session,
                                               mock_process_category,
                                               mock_complete_workflow,
                                               sample_session_data,
                                               temp_directory):
        """Test complete enhanced scraping workflow from start to finish."""
        
        # Setup mocks
        mock_process_category.side_effect = mock_complete_workflow
        mock_create_session.return_value = f"{temp_directory}/test_session.json"
        mock_load_session.return_value = sample_session_data

        # Initialize enhanced scraper
        with EcommerceScraper(
            verbose=False,
            session_id="e2e_test_session"
        ) as scraper:
            
            # Verify enhanced architecture is active
            arch_info = scraper.get_architecture_info()
            assert arch_info["architecture_type"] == "enhanced"
            assert arch_info["components"]["cyclical_processor"] is True
            assert arch_info["components"]["json_manager"] is True
            
            # Execute scraping
            result = scraper.scrape_category(
                category_url="https://test.com/e2e-category",
                vendor="test_vendor",
                category_name="test_category",
                max_pages=2
            )
            
            # Verify results
            assert result.success is True
            assert result.vendor == "test_vendor"
            assert result.category == "test_category"
            assert result.session_id == "e2e_test_session"
            assert len(result.products) == 2
            
            # Verify products are StandardizedProduct instances
            for product in result.products:
                assert hasattr(product, 'name')
                assert hasattr(product, 'description')
                assert hasattr(product, 'price')
                assert hasattr(product, 'image_url')
                assert product.vendor == "test_vendor"
                assert product.category == "test_category"

    def test_architecture_info(self):
        """Test architecture information retrieval."""

        scraper = EcommerceScraper(
            verbose=False,
            session_id="architecture_test"
        )

        info = scraper.get_architecture_info()

        # Verify enhanced architecture
        assert info["architecture_type"] == "enhanced"

        # Should have cyclical components
        assert "cyclical_processor" in info["components"]
        assert "json_manager" in info["components"]
        assert "enhanced_progress_tracker" in info["components"]

        # Cleanup
        scraper.cleanup()

    @patch('ecommerce_scraper.workflows.cyclical_processor.CyclicalProcessor.process_category')
    def test_error_handling_e2e(self, mock_process_category):
        """Test end-to-end error handling."""
        
        # Mock a failure in cyclical processing
        mock_process_category.side_effect = Exception("Simulated processing failure")
        
        with EcommerceScraper(
            verbose=False,
            session_id="error_test_session"
        ) as scraper:

            result = scraper.scrape_category(
                category_url="https://test.com/error-category",
                vendor="error_vendor",
                category_name="error_category"
            )
            
            # Verify error handling
            assert result.success is False
            assert result.error is not None
            assert "Simulated processing failure" in result.error
            assert result.vendor == "error_vendor"
            assert result.category == "error_category"

    def test_session_statistics_e2e(self):
        """Test session statistics collection end-to-end."""
        
        with EcommerceScraper(
            verbose=False,
            session_id="stats_test_session"
        ) as scraper:
            
            # Get initial statistics
            initial_stats = scraper.get_session_statistics()
            assert initial_stats["session_id"] == "stats_test_session"
            
            # Simulate some activity by starting session tracking
            scraper.enhanced_progress_tracker.start_session(
                "stats_test_session", "stats_vendor", "stats_category"
            )
            
            # Get updated statistics
            updated_stats = scraper.get_session_statistics()
            assert updated_stats["vendor"] == "stats_vendor"
            assert updated_stats["category"] == "stats_category"

    def test_performance_metrics_e2e(self):
        """Test performance metrics collection end-to-end."""
        
        with EcommerceScraper(
            verbose=False,
            session_id="perf_test_session"
        ) as scraper:
            
            # Get performance metrics
            metrics = scraper.get_performance_metrics()
            
            assert "current" in metrics
            assert "collection_info" in metrics
            assert "cpu_percent" in metrics["current"]
            assert "memory_mb" in metrics["current"]

    @patch('ecommerce_scraper.storage.json_manager.JSONManager.create_session_file')
    @patch('ecommerce_scraper.storage.backup_manager.BackupManager.create_backup')
    def test_storage_and_backup_e2e(self, mock_create_backup, mock_create_session, temp_directory):
        """Test storage and backup functionality end-to-end."""
        
        # Setup mocks
        session_file = f"{temp_directory}/storage_test_session.json"
        backup_file = f"{temp_directory}/backups/storage_test_backup.json"
        
        mock_create_session.return_value = session_file
        mock_create_backup.return_value = backup_file
        
        # Create actual session file for testing
        session_data = {
            "scraping_session": {"session_id": "storage_test"},
            "products": [],
            "session_statistics": {}
        }
        
        Path(session_file).parent.mkdir(parents=True, exist_ok=True)
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        with EcommerceScraper(
            verbose=False,
            session_id="storage_test_session"
        ) as scraper:
            
            # Test JSON manager functionality
            assert scraper.json_manager is not None
            
            # Test backup manager functionality
            assert scraper.backup_manager is not None
            
            # Verify session file creation was called
            mock_create_session.assert_called()

    def test_context_manager_cleanup_e2e(self):
        """Test context manager cleanup functionality."""
        
        scraper = EcommerceScraper(
            verbose=False,
            session_id="cleanup_test_session"
        )
        
        # Verify scraper is initialized
        assert scraper.performance_metrics is not None
        assert scraper.performance_metrics.collecting is True
        
        # Use context manager
        with scraper:
            # Verify scraper is still functional
            arch_info = scraper.get_architecture_info()
            assert arch_info["architecture_type"] == "enhanced"
        
        # After context exit, performance collection should be stopped
        # (This is handled in cleanup method)



    @patch('ecommerce_scraper.workflows.cyclical_processor.CyclicalProcessor.process_category')
    @patch('ecommerce_scraper.storage.json_manager.JSONManager.create_session_file')
    @patch('ecommerce_scraper.storage.json_manager.JSONManager.finalize_session')
    def test_complete_session_lifecycle_e2e(self, 
                                          mock_finalize,
                                          mock_create_session,
                                          mock_process_category,
                                          mock_complete_workflow,
                                          temp_directory):
        """Test complete session lifecycle from creation to finalization."""
        
        # Setup mocks
        session_file = f"{temp_directory}/lifecycle_session.json"
        mock_create_session.return_value = session_file
        mock_process_category.side_effect = mock_complete_workflow
        mock_finalize.return_value = {"success": True, "total_products": 15}
        
        with EcommerceScraper(
            verbose=False,
            session_id="lifecycle_test"
        ) as scraper:

            # Execute complete workflow
            result = scraper.scrape_category(
                category_url="https://test.com/lifecycle",
                vendor="lifecycle_vendor",
                category_name="lifecycle_category",
                max_pages=3
            )
            
            # Verify session lifecycle
            mock_create_session.assert_called_once()
            mock_process_category.assert_called_once()
            mock_finalize.assert_called_once()
            
            assert result.success is True
