#!/usr/bin/env python3
"""
Test suite for Enhanced Agent Workflows (Phase 2 completion).

This test validates that all agents have been successfully enhanced with:
- Multi-vendor support
- State management integration
- Progress tracking capabilities
- StandardizedProduct schema compliance
- Batch processing integration
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from ecommerce_scraper.agents.product_scraper import ProductScraperAgent
from ecommerce_scraper.agents.site_navigator import SiteNavigatorAgent
from ecommerce_scraper.agents.data_extractor import DataExtractorAgent
from ecommerce_scraper.agents.data_validator import DataValidatorAgent
from ecommerce_scraper.state.state_manager import StateManager
from ecommerce_scraper.progress.progress_tracker import ProgressTracker
from ecommerce_scraper.main import EcommerceScraper


class TestEnhancedAgentWorkflows:
    """Test suite for enhanced agent workflows."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.state_manager = StateManager()
        self.progress_tracker = ProgressTracker(self.state_manager)
        # Use empty tools list to avoid validation issues
        self.mock_tools = []
        self.mock_llm = Mock()
    
    def test_enhanced_product_scraper_agent(self):
        """Test ProductScraperAgent with enhanced capabilities."""
        print("Testing Enhanced ProductScraperAgent...")

        # Test agent initialization with enhanced components (without LLM to avoid validation issues)
        agent = ProductScraperAgent(
            tools=self.mock_tools,
            llm=None,  # Skip LLM to avoid CrewAI validation issues in tests
            state_manager=self.state_manager,
            progress_tracker=self.progress_tracker
        )

        # Verify enhanced components are stored
        assert agent.state_manager is not None
        assert agent.progress_tracker is not None
        assert agent.get_agent() is not None

        # Test multi-vendor scraping task creation
        task = agent.create_multi_vendor_scraping_task(
            vendor="asda",
            category="bread",
            session_id="test_session_123",
            max_pages=5
        )

        assert task is not None
        assert "asda" in task.description
        assert "bread" in task.description
        assert "StandardizedProduct" in task.description

        # Test progress update method
        agent.update_progress("asda", "bread", 10, 2)

        # Test vendor config retrieval
        config = agent.get_vendor_config("asda")
        assert config is not None

        # Test session creation
        session_id = agent.create_session()
        assert session_id is not None

        print("✅ Enhanced ProductScraperAgent tests passed")
    
    def test_enhanced_site_navigator_agent(self):
        """Test SiteNavigatorAgent with multi-vendor support."""
        print("Testing Enhanced SiteNavigatorAgent...")

        # Test agent initialization with site configurations
        agent = SiteNavigatorAgent(
            tools=self.mock_tools,
            llm=None,  # Skip LLM to avoid CrewAI validation issues in tests
            site_configs={}
        )
        
        # Verify site configs are stored
        assert hasattr(agent, 'site_configs')
        assert agent.get_agent() is not None
        
        # Test vendor navigation task creation
        task = agent.create_vendor_navigation_task(
            vendor="tesco",
            category="electronics",
            session_id="test_session_456"
        )
        
        assert task is not None
        assert "tesco" in task.description
        assert "electronics" in task.description
        assert "GDPR" in task.description
        # Print task description for debugging
        print(f"Task description: {task.description}")
        assert "Rate limit" in task.description
        
        print("✅ Enhanced SiteNavigatorAgent tests passed")
    
    def test_enhanced_data_extractor_agent(self):
        """Test DataExtractorAgent with StandardizedProduct schema."""
        print("Testing Enhanced DataExtractorAgent...")

        # Test agent initialization with site configurations
        agent = DataExtractorAgent(
            tools=self.mock_tools,
            llm=None,  # Skip LLM to avoid CrewAI validation issues in tests
            site_configs={}
        )
        
        # Verify site configs are stored
        assert hasattr(agent, 'site_configs')
        assert agent.get_agent() is not None
        
        # Test standardized extraction task creation
        task = agent.create_standardized_extraction_task(
            vendor="waitrose",
            category="groceries",
            session_id="test_session_789"
        )
        
        assert task is not None
        assert "waitrose" in task.description
        assert "groceries" in task.description
        assert "StandardizedProduct" in task.description
        assert "GBP" in task.description
        assert '"name":' in task.description
        assert '"price":' in task.description
        
        print("✅ Enhanced DataExtractorAgent tests passed")
    
    def test_enhanced_data_validator_agent(self):
        """Test DataValidatorAgent with StandardizedProduct validation."""
        print("Testing Enhanced DataValidatorAgent...")

        # Test agent initialization
        agent = DataValidatorAgent(
            tools=self.mock_tools,
            llm=None  # Skip LLM to avoid CrewAI validation issues in tests
        )
        
        assert agent.get_agent() is not None
        
        # Test standardized validation task creation
        task = agent.create_standardized_validation_task(
            vendor="costco",
            category="toys",
            session_id="test_session_101"
        )
        
        assert task is not None
        assert "costco" in task.description
        assert "toys" in task.description
        assert "StandardizedProduct" in task.description
        assert "REQUIRED FIELDS" in task.description
        assert "GBP" in task.description
        
        print("✅ Enhanced DataValidatorAgent tests passed")
    
    def test_enhanced_ecommerce_scraper(self):
        """Test EcommerceScraper with enhanced capabilities."""
        print("Testing Enhanced EcommerceScraper...")
        
        # Test scraper initialization with enhanced components
        scraper = EcommerceScraper(
            verbose=False,
            enable_state_management=True,
            enable_progress_tracking=True
        )
        
        # Verify enhanced components are initialized
        assert scraper.state_manager is not None
        assert scraper.progress_tracker is not None
        assert scraper.batch_processor is None  # Initialized when needed
        
        # Verify agents have enhanced capabilities
        assert hasattr(scraper.product_scraper, 'state_manager')
        assert hasattr(scraper.product_scraper, 'progress_tracker')
        assert hasattr(scraper.site_navigator, 'site_configs')
        assert hasattr(scraper.data_extractor, 'site_configs')
        
        print("✅ Enhanced EcommerceScraper tests passed")
    
    @patch('ecommerce_scraper.main.Crew')
    @patch('ecommerce_scraper.main.EcommerceStagehandTool')
    def test_multi_vendor_scraping_workflow(self, mock_stagehand, mock_crew):
        """Test the complete multi-vendor scraping workflow."""
        print("Testing Multi-Vendor Scraping Workflow...")
        
        # Mock the crew execution
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {"products": [], "metadata": {}}
        mock_crew.return_value = mock_crew_instance
        
        # Mock the stagehand tool
        mock_stagehand.return_value = Mock()
        
        # Test scraper with enhanced workflow
        scraper = EcommerceScraper(verbose=False)
        
        # Test multi-vendor scraping method
        result = scraper.scrape_vendor_category(
            vendor="hamleys",
            category="toys",
            max_pages=3,
            session_id="test_workflow_session"
        )
        
        # Verify result structure
        assert result is not None
        assert "success" in result
        assert "vendor" in result
        assert "category" in result
        assert "session_id" in result
        assert result["vendor"] == "hamleys"
        assert result["category"] == "toys"
        
        # Verify crew was called with correct agents and tasks
        mock_crew.assert_called_once()
        call_args = mock_crew.call_args
        assert len(call_args[1]["agents"]) == 4  # All 4 agents
        assert len(call_args[1]["tasks"]) == 4   # All 4 tasks
        
        print("✅ Multi-Vendor Scraping Workflow tests passed")


def run_enhanced_agent_tests():
    """Run all enhanced agent workflow tests."""
    print("🚀 Starting Enhanced Agent Workflows Tests (Phase 2 Completion)")
    print("=" * 70)
    
    test_suite = TestEnhancedAgentWorkflows()
    test_suite.setup_method()
    
    try:
        # Run all tests
        test_suite.test_enhanced_product_scraper_agent()
        test_suite.test_enhanced_site_navigator_agent()
        test_suite.test_enhanced_data_extractor_agent()
        test_suite.test_enhanced_data_validator_agent()
        test_suite.test_enhanced_ecommerce_scraper()
        test_suite.test_multi_vendor_scraping_workflow()
        
        print("\n" + "=" * 70)
        print("🎉 ALL ENHANCED AGENT WORKFLOW TESTS PASSED!")
        print("✅ Phase 2: Enhanced Agent Workflows - COMPLETE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_enhanced_agent_tests()
    sys.exit(0 if success else 1)
