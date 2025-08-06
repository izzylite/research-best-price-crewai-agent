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
from typing import Dict, Any, Optional, Union
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .custom_logger import setup_logger

class SimplifiedStagehandInput(BaseModel):
    """Input schema for SimplifiedStagehandTool."""
    operation: str = Field(
        description="Operation to perform: extract, act, observe, or navigate"
    )
    instruction: Optional[str] = Field(
        default=None,
        description="Instruction for extract/observe operations"
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
    - extract: Extract structured data using natural language instructions
    - act: Perform atomic actions like clicking, typing, scrolling
    - observe: Identify and observe page elements
    - navigate: Navigate to URLs

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
            # Extract operation from kwargs
            operation = kwargs.get("operation", "")
            if not operation:
                raise ValueError("operation parameter is required")

            # Call the main dispatch method with all kwargs
            return self._execute_operation(**kwargs)

        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return f"Error: {str(e)}"

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
                if not instruction:
                    raise ValueError("extract operation requires 'instruction' parameter")
                return run_async(self.extract(instruction))

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
    
    def __init__(self, log_dir: str = 'logs', **kwargs):
        """Initialize the simplified Stagehand tool."""
        super().__init__(**kwargs)
        import uuid
        self._instance_id = str(uuid.uuid4())[:8]
        self._logger = setup_logger(__name__, log_dir=log_dir)
        self._logger.info(f"SimplifiedStagehandTool initialized - Instance ID: {self._instance_id}")
        self._logger.info(f"Viewport configured: {self.viewport_width}x{self.viewport_height}")
        print(f"SimplifiedStagehandTool created - Instance ID: {self._instance_id}")  # Force console output

    @property
    def logger(self):
        """Access logger through property to avoid Pydantic field issues."""
        return self._logger
    
    async def _get_stagehand(self):
        """Get or create Stagehand instance using official v0.5.0 API."""
        if self._stagehand is None or not self._session_initialized:
            try:
                # Import official Stagehand v0.5.0
                from stagehand import Stagehand

                self.logger.info("Initializing Stagehand v0.5.0 session...")

                # Get credentials from environment
                import os

                api_key = os.getenv('BROWSERBASE_API_KEY')
                project_id = os.getenv('BROWSERBASE_PROJECT_ID')
                model_api_key = os.getenv('OPENAI_API_KEY')

                if not api_key or not project_id:
                    raise Exception("Browserbase API key and project ID are required. Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID environment variables.")

                if not model_api_key:
                    raise Exception("OpenAI API key is required for Stagehand operations. Set OPENAI_API_KEY environment variable.")

                # Create Stagehand instance using official v0.5.0 API pattern
                # This matches the working pattern from our test
                stagehand_config = {
                    "env": "BROWSERBASE",
                    "api_key": api_key,
                    "project_id": project_id,
                    "model_name": "gpt-4o",
                    "model_api_key": model_api_key,
                }

                # CRITICAL FIX: Add session_id for session reuse if provided
                if self.session_id:
                    stagehand_config["browserbase_session_id"] = self.session_id
                    self.logger.info(f"Reusing Browserbase session: {self.session_id}")
                else:
                    self.logger.info("Creating new Browserbase session")

                self._stagehand = Stagehand(**stagehand_config)

                # Initialize following official pattern
                await self._stagehand.init()
                self._session_initialized = True

                self.logger.info("Stagehand v0.5.0 session initialized successfully")

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
                    self.logger.info(f"Session ID captured: {self.session_id}")
                else:
                    self.logger.warning("Could not retrieve session ID from Stagehand instance")
                    # Log available attributes for debugging
                    attrs = [attr for attr in dir(self._stagehand) if not attr.startswith('__')]
                    self.logger.debug(f"Available Stagehand attributes: {attrs[:10]}...")  # First 10 only

            except Exception as e:
                self.logger.error(f"Failed to initialize Stagehand v0.5.0: {e}")
                raise Exception(f"Failed to initialize Stagehand v0.5.0: {e}")

        return self._stagehand
    
    async def extract(self, instruction: str) -> str:
        """
        Extract structured data using schema-based extraction.

        Following official Stagehand pattern with Pydantic schema.

        Args:
            instruction: Detailed instruction for what to extract

        Returns:
            JSON string with extracted data
        """
        try:
            stagehand = await self._get_stagehand()

            self.logger.info(f"Schema-based extraction: {instruction[:100]}...")

            # Create a simple, flexible schema following official documentation
            from typing import List, Optional
            from pydantic import BaseModel

            class Product(BaseModel):
                name: str
                description: str
                price: str
                image_url: Optional[str] = None  # Optional field
                weight: Optional[str] = None
                category: str
                vendor: str

            class ProductList(BaseModel):
                products: List[Product]

            # Use schema-based extraction following official documentation
            # Simplified instruction focusing on what actually works
            detailed_instruction = f"""
            {instruction}

            Extract all products from this page. For each product, extract:
            - name: Product name/title
            - description: Product description if available
            - price: Product price (e.g., "£1.97")
            - weight: Product weight/size (e.g., "150g", "400g")
            - category: Product category
            - vendor: Vendor name
            - image_url: Set to null (will be handled separately)

            Return valid JSON with all required fields.
            """

            extraction = await stagehand.page.extract(
                detailed_instruction,
                schema=ProductList
            )

            # Handle the extraction result
            if hasattr(extraction, 'model_dump'):
                # Pydantic model - get the products list
                result_dict = extraction.model_dump()
                products = result_dict.get('products', [])
            elif hasattr(extraction, 'products'):
                # Direct access to products
                products = extraction.products
                if hasattr(products[0], 'model_dump'):
                    products = [p.model_dump() for p in products]
            else:
                # Fallback - assume it's already a list
                products = extraction if isinstance(extraction, list) else []

            # Log extraction success
            self.logger.info(f"Successfully extracted {len(products)} products")

            # Return clean JSON array
            result = json.dumps(products, indent=2, default=str)

            return result

        except Exception as error:
            error_msg = f"Failed to extract content: {str(error)}"
            self.logger.error(f"{error_msg}")
            raise Exception(error_msg)


    
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
            stagehand = await self._get_stagehand()
            
            self.logger.info(f"Performing action: {action}")
            
            # Direct API call following official pattern
            await stagehand.page.act({
                "action": action,
                **({"variables": variables} if variables else {})
            })
            
            result = f"Action performed: {action}"
            self.logger.info(f"{result}")
            
            return result
            
        except Exception as error:
            error_msg = f"Failed to perform action: {str(error)}"
            self.logger.error(f"{error_msg}")
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
            self.logger.info(f"Starting observation with instruction: {instruction}")
            print(f"OBSERVE (official v0.5.0) - instruction: '{instruction}'")

            stagehand = await self._get_stagehand()

            # Official v0.5.0 API pattern: Simple string parameter
            # Based on our successful test: await page.observe(instruction)
            observations = await stagehand.page.observe(instruction)

            # Format result as JSON string
            result = f"Observations: {json.dumps(observations, default=str)}"
            self.logger.info(f"Observation completed successfully")

            return result

        except Exception as error:
            error_msg = f"Failed to observe: {str(error)}"
            self.logger.error(f"{error_msg}")
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
            stagehand = await self._get_stagehand()
            
            self.logger.info(f"Navigating to: {url}")
            
            # Direct API call following official pattern (Python naming convention)
            await stagehand.page.goto(url, wait_until="domcontentloaded")
            
            # Return session info following official pattern
            session_id = getattr(stagehand, 'browserbaseSessionID', 'unknown')
            result = f"Navigated to: {url}\nSession: {session_id}"
            
            self.logger.info(f"Successfully navigated to {url}")
            
            return result
            
        except Exception as error:
            error_msg = f"Failed to navigate: {str(error)}"
            self.logger.error(f"{error_msg}")
            raise Exception(error_msg)
    

    
    def get_session_id(self) -> Optional[str]:
        """Get the current Browserbase session ID."""
        return self.session_id
    
    async def close(self):
        """Close the Stagehand session following official cleanup pattern."""
        if self._stagehand and self._session_initialized:
            try:
                self.logger.info("Closing Stagehand session...")
                await self._stagehand.close()
                self.logger.info("Stagehand session closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing Stagehand session: {e}")
            finally:
                self._stagehand = None
                self._session_initialized = False
                self.session_id = None
