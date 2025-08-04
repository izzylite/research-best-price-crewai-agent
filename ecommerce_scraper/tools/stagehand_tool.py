"""Enhanced Stagehand tool for ecommerce scraping with CrewAI."""

import time
import json
import asyncio
import logging
import hashlib
from typing import Any, Dict, Optional
from crewai.tools import BaseTool
from stagehand import Stagehand
from stagehand.schemas import AvailableModel
from pydantic import BaseModel, Field

from ..config.settings import settings


# Global persistent event loop for Stagehand operations
_stagehand_loop = None
_stagehand_thread = None
_loop_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None

def _get_persistent_loop():
    """Get or create a persistent event loop for Stagehand operations."""
    global _stagehand_loop, _stagehand_thread
    import threading

    if _stagehand_loop is None or _stagehand_loop.is_closed():
        def create_loop():
            global _stagehand_loop
            _stagehand_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_stagehand_loop)
            _stagehand_loop.run_forever()

        _stagehand_thread = threading.Thread(target=create_loop, daemon=True)
        _stagehand_thread.start()

        # Wait for loop to be ready
        import time
        while _stagehand_loop is None:
            time.sleep(0.01)

    return _stagehand_loop

def run_async_safely(coro):
    """
    Run async operations in a persistent event loop to maintain session context.
    This fixes the root cause by ensuring all Stagehand operations use the same event loop.
    """
    loop = _get_persistent_loop()

    # Submit the coroutine to the persistent loop
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


class StagehandInput(BaseModel):
    """Input schema for Stagehand tool with enhanced security and best practices."""
    instruction: str = Field(..., description="Natural language instruction for the browser action")
    url: Optional[str] = Field(None, description="URL to navigate to (if not already on the page)")
    command_type: str = Field("act", description="Type of command: 'act', 'extract', 'observe', or 'preview'")
    selector: Optional[str] = Field(None, description="CSS selector to limit scope (for extract/observe)")
    wait_time: Optional[int] = Field(None, description="Time to wait before executing (in seconds)")
    variables: Optional[Dict[str, str]] = Field(None, description="Variables for sensitive data substitution (e.g., {'email': 'user@example.com'})")
    preview_only: bool = Field(False, description="If True, only preview the action without executing it")
    use_cache: bool = Field(True, description="Whether to use cached results for repeated operations")
    extraction_schema: Optional[Any] = Field(None, description="Pydantic model class for structured extraction (extract command only)")


class EcommerceStagehandTool(BaseTool):
    """Enhanced Stagehand tool optimized for ecommerce scraping with best practices."""

    name: str = "ecommerce_stagehand_tool"
    description: str = """
    Enhanced AI-powered browser automation tool for ecommerce scraping following Stagehand best practices.
    Features schema-based extraction, observe-then-act patterns, and built-in variable substitution.

    Command types:
    - 'act': Perform actions like clicking, typing, scrolling, navigating (with built-in variable support)
    - 'extract': Extract structured data using Pydantic schemas (StandardizedProduct, ProductBatch)
    - 'observe': Identify and analyze elements with suggested actions
    - 'preview': Preview actions without executing them (uses observe internally)

    Enhanced Features:
    - Schema-based extraction: Use 'schema' parameter with Pydantic models for structured data
    - Built-in variable substitution: Pass variables directly to Stagehand (no manual substitution)
    - Intelligent caching: Automatic caching of safe operations (extract, observe, preview)
    - Simplified async handling: Robust async/sync integration following Stagehand patterns

    Best Practices:
    - Use extraction_schema parameter for structured extraction: extraction_schema=StandardizedProduct
    - Use variables for sensitive data: variables={"email": "user@example.com"}
    - Use preview command for action previewing before execution
    - Be atomic and specific in instructions

    Examples:
    - Schema extraction: instruction="Extract product data", command_type="extract", extraction_schema=StandardizedProduct
    - Secure action: instruction="Type %email% in email field", variables={"email": "user@example.com"}
    - Action preview: instruction="Find login button", command_type="preview"
    """
    args_schema: type[BaseModel] = StagehandInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._stagehand: Optional[Stagehand] = None
        self._current_url: Optional[str] = None
        self._cache: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)

        # Setup logging if not already configured
        if not self._logger.handlers:
            settings.setup_logging()



    def _get_cache_key(self, instruction: str, url: Optional[str] = None, command_type: str = "act") -> str:
        """Generate cache key for operation."""
        cache_data = f"{instruction}:{url}:{command_type}"
        return hashlib.md5(cache_data.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Get cached result if available and not expired."""
        if not settings.enable_caching or cache_key not in self._cache:
            return None

        cached_item = self._cache[cache_key]
        if time.time() - cached_item['timestamp'] > settings.cache_ttl_seconds:
            del self._cache[cache_key]
            return None

        self._logger.debug(f"Using cached result for key: {cache_key[:8]}...")
        return cached_item['result']

    def _cache_result(self, cache_key: str, result: str) -> None:
        """Cache operation result."""
        if settings.enable_caching:
            self._cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }

    def _get_stagehand(self) -> Stagehand:
        """Get or create Stagehand instance with enhanced error handling."""
        if self._stagehand is None:
            # Determine model name from settings
            model_name = getattr(AvailableModel, settings.stagehand_model_name.upper().replace('-', '_'),
                                AvailableModel.GPT_4O)

            self._stagehand = Stagehand(
                api_key=settings.browserbase_api_key,
                project_id=settings.browserbase_project_id,
                model_api_key=settings.get_model_api_key(),
                model_name=model_name,
                dom_settle_timeout_ms=settings.stagehand_dom_settle_timeout_ms,
                headless=settings.stagehand_headless,
                verbose=settings.stagehand_verbose,
                self_heal=True,
                wait_for_captcha_solves=True,
            )

            # Initialize Stagehand using enhanced async wrapper
            try:
                print("🔄 Initializing Stagehand session...")
                run_async_safely(self._stagehand.init())
                print("✅ Stagehand session initialized successfully")
            except Exception as e:
                print(f"❌ Error: Failed to initialize Stagehand: {e}")
                self._stagehand = None
                raise

        return self._stagehand

    def _safe_async_call(self, async_func, *args, **kwargs):
        """Safely call an async function with proper isolation."""
        coro = async_func(*args, **kwargs)
        return run_async_safely(coro)

    def _run(self, **kwargs) -> str:
        """Execute the Stagehand command with best practices."""
        try:
            # Extract parameters from kwargs and remove them to avoid conflicts
            instruction = kwargs.pop("instruction", None)
            url = kwargs.pop("url", None)
            command_type = kwargs.pop("command_type", "act")
            selector = kwargs.pop("selector", None)
            wait_time = kwargs.pop("wait_time", None)
            use_cache = kwargs.pop("use_cache", True)

            if not instruction:
                return "Error: instruction is required"

            # Preview command will be handled in _execute_with_retry
            # No need to convert here

            # Variables will be handled by Stagehand's built-in system
            # No need for manual substitution

            # Check cache first (only for safe operations that don't change state)
            cache_key = None
            if use_cache and command_type in ["extract", "observe", "preview"]:
                cache_key = self._get_cache_key(instruction, url, command_type)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
            
            stagehand = self._get_stagehand()
            
            # Navigate to URL if provided and different from current
            if url and url != self._current_url:
                # Ensure Stagehand is initialized before using page
                if not hasattr(stagehand, 'page') or stagehand.page is None:
                    return "Error: Stagehand page is not initialized. Please check the configuration."

                try:
                    print(f"Navigating to: {url}")
                    # Use safe async call to avoid coroutine reuse
                    self._safe_async_call(stagehand.page.goto, url)
                    self._current_url = url
                    print("Navigation completed")

                    # Auto-handle common popups after navigation
                    # self._auto_handle_popups(stagehand)

                    # If this is just a navigation request, return success
                    if instruction and any(nav_word in instruction.lower() for nav_word in ['navigate', 'go to', 'visit', 'open']):
                        return f"Successfully navigated to {url}"

                except Exception as e:
                    error_msg = str(e)
                    self._logger.error(f"Navigation error: {error_msg}")

                    # Log the error but don't reinitialize to avoid creating new sessions
                    self._logger.warning(f"Navigation failed: {error_msg}")
                    return f"Error navigating to {url}: {error_msg}"
            
            # Wait if specified (keep this for user-requested delays)
            if wait_time:
                time.sleep(wait_time)

            # Add ecommerce-specific delay to be respectful (keep this for rate limiting)
            if self._current_url:
                time.sleep(settings.default_delay_between_requests)

            # Execute command based on type with retry logic
            result = self._execute_with_retry(stagehand, command_type, instruction, selector, **kwargs)

            # Cache result if applicable
            if cache_key and result and not result.startswith("Error"):
                self._cache_result(cache_key, result)

            return result
                
        except Exception as e:
            self._logger.error(f"Error executing Stagehand command: {str(e)}")
            return f"Error executing Stagehand command: {str(e)}"



    def _execute_with_retry(self, stagehand: Stagehand, command_type: str, instruction: str, selector: Optional[str] = None, **kwargs) -> str:
        """Execute command with retry logic and proper error handling."""
        last_error = None

        for attempt in range(settings.max_retries):
            try:
                self._logger.info(f"Executing {command_type} command (attempt {attempt + 1}): {instruction[:50]}...")

                if command_type == "act":
                    # Use longer DOM settle timeout on retry attempts
                    dom_timeout = 5000 if attempt > 0 else 3000
                    variables = kwargs.get("variables")

                    # Use Stagehand's built-in variable substitution
                    if variables:
                        result = self._safe_async_call(stagehand.page.act,
                            action=instruction,
                            variables=variables,
                            domSettleTimeoutMs=dom_timeout
                        )
                    else:
                        result = self._safe_async_call(stagehand.page.act, instruction, domSettleTimeoutMs=dom_timeout)

                    self._logger.info("Action completed")
                    return f"Action completed: {result}"

                elif command_type == "extract":
                    # Use longer DOM settle timeout on retry attempts
                    dom_timeout = 5000 if attempt > 0 else 3000

                    # Check if we should use structured schema extraction
                    schema = kwargs.get("extraction_schema")
                    if schema:
                        # Use Pydantic schema for structured extraction
                        if selector:
                            result = self._safe_async_call(stagehand.page.extract,
                                instruction=instruction,
                                schema=schema,
                                selector=selector,
                                domSettleTimeoutMs=dom_timeout
                            )
                        else:
                            result = self._safe_async_call(stagehand.page.extract,
                                instruction=instruction,
                                schema=schema,
                                domSettleTimeoutMs=dom_timeout
                            )

                        # Return structured result
                        if hasattr(result, 'model_dump'):
                            return json.dumps(result.model_dump(), indent=2, default=str)
                        else:
                            return json.dumps(result, indent=2, default=str)
                    else:
                        # Fallback to text-based extraction
                        if selector:
                            result = run_async_safely(stagehand.page.extract(instruction, selector=selector, domSettleTimeoutMs=dom_timeout))
                        else:
                            result = run_async_safely(stagehand.page.extract(instruction, domSettleTimeoutMs=dom_timeout))

                    self._logger.info("Data extracted")
                    # Try to format as JSON if possible
                    try:
                        if isinstance(result, str):
                            # Try to parse as JSON
                            parsed = json.loads(result)
                            return json.dumps(parsed, indent=2)
                        else:
                            return json.dumps(result, indent=2, default=str)
                    except (json.JSONDecodeError, TypeError):
                        return str(result)

                elif command_type == "observe":
                    # Use longer DOM settle timeout on retry attempts
                    dom_timeout = 5000 if attempt > 0 else 3000

                    # Use Stagehand's built-in observe parameters
                    observe_params = {
                        "instruction": instruction,
                        "domSettleTimeoutMs": dom_timeout,
                        "returnAction": True  # Always return suggested actions
                    }

                    if selector:
                        observe_params["selector"] = selector

                    result = run_async_safely(stagehand.page.observe(**observe_params))
                    self._logger.info("Elements observed")

                    # Format observe results for better readability
                    if isinstance(result, list) and result:
                        formatted_results = []
                        for i, action in enumerate(result[:5]):  # Limit to top 5 actions
                            if isinstance(action, dict):
                                formatted_results.append(f"{i+1}. {action.get('description', 'Unknown action')}")
                            else:
                                formatted_results.append(f"{i+1}. {str(action)}")
                        return f"Observed elements:\n" + "\n".join(formatted_results)
                    else:
                        return f"Observed elements: {result}"

                elif command_type == "preview":
                    # Preview is the same as observe but with explicit preview context
                    dom_timeout = 5000 if attempt > 0 else 3000

                    observe_params = {
                        "instruction": instruction,
                        "domSettleTimeoutMs": dom_timeout,
                        "returnAction": True  # Always return suggested actions for preview
                    }

                    if selector:
                        observe_params["selector"] = selector

                    result = run_async_safely(stagehand.page.observe(**observe_params))
                    self._logger.info("Action previewed")

                    # Format preview results with preview-specific messaging
                    if isinstance(result, list) and result:
                        formatted_results = []
                        for i, action in enumerate(result[:3]):  # Limit to top 3 for preview
                            if isinstance(action, dict):
                                formatted_results.append(f"{i+1}. Preview: {action.get('description', 'Unknown action')}")
                            else:
                                formatted_results.append(f"{i+1}. Preview: {str(action)}")
                        return f"Action preview (top suggestions):\n" + "\n".join(formatted_results)
                    else:
                        return f"Action preview: {result}"

                else:
                    return f"Error: Unknown command type '{command_type}'. Use 'act', 'extract', 'observe', or 'preview'."

            except Exception as e:
                last_error = e
                error_msg = str(e)
                self._logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

                # Handle specific CDP errors that require special treatment
                if "Object id doesn't reference a Node" in error_msg or "DOM.describeNode" in error_msg:
                    self._logger.info("CDP DOM error detected - waiting for page to stabilize")

                    # Try to refresh the page state using Stagehand's built-in waiting
                    try:
                        if hasattr(stagehand, 'page') and stagehand.page:
                            run_async_safely(stagehand.page.wait_for_load_state('networkidle', timeout=10000))
                            # Only use minimal sleep for DOM stability if needed
                            time.sleep(2)
                    except:
                        # Fallback to longer wait if Stagehand wait fails
                        time.sleep(5)

                elif "'NoneType' object has no attribute 'send'" in error_msg or "Page.evaluate" in error_msg:
                    self._logger.info("Browser page connection lost - waiting before retry")
                    # Don't reinitialize, just wait and let retry handle it
                    time.sleep(5)

                elif "Protocol error" in error_msg or "Session closed" in error_msg:
                    self._logger.info("Browser session error detected - longer wait before retry")
                    time.sleep(10)  # Keep this for session recovery

                if attempt < settings.max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  # Cap exponential backoff at 30 seconds
                    self._logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        return f"Error: All {settings.max_retries} attempts failed. Last error: {str(last_error)}"

    def _auto_handle_popups(self, stagehand) -> None:
        """Automatically handle common popups after navigation."""
        try:
            self._logger.info("Auto-handling common popups...")

            # Use Stagehand's built-in DOM settling instead of manual sleep

            # Try to dismiss cookie consent
            try:
                run_async_safely(stagehand.page.act(
                    "Look for cookie consent banner or privacy dialog and click Accept All, I Accept, or Accept Cookies",
                    domSettleTimeoutMs=2000
                ))
                self._logger.info("Attempted cookie consent dismissal")
            except Exception as e:
                self._logger.debug(f"Cookie consent handling failed: {e}")

            # Final check for any remaining overlays
            try:
                run_async_safely(stagehand.page.act(
                    "Look for any remaining popup, modal, or overlay blocking the main content and dismiss it",
                    domSettleTimeoutMs=2000
                ))
                self._logger.info("Attempted general popup dismissal")
            except Exception as e:
                self._logger.debug(f"General popup handling failed: {e}")

            self._logger.info("Auto popup handling completed")

        except Exception as e:
            self._logger.warning(f"Auto popup handling encountered error: {e}")

    def extract_product_data(self, **kwargs) -> str:
        """Extract structured product data using StandardizedProduct schema."""
        try:
            # Import the schema
            from ..schemas.standardized_product import StandardizedProduct

            # Use schema-based extraction for structured data
            instruction = "Extract product information from this page including name, description, price, image URL, weight, category, and vendor details"

            return self._run(
                instruction=instruction,
                command_type="extract",
                extraction_schema=StandardizedProduct,
                use_cache=True,
                **kwargs
            )

        except Exception as e:
            self._logger.error(f"Error extracting product data: {str(e)}")
            return f"Error extracting product data: {str(e)}"





    def preview_action(self, instruction: str, variables: Optional[Dict[str, str]] = None) -> str:
        """Preview an action without executing it using the preview command type."""
        try:
            return self._run(
                instruction=instruction,
                command_type="preview",  # Now properly handled in _execute_with_retry
                variables=variables,
                use_cache=True
            )
        except Exception as e:
            self._logger.error(f"Error previewing action: {str(e)}")
            return f"Error previewing action: {str(e)}"





    def close(self):
        """Close the Stagehand session and cleanup resources."""
        if self._stagehand:
            try:
                self._logger.info("Closing Browserbase session...")
                run_async_safely(self._stagehand.close())
                self._logger.info("Browserbase session closed successfully")
            except Exception as e:
                self._logger.warning(f"⚠️ Warning: Error closing Stagehand session: {e}")
            finally:
                self._stagehand = None
                self._current_url = None
                # Clear cache on session close
                self._cache.clear()
                self._logger.info("Cache cleared")
        else:
            self._logger.info("No active Stagehand session to close")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.close()
        if exc_type:
            self._logger.error(f"Exception in context manager: {exc_type.__name__}: {exc_val}")
        return False  # Don't suppress exceptions

    @classmethod
    def create_with_context(cls, **kwargs):
        """Factory method to create tool with context manager pattern."""
        return cls(**kwargs)

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session."""
        return {
            "has_active_session": self._stagehand is not None,
            "current_url": self._current_url,
            "cache_size": len(self._cache),
            "settings": settings.get_safe_config()
        }



    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._cache:
            return {"cache_size": 0, "cache_keys": []}

        return {
            "cache_size": len(self._cache),
            "cache_keys": [key[:8] + "..." for key in self._cache.keys()],
            "oldest_entry": min(item['timestamp'] for item in self._cache.values()) if self._cache else None,
            "newest_entry": max(item['timestamp'] for item in self._cache.values()) if self._cache else None
        }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close()
