# Product-Specific Search Scraper Architecture

## 🚀 Overview

The Product-Specific Search Scraper is a complete AI-powered search system that allows users to search for specific products across UK retailers using intelligent retailer discovery, targeted extraction, and validation with feedback loops. This system replaces the category-based scraping approach with a more focused, product-centric methodology.

## 🏗️ Architecture Components

### 🤖 Specialized Agents

#### Enhanced NavigationAgent (AI-Powered Retailer Research)
- **Purpose**: AI-powered retailer discovery and navigation
- **Responsibilities**:
  - Research UK retailers using Perplexity AI for specific products
  - Identify legitimate retailers (exclude price comparison sites)
  - Find direct product URLs where possible
  - Navigate to retailer websites and product pages
  - Handle popups and site-specific challenges
- **Tools**:
  - PerplexityRetailerResearchTool for AI research
  - SimplifiedStagehandTool for web automation
- **Output**: List of researched retailers with product URLs and availability

#### Targeted ExtractionAgent
- **Purpose**: Product-specific data extraction with core field focus
- **Responsibilities**:
  - Extract only core fields: product name, price (GBP), direct URL
  - Focus on products matching the search query
  - Validate product relevance during extraction
  - Ensure URLs are direct product pages, not search results
- **Tools**: SimplifiedStagehandTool with targeted extraction schemas
- **Output**: Focused product data with core fields only

#### ProductSearchValidationAgent
- **Purpose**: Intelligent validation with feedback loops and retry logic
- **Responsibilities**:
  - Validate product name matches search query (semantic matching)
  - Verify URLs are from legitimate UK retailers
  - Ensure URLs lead to purchasable product pages
  - Generate specific feedback for failed validations
  - Recommend retry strategies and alternative retailers
  - Limit retry attempts to maximum 3 per product search
- **Tools**: Built-in validation algorithms and feedback generation
- **Output**: Validated products and retry recommendations

### 🔄 Cyclical Workflow

The enhanced architecture implements a cyclical workflow:

```
Navigation → Extraction → Validation → Feedback Loop → Next Page
```

#### Workflow Steps:
1. **Navigation**: Prepare page for extraction
2. **Extraction**: Extract product data
3. **Validation**: Validate and store data
4. **Feedback**: Re-extract if validation fails
5. **Pagination**: Move to next page if available

### 💾 Storage System

#### JSONManager
- Atomic file operations with backup creation
- Session-based data accumulation across pages
- Deduplication based on product key (name + price + vendor)
- Comprehensive session metadata tracking

#### BackupManager
- Automatic backup creation before updates
- Compressed backup support
- Backup verification and integrity checking
- Retention policy management

### 📊 Monitoring System

#### EnhancedProgressTracker
- Real-time session and page progress tracking
- Performance metrics collection
- Live progress display with Rich console
- Session statistics and completion rates

#### PerformanceMetrics
- System resource monitoring (CPU, memory, network)
- Custom metric collection
- Performance window analysis
- Alert system for threshold violations

### 📡 Communication System

#### MessageProtocol
- Structured inter-agent communication
- Typed message formats (PageReady, ExtractionBatch, ValidationResult, etc.)
- JSON serialization/deserialization
- Message routing and handling

#### FeedbackSystem
- Validation failure analysis
- Improvement suggestion generation
- Re-extraction coordination
- Feedback effectiveness tracking

## 🎯 Architecture Benefits

- **Role Separation**: Clear single responsibility for each agent
- **Feedback Loops**: ValidationAgent guides ExtractionAgent improvements
- **Cyclical Processing**: Complete pagination handling with state persistence
- **Resource Efficiency**: Shared browser session across agents
- **Full Persistence**: Session recovery, backup, and resume capabilities
- **Real-time Monitoring**: Comprehensive progress tracking and performance metrics
- **Data Quality**: Schema validation, deduplication, and re-extraction capabilities

## 🚀 Usage

### Basic Scraping

```python
from ecommerce_scraper.main import EcommerceScraper

# Initialize the enhanced scraper
with EcommerceScraper() as scraper:
    result = scraper.scrape_category(
        category_url="https://groceries.asda.com/aisle/fresh-food/fresh-fruit",
        vendor="asda",
        category_name="fresh_fruit",
        max_pages=5
    )

    print(f"Scraped {len(result.products)} products")
    print(f"Session ID: {result.session_id}")
```

### Architecture Information

```python
scraper = EcommerceScraper()
info = scraper.get_architecture_info()
print(info["architecture_type"])  # "enhanced"
print(info["components"])  # Shows all enhanced components
```

### Session Statistics

```python
with EcommerceScraper() as scraper:
    result = scraper.scrape_category(...)

    # Get comprehensive session statistics
    stats = scraper.get_session_statistics()
    print(f"Pages processed: {stats['pages_processed']}")
    print(f"Success rate: {stats['overall_success_rate']:.1f}%")

    # Get performance metrics
    performance = scraper.get_performance_metrics()
    print(f"CPU usage: {performance['current']['cpu_percent']:.1f}%")
    print(f"Memory usage: {performance['current']['memory_mb']:.1f}MB")
```

## 📁 Directory Structure

```
ecommerce_scraper/
├── agents/
│   ├── navigation_agent.py      # NavigationAgent
│   ├── extraction_agent.py      # ExtractionAgent
│   ├── validation_agent.py      # ValidationAgent
│   └── ...                      # Legacy agents
├── workflows/
│   └── cyclical_processor.py    # CyclicalProcessor
├── storage/
│   ├── json_manager.py          # JSONManager
│   └── backup_manager.py        # BackupManager
├── monitoring/
│   ├── enhanced_progress_tracker.py  # EnhancedProgressTracker
│   └── performance_metrics.py   # PerformanceMetrics
├── communication/
│   ├── message_protocol.py      # MessageProtocol
│   └── feedback_system.py       # FeedbackSystem
└── main.py                      # Enhanced EcommerceScraper
```

## 🧪 Testing

### Run All Tests

```bash
cd tests
python run_enhanced_tests.py all --verbose --coverage
```

### Run Specific Test Types

```bash
# Unit tests
python run_enhanced_tests.py unit

# Integration tests  
python run_enhanced_tests.py integration

# End-to-end tests
python run_enhanced_tests.py e2e
```

### Test Coverage

The test suite covers:
- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interactions and workflows
- **End-to-End Tests**: Complete scraping workflows

## 📈 Performance Improvements

### Resource Efficiency
- **Single Browser Session**: Shared across all agents
- **Atomic Storage**: Prevents data corruption
- **Memory Management**: Efficient batch processing
- **CPU Optimization**: Specialized agent responsibilities

### Scalability Improvements
- **Persistent State**: Session recovery and resume
- **Feedback Loops**: Continuous quality improvement
- **Performance Monitoring**: Real-time resource tracking
- **Error Recovery**: Comprehensive error handling

### Data Quality Improvements
- **Schema Validation**: Strict StandardizedProduct compliance
- **Deduplication**: Cross-page duplicate removal
- **Re-extraction**: Feedback-driven quality improvement
- **Backup System**: Data integrity protection

## 🔧 Configuration

### Scraper Settings

```python
scraper = EcommerceScraper(
    verbose=True,                          # Enable detailed logging
    session_id="custom_session_id"         # Custom session identifier
)
```

### Performance Tuning

```python
# Configure performance metrics
scraper.performance_metrics.set_threshold("cpu_percent", 70.0)
scraper.performance_metrics.set_threshold("memory_mb", 1024.0)

# Add custom metrics
scraper.performance_metrics.add_custom_metric(
    "products_per_minute", 
    lambda: scraper.get_session_statistics()["products_per_minute"]
)
```

## 🚨 Important Notes

### StagehandTool Preservation
- **DO NOT MODIFY** `ecommerce_scraper/tools/stagehand_tool.py`
- Significant effort was invested in creating the working version
- The enhanced architecture reuses the existing StagehandTool



### Session Management
- Each scraping session gets a unique ID
- Session data persists across interruptions
- Automatic cleanup and backup management

## 🎯 Next Steps

1. **Monitoring**: Implement production monitoring dashboards
2. **Optimization**: Fine-tune performance based on metrics
3. **Extension**: Add new specialized agents as needed
4. **Scaling**: Implement distributed processing capabilities

## 📚 Additional Resources

- [Enhanced Multi-Agent Architecture Document](ENHANCED_MULTI_AGENT_ARCHITECTURE.md)
- [Test Suite Documentation](tests/README.md)
- [Performance Optimization Guide](docs/performance_optimization.md)
- [Migration Guide](docs/migration_guide.md)
