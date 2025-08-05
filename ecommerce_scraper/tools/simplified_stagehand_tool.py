"""
Simplified Stagehand Tool based on official Browserbase MCP patterns.

This implementation follows the official patterns from:
https://github.com/browserbase/mcp-server-browserbase/tree/main/src/tools

Key improvements:
1. Direct stagehand.page.extract() calls (no command_type abstraction)
2. Simple instruction-based API
3. Proper session management with context sharing
4. Clean error handling
5. Variable substitution support
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, Union
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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
            logger.error(f"[ERROR] Tool execution failed: {e}")
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
                logger.info(f"[DEBUG] observe operation - kwargs={kwargs}")
                logger.info(f"[DEBUG] observe operation - instruction='{instruction}' (type: {type(instruction)}, len: {len(instruction) if instruction else 'N/A'})")
                logger.info(f"[DEBUG] observe operation - return_action={return_action}")
                if not instruction:
                    logger.error(f"[DEBUG] observe operation failed - instruction is empty or None")
                    logger.error(f"[DEBUG] observe operation failed - kwargs keys: {list(kwargs.keys())}")
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
            logger.error(f"[ERROR] Operation execution failed: {e}")
            return f"Error: {str(e)}"

    # Tool configuration
    session_id: Optional[str] = Field(default=None, description="Browserbase session ID for session reuse")
    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")

    # Internal state
    _stagehand: Optional[Any] = None
    _session_initialized: bool = False
    
    def __init__(self, **kwargs):
        """Initialize the simplified Stagehand tool."""
        super().__init__(**kwargs)
        logger.info(f"[SIMPLIFIED] SimplifiedStagehandTool initialized")
        logger.info(f"[VIEWPORT] Viewport configured: {self.viewport_width}x{self.viewport_height}")
    
    async def _get_stagehand(self):
        """Get or create Stagehand instance following official patterns."""
        if self._stagehand is None or not self._session_initialized:
            try:
                # Import here to avoid circular imports
                from stagehand import Stagehand
                
                logger.info("[INIT] Initializing Stagehand session...")
                
                # Get Browserbase credentials from environment (same as current tool)
                import os

                api_key = os.getenv('BROWSERBASE_API_KEY')
                project_id = os.getenv('BROWSERBASE_PROJECT_ID')

                if not api_key or not project_id:
                    raise Exception("Browserbase API key and project ID are required. Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID environment variables.")

                # Create Stagehand instance using same pattern as working tool
                stagehand_config = {
                    "api_key": api_key,
                    "project_id": project_id,
                    "model_api_key": os.getenv('OPENAI_API_KEY'),  # Required for extraction
                    "dom_settle_timeout_ms": 3000,
                    "headless": True,
                    "verbose": False,
                    "self_heal": True,
                    "wait_for_captcha_solves": True,
                    "browserbase_session_create_params": {
                        "project_id": project_id,
                        "browser_settings": {
                            "viewport": {
                                "width": self.viewport_width,
                                "height": self.viewport_height,
                            },
                            "block_ads": True,
                        },
                    }
                }

                # Add session ID for session reuse if provided
                if self.session_id:
                    stagehand_config["browserbase_session_id"] = self.session_id
                    logger.info(f"[SESSION] Reusing Browserbase session: {self.session_id}")

                self._stagehand = Stagehand(**stagehand_config)
                
                # Initialize following official pattern
                await self._stagehand.init()
                self._session_initialized = True
                
                logger.info("[SUCCESS] Stagehand session initialized successfully")
                
                # Store session ID for reuse
                if hasattr(self._stagehand, 'browserbaseSessionID'):
                    self.session_id = self._stagehand.browserbaseSessionID
                    logger.info(f"[SESSION] Session ID: {self.session_id}")
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to initialize Stagehand: {e}")
                raise Exception(f"Failed to initialize Stagehand: {e}")
        
        return self._stagehand
    
    async def extract(self, instruction: str) -> str:
        """
        Extract structured data from the current page using natural language instruction.
        
        Following official pattern: await stagehand.page.extract(instruction)
        
        Args:
            instruction: Detailed instruction for what to extract
            
        Returns:
            JSON string with extracted data
        """
        try:
            stagehand = await self._get_stagehand()
            
            logger.info(f"[EXTRACT] Extracting with instruction: {instruction[:100]}...")
            
            # Direct API call following official pattern
            extraction = await stagehand.page.extract(instruction)

            # Handle different extraction result types
            if hasattr(extraction, 'model_dump'):
                # Pydantic model - convert to dict
                extraction_dict = extraction.model_dump()
            elif hasattr(extraction, '__dict__'):
                # Object with attributes - convert to dict
                extraction_dict = extraction.__dict__
            else:
                # Already a dict or primitive type
                extraction_dict = extraction

            # If the result has an "extraction" key, unwrap it
            if isinstance(extraction_dict, dict) and "extraction" in extraction_dict:
                # Try to parse the inner extraction as JSON
                inner_extraction = extraction_dict["extraction"]
                if isinstance(inner_extraction, str):
                    try:
                        extraction_dict = json.loads(inner_extraction)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, keep the original structure
                        pass
                else:
                    extraction_dict = inner_extraction

            # Return formatted JSON following official pattern
            result = json.dumps(extraction_dict, indent=2, default=str)
            logger.info(f"[EXTRACT] Successfully extracted {len(result)} characters")

            return result
            
        except Exception as error:
            error_msg = f"Failed to extract content: {str(error)}"
            logger.error(f"[EXTRACT] {error_msg}")
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
            
            logger.info(f"[ACT] Performing action: {action}")
            
            # Direct API call following official pattern
            await stagehand.page.act({
                "action": action,
                **({"variables": variables} if variables else {})
            })
            
            result = f"Action performed: {action}"
            logger.info(f"[ACT] {result}")
            
            return result
            
        except Exception as error:
            error_msg = f"Failed to perform action: {str(error)}"
            logger.error(f"[ACT] {error_msg}")
            raise Exception(error_msg)
    
    async def observe(self, instruction: str, return_action: bool = False) -> str:
        """
        Observe and identify elements on the page.

        Following official pattern: await stagehand.page.observe({instruction, returnAction})

        Args:
            instruction: Detailed instruction for what to observe
            return_action: Whether to return suggested actions

        Returns:
            JSON string with observation data
        """
        try:
            logger.info(f"[OBSERVE] Method called with instruction='{instruction}' (type: {type(instruction)}, len: {len(instruction) if instruction else 'N/A'})")
            logger.info(f"[OBSERVE] Method called with return_action={return_action}")

            if not instruction:
                error_msg = "No instruction provided for observe."
                logger.error(f"[OBSERVE] {error_msg}")
                raise ValueError(error_msg)

            stagehand = await self._get_stagehand()

            logger.info(f"[OBSERVE] Observing with instruction: {instruction[:100]}...")

            # Direct API call following official pattern
            observations = await stagehand.page.observe({
                "instruction": instruction,
                "returnAction": return_action
            })

            result = json.dumps(observations, indent=2)
            logger.info(f"[OBSERVE] Successfully observed {len(observations) if isinstance(observations, list) else 1} elements")

            return result

        except Exception as error:
            error_msg = f"Failed to observe: {str(error)}"
            logger.error(f"[OBSERVE] {error_msg}")
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
            
            logger.info(f"[NAVIGATE] Navigating to: {url}")
            
            # Direct API call following official pattern (Python naming convention)
            await stagehand.page.goto(url, wait_until="domcontentloaded")
            
            # Return session info following official pattern
            session_id = getattr(stagehand, 'browserbaseSessionID', 'unknown')
            result = f"Navigated to: {url}\nSession: {session_id}"
            
            logger.info(f"[NAVIGATE] Successfully navigated to {url}")
            
            return result
            
        except Exception as error:
            error_msg = f"Failed to navigate: {str(error)}"
            logger.error(f"[NAVIGATE] {error_msg}")
            raise Exception(error_msg)
    

    
    def get_session_id(self) -> Optional[str]:
        """Get the current Browserbase session ID."""
        return self.session_id
    
    async def close(self):
        """Close the Stagehand session following official cleanup pattern."""
        if self._stagehand and self._session_initialized:
            try:
                logger.info("[CLEANUP] Closing Stagehand session...")
                await self._stagehand.close()
                logger.info("[CLEANUP] Stagehand session closed successfully")
            except Exception as e:
                logger.warning(f"[CLEANUP] Error closing Stagehand session: {e}")
            finally:
                self._stagehand = None
                self._session_initialized = False
                self.session_id = None
