# AI Activity Logging System

The ecommerce scraper now includes a comprehensive logging system that tracks all AI agent thoughts, tool calls, and task events. This helps with debugging, monitoring, and understanding how the AI agents make decisions.

## Features

### 🔍 **Comprehensive Tracking**
- **AI Thoughts**: Captures agent reasoning and decision-making processes
- **Tool Calls**: Logs all tool executions with inputs, outputs, and timing
- **Task Events**: Tracks task lifecycle (started, completed, failed, delegated)
- **Session Management**: Organizes logs by scraping session for easy analysis

### 📊 **Rich Analytics**
- Success/failure rates for tool calls
- Execution timing and performance metrics
- Agent activity summaries
- Session statistics and summaries

### 🛠️ **Easy Debugging**
- Structured JSON logs for programmatic analysis
- Human-readable log files for manual review
- CLI tool for viewing and analyzing logs
- Real-time logging during scraping operations

## Quick Start

### 1. Automatic Logging
Logging is automatically enabled when you run the scraper:

```bash
python enhanced_interactive_scraper.py
```

The system will display the session ID and log location:
```
🔍 AI Logging enabled for session: scraper_20250803_142530
📁 Logs will be saved to: logs/scraper_20250803_142530/
```

### 2. View Logs
Use the log viewer to analyze your scraping sessions:

```bash
# List all available sessions
python view_logs.py

# View specific session details
python view_logs.py --session scraper_20250803_142530

# View AI thoughts only
python view_logs.py --session scraper_20250803_142530 --thoughts

# View tool calls only  
python view_logs.py --session scraper_20250803_142530 --tools

# View task events only
python view_logs.py --session scraper_20250803_142530 --tasks

# Limit number of entries shown
python view_logs.py --session scraper_20250803_142530 --tools --limit 20
```

## Log Structure

Each scraping session creates a directory with these files:

```
logs/
├── session_YYYYMMDD_HHMMSS/
│   ├── ai_thoughts.jsonl          # AI agent thoughts and reasoning
│   ├── tool_calls.jsonl           # All tool calls with inputs/outputs  
│   ├── task_events.jsonl          # Task lifecycle events
│   ├── ai_activity.log            # Standard log format
│   └── session_summary.json       # Session statistics and summary
```

### AI Thoughts (ai_thoughts.jsonl)
Records agent reasoning processes:
```json
{
  "timestamp": "2025-08-03T14:25:31.495Z",
  "agent_name": "Multi-Vendor Product Scraping Coordinator", 
  "thought": "I need to navigate to the category URL and extract products...",
  "context": "scraping_task",
  "task_id": "e09d587b-550a-4849-8da0-ebd7a0cdd7c5"
}
```

### Tool Calls (tool_calls.jsonl)
Records all tool executions:
```json
{
  "timestamp": "2025-08-03T14:25:31.495Z",
  "agent_name": "Multi-Vendor Product Scraping Coordinator",
  "tool_name": "ecommerce_stagehand_tool.navigate",
  "tool_input": {"url": "https://groceries.asda.com/dept/fruit-veg-salad/fruit/..."},
  "tool_output": "Successfully navigated to category page",
  "execution_time_ms": 1250.5,
  "success": true,
  "error": null
}
```

### Task Events (task_events.jsonl)
Records task lifecycle:
```json
{
  "timestamp": "2025-08-03T14:25:31.495Z", 
  "task_id": "e09d587b-550a-4849-8da0-ebd7a0cdd7c5",
  "agent_name": "Multi-Vendor Product Scraping Coordinator",
  "event_type": "started",
  "description": "Scraping task initiated for ASDA fruit category",
  "metadata": {"vendor": "asda", "category": "Fruit"}
}
```

### Session Summary (session_summary.json)
Contains session statistics:
```json
{
  "session_start": "2025-08-03T14:25:24.000Z",
  "session_end": "2025-08-03T14:30:30.000Z", 
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

## Debugging Workflows

### 1. **Identify Failed Tool Calls**
```bash
python view_logs.py --session SESSION_ID --tools
```
Look for ❌ symbols indicating failed tool calls.

### 2. **Understand Agent Reasoning**
```bash
python view_logs.py --session SESSION_ID --thoughts
```
Review agent thoughts to understand decision-making process.

### 3. **Track Task Flow**
```bash
python view_logs.py --session SESSION_ID --tasks
```
Monitor task progression and identify bottlenecks.

### 4. **Performance Analysis**
Check session summary for:
- Tool success rates
- Execution times
- Agent efficiency

## Programmatic Access

You can also access logs programmatically:

```python
from ecommerce_scraper.logging import get_ai_logger, LogViewer

# Get current session logger
logger = get_ai_logger()

# Get recent thoughts
recent_thoughts = logger.get_recent_thoughts(limit=10)

# Get recent tool calls
recent_calls = logger.get_recent_tool_calls(limit=10)

# Get session summary
summary = logger.get_session_summary()

# Use log viewer for analysis
viewer = LogViewer("logs")
sessions = viewer.list_sessions()
session_summary = viewer.load_session_summary(sessions[0])
```

## Configuration

### Log Retention
- Logs are kept indefinitely by default
- Each session creates a new directory
- Consider archiving logs older than 30 days for disk space management

### Privacy Considerations
- Logs may contain URLs and extracted data
- Store logs securely and avoid public exposure
- Consider data retention policies for compliance

## Troubleshooting

### Common Issues

**1. No logs generated**
- Ensure the scraper is running with logging enabled
- Check file permissions in the logs directory

**2. Missing session data**
- Verify the session completed successfully
- Check for errors in ai_activity.log

**3. Large log files**
- Use the --limit parameter to view recent entries
- Consider log rotation for long-running sessions

### Getting Help

If you encounter issues with the logging system:

1. Check the ai_activity.log file for error messages
2. Verify all dependencies are installed
3. Ensure proper file permissions for the logs directory
4. Review the session summary for overall health metrics

## Benefits

### For Developers
- **Debugging**: Quickly identify where and why scraping fails
- **Optimization**: Analyze performance bottlenecks and tool efficiency
- **Monitoring**: Track system health and success rates

### For Users
- **Transparency**: Understand what the AI agents are doing
- **Reliability**: Confidence in the scraping process
- **Troubleshooting**: Self-service debugging capabilities

The logging system transforms the ecommerce scraper from a "black box" into a transparent, debuggable, and monitorable system that provides deep insights into AI agent behavior and system performance.
