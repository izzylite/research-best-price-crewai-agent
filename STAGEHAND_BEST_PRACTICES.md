# Stagehand Best Practices Implementation

This document outlines the comprehensive implementation of Stagehand best practices in our ecommerce scraper, based on the official [Stagehand documentation](https://docs.stagehand.dev/get_started/introduction).

## 🔐 Security Improvements

### 1. Variable Substitution for Sensitive Data

**Before (Insecure):**
```python
tool._run(
    instruction="Type 'user@example.com' in the email field",
    command_type="act"
)
```

**After (Secure):**
```python
tool._run(
    instruction="Type %email% in the email field",
    command_type="act",
    variables={"email": "user@example.com"}
)
```

### 2. Environment Variable Management

- ✅ Removed all hardcoded API keys from source code
- ✅ Implemented secure configuration management with `pydantic-settings`
- ✅ Added validation for required environment variables
- ✅ Created safe configuration display that masks sensitive data

## 👀 Action Previewing with observe()

### Preview Actions Before Execution

```python
# Preview what actions are available
preview_result = tool.preview_action(
    instruction="Find the add to cart button"
)

# Execute specific observed action
tool.execute_observed_action(
    action_dict=preview_result,
    variables={"quantity": "2"}
)
```

### Benefits:
- Reduces LLM inference costs
- Prevents unintended actions
- Allows for action validation before execution

## ⚛️ Atomic and Specific Instructions

### Before (Broad Instructions):
```python
# ❌ BAD: Too broad and multi-step
tool._run(instruction="Fill out the form and submit it")
```

### After (Atomic Instructions):
```python
# ✅ GOOD: Atomic and specific
tool._run(instruction="Type %email% in the email input field", variables={"email": "user@example.com"})
tool._run(instruction="Type %password% in the password field", variables={"password": "secure123"})
tool._run(instruction="Click the 'Sign In' button")
```

## 💾 Caching for Performance

### Automatic Caching
```python
# First call - executes and caches
result1 = tool._run(
    instruction="Extract product title and price",
    command_type="extract",
    use_cache=True
)

# Second call - uses cache
result2 = tool._run(
    instruction="Extract product title and price", 
    command_type="extract",
    use_cache=True
)
```

### Cache Management
```python
# Check cache statistics
cache_stats = tool.get_cache_stats()

# Clear cache manually
tool.clear_cache()
```

## 🔄 Enhanced Error Handling and Retry Logic

### Automatic Retries with Exponential Backoff
```python
# Automatically retries failed operations up to max_retries times
# with exponential backoff (2^attempt seconds)
result = tool._run(
    instruction="Click the submit button",
    command_type="act"
)
```

### Configuration
```python
# In settings.py
max_retries: int = Field(3, env="MAX_RETRIES")
```

## 🏗️ Context Manager Pattern

### Automatic Resource Cleanup
```python
# Old way - manual cleanup required
tool = EcommerceStagehandTool()
try:
    result = tool._run(instruction="Navigate to product page")
finally:
    tool.close()

# New way - automatic cleanup
with EcommerceStagehandTool.create_with_context() as tool:
    result = tool._run(instruction="Navigate to product page")
    # Automatically cleaned up when exiting context
```

## 📊 Enhanced Logging and Monitoring

### Structured Logging
```python
# Configurable log levels and formats
log_level: str = Field("INFO", env="LOG_LEVEL")
log_format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Automatic log file creation
settings.setup_logging()  # Creates ecommerce_scraper.log
```

### Session Information
```python
# Get detailed session information
session_info = tool.get_session_info()
print(session_info)
# Output:
# {
#   "has_active_session": True,
#   "current_url": "https://example.com",
#   "cache_size": 5,
#   "settings": {...}
# }
```

## 🚀 Performance Optimizations

### 1. Intelligent Caching
- Caches extract and observe operations
- Configurable TTL (Time To Live)
- Automatic cache cleanup on session close

### 2. Retry Logic with Backoff
- Exponential backoff prevents overwhelming servers
- Configurable retry attempts
- Detailed error logging

### 3. Session Management
- Proper session lifecycle management
- Resource cleanup on errors
- Context manager support

## 📝 Usage Examples

### Basic Usage with Best Practices
```python
from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool

# Use context manager for automatic cleanup
with EcommerceStagehandTool.create_with_context() as tool:
    # Navigate with atomic instruction
    tool._run(
        instruction="Navigate to the product page",
        url="https://demo.vercel.store/products/acme-mug",
        command_type="act"
    )
    
    # Preview before acting
    preview = tool.preview_action("Find the add to cart button")
    print(f"Available actions: {preview}")
    
    # Extract with caching
    product_data = tool._run(
        instruction="Extract product title, price, and description",
        command_type="extract",
        use_cache=True
    )
    
    # Secure form interaction
    tool._run(
        instruction="Type %email% in the email field",
        command_type="act",
        variables={"email": "secure@example.com"}
    )
```

### Advanced Product Extraction
```python
with EcommerceStagehandTool.create_with_context() as tool:
    # Navigate to product
    tool._run(
        instruction="Navigate to product page",
        url="https://demo.vercel.store/products/acme-circles-t-shirt",
        command_type="act"
    )
    
    # Use enhanced extraction method
    product_data = tool.extract_product_data()
    
    # Get session statistics
    session_info = tool.get_session_info()
    cache_stats = tool.get_cache_stats()
    
    print(f"Session: {session_info}")
    print(f"Cache: {cache_stats}")
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_project_id
OPENAI_API_KEY=your_openai_api_key

# Optional Performance Settings
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
MAX_RETRIES=3
DEFAULT_DELAY_BETWEEN_REQUESTS=2

# Optional Security Settings
ENABLE_VARIABLE_SUBSTITUTION=true
LOG_SENSITIVE_DATA=false

# Optional Logging Settings
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 🎯 Key Benefits

1. **Security**: No sensitive data sent to LLMs
2. **Performance**: Intelligent caching and retry logic
3. **Reliability**: Atomic instructions and error handling
4. **Maintainability**: Clean code with context managers
5. **Observability**: Comprehensive logging and monitoring
6. **Cost Efficiency**: Reduced LLM API calls through caching and previewing

## 🚀 Getting Started

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Set environment variables**: Copy `.env.example` to `.env` and fill in your API keys
3. **Run the example**: `python examples/stagehand_best_practices_example.py`
4. **Use in your code**: Import and use `EcommerceStagehandTool` with context managers

This implementation makes our ecommerce scraper production-ready with enterprise-grade security, performance, and reliability features! 🤘
