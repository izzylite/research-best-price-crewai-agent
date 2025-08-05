# 🏗️ Enhanced Multi-Agent Ecommerce Scraping Architecture

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Agent Specifications](#agent-specifications)
3. [Workflow Process](#workflow-process)
4. [Data Flow & Communication](#data-flow--communication)
5. [File Management System](#file-management-system)
6. [Error Handling & Recovery](#error-handling--recovery)
7. [Performance Considerations](#performance-considerations)
8. [Implementation Guidelines](#implementation-guidelines)
9. [Testing Strategy](#testing-strategy)
10. [Monitoring & Logging](#monitoring--logging)

---

## 🎯 Architecture Overview

### Core Principles
- **Single Responsibility**: Each agent has one primary function
- **Zero Overlap**: No functional redundancy between agents
- **Feedback Loops**: Quality assurance through re-extraction
- **Persistent Storage**: Incremental data saving with recovery
- **Cyclical Processing**: Complete pagination handling

### System Components
```
┌─────────────────────────────────────────────────────────────┐
│                    ENHANCED SCRAPING SYSTEM                 │
├─────────────────────────────────────────────────────────────┤
│  Input: Category URL from enhanced_interactive_scraper.py   │
│         ↓                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │NavigationAgt│ →  │ExtractionAgt│ →  │ValidationAgt│      │
│  │(Prepare)    │    │(Extract)    │    │(Validate &  │      │
│  │             │ ←  │             │ ←  │ Save)       │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│         ↑                                       ↓           │
│         └─── Pagination Check ←─── JSON File Update         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Specifications

### Agent 1: NavigationAgent
**Role**: "Ecommerce Site Navigation and Pagination Specialist"

#### Primary Responsibilities
- Navigate to category URLs and subsequent pages
- Dismiss popups, banners, cookie consents, age verification dialogs
- Handle dynamic content loading (infinite scroll, "Load More" buttons)
- Ensure all products on current page are fully loaded and visible
- Detect and navigate pagination (next page, page numbers, infinite scroll)
- Prepare pages for extraction without extracting any data

#### Tools & Capabilities
- **Tools**: StagehandTool only
- **Popup Handling**: Cookie banners, age verification, newsletters, location dialogs
- **Dynamic Loading**: Infinite scroll detection, "Load More" button clicking
- **Pagination Detection**: Next/Previous buttons, page numbers, end-of-results detection

#### Input/Output
- **Input**: Category URL (initial) or pagination signal (subsequent)
- **Output**: Page preparation status ("ready", "error", "no-more-pages")

#### State Management
- Current page number/position
- Pagination method detected (buttons, infinite scroll, etc.)
- Total pages discovered (if determinable)
- Navigation history for error recovery

### Agent 2: ExtractionAgent
**Role**: "StandardizedProduct Data Extraction Specialist"

#### Primary Responsibilities
- Extract ALL product data from prepared category pages
- Apply StandardizedProduct schema format consistently
- Handle vendor-specific data structures and layouts
- Process re-extraction requests from ValidationAgent
- Focus purely on data extraction accuracy and completeness

#### Tools & Capabilities
- **Tools**: StagehandTool + PriceExtractor + ImageExtractor
- **Schema Compliance**: Strict StandardizedProduct format adherence
- **Vendor Adaptation**: Handle different site structures (ASDA, Tesco, etc.)
- **Re-extraction**: Process feedback and improve extraction quality

#### Input/Output
- **Input**: Page ready signal + optional re-extraction feedback
- **Output**: Raw product data batch in StandardizedProduct format

#### Extraction Strategy
- Product listing detection and parsing
- Individual product data extraction
- Image URL resolution and validation
- Price parsing with currency standardization
- Category and vendor assignment

### Agent 3: ValidationAgent
**Role**: "StandardizedProduct Data Validation, Feedback & Storage Expert"

#### Primary Responsibilities
- Validate extracted data against StandardizedProduct schema
- Provide feedback to ExtractionAgent for re-extraction if needed
- Save successfully validated products to JSON files
- Accumulate results across all pages in a single session
- Manage persistent storage and data integrity

#### Tools & Capabilities
- **Tools**: ProductDataValidator + File I/O operations
- **Validation Rules**: StandardizedProduct schema compliance
- **Feedback Generation**: Specific improvement suggestions for re-extraction
- **File Management**: Atomic JSON updates, backup creation
- **Deduplication**: Cross-page duplicate detection and removal

#### Input/Output
- **Input**: Raw product data batch from ExtractionAgent
- **Output**: Validation result + JSON file update + feedback (if needed)

#### Validation Criteria
- Required field presence and format validation
- Data type and range validation
- URL format validation for images
- Price format and currency validation
- Text quality and completeness checks

---

## 🔄 Workflow Process

### Phase 1: Initialization
1. **Input Reception**: Receive category URL from enhanced_interactive_scraper.py
2. **Session Creation**: Generate unique session ID and initialize JSON file
3. **Agent Preparation**: Initialize all three agents with appropriate tools
4. **State Setup**: Initialize pagination state and progress tracking

### Phase 2: Cyclical Processing Loop

#### Cycle Step 1: Navigation (NavigationAgent)
```
┌─ NavigationAgent Execution ─┐
│ 1. Navigate to current page  │
│ 2. Dismiss popups/banners    │
│ 3. Handle dynamic loading    │
│ 4. Ensure products visible   │
│ 5. Signal "page ready"       │
└─────────────────────────────┘
```

#### Cycle Step 2: Extraction (ExtractionAgent)
```
┌─ ExtractionAgent Execution ─┐
│ 1. Receive "page ready"      │
│ 2. Extract all products      │
│ 3. Apply StandardizedProduct │
│ 4. Return product batch      │
└─────────────────────────────┘
```

#### Cycle Step 3: Validation & Storage (ValidationAgent)
```
┌─ ValidationAgent Execution ─┐
│ 1. Validate product batch    │
│ 2. Decision Point:           │
│    ├─ Valid: Save to JSON    │
│    └─ Invalid: Request       │
│       re-extraction          │
│ 3. Update accumulated data   │
│ 4. Signal completion         │
└─────────────────────────────┘
```

#### Cycle Step 4: Pagination Check (NavigationAgent)
```
┌─ Pagination Check ─┐
│ 1. Check for more   │
│    pages/content    │
│ 2. Decision:        │
│    ├─ More: Next    │
│    │   page → Step 1│
│    └─ Done: End     │
│       cycle         │
└────────────────────┘
```

### Phase 3: Completion
1. **Final Validation**: Ensure all data is properly saved
2. **Summary Generation**: Create scraping session summary
3. **Cleanup**: Close browser sessions and temporary resources
4. **Result Return**: Return final JSON file path and statistics

---

## 📡 Data Flow & Communication

### Inter-Agent Communication Protocol

#### NavigationAgent → ExtractionAgent
```json
{
  "status": "page_ready",
  "page_info": {
    "current_page": 1,
    "products_visible": 24,
    "page_url": "https://...",
    "timestamp": "2025-01-04T12:34:56Z"
  }
}
```

#### ExtractionAgent → ValidationAgent
```json
{
  "extraction_batch": [
    {
      "name": "Product Name",
      "description": "Product Description",
      "price": {"amount": 10.99, "currency": "GBP"},
      "image_url": "https://...",
      "category": "Category",
      "vendor": "vendor_name",
      "scraped_at": "2025-01-04T12:34:56Z"
    }
  ],
  "extraction_metadata": {
    "page_number": 1,
    "products_found": 24,
    "extraction_method": "category_listing"
  }
}
```

#### ValidationAgent → ExtractionAgent (Re-extraction Request)
```json
{
  "validation_result": "failed",
  "feedback": {
    "issues": [
      "Missing product descriptions for 5 products",
      "Invalid price format for 2 products",
      "Missing image URLs for 3 products"
    ],
    "suggestions": [
      "Look for description in product title or subtitle",
      "Check for alternative price selectors",
      "Verify image URL extraction selectors"
    ]
  },
  "retry_count": 1,
  "max_retries": 3
}
```

#### ValidationAgent → NavigationAgent (Pagination Signal)
```json
{
  "validation_complete": true,
  "products_saved": 22,
  "products_failed": 2,
  "ready_for_pagination": true,
  "session_stats": {
    "total_pages_processed": 1,
    "total_products_saved": 22,
    "total_validation_failures": 2
  }
}
```

---

## 🗂️ File Management System

### JSON File Structure
```json
{
  "scraping_session": {
    "session_id": "asda_fruit_20250104_123456",
    "vendor": "asda",
    "category": "Fruit",
    "category_url": "https://groceries.asda.com/aisle/fruit-veg-flowers/fruit/view-all-fruit/...",
    "started_at": "2025-01-04T12:34:56Z",
    "last_updated": "2025-01-04T12:45:30Z",
    "status": "in_progress",
    "pagination_info": {
      "total_pages_processed": 3,
      "current_page": 3,
      "pagination_method": "load_more_button",
      "has_more_pages": true
    }
  },
  "products": [
    {
      "name": "Organic Bananas 6 Pack",
      "description": "Fresh organic bananas, perfect for snacking",
      "price": {
        "amount": 1.50,
        "currency": "GBP"
      },
      "image_url": "https://i2.wp.com/asda.scene7.com/is/image/Asda/...",
      "category": "Fruit",
      "vendor": "asda",
      "weight": "6 pack",
      "scraped_at": "2025-01-04T12:34:56Z",
      "page_number": 1,
      "validation_status": "passed"
    }
  ],
  "session_statistics": {
    "total_products_found": 67,
    "total_products_validated": 65,
    "total_products_failed": 2,
    "validation_success_rate": 97.01,
    "re_extraction_attempts": 3,
    "pages_processed": 3,
    "average_products_per_page": 22.33,
    "scraping_duration_seconds": 145
  },
  "validation_log": [
    {
      "timestamp": "2025-01-04T12:35:15Z",
      "page": 1,
      "products_validated": 24,
      "products_failed": 1,
      "issues": ["Missing description for product ID temp_001"]
    }
  ],
  "error_log": [
    {
      "timestamp": "2025-01-04T12:36:22Z",
      "agent": "ExtractionAgent",
      "error_type": "extraction_failure",
      "message": "Failed to extract price for product at position 15",
      "retry_attempted": true,
      "resolved": true
    }
  ]
}
```

### File Management Operations

#### File Creation
- **Location**: `./results/scraping_sessions/`
- **Naming**: `{vendor}_{category}_{timestamp}.json`
- **Initialization**: Create with session metadata and empty products array

#### Atomic Updates
```python
def update_json_file(file_path, new_products, session_stats):
    # 1. Read current file
    # 2. Create backup
    # 3. Merge new products
    # 4. Update statistics
    # 5. Write atomically (temp file + rename)
    # 6. Verify write success
    # 7. Remove backup on success
```

#### Backup Strategy
- **Automatic Backups**: Before each update
- **Backup Location**: `./results/backups/`
- **Retention**: Keep last 5 backups per session
- **Recovery**: Automatic recovery from backup on corruption

---

## 🚨 Error Handling & Recovery

### Error Categories

#### Navigation Errors
- **Popup Handling Failures**: Retry with alternative selectors
- **Page Load Timeouts**: Increase timeout and retry
- **Pagination Detection Failures**: Manual pagination fallback
- **Site Blocking**: Implement respectful delays and retry

#### Extraction Errors
- **Missing Product Data**: Request re-extraction with feedback
- **Schema Validation Failures**: Provide specific correction guidance
- **Network Timeouts**: Retry with exponential backoff
- **Site Structure Changes**: Adaptive selector strategies

#### Validation Errors
- **File I/O Errors**: Backup recovery and retry
- **Data Corruption**: Rollback to last known good state
- **Disk Space Issues**: Cleanup and compression strategies
- **Schema Violations**: Detailed feedback for re-extraction

### Recovery Mechanisms

#### Session Recovery
```python
def recover_session(session_file):
    # 1. Load existing session data
    # 2. Determine last successful page
    # 3. Resume from next page
    # 4. Validate data integrity
    # 5. Continue normal processing
```

#### Agent Recovery
- **NavigationAgent**: Reset browser state, clear cache
- **ExtractionAgent**: Reinitialize extraction tools
- **ValidationAgent**: Verify file integrity, restore from backup

#### Data Recovery
- **Corruption Detection**: Checksum validation
- **Backup Restoration**: Automatic rollback to last good state
- **Partial Recovery**: Salvage valid products from corrupted batches

---

## ⚡ Performance Considerations

### Optimization Strategies

#### Navigation Optimization
- **Smart Popup Detection**: Learn from previous dismissals
- **Preemptive Loading**: Predict and preload next pages
- **Caching**: Cache navigation patterns per vendor
- **Parallel Preparation**: Prepare next page while extracting current

#### Extraction Optimization
- **Batch Processing**: Extract multiple products simultaneously
- **Selector Caching**: Reuse successful selectors within session
- **Image Validation**: Async image URL verification
- **Memory Management**: Stream processing for large product lists

#### Validation Optimization
- **Incremental Validation**: Validate as products are extracted
- **Parallel Processing**: Validate multiple products concurrently
- **Smart Caching**: Cache validation results for similar products
- **Compression**: Compress JSON files for large datasets

### Resource Management

#### Memory Management
- **Streaming**: Process products in batches to limit memory usage
- **Garbage Collection**: Explicit cleanup after each page
- **Buffer Limits**: Maximum products in memory before flush to disk

#### Network Management
- **Rate Limiting**: Respectful delays between requests
- **Connection Pooling**: Reuse browser connections
- **Timeout Management**: Progressive timeout increases
- **Retry Logic**: Exponential backoff with jitter

#### Storage Management
- **Disk Space Monitoring**: Check available space before writing
- **File Rotation**: Archive old sessions automatically
- **Compression**: Compress completed sessions
- **Cleanup**: Remove temporary files and backups

---

## 🛠️ Implementation Guidelines

### Development Phases

#### Phase 1: Core Agent Implementation
1. **NavigationAgent**: Basic navigation and popup handling
2. **ExtractionAgent**: StandardizedProduct extraction
3. **ValidationAgent**: Schema validation and file operations
4. **Integration**: Basic cyclical workflow

#### Phase 2: Enhanced Features
1. **Feedback Loop**: Re-extraction mechanism
2. **Pagination**: Complete pagination handling
3. **Error Handling**: Comprehensive error recovery
4. **Performance**: Optimization and resource management

#### Phase 3: Advanced Features
1. **Monitoring**: Real-time progress tracking
2. **Analytics**: Performance metrics and reporting
3. **Scalability**: Multi-session parallel processing
4. **Maintenance**: Automated cleanup and archiving

### Code Organization

#### Directory Structure
```
ecommerce_scraper/
├── agents/
│   ├── navigation_agent.py      # NavigationAgent implementation
│   ├── extraction_agent.py      # ExtractionAgent implementation
│   └── validation_agent.py      # ValidationAgent implementation
├── workflows/
│   ├── cyclical_processor.py    # Main workflow orchestration
│   └── session_manager.py       # Session state management
├── storage/
│   ├── json_manager.py          # JSON file operations
│   └── backup_manager.py        # Backup and recovery
├── communication/
│   ├── message_protocol.py      # Inter-agent communication
│   └── feedback_system.py       # Validation feedback handling
└── monitoring/
    ├── progress_tracker.py      # Progress monitoring
    └── performance_metrics.py   # Performance analytics
```

#### Configuration Management
```python
# Agent-specific configurations
NAVIGATION_CONFIG = {
    "popup_timeout": 10,
    "page_load_timeout": 30,
    "pagination_detection_timeout": 5,
    "max_scroll_attempts": 10
}

EXTRACTION_CONFIG = {
    "batch_size": 50,
    "extraction_timeout": 60,
    "max_retry_attempts": 3,
    "schema_validation": True
}

VALIDATION_CONFIG = {
    "max_re_extraction_attempts": 3,
    "backup_frequency": "per_page",
    "compression_enabled": True,
    "deduplication_enabled": True
}
```

---

## 🧪 Testing Strategy

### Unit Testing

#### NavigationAgent Tests
- Popup dismissal accuracy
- Pagination detection reliability
- Dynamic content loading verification
- Error handling and recovery

#### ExtractionAgent Tests
- StandardizedProduct schema compliance
- Vendor-specific extraction accuracy
- Re-extraction improvement verification
- Performance benchmarking

#### ValidationAgent Tests
- Schema validation accuracy
- File I/O operations reliability
- Backup and recovery mechanisms
- Feedback generation quality

### Integration Testing

#### Workflow Testing
- Complete cyclical process execution
- Inter-agent communication reliability
- Error propagation and handling
- Session recovery mechanisms

#### Performance Testing
- Large dataset processing
- Memory usage optimization
- Network efficiency
- Storage performance

### End-to-End Testing

#### Real-World Scenarios
- Complete category scraping (all UK vendors)
- Interrupted session recovery
- Network failure handling
- Site structure change adaptation

#### Quality Assurance
- Data accuracy verification
- Schema compliance validation
- Performance benchmarking
- User acceptance testing

---

## 📊 Monitoring & Logging

### Real-Time Monitoring

#### Progress Tracking
```python
class ProgressMonitor:
    def track_navigation(self, page_num, total_pages):
        # Track navigation progress

    def track_extraction(self, products_extracted, page_num):
        # Track extraction progress

    def track_validation(self, products_validated, products_failed):
        # Track validation progress

    def generate_real_time_stats(self):
        # Generate current session statistics
```

#### Performance Metrics
- Pages processed per minute
- Products extracted per minute
- Validation success rate
- Error frequency and types
- Resource utilization (CPU, memory, network)

### Logging System

#### Log Levels
- **DEBUG**: Detailed execution flow
- **INFO**: Major milestones and progress
- **WARNING**: Recoverable errors and retries
- **ERROR**: Serious errors requiring attention
- **CRITICAL**: System failures requiring immediate action

#### Log Categories
```python
# Agent-specific loggers
navigation_logger = logging.getLogger('navigation_agent')
extraction_logger = logging.getLogger('extraction_agent')
validation_logger = logging.getLogger('validation_agent')

# System loggers
workflow_logger = logging.getLogger('workflow')
performance_logger = logging.getLogger('performance')
error_logger = logging.getLogger('error_handling')
```

#### Log Output Formats
```json
{
  "timestamp": "2025-01-04T12:34:56Z",
  "level": "INFO",
  "agent": "NavigationAgent",
  "session_id": "asda_fruit_20250104_123456",
  "page": 2,
  "message": "Successfully navigated to page 2",
  "metadata": {
    "products_visible": 24,
    "popups_dismissed": 1,
    "load_time_seconds": 3.2
  }
}
```

---

## 📈 Success Metrics

### Quality Metrics
- **Data Accuracy**: >95% schema compliance
- **Completeness**: >90% required fields populated
- **Consistency**: <5% duplicate products across pages
- **Validation Success**: >95% first-pass validation rate

### Performance Metrics
- **Speed**: <2 minutes per category page
- **Efficiency**: >20 products extracted per minute
- **Reliability**: <1% session failure rate
- **Recovery**: <30 seconds average recovery time

### System Metrics
- **Uptime**: >99% system availability
- **Resource Usage**: <2GB memory per session
- **Storage Efficiency**: <10MB per 1000 products
- **Error Rate**: <2% unrecoverable errors

---

## 🎯 Implementation Roadmap

### Week 1-2: Foundation
- [ ] Implement basic NavigationAgent
- [ ] Implement basic ExtractionAgent
- [ ] Implement basic ValidationAgent
- [ ] Create simple cyclical workflow

### Week 3-4: Core Features
- [ ] Add feedback loop between ValidationAgent and ExtractionAgent
- [ ] Implement comprehensive pagination handling
- [ ] Add JSON file management and persistence
- [ ] Create error handling and recovery mechanisms

### Week 5-6: Enhancement
- [ ] Optimize performance and resource usage
- [ ] Add comprehensive monitoring and logging
- [ ] Implement backup and recovery systems
- [ ] Create testing framework and test suites

### Week 7-8: Polish
- [ ] Performance tuning and optimization
- [ ] Documentation completion
- [ ] User acceptance testing
- [ ] Production deployment preparation

---

## 🎉 Conclusion

This architecture provides a robust, scalable, and maintainable solution for multi-agent ecommerce scraping with:

- **Clear separation of concerns** between navigation, extraction, and validation
- **Comprehensive error handling** and recovery mechanisms
- **Persistent data storage** with backup and recovery capabilities
- **Feedback loops** for continuous quality improvement
- **Performance optimization** for large-scale operations
- **Comprehensive monitoring** and logging for operational visibility

The cyclical workflow ensures complete category coverage while the feedback system maintains high data quality standards. The persistent storage system provides resilience against interruptions and enables session recovery.

This design eliminates role overlaps, creates efficient resource utilization, and provides a foundation for scalable ecommerce data extraction operations.
