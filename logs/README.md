# Logs Directory

This directory contains comprehensive logs for debugging and monitoring the ecommerce scraper system.

## Log Structure

Each scraping session creates a subdirectory with the following files:

```
logs/
├── session_YYYYMMDD_HHMMSS/
│   ├── ai_thoughts.jsonl          # AI agent thoughts and reasoning
│   ├── tool_calls.jsonl           # All tool calls with inputs/outputs
│   ├── task_events.jsonl          # Task lifecycle events
│   ├── ai_activity.log            # Standard log format
│   └── session_summary.json       # Session statistics and summary
```

## File Descriptions

### ai_thoughts.jsonl
Records AI agent thoughts and reasoning processes:
```json
{
  "timestamp": "2025-08-03T23:20:31.495Z",
  "agent_name": "Multi-Vendor Product Scraping Coordinator",
  "thought": "I need to navigate to the category URL and extract products...",
  "context": "scraping_task",
  "task_id": "e09d587b-550a-4849-8da0-ebd7a0cdd7c5"
}
```

### tool_calls.jsonl
Records all tool calls with detailed information:
```json
{
  "timestamp": "2025-08-03T23:20:31.495Z",
  "agent_name": "Multi-Vendor Product Scraping Coordinator",
  "tool_name": "ecommerce_stagehand_tool",
  "tool_input": {"instruction": "Navigate to URL", "url": "https://..."},
  "tool_output": "Successfully navigated to...",
  "execution_time_ms": 1250.5,
  "success": true,
  "error": null
}
```

### task_events.jsonl
Records task lifecycle events:
```json
{
  "timestamp": "2025-08-03T23:20:31.495Z",
  "task_id": "e09d587b-550a-4849-8da0-ebd7a0cdd7c5",
  "agent_name": "Multi-Vendor Product Scraping Coordinator",
  "event_type": "started",
  "description": "Scraping task initiated for ASDA fruit category",
  "metadata": {"vendor": "asda", "category": "Fruit"}
}
```

### session_summary.json
Contains session statistics:
```json
{
  "session_start": "2025-08-03T23:20:24.000Z",
  "session_end": "2025-08-03T23:25:30.000Z",
  "total_thoughts": 15,
  "total_tool_calls": 8,
  "total_tasks": 3,
  "successful_tool_calls": 7,
  "failed_tool_calls": 1,
  "tool_success_rate": 0.875,
  "agents_used": ["Multi-Vendor Product Scraping Coordinator", "Data Extractor"],
  "tools_used": ["ecommerce_stagehand_tool", "product_data_validator"]
}
```

## Usage

The logging system is automatically initialized when the scraper runs. To access logs programmatically:

```python
from ecommerce_scraper.logging.ai_logger import get_ai_logger

# Get the current logger
logger = get_ai_logger()

# Get recent thoughts
recent_thoughts = logger.get_recent_thoughts(limit=10)

# Get recent tool calls
recent_calls = logger.get_recent_tool_calls(limit=10)

# Get session summary
summary = logger.get_session_summary()
```

## Log Retention

- Logs are kept indefinitely for debugging purposes
- Each session creates a new directory
- Old logs can be manually cleaned up if disk space is a concern
- Consider archiving logs older than 30 days

## Debugging Tips

1. **Check tool_calls.jsonl** for failed tool executions
2. **Review ai_thoughts.jsonl** to understand agent reasoning
3. **Monitor task_events.jsonl** for task flow issues
4. **Use session_summary.json** for quick performance overview

## Privacy Note

Logs may contain URLs and extracted data. Ensure logs are stored securely and not exposed publicly.
