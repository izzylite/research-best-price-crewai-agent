"""Enhanced Stagehand tool for ecommerce scraping with CrewAI."""

import time
import json
import asyncio
import threading
import logging
import hashlib
from typing import Any, Dict, Optional, List, Union
from crewai.tools import BaseTool
from stagehand import Stagehand
from stagehand.schemas import AvailableModel
from pydantic import BaseModel, Field

from ..config.settings import settings


def run_async_safely(coro):
    """
    Run async coroutine safely in sync context.
    Handles various event loop scenarios robustly.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, we can't use run_until_complete
            # Create a new thread to run the coroutine
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            # Loop exists but not running, use it
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(coro)
    except Exception as e:
        # Last resort: try with a new event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        except Exception as e2:
            raise Exception(f"Failed to run async operation: {e}, {e2}")


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


class EcommerceStagehandTool(BaseTool):
    """Enhanced Stagehand tool optimized for ecommerce scraping with best practices."""

    name: str = "ecommerce_stagehand_tool"
    description: str = """
    AI-powered browser automation tool for ecommerce scraping. Can navigate websites,
    interact with elements, and extract structured product data.

    Command types:
    - 'act': Perform actions like clicking, typing, scrolling, navigating
    - 'extract': Extract structured data from the current page
    - 'observe': Identify and analyze elements on the page
    - 'preview': Preview actions without executing them (uses observe internally)

    Best Practices:
    - Use variables for sensitive data: variables={"email": "user@example.com"}
    - Use preview_only=True to see actions before executing
    - Be atomic and specific in instructions
    - Use caching for repeated operations

    Examples:
    - Navigate: instruction="Navigate to the product page", url="https://example.com/product", command_type="act"
    - Extract: instruction="Extract product title and price", command_type="extract"
    - Preview: instruction="Click the login button", command_type="preview"
    - Secure input: instruction="Type %email% in email field", variables={"email": "user@example.com"}
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

    def _substitute_variables(self, instruction: str, variables: Optional[Dict[str, str]] = None) -> str:
        """Substitute variables in instruction for security."""
        if not variables or not settings.enable_variable_substitution:
            return instruction

        result = instruction
        for key, value in variables.items():
            placeholder = f"%{key}%"
            result = result.replace(placeholder, value)

        return result

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
        """Get or create Stagehand instance."""
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

            # Initialize Stagehand using our robust async helper
            try:
                print("🔄 Initializing Stagehand session...")
                run_async_safely(self._stagehand.init())
                print("✅ Stagehand session initialized successfully")
            except Exception as e:
                print(f"❌ Error: Failed to initialize Stagehand: {e}")
                self._stagehand = None
                raise

        return self._stagehand
    
    def _run(self, **kwargs) -> str:
        """Execute the Stagehand command with best practices."""
        try:
            instruction = kwargs.get("instruction")
            url = kwargs.get("url")
            command_type = kwargs.get("command_type", "act")
            selector = kwargs.get("selector")
            wait_time = kwargs.get("wait_time")
            variables = kwargs.get("variables")
            preview_only = kwargs.get("preview_only", False)
            use_cache = kwargs.get("use_cache", True)

            if not instruction:
                return "Error: instruction is required"

            # Handle preview command type
            if command_type == "preview":
                preview_only = True
                command_type = "observe"

            # Substitute variables for security
            original_instruction = instruction
            instruction = self._substitute_variables(instruction, variables)

            # Check cache first (only for extract operations to avoid side effects)
            cache_key = None
            if use_cache and command_type in ["extract", "observe"]:
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
                    print(f"🌐 Navigating to: {url}")
                    run_async_safely(stagehand.page.goto(url))
                    self._current_url = url
                    # Wait for page to load
                    time.sleep(2)
                    print("✅ Navigation completed")
                except Exception as e:
                    return f"Error navigating to {url}: {str(e)}"
            
            # Wait if specified
            if wait_time:
                time.sleep(wait_time)
            
            # Add ecommerce-specific delay to be respectful
            if self._current_url:
                time.sleep(settings.default_delay_between_requests)

            # Execute command based on type with retry logic
            result = self._execute_with_retry(stagehand, command_type, instruction, selector)

            # Cache result if applicable
            if cache_key and result and not result.startswith("Error"):
                self._cache_result(cache_key, result)

            return result
                
        except Exception as e:
            self._logger.error(f"Error executing Stagehand command: {str(e)}")
            return f"Error executing Stagehand command: {str(e)}"

    def _execute_with_retry(self, stagehand: Stagehand, command_type: str, instruction: str, selector: Optional[str] = None) -> str:
        """Execute command with retry logic and proper error handling."""
        last_error = None

        for attempt in range(settings.max_retries):
            try:
                self._logger.info(f"🔧 Executing {command_type} command (attempt {attempt + 1}): {instruction[:50]}...")

                if command_type == "act":
                    result = run_async_safely(stagehand.page.act(instruction))
                    self._logger.info("✅ Action completed")
                    return f"Action completed: {result}"

                elif command_type == "extract":
                    if selector:
                        result = run_async_safely(stagehand.page.extract(instruction, selector=selector))
                    else:
                        result = run_async_safely(stagehand.page.extract(instruction))

                    self._logger.info("✅ Data extracted")
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
                    if selector:
                        result = run_async_safely(stagehand.page.observe(instruction, selector=selector))
                    else:
                        result = run_async_safely(stagehand.page.observe(instruction))
                    self._logger.info("✅ Elements observed")

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

                else:
                    return f"Error: Unknown command type '{command_type}'. Use 'act', 'extract', or 'observe'."

            except Exception as e:
                last_error = e
                self._logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < settings.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        return f"Error: All {settings.max_retries} attempts failed. Last error: {str(last_error)}"

    def extract_product_data(self, **kwargs) -> str:
        """Extract structured product data using enhanced best practices."""
        try:
            # Use the enhanced _run method with caching and retry logic
            instruction = """Extract comprehensive product information from this page including:
- Product title/name
- Current price and original price (if on sale)
- Product description
- Brand and model information
- Availability status
- Product images (all URLs)
- Customer ratings and review count
- Product specifications and features
- Shipping information
- Product variants (sizes, colors, etc.)

Return the data in a structured JSON format."""

            return self._run(
                instruction=instruction,
                command_type="extract",
                use_cache=True
            )

        except Exception as e:
            self._logger.error(f"Error extracting product data: {str(e)}")
            return f"Error extracting product data: {str(e)}"

    def preview_action(self, instruction: str, variables: Optional[Dict[str, str]] = None) -> str:
        """Preview an action without executing it using observe()."""
        try:
            return self._run(
                instruction=instruction,
                command_type="preview",
                variables=variables,
                use_cache=True
            )
        except Exception as e:
            self._logger.error(f"Error previewing action: {str(e)}")
            return f"Error previewing action: {str(e)}"

    def execute_observed_action(self, action_dict: Dict[str, Any], variables: Optional[Dict[str, str]] = None) -> str:
        """Execute a previously observed action with variable substitution."""
        try:
            if not isinstance(action_dict, dict) or 'method' not in action_dict:
                return "Error: Invalid action dictionary. Must contain 'method' key."

            # Build instruction from action dictionary
            method = action_dict.get('method', '')
            description = action_dict.get('description', '')
            arguments = action_dict.get('arguments', [])

            if variables and arguments:
                # Substitute variables in arguments
                substituted_args = []
                for arg in arguments:
                    if isinstance(arg, str):
                        substituted_args.append(self._substitute_variables(arg, variables))
                    else:
                        substituted_args.append(arg)
                arguments = substituted_args

            instruction = f"{method.title()} on {description}"
            if arguments:
                instruction += f" with arguments: {arguments}"

            return self._run(
                instruction=instruction,
                command_type="act",
                variables=variables
            )

        except Exception as e:
            self._logger.error(f"Error executing observed action: {str(e)}")
            return f"Error executing observed action: {str(e)}"

    def close(self):
        """Close the Stagehand session and cleanup resources."""
        if self._stagehand:
            try:
                self._logger.info("🔄 Closing Browserbase session...")
                run_async_safely(self._stagehand.close())
                self._logger.info("✅ Browserbase session closed successfully")
            except Exception as e:
                self._logger.warning(f"⚠️ Warning: Error closing Stagehand session: {e}")
            finally:
                self._stagehand = None
                self._current_url = None
                # Clear cache on session close
                self._cache.clear()
                self._logger.info("🧹 Cache cleared")
        else:
            self._logger.info("ℹ️ No active Stagehand session to close")

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

    def clear_cache(self) -> None:
        """Manually clear the cache."""
        self._cache.clear()
        self._logger.info("🧹 Cache manually cleared")

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
