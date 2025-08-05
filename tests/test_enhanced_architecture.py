"""Comprehensive test suite for the CrewAI Flow-based architecture."""

import pytest
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import Flow-based architecture components
from ecommerce_scraper.agents.navigation_agent import NavigationAgent
from ecommerce_scraper.agents.extraction_agent import ExtractionAgent
from ecommerce_scraper.agents.validation_agent import ValidationAgent
from ecommerce_scraper.workflows.ecommerce_flow import EcommerceScrapingFlow, EcommerceScrapingState
from ecommerce_scraper.workflows.flow_utils import FlowResultProcessor, FlowStateManager, FlowPerformanceMonitor
from ecommerce_scraper.workflows.flow_routing import FlowRouter
from ecommerce_scraper.main import EcommerceScraper


class TestFlowArchitecture:
    """Test suite for the CrewAI Flow-based architecture."""

    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_stagehand_tool(self):
        """Mock StagehandTool for testing."""
        mock_tool = Mock()
        mock_tool._run.return_value = "Mock response"
        return mock_tool

    @pytest.fixture
    def sample_products(self):
        """Sample product data for testing."""
        return [
            {
                "name": "Test Product 1",
                "description": "Test description 1",
                "price": {"amount": 10.99, "currency": "GBP"},
                "image_url": "https://example.com/image1.jpg",
                "category": "test_category",
                "vendor": "test_vendor",
                "scraped_at": datetime.now().isoformat()
            },
            {
                "name": "Test Product 2",
                "description": "Test description 2",
                "price": {"amount": 15.99, "currency": "GBP"},
                "image_url": "https://example.com/image2.jpg",
                "category": "test_category",
                "vendor": "test_vendor",
                "scraped_at": datetime.now().isoformat()
            }
        ]

    def test_navigation_agent_initialization(self, mock_stagehand_tool):
        """Test NavigationAgent initialization."""
        agent = NavigationAgent(tools=[mock_stagehand_tool])
        
        assert agent is not None
        assert hasattr(agent, 'agent')
        assert agent.get_agent() is not None

    def test_extraction_agent_initialization(self, mock_stagehand_tool):
        """Test ExtractionAgent initialization."""
        mock_price_extractor = Mock()
        mock_image_extractor = Mock()
        
        agent = ExtractionAgent(tools=[mock_stagehand_tool, mock_price_extractor, mock_image_extractor])
        
        assert agent is not None
        assert hasattr(agent, 'agent')
        assert agent.get_agent() is not None

    def test_validation_agent_initialization(self):
        """Test ValidationAgent initialization."""
        mock_validator = Mock()
        mock_price_extractor = Mock()
        
        agent = ValidationAgent(tools=[mock_validator, mock_price_extractor])
        
        assert agent is not None
        assert hasattr(agent, 'agent')
        assert agent.get_agent() is not None

    def test_cyclical_processor_initialization(self):
        """Test CyclicalProcessor initialization."""
        processor = CyclicalProcessor(verbose=False)
        
        assert processor is not None
        assert hasattr(processor, 'navigation_agent')
        assert hasattr(processor, 'extraction_agent')
        assert hasattr(processor, 'validation_agent')
        assert processor.session_stats is not None

    def test_json_manager_session_creation(self, temp_directory):
        """Test JSON manager session file creation."""
        json_manager = JSONManager(base_directory=temp_directory)
        
        session_file = json_manager.create_session_file(
            vendor="test_vendor",
            category="test_category",
            session_id="test_session_123",
            category_url="https://example.com/category"
        )
        
        assert Path(session_file).exists()
        
        # Verify file structure
        session_data = json_manager.load_session_data(session_file)
        assert session_data is not None
        assert "scraping_session" in session_data
        assert "products" in session_data
        assert "session_statistics" in session_data
        assert session_data["scraping_session"]["vendor"] == "test_vendor"
        assert session_data["scraping_session"]["category"] == "test_category"

    def test_json_manager_product_update(self, temp_directory, sample_products):
        """Test JSON manager product updates with deduplication."""
        json_manager = JSONManager(base_directory=temp_directory)
        
        # Create session file
        session_file = json_manager.create_session_file(
            vendor="test_vendor",
            category="test_category",
            session_id="test_session_123",
            category_url="https://example.com/category"
        )
        
        # Update with products
        update_result = json_manager.update_session_products(
            filepath=session_file,
            new_products=sample_products,
            page_number=1
        )
        
        assert update_result["success"] is True
        assert update_result["products_added"] == 2
        assert update_result["total_products"] == 2
        
        # Verify products were saved
        session_data = json_manager.load_session_data(session_file)
        assert len(session_data["products"]) == 2

    def test_backup_manager_creation(self, temp_directory, sample_products):
        """Test backup manager backup creation."""
        # Create a test file
        test_file = Path(temp_directory) / "test_session.json"
        test_data = {"products": sample_products}
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        backup_manager = BackupManager(base_directory=temp_directory)
        backup_path = backup_manager.create_backup(str(test_file), backup_type="test")
        
        assert Path(backup_path).exists()
        
        # Verify backup content
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        assert backup_data == test_data

    def test_enhanced_progress_tracker(self):
        """Test enhanced progress tracker functionality."""
        tracker = EnhancedProgressTracker()
        
        # Start session
        session = tracker.start_session("test_session", "test_vendor", "test_category")
        assert session.session_id == "test_session"
        assert session.vendor == "test_vendor"
        assert session.category == "test_category"
        
        # Start page
        page = tracker.start_page("test_session", 1)
        assert page.page_number == 1
        assert page.status == "navigation"
        
        # Update page status
        tracker.update_page_status("test_session", 1, "complete", products_validated=10)
        
        # Get session stats
        stats = tracker.get_session_stats("test_session")
        assert stats["session_id"] == "test_session"
        assert stats["total_validated"] == 10

    def test_performance_metrics(self):
        """Test performance metrics collection."""
        metrics = PerformanceMetrics(enable_auto_collection=False)
        
        # Get current snapshot
        snapshot = metrics.get_current_snapshot()
        assert snapshot is not None
        assert hasattr(snapshot, 'cpu_percent')
        assert hasattr(snapshot, 'memory_mb')
        assert hasattr(snapshot, 'timestamp')
        
        # Add custom metric
        metrics.add_custom_metric("test_metric", lambda: 42)
        
        # Record custom value
        metrics.record_custom_value("custom_value", 100)
        
        # Get performance summary
        summary = metrics.get_performance_summary()
        assert "current" in summary
        assert "collection_info" in summary

    def test_message_protocol(self):
        """Test message protocol functionality."""
        # Create page ready message
        page_ready = MessageProtocol.create_page_ready_message(
            session_id="test_session",
            page_info={"current_page": 1, "products_visible": 24},
            status="page_ready"
        )
        
        assert page_ready.message_type == MessageType.PAGE_READY
        assert page_ready.session_id == "test_session"
        assert page_ready.page_info["current_page"] == 1
        
        # Serialize and parse message
        serialized = MessageProtocol.serialize_message(page_ready)
        parsed = MessageProtocol.parse_message(serialized)
        
        assert parsed.message_type == MessageType.PAGE_READY
        assert parsed.session_id == "test_session"

    def test_feedback_analyzer(self, sample_products):
        """Test feedback analyzer functionality."""
        # Create products with validation issues
        problematic_products = [
            {"name": "Product 1", "price": {"amount": 10.99}},  # Missing description
            {"name": "", "description": "Desc", "price": {"amount": 15.99}},  # Empty name
            {"name": "Product 3", "description": "Desc"}  # Missing price
        ]
        
        analysis = FeedbackAnalyzer.analyze_validation_failures(
            products=problematic_products,
            validation_errors=["Missing required fields"]
        )
        
        assert analysis["total_products"] == 3
        assert analysis["failed_products"] > 0
        assert "missing_fields" in analysis
        
        # Generate suggestions
        suggestions = FeedbackAnalyzer.generate_improvement_suggestions(
            analysis, "test_vendor", "test_category"
        )
        
        assert len(suggestions) > 0
        assert any("description" in s.lower() for s in suggestions)

    def test_feedback_coordinator(self, sample_products):
        """Test feedback coordinator functionality."""
        coordinator = FeedbackCoordinator()
        
        # Test feedback requirement decision
        validation_result = {
            "products_saved": 2,
            "products_failed": 8,  # High failure rate
            "validation_errors": ["Missing fields"]
        }
        
        should_feedback = coordinator.should_request_feedback(validation_result)
        assert should_feedback is True
        
        # Generate feedback request
        feedback_message = coordinator.generate_feedback_request(
            session_id="test_session",
            validation_result=validation_result,
            products=sample_products,
            vendor="test_vendor",
            category="test_category"
        )
        
        assert feedback_message.message_type == MessageType.FEEDBACK_REQUEST
        assert feedback_message.session_id == "test_session"
        assert len(feedback_message.feedback["issues"]) > 0

    def test_flow_scraper_initialization(self):
        """Test Flow-based scraper initialization."""
        scraper = EcommerceScraper(verbose=False)

        assert hasattr(scraper, 'flow_router')
        assert hasattr(scraper, 'performance_monitor')
        assert scraper._current_flow is None  # No active flow initially

    def test_architecture_info(self):
        """Test architecture information retrieval."""
        scraper = EcommerceScraper(verbose=False)

        info = scraper.get_architecture_info()
        assert info["architecture_type"] == "crewai_flow"
        assert "flow_router" in info["components"]
        assert "automatic_routing" in info["features"]
        assert info["features"]["state_management"] == "Automatic with Pydantic + SQLite"

    def test_context_manager(self):
        """Test scraper context manager functionality."""
        with EcommerceScraper(verbose=False) as scraper:
            assert scraper is not None
            assert hasattr(scraper, 'cleanup')

        # Cleanup should have been called automatically

    def test_flow_plot_creation(self):
        """Test Flow plot creation for debugging."""
        scraper = EcommerceScraper(verbose=False)

        plot_file = scraper.create_flow_plot("test_flow_plot")
        assert plot_file == "test_flow_plot.html"

    def test_flow_state_management(self):
        """Test Flow state management utilities."""
        # Test state creation
        state = EcommerceScrapingState(
            category_url="https://test.com/category",
            vendor="test_vendor",
            category_name="test_category",
            max_pages=5
        )

        assert state.category_url == "https://test.com/category"
        assert state.vendor == "test_vendor"
        assert state.current_page == 1
        assert state.products == []

        # Test state statistics
        stats = FlowStateManager.get_flow_statistics(state)
        assert "vendor" in stats
        assert "category" in stats
        assert stats["pages_processed"] == 0

    def test_flow_router(self):
        """Test Flow routing logic."""
        router = FlowRouter(max_retries=3, max_pages=10)

        # Test successful validation routing
        mock_state = Mock()
        mock_state.current_page = 1
        mock_state.max_pages = 5
        mock_state.extraction_attempts = 0

        validation_result = {"validation_passed": True}
        next_action = router.route_after_validation(mock_state, validation_result)

        # Should continue to next page or complete
        assert next_action in ["next_page", "complete"]
