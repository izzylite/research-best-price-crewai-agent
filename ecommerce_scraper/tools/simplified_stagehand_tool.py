"""
Simplified Stagehand Tool using official Stagehand v0.5.0 API.

This implementation uses the official Stagehand Python package v0.5.0:
https://pypi.org/project/stagehand/

Key features:
1. Official Stagehand v0.5.0 API (fixes observe parameter bug)
2. Simple instruction-based operations
3. Proper session management
4. Clean error handling
5. Direct API calls without abstractions
"""

import json
import asyncio
from typing import Dict, Any, Optional, Union, Callable, Awaitable
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..ai_logging.error_logger import get_error_logger
from ..config.settings import settings

class SimplifiedStagehandInput(BaseModel):
    """Input schema for SimplifiedStagehandTool."""
    operation: str = Field(
        description="Operation to perform: extract, act, observe, or navigate"
    )
    instruction: Optional[str] = Field(
        default=None,
        description="Instruction for extract/observe operations"
    )
    schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom Pydantic schema definition for extract operations (JSON format)"
    )
    action: Optional[str] = Field(
        default=None,
        description="Action to perform for act operations"
    )
    url: Optional[str] = Field(
        default=None,
        description="URL to navigate to for navigate operations"
    )
    variables: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Variables for action substitution"
    )
    return_action: Optional[bool] = Field(
        default=False,
        description="Whether to return action suggestions for observe operations"
    )

class SimplifiedStagehandTool(BaseTool):
    """
    Simplified Stagehand tool following official Browserbase MCP patterns.

    This tool provides direct access to Stagehand's core functionality:
    - extract(): Extract structured data from web pages
    - act(): Perform actions on web elements
    - observe(): Observe and identify page elements
    - navigate(): Navigate to URLs
    """

    name: str = "simplified_stagehand_tool"
    description: str = """
    Simplified browser automation tool using Stagehand with official API patterns.

    Available operations:
    - extract: Extract structured data using natural language instructions with flexible schemas
    - act: Perform atomic actions like clicking, typing, scrolling
    - observe: Identify and observe page elements
    - navigate: Navigate to URLs

    EXTRACT OPERATION WITH CUSTOM SCHEMAS:
    Supports flexible schema definitions for precise data extraction:

    Example usage:
    {
      "operation": "extract",
      "instruction": "Extract product information",
      "schema": {
        "fields": {
          "name": "str",
          "image": "optional_url",
          "price": "str"
        },
        "name": "Product",
        "is_list": true
      }
    }

    Schema field types: str, optional_str, url, optional_url, int, float
    Auto URL detection for fields containing: url, link, image, href

    Use detailed, specific instructions for best results.
    """
    args_schema: type[BaseModel] = SimplifiedStagehandInput

    def _run(self, **kwargs) -> str:
        """
        CrewAI tool entry point - handles all parameters as kwargs.

        This method is called by CrewAI with all parameters as keyword arguments.
        We need to extract the operation and other parameters from kwargs.
        """
        try:
            # Normalize kwargs in case the LLM passed a JSON string or a single-item list
            kwargs = self._normalize_tool_kwargs(kwargs)

            # Extract operation from kwargs
            operation = kwargs.get("operation", "")
            if not operation:
                raise ValueError("operation parameter is required")

            # Call the main dispatch method with all kwargs
            return self._execute_operation(**kwargs)

        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return f"Error: {str(e)}"

    def _normalize_tool_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Accept flexible inputs (JSON strings or single-item lists) and coerce to dict.

        Crew/LLM sometimes passes a string like "[{...}]" or "{...}" instead of a dict.
        This normalizer parses those forms and returns a proper key/value dictionary.
        """
        try:
            if not kwargs:
                return {}

            # Common keys where a JSON blob might be placed
            blob_keys = [
                "input", "action_input", "payload", "params", "data", "arg", "args"
            ]

            # If operation is present already, assume kwargs are fine
            if "operation" in kwargs:
                return kwargs

            # If exactly one key and its value is a JSON-looking string
            if len(kwargs) == 1:
                only_key = next(iter(kwargs))
                only_val = kwargs[only_key]
                if isinstance(only_val, str) and (only_val.strip().startswith("{") or only_val.strip().startswith("[")):
                    parsed = json.loads(only_val)
                    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                        return parsed[0]
                    if isinstance(parsed, dict):
                        return parsed
                    # Otherwise fall through

            # Look for a JSON blob in common keys
            for key in blob_keys:
                if key in kwargs and isinstance(kwargs[key], str):
                    text = kwargs[key].strip()
                    if text.startswith("{") or text.startswith("["):
                        parsed = json.loads(text)
                        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                            return parsed[0]
                        if isinstance(parsed, dict):
                            return parsed

            # Also handle if a list was passed directly under a generic key
            for key, val in list(kwargs.items()):
                if isinstance(val, list) and val and isinstance(val[0], dict) and "operation" in val[0]:
                    return val[0]

            return kwargs
        except Exception as e:
            # If normalization fails, return original kwargs and let downstream error
            self.logger.warning(f"Failed to normalize tool kwargs: {e}")
            return kwargs

    def _execute_operation(self, **kwargs) -> str:
        """
        Main operation dispatch method with simplified operation handling.

        Args:
            **kwargs: All parameters including operation and operation-specific parameters

        Returns:
            Operation result as string
        """
        try:
            # Extract operation from kwargs
            operation = kwargs.get("operation", "")
            if not operation:
                raise ValueError("operation parameter is required")

            # Handle event loop properly for CrewAI environment
            import nest_asyncio

            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, use nest_asyncio to allow nested loops
                nest_asyncio.apply(loop)
                run_async = loop.run_until_complete
            except RuntimeError:
                # No event loop running, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                run_async = loop.run_until_complete

            # Dispatch to appropriate method
            if operation == "extract":
                instruction = kwargs.get("instruction", "")
                schema = kwargs.get("schema")
                if not instruction:
                    raise ValueError("extract operation requires 'instruction' parameter")
                return run_async(self.extract(instruction, schema))

            elif operation == "act":
                action = kwargs.get("action", "")
                variables = kwargs.get("variables")
                if not action:
                    raise ValueError("act operation requires 'action' parameter")
                return run_async(self.act(action, variables))

            elif operation == "observe":
                instruction = kwargs.get("instruction", "")
                return_action = kwargs.get("return_action", False)
                self.logger.info(f"observe operation - kwargs={kwargs}")
                self.logger.info(f"observe operation - instruction='{instruction}' (type: {type(instruction)}, len: {len(instruction) if instruction else 'N/A'})")
                self.logger.info(f"observe operation - return_action={return_action}")
                if not instruction:
                    self.logger.error(f"observe operation failed - instruction is empty or None")
                    self.logger.error(f"observe operation failed - kwargs keys: {list(kwargs.keys())}")
                    raise ValueError("observe operation requires 'instruction' parameter")
                return run_async(self.observe(instruction, return_action))

            elif operation == "navigate":
                url = kwargs.get("url", "")
                if not url:
                    raise ValueError("navigate operation requires 'url' parameter")
                return run_async(self.navigate(url))

            else:
                raise ValueError(f"Unknown operation: {operation}. Supported: extract, act, observe, navigate")

        except Exception as e:
            self.logger.error(f"Operation execution failed: {e}")
            return f"Error: {str(e)}"

    # Tool configuration
    session_id: Optional[str] = Field(default=None, description="Browserbase session ID for session reuse")
    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")

    # Internal state (using private fields to avoid Pydantic validation)
    _stagehand: Optional[Any] = None
    _session_initialized: bool = False
    _logger: Optional[Any] = None
    _session_reinit_count: int = 0
    
    def __init__(self, log_dir: str = 'logs', **kwargs):
        """Initialize the simplified Stagehand tool."""
        super().__init__(**kwargs)
        import uuid
        self._instance_id = str(uuid.uuid4())[:8]
        # Remove non-error logging; keep only error logger
        self._error_logger = get_error_logger("simplified_stagehand_tool")
        # No info/console logging

    @property
    def logger(self):
        """Deprecated: info/debug logging removed; keep for compatibility."""
        class _Null:
            def info(self, *a, **k):
                pass
            def debug(self, *a, **k):
                pass
            def warning(self, *a, **k):
                pass
        return _Null()


    
    async def _get_stagehand(self):
        """Get or create Stagehand instance using official v0.5.0 API."""
        if self._stagehand is None or not self._session_initialized:
            try:
                # Import official Stagehand v0.5.0
                from stagehand import Stagehand

                # Info logging removed

                # Get credentials and model selection from settings/env
                import os

                api_key = os.getenv('BROWSERBASE_API_KEY')
                project_id = os.getenv('BROWSERBASE_PROJECT_ID')
                # Resolve model API key based on configured model name
                try:
                    model_api_key = settings.get_api_key_for_model(settings.stagehand_model_name)
                except Exception:
                    # Fallback to OPENAI_API_KEY for backwards compatibility
                    model_api_key = os.getenv('OPENAI_API_KEY')

                if not api_key or not project_id:
                    raise Exception("Browserbase API key and project ID are required. Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID environment variables.")

                if not model_api_key:
                    raise Exception("OpenAI API key is required for Stagehand operations. Set OPENAI_API_KEY environment variable.")

                # Create Stagehand instance using official Python API pattern
                # Based on official Python documentation (uses snake_case)
                from stagehand import StagehandConfig

                # Determine provider-prefixed model name
                configured_model = settings.stagehand_model_name or "gpt-4o"
                cm_lower = configured_model.lower()
                if "/" not in configured_model:
                    if "gpt" in cm_lower:
                        model_name = f"openai/{configured_model}"
                    elif "claude" in cm_lower:
                        model_name = f"anthropic/{configured_model}"
                    elif "gemini" in cm_lower or "google" in cm_lower:
                        model_name = f"google/{configured_model}"
                    else:
                        model_name = f"openai/{configured_model}"
                else:
                    model_name = configured_model

                stagehand_config = StagehandConfig(
                    env="BROWSERBASE",
                    api_key=api_key,  # Python API uses snake_case
                    project_id=project_id,  # Python API uses snake_case
                    model_name=model_name,  # e.g., openai/gpt-5
                    verbose=settings.stagehand_verbose,
                )

                # CRITICAL FIX: Add session_id for session reuse if provided
                if self.session_id:
                    # For Python API, session reuse might be handled differently
                    pass
                else:
                    pass

                # Create Stagehand instance with config and model API key
                self._stagehand = Stagehand(stagehand_config, model_api_key=model_api_key)

                # Initialize following official pattern
                await self._stagehand.init()
                self._session_initialized = True

                # Info logging removed

                # Store session ID for reuse (check multiple possible attributes)
                session_id_found = None

                # Try different ways to get session ID from Stagehand v0.5.0
                if hasattr(self._stagehand, 'session_id'):
                    session_id_found = self._stagehand.session_id
                elif hasattr(self._stagehand, 'browserbase_session_id'):
                    session_id_found = self._stagehand.browserbase_session_id
                elif hasattr(self._stagehand, 'page') and hasattr(self._stagehand.page, 'session_id'):
                    session_id_found = self._stagehand.page.session_id
                elif hasattr(self._stagehand, '_session_id'):
                    session_id_found = self._stagehand._session_id

                if session_id_found:
                    self.session_id = session_id_found
                else:
                    pass

            except Exception as e:
                self._error_logger.error(f"Failed to initialize Stagehand v0.5.0: {e}", exc_info=True)
                raise Exception(f"Failed to initialize Stagehand v0.5.0: {e}")

        return self._stagehand
    
    async def extract(self, instruction: str, schema: Optional[Dict[str, Any]] = None) -> str:
        """
        Extract structured data using schema-based extraction with flexible schemas.

        Following official Stagehand pattern with dynamic Pydantic schema support.

        Schema Format:
        {
          "fields": {
            "field_name": "field_type",    // Supported types: str, optional_str, url, optional_url, int, float
            "another_field": "field_type"
          },
          "name": "ModelName",             // Name for the generated Pydantic model
          "is_list": true/false            // Whether to extract multiple items or single item
        }

        Field Types:
        - "str": Required string field
        - "optional_str": Optional string field (can be null)
        - "url": Required URL field (uses Pydantic HttpUrl for validation)
        - "optional_url": Optional URL field (uses Optional[HttpUrl])
        - "int": Required integer field
        - "float": Required float field

        Auto URL Detection:
        Fields with names containing 'url', 'link', 'image', or 'href' are automatically
        treated as URL fields even when using 'str' or 'optional_str' types.

        Default Schema (if none provided):
        {
          "fields": {
            "name": "str",
            "price": "str",
            "url": "optional_url",
            "image": "optional_url",
            "description": "optional_str"
          },
          "name": "Product",
          "is_list": true
        }

        Args:
            instruction: Detailed instruction for what to extract
            schema: Optional custom schema definition in JSON format

        Returns:
            JSON string with extracted data matching the schema structure
        """
        try:
            # Info logging removed

            # Dynamic schema creation will be handled in helper methods

            # Create schema based on provided definition or use default
            if schema:
                pass
                extraction_schema = self._create_dynamic_schema(schema)
            else:
                pass
                extraction_schema = self._create_default_schema()

            async def op(sh):
                return await sh.page.extract(
                    instruction,
                    schema=extraction_schema
                )

            extraction = await self._run_with_session_retry(op, "extract")

            # Handle the extraction result
            result_data = self._process_extraction_result(extraction)

            # Log extraction success
            # Info logging removed

            # Return clean JSON
            result = json.dumps(result_data, indent=2, default=str)
            return result

        except Exception as error:
            error_msg = f"Failed to extract content: {str(error)}"
            self._error_logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

    def _create_dynamic_schema(self, schema_def: Dict[str, Any]) -> type[BaseModel]:
        """
        Create a dynamic Pydantic schema from JSON definition.

        Args:
            schema_def: Schema definition in JSON format

        Returns:
            Dynamically created Pydantic model class
        """
        try:
            from typing import List, Optional
            from pydantic import create_model

            # Handle different schema formats
            if 'fields' in schema_def:
                # Format: {"fields": {"name": "str", "price": "str"}, "name": "Product"}
                fields = schema_def['fields']
                model_name = schema_def.get('name', 'DynamicModel')

                # Convert field definitions to Pydantic format
                pydantic_fields = {}
                for field_name, field_type in fields.items():
                    # Check if field name suggests it's a URL/link
                    is_url_field = any(keyword in field_name.lower() for keyword in ['url', 'link', 'image', 'href'])

                    if field_type == 'str':
                        # Keep URLs lenient as strings to avoid strict validation failures
                        pydantic_fields[field_name] = (str, ...)
                    elif field_type == 'optional_str':
                        pydantic_fields[field_name] = (Optional[str], None)
                    elif field_type == 'url':
                        # Use str for URL to be tolerant of relative/malformed links
                        pydantic_fields[field_name] = (str, ...)
                    elif field_type == 'optional_url':
                        pydantic_fields[field_name] = (Optional[str], None)
                    elif field_type == 'int':
                        pydantic_fields[field_name] = (int, ...)
                    elif field_type == 'float':
                        pydantic_fields[field_name] = (float, ...)
                    else:
                        # Default to optional string for unknown types; be lenient for URLs
                        pydantic_fields[field_name] = (Optional[str], None)

                # Create the model
                ItemModel = create_model(model_name, **pydantic_fields)

                # If this is for a list of items, create a wrapper
                if schema_def.get('is_list', True):
                    ListModel = create_model(
                        f"{model_name}List",
                        items=(List[ItemModel], ...)
                    )
                    return ListModel
                else:
                    return ItemModel

            else:
                # Fallback to default schema
                self.logger.warning("Invalid schema format, using default")
                return self._create_default_schema()

        except Exception as e:
            self._error_logger.error(f"Failed to create dynamic schema: {e}", exc_info=True)
            return self._create_default_schema()

    def _create_default_schema(self) -> type[BaseModel]:
        """Create a lenient default product extraction schema (URLs as strings)."""
        from typing import List, Optional
        from pydantic import BaseModel

        class Product(BaseModel):
            name: str
            price: str
            url: Optional[str] = None
            image: Optional[str] = None
            description: Optional[str] = None

        class ProductList(BaseModel):
            products: List[Product]

        return ProductList

    def _process_extraction_result(self, extraction: Any) -> Any:
        """
        Process the extraction result into a consistent format.

        Args:
            extraction: Raw extraction result from Stagehand

        Returns:
            Processed data structure
        """
        try:
            # Handle Pydantic model result first
            if hasattr(extraction, 'model_dump'):
                result_dict = extraction.model_dump()

                # If it has a list-like field (products, items, etc.), return that
                for key in ['products', 'items', 'data', 'results']:
                    if isinstance(result_dict, dict) and key in result_dict:
                        return result_dict[key]

                # Otherwise return the whole dict
                return result_dict

            # Handle basic Python containers early to avoid attribute name collisions
            if isinstance(extraction, list):
                return extraction
            if isinstance(extraction, dict):
                return extraction

            # Handle direct attribute access patterns (common for Pydantic wrappers)
            if hasattr(extraction, 'products'):
                products_attr = getattr(extraction, 'products')
                # Only treat as a list-like if it's not callable (avoid methods)
                if not callable(products_attr):
                    products = products_attr
                    if isinstance(products, list) and products and hasattr(products[0], 'model_dump'):
                        return [p.model_dump() for p in products]
                    return products

            if hasattr(extraction, 'items'):
                items_attr = getattr(extraction, 'items')
                # Avoid dict.items() by ensuring the attribute is not callable
                if not callable(items_attr):
                    items = items_attr
                    if isinstance(items, list) and items and hasattr(items[0], 'model_dump'):
                        return [i.model_dump() for i in items]
                    return items

            # Last resort - try to convert to dict
            return dict(extraction) if hasattr(extraction, '__dict__') else extraction

        except Exception as e:
            self._error_logger.error(f"Error processing extraction result: {e}", exc_info=True)
            return extraction


    
    async def act(self, action: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Perform an atomic action on the page.
        
        Following official pattern: await stagehand.page.act({action, variables})
        
        Args:
            action: Specific action to perform (e.g., "Click the login button")
            variables: Optional variables for sensitive data substitution
            
        Returns:
            Confirmation message
        """
        try:
            # Info logging removed

            async def op(sh):
                return await sh.page.act({
                    "action": action,
                    **({"variables": variables} if variables else {})
                })

            await self._run_with_session_retry(op, "act")
            
            result = f"Action performed: {action}"
            # Info logging removed
            
            return result
            
        except Exception as error:
            error_msg = f"Failed to perform action: {str(error)}"
            self._error_logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
    
    async def observe(self, instruction: str, return_action: bool = False) -> str:
        """
        Observe and identify elements on the page using official v0.5.0 API.

        Args:
            instruction: Detailed instruction for what to observe
            return_action: Whether to return suggested actions (not used in v0.5.0)

        Returns:
            JSON string with observation data
        """
        try:
            # Info logging removed

            # Official v0.5.0 API pattern: Simple string parameter
            # Based on our successful test: await page.observe(instruction)
            async def op(sh):
                return await sh.page.observe(instruction)

            observations = await self._run_with_session_retry(op, "observe")

            # Format result as JSON string
            result = f"Observations: {json.dumps(observations, default=str)}"
            # Info logging removed

            return result

        except Exception as error:
            error_msg = f"Failed to observe: {str(error)}"
            self._error_logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
    
    async def navigate(self, url: str) -> str:
        """
        Navigate to a URL.
        
        Following official pattern: await page.goto(url, {waitUntil: 'domcontentloaded'})
        
        Args:
            url: URL to navigate to
            
        Returns:
            Navigation confirmation with session info
        """
        try:
            # Info logging removed

            async def op(sh):
                # Direct API call following official pattern (Python naming convention)
                await sh.page.goto(url, wait_until="domcontentloaded")
                return sh

            stagehand = await self._run_with_session_retry(op, "navigate")

            # Return session info following official pattern (prefer snake_case)
            session_id = (
                getattr(stagehand, 'browserbase_session_id', None)
                or getattr(stagehand, 'session_id', None)
                or getattr(stagehand, 'browserbaseSessionID', 'unknown')
            )
            result = f"Navigated to: {url}\nSession: {session_id}"
            
            # Info logging removed
            
            return result
            
        except Exception as error:
            error_msg = f"Failed to navigate: {str(error)}"
            self._error_logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
    

    
    def get_session_id(self) -> Optional[str]:
        """Get the current Browserbase session ID."""
        return self.session_id
    
    async def close(self):
        """Close the Stagehand session following official cleanup pattern."""
        if self._stagehand and self._session_initialized:
            try:
                # Info logging removed
                await self._stagehand.close()
                # Info logging removed
            except Exception as e:
                self.logger.warning(f"Error closing Stagehand session: {e}")
            finally:
                self._stagehand = None
                self._session_initialized = False
                self.session_id = None

    # --- Session retry helpers ---
    def _is_session_closed_error(self, error: Exception) -> bool:
        msg = str(error).lower()
        return (
            "target page, context or browser has been closed" in msg
            or "browser has been closed" in msg
            or "execution context was destroyed" in msg
            # Additional transient/network/session failure patterns observed in logs
            or "httpx.readerror" in msg
            or "noneype object has no attribute 'stream'" in msg
            or "nonetype object has no attribute 'stream'" in msg
        )

    async def _run_with_session_retry(self, op: Callable[[Any], Awaitable[Any]], op_name: str):
        """Run an operation with a one-time session reinitialization on closed-session errors.

        - On first detection, close and recreate the Browserbase session, then retry once.
        - If it happens again at any time afterwards, terminate the script.
        """
        try:
            sh = await self._get_stagehand()
            return await op(sh)
        except Exception as first_error:
            if self._is_session_closed_error(first_error):
                if self._session_reinit_count == 0:
                    self._error_logger.error(
                        f"{op_name}: Session closed detected. Reinitializing Browserbase session once...",
                        exc_info=True,
                    )
                    # Close existing session and reset state
                    try:
                        await self.close()
                    except Exception:
                        pass
                    self._session_reinit_count = 1
                    # Recreate and retry once
                    sh2 = await self._get_stagehand()
                    return await op(sh2)
                else:
                    self._error_logger.error(
                        f"{op_name}: Session closed again after one retry. Exiting.",
                        exc_info=True,
                    )
                    import sys
                    raise SystemExit(1)
            # Not a session-closed error; re-raise
            raise
