# Multi-Site Ecommerce Scraping Strategy

## Executive Summary

This document outlines the technical architecture and implementation strategy for comprehensive iterative testing of our CrewAI ecommerce scraping workflow across 10 UK retail websites. The system will provide automated product data extraction with standardized JSON output, interactive vendor/category selection, and robust pagination with state management.

## Target Websites & Challenges

### Primary Targets
1. **ASDA** (https://www.asda.com/) - Groceries, anti-bot measures
2. **Costco** (https://www.costco.com/) - Wholesale/Groceries, membership requirements
3. **Waitrose** (https://www.waitrose.com/) - Premium groceries, location-based content
4. **Tesco** (https://www.tesco.com/groceries/en-GB) - Groceries, complex category structure
5. **Hamleys** (https://www.hamleys.com/) - Toys, age verification
6. **Mamas & Papas** (https://www.mamasandpapas.com/) - Baby products, variant complexity
7. **Selfridges** (https://www.selfridges.com/GB/en/) - Luxury retail, premium content protection
8. **Next** (https://www.next.co.uk/) - Fashion/Home, size/color variants
9. **Primark** (https://www.primark.com/en-gb) - Fashion, limited online catalog
10. **The Toy Shop** (https://www.thetoyshop.com/) - Toys, seasonal content

### Site-Specific Challenges
- **Cookie Consent**: GDPR compliance banners on all UK sites
- **Location Detection**: Delivery area restrictions and store locators
- **Age Verification**: Required for toy sites and some products
- **Anti-Bot Measures**: Rate limiting, CAPTCHA, behavioral detection
- **Dynamic Content**: JavaScript-heavy product listings and infinite scroll
- **Membership Requirements**: Costco requires login for pricing
- **Variant Complexity**: Fashion sites with size/color/style combinations

## Technical Architecture

### Core Components

#### 1. Enhanced Agent Architecture
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  SiteNavigatorAgent │    │ CategoryDiscoverer  │    │  ProductScraperAgent│
│  - Site navigation  │    │  - Dynamic category │    │  - Product extraction│
│  - Popup handling   │    │    discovery        │    │  - Data coordination │
│  - Anti-bot evasion │    │  - Menu traversal   │    │  - Quality control   │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  DataExtractorAgent │    │   StateManager      │    │  DataValidatorAgent │
│  - Product data     │    │  - Pagination state │    │  - Schema validation│
│  - Image extraction │    │  - Progress tracking│    │  - Data cleaning    │
│  - Price parsing    │    │  - Resume capability│    │  - Quality assurance│
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

#### 2. Data Flow Architecture
```
User Input → Vendor Selection → Category Discovery → Pagination Planning
     ↓              ↓                ↓                    ↓
CLI Interface → Site Navigator → Category Discoverer → State Manager
     ↓              ↓                ↓                    ↓
Batch Processing → Product Scraper → Data Extractor → Data Validator
     ↓              ↓                ↓                    ↓
Progress Tracking → JSON Storage → Validation → Final Output
```

### 3. Standardized Data Schema

```json
{
  "name": "string (required)",
  "description": "string (required)", 
  "price": {
    "amount": "number (required)",
    "currency": "string (required, default: GBP)"
  },
  "image_url": "string (required)",
  "weight": "string (optional, null if not available)",
  "category": "string (required)",
  "vendor": "string (required)",
  "scraped_at": "ISO timestamp (required)"
}
```

## Agent Role Definitions & Workflow

### 1. SiteNavigatorAgent
**Primary Responsibilities:**
- Initial site navigation and popup handling
- Cookie consent and GDPR compliance
- Location/delivery area selection
- Age verification handling
- Anti-bot evasion strategies

**Tools:** EcommerceStagehandTool, SiteConfigManager

**Workflow:**
1. Navigate to target website
2. Handle initial popups (cookies, location, newsletters)
3. Verify site accessibility and readiness
4. Report navigation status to coordinator

### 2. CategoryDiscovererAgent (New)
**Primary Responsibilities:**
- Dynamic category structure discovery
- Menu traversal and category mapping
- Product count estimation per category
- Category hierarchy extraction

**Tools:** EcommerceStagehandTool, CategoryMapper

**Workflow:**
1. Analyze site navigation structure
2. Extract available product categories
3. Map category URLs and product counts
4. Return structured category data for user selection

### 3. ProductScraperAgent (Enhanced)
**Primary Responsibilities:**
- Orchestrate multi-page scraping workflows
- Coordinate between other agents
- Manage pagination state
- Quality control and error handling

**Tools:** ProductDataValidator, StateManager, ProgressTracker

**Workflow:**
1. Receive category/vendor selections from CLI
2. Plan pagination strategy with StateManager
3. Coordinate page-by-page extraction
4. Monitor progress and handle errors
5. Ensure data quality standards

### 4. DataExtractorAgent (Enhanced)
**Primary Responsibilities:**
- Extract product data from current page
- Handle variant detection and extraction
- Image URL extraction and validation
- Price parsing and currency normalization

**Tools:** EcommerceStagehandTool, PriceExtractor, ImageExtractor, VariantDetector

**Workflow:**
1. Extract all products from current page
2. Parse and normalize product data
3. Handle variants and options
4. Validate extracted data structure
5. Pass to DataValidatorAgent

### 5. DataValidatorAgent (Enhanced)
**Primary Responsibilities:**
- Schema validation against standardized format
- Data cleaning and normalization
- Duplicate detection and removal
- Quality assurance checks

**Tools:** ProductDataValidator, SchemaValidator, DataCleaner

**Workflow:**
1. Validate against required JSON schema
2. Clean and normalize data fields
3. Check for duplicates within batch
4. Apply quality filters
5. Save validated data to JSON files

## State Management & Pagination Strategy

### Pagination State Structure
```json
{
  "session_id": "uuid",
  "vendor": "site_name",
  "category": "category_name", 
  "current_page": 1,
  "total_pages": null,
  "products_scraped": 0,
  "last_product_url": "string",
  "pagination_method": "numbered|infinite_scroll|load_more",
  "resume_url": "string",
  "started_at": "timestamp",
  "last_updated": "timestamp",
  "status": "active|paused|completed|error"
}
```

### State Persistence
- **File Location:** `./scraping_state/{vendor}_{category}_{session_id}.json`
- **Auto-save:** After each page completion
- **Resume Logic:** Detect incomplete sessions on startup
- **Cleanup:** Archive completed sessions after 7 days

### Pagination Strategies
1. **Numbered Pagination:** Traditional page numbers (1, 2, 3...)
2. **Infinite Scroll:** Detect scroll triggers and load more content
3. **Load More Buttons:** Click-based pagination
4. **Offset-based:** URL parameter manipulation

## Error Handling & Retry Mechanisms

### Error Categories
1. **Network Errors:** Timeouts, connection failures
2. **Anti-Bot Detection:** CAPTCHA, rate limiting, IP blocking
3. **Site Structure Changes:** Selector failures, layout changes
4. **Data Quality Issues:** Missing required fields, invalid formats
5. **Session Expiration:** Login timeouts, session invalidation

### Retry Strategies
```python
RETRY_CONFIG = {
    "network_errors": {
        "max_retries": 3,
        "backoff_factor": 2,
        "delay_range": (5, 15)
    },
    "anti_bot_detection": {
        "max_retries": 2, 
        "backoff_factor": 5,
        "delay_range": (30, 120),
        "strategy": "new_session"
    },
    "selector_failures": {
        "max_retries": 1,
        "fallback": "ai_extraction",
        "escalate_to": "manual_review"
    }
}
```

### Circuit Breaker Pattern
- **Failure Threshold:** 5 consecutive failures per site
- **Recovery Time:** 30 minutes before retry
- **Fallback:** Switch to alternative extraction methods

## Performance Optimization Strategies

### 1. Concurrent Processing
- **Site-level Parallelism:** Multiple vendors simultaneously
- **Category-level Batching:** Process categories in parallel per site
- **Rate Limiting:** Respect site-specific delays and politeness policies

### 2. Caching Strategy
- **Category Data:** Cache discovered categories for 24 hours
- **Site Configurations:** Cache navigation patterns and selectors
- **Session Management:** Reuse browser sessions when possible

### 3. Resource Management
- **Memory Optimization:** Process products in batches of 50
- **Browser Session Limits:** Maximum 3 concurrent Browserbase sessions
- **Storage Optimization:** Compress and archive old scraping data

## Data Validation & Quality Assurance

### Validation Pipeline
1. **Schema Compliance:** Ensure all required fields present
2. **Data Type Validation:** Verify field types and formats
3. **Business Logic Validation:** Price > 0, valid URLs, etc.
4. **Duplicate Detection:** Cross-reference within and across batches
5. **Quality Scoring:** Assign quality scores based on completeness

### Quality Metrics
- **Completeness Score:** Percentage of required fields populated
- **Accuracy Score:** Validation against known product databases
- **Consistency Score:** Format consistency across similar products
- **Freshness Score:** Time since last update

### Data Cleaning Rules
- **Price Normalization:** Convert all prices to GBP with consistent formatting
- **Text Cleaning:** Remove HTML tags, normalize whitespace, handle encoding
- **URL Validation:** Ensure image URLs are accessible and valid
- **Category Standardization:** Map site-specific categories to standard taxonomy

## Security & Compliance Considerations

### 1. Rate Limiting & Politeness
- **Request Delays:** Minimum 2-5 seconds between requests per site
- **Concurrent Limits:** Maximum 2 concurrent sessions per vendor
- **Respect robots.txt:** Honor site crawling policies
- **User-Agent Rotation:** Use realistic browser user agents

### 2. Data Privacy
- **No Personal Data:** Avoid scraping user reviews, personal information
- **GDPR Compliance:** Handle cookie consent appropriately
- **Data Retention:** Automatic cleanup of old scraping data

### 3. Legal Compliance
- **Terms of Service:** Review and comply with site ToS
- **Fair Use:** Educational/research purposes only
- **Attribution:** Maintain source attribution in scraped data

## Monitoring & Alerting

### Key Metrics
- **Success Rate:** Percentage of successful product extractions
- **Performance:** Average time per product/page
- **Error Rate:** Categorized error frequency
- **Data Quality:** Average quality scores per vendor

### Alerting Thresholds
- **High Error Rate:** >20% failures in 1 hour
- **Performance Degradation:** >50% slower than baseline
- **Anti-Bot Detection:** Multiple CAPTCHA encounters
- **Data Quality Issues:** <80% schema compliance

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Enhanced CLI interface with vendor/category selection
- Category discovery system implementation
- State management and pagination framework
- Standardized schema implementation

### Phase 2: Core Functionality (Week 2)
- Multi-vendor site configurations
- Enhanced agent workflows
- Batch processing implementation
- Progress tracking and resume functionality

### Phase 3: Testing & Optimization (Week 3)
- Comprehensive testing across all 10 sites
- Performance optimization and error handling
- Quality assurance and validation improvements
- Documentation and user guides

### Phase 4: Production Readiness (Week 4)
- Monitoring and alerting setup
- Security review and compliance verification
- Final testing and bug fixes
- Deployment and maintenance procedures

## Success Criteria

### Functional Requirements
- ✅ Successfully scrape from all 10 target UK retail websites
- ✅ Extract minimum 100 products per site with >90% schema compliance
- ✅ Handle pagination across different site architectures
- ✅ Provide resume functionality for interrupted sessions
- ✅ Interactive CLI with vendor and category selection

### Performance Requirements
- ✅ Average extraction time <30 seconds per product
- ✅ Success rate >85% across all sites
- ✅ Handle concurrent scraping of 3+ sites
- ✅ Memory usage <2GB during peak operation

### Quality Requirements
- ✅ Data quality score >80% average across all products
- ✅ <5% duplicate products within same vendor/category
- ✅ All required schema fields populated for >95% of products
- ✅ Image URLs accessible for >90% of products

This strategy provides a comprehensive foundation for implementing robust, scalable, and compliant multi-site ecommerce scraping across the UK retail landscape.
