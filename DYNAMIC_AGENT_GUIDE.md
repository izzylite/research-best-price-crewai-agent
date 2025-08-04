# Dynamic Multi-Agent Scraping Guide

## 🎯 Overview

This system replaces the problematic BatchProcessor threading approach with CrewAI's native multi-agent orchestration to eliminate the "signal only works in main thread" errors while maintaining concurrent scraping capabilities.

## 🤖 How Dynamic Agent Delegation Works

### The Complete Flow

```
1. User Selection
   ├── Vendors: ASDA, Tesco, etc.
   ├── Categories: Electronics, Clothing, etc.
   └── Scope: Recent (3 pages) vs Complete (all pages)
   
2. Plan Creation
   ├── Session ID: scraping_20250803_203045
   ├── Scope Configuration: max_pages = 3 or None
   ├── Estimated Products & Duration
   └── URL Extraction from Categories
   
3. Multi-Agent Category Scraping (No Discovery Needed!)
   ├── CLI provides direct URLs:
   │   ├── "https://groceries.asda.com/dept/food-cupboard/tinned-food_1215286"
   │   ├── "https://groceries.asda.com/dept/fresh-food/fruit_1215135"
   │   └── "https://groceries.asda.com/dept/fresh-food/vegetables_1215136"
   │
   ├── Category Crew #1 (Tinned Food)
   │   ├── ProductScraperAgent: Extracts products directly from page (Browserbase session #1)
   │   ├── DataExtractorAgent: Standardizes prices/images (Browserbase session #2)
   │   └── DataValidatorAgent: Validates final output (ProductDataValidator)
   │
   ├── Category Crew #2 (Fruit)
   │   ├── ProductScraperAgent: Extracts products directly from page (Browserbase session #3)
   │   ├── DataExtractorAgent: Standardizes prices/images (Browserbase session #4)
   │   └── DataValidatorAgent: Validates final output (ProductDataValidator)
   │
   └── Category Crew #3 (Vegetables)
       ├── ProductScraperAgent: Extracts products directly from page (Browserbase session #5)
       ├── DataExtractorAgent: Standardizes prices/images (Browserbase session #6)
       └── DataValidatorAgent: Validates final output (ProductDataValidator)
   
4. CrewAI Orchestration
   ├── Runs agents concurrently (no threading issues!)
   ├── Each agent operates independently
   ├── Automatic error isolation
   └── Results combined into final dataset
```

## 🔧 Key Components

### 1. Scope Configuration

```python
SCRAPING_SCOPES = {
    "recent": {
        "name": "Recent products only",
        "description": "First 2-3 pages per category (faster, good for testing)",
        "max_pages": 3
    },
    "complete": {
        "name": "All available products", 
        "description": "Complete product catalog (comprehensive, slower)",
        "max_pages": None
    }
}
```

**How it works:**
- User selects scope during interactive setup
- `max_pages` parameter passed to each SubCategoryScraperAgent
- Agents respect pagination limits based on scope

### 2. Plan Integration

```python
plan = {
    "session_id": "scraping_20250803_203045",
    "scope": "recent",
    "vendors": {...},
    "total_estimated_products": 500,
    "estimated_duration_minutes": 30
}
```

**How it works:**
- Plan created during interactive setup
- Session ID used for tracking and logging
- Scope configuration passed to dynamic scraper
- Progress tracked against plan estimates

### 3. Multi-Agent Crew Creation

```python
# For each URL from CLI selection, create a specialized crew
category_data = {
    "name": "Tinned Food",
    "url": "https://groceries.asda.com/dept/food-cupboard/tinned-food_1215286"
}

# Create specialized agents (like main.py)
product_scraper = CategoryScraperAgent.create_product_scraper_agent("Tinned Food", agent_id=1)
data_extractor = CategoryScraperAgent.create_data_extractor_agent("Tinned Food", agent_id=2)
data_validator = CategoryScraperAgent.create_data_validator_agent("Tinned Food", agent_id=3)

# Create tasks for each agent
scraping_task = CategoryScraperAgent.create_product_scraping_task(category_data, "asda", product_scraper, max_pages=3)
extraction_task = CategoryScraperAgent.create_data_extraction_task(category_data, "asda", data_extractor)
validation_task = CategoryScraperAgent.create_data_validation_task(category_data, "asda", data_validator)

# Execute with multi-agent crew
crew = Crew(
    agents=[product_scraper, data_extractor, data_validator],
    tasks=[scraping_task, extraction_task, validation_task],
    process=Process.sequential
)
```

**How it works:**
- **Multi-agent crew per category** (like main.py architecture)
- **Specialized roles**: Product extraction → Data standardization → Validation
- **Tool distribution**: Each agent gets only the tools they need
- **Sequential processing**: Extract → Standardize → Validate pipeline
- **Independent Browserbase sessions** for extraction and standardization agents
- **Scope integration**: Max pages passed to extraction task only
- **Direct product access**: First step extracts products immediately (no navigation needed)

## 🚀 Advantages Over BatchProcessor

| Aspect | BatchProcessor (Old) | Dynamic Agents (New) |
|--------|---------------------|---------------------|
| **Threading** | Custom worker threads → Signal errors | CrewAI native execution ✅ |
| **Concurrency** | Fixed thread pool | One agent per CLI-selected URL ✅ |
| **Error Handling** | Batch-level failures | Agent-level isolation ✅ |
| **Scope Integration** | ❌ Not implemented | ✅ Fully integrated |
| **Plan Tracking** | ❌ Limited | ✅ Session ID + progress |
| **Observability** | Basic batch progress | Per-agent detailed logging ✅ |
| **URL Usage** | ❌ Ignored CLI selections | ✅ Direct scraping of CLI URLs |
| **Unnecessary Discovery** | ❌ N/A | ✅ Eliminated - no CategoryDiscoveryAgent |

## 📊 Scope Impact Examples

### Recent Scope (max_pages: 3)
```
Electronics Category
├── Phones: Pages 1-3 → ~75 products
├── Laptops: Pages 1-3 → ~75 products  
└── Tablets: Pages 1-3 → ~75 products
Total: ~225 products in ~6 minutes
```

### Complete Scope (max_pages: None)
```
Electronics Category  
├── Phones: All pages → ~500 products
├── Laptops: All pages → ~400 products
└── Tablets: All pages → ~300 products
Total: ~1200 products in ~30 minutes
```

## 🔍 Session Tracking

Each scraping session gets:
- **Unique Session ID**: `scraping_20250803_203045`
- **Plan File**: `scraping_plans/scraping_20250803_203045.json`
- **Agent Logs**: Individual agent progress and results
- **Progress Tracking**: Real-time updates per agent

## 🛠️ Configuration

### Dynamic Scraper Initialization
```python
dynamic_scraper = DynamicMultiAgentScraper(
    max_concurrent_agents=3,           # Max agents per category
    max_pages_per_category=3,          # From scope selection
    session_id="scraping_20250803_203045"  # From plan
)
```

### Agent Task Configuration
```python
task_description = f"""
Scrape products from: {subcategory['name']}
Max pages to scrape: {max_pages or 'All available'}

Your task is to:
1. Navigate to the subcategory page
2. Extract all visible products with complete details
3. Handle pagination to get products from up to {max_pages} pages
4. Validate and standardize the product data
...
"""
```

## 🎯 Next Steps

1. **Test the Integration**: Run `python enhanced_interactive_scraper.py`
2. **Monitor Agent Behavior**: Check that scope limits are respected
3. **Verify Session Tracking**: Ensure plan files are created correctly
4. **Performance Testing**: Compare recent vs complete scope timing

The dynamic agent approach maintains all the planning and scoping functionality while eliminating threading issues through CrewAI's native orchestration capabilities.
