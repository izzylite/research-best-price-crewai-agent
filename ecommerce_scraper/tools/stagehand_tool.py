"""Enhanced Stagehand tool for ecommerce scraping with CrewAI."""

import time
import json
from typing import Any, Dict, Optional, List
from crewai.tools import BaseTool
from stagehand import Stagehand
from stagehand.schemas import AvailableModel
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..schemas.product import Product


class StagehandInput(BaseModel):
    """Input schema for Stagehand tool."""
    instruction: str = Field(..., description="Natural language instruction for the browser action")
    url: Optional[str] = Field(None, description="URL to navigate to (if not already on the page)")
    command_type: str = Field("act", description="Type of command: 'act', 'extract', or 'observe'")
    selector: Optional[str] = Field(None, description="CSS selector to limit scope (for extract/observe)")
    wait_time: Optional[int] = Field(None, description="Time to wait before executing (in seconds)")


class EcommerceStagehandTool(BaseTool):
    """Enhanced Stagehand tool optimized for ecommerce scraping."""
    
    name: str = "ecommerce_stagehand_tool"
    description: str = """
    AI-powered browser automation tool for ecommerce scraping. Can navigate websites, 
    interact with elements, and extract structured product data.
    
    Command types:
    - 'act': Perform actions like clicking, typing, scrolling, navigating
    - 'extract': Extract structured data from the current page
    - 'observe': Identify and analyze elements on the page
    
    Examples:
    - Navigate and search: instruction="Go to amazon.com and search for 'wireless headphones'", command_type="act"
    - Extract products: instruction="Extract all product information including name, price, rating", command_type="extract"
    - Find elements: instruction="Find the 'Add to Cart' button", command_type="observe"
    """
    args_schema: type[BaseModel] = StagehandInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._stagehand: Optional[Stagehand] = None
        self._current_url: Optional[str] = None
        
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
            # Initialize Stagehand asynchronously - this is critical!
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an async context, we need to handle this differently
                    # For now, we'll defer initialization to first use
                    pass
                else:
                    loop.run_until_complete(self._stagehand.init())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(self._stagehand.init())
        return self._stagehand
    
    def _run(self, **kwargs) -> str:
        """Execute the Stagehand command."""
        try:
            instruction = kwargs.get("instruction")
            url = kwargs.get("url")
            command_type = kwargs.get("command_type", "act")
            selector = kwargs.get("selector")
            wait_time = kwargs.get("wait_time")
            
            if not instruction:
                return "Error: instruction is required"
            
            stagehand = self._get_stagehand()
            
            # Navigate to URL if provided and different from current
            if url and url != self._current_url:
                # Ensure Stagehand is initialized before using page
                if not hasattr(stagehand, 'page') or stagehand.page is None:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # We're in an async context but can't await here
                            # This is a limitation - the tool needs to be async
                            return "Error: Stagehand requires async initialization but tool is called synchronously"
                        else:
                            loop.run_until_complete(stagehand.init())
                    except RuntimeError:
                        asyncio.run(stagehand.init())

                stagehand.page.goto(url)
                self._current_url = url
                # Wait for page to load
                time.sleep(2)
            
            # Wait if specified
            if wait_time:
                time.sleep(wait_time)
            
            # Add ecommerce-specific delay to be respectful
            if self._current_url:
                time.sleep(settings.default_delay_between_requests)
            
            # Execute command based on type
            if command_type == "act":
                result = stagehand.page.act(instruction)
                return f"Action completed: {result}"
                
            elif command_type == "extract":
                if selector:
                    result = stagehand.page.extract(instruction, selector=selector)
                else:
                    result = stagehand.page.extract(instruction)
                
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
                    result = stagehand.page.observe(instruction, selector=selector)
                else:
                    result = stagehand.page.observe(instruction)
                return f"Observed elements: {result}"
                
            else:
                return f"Error: Unknown command type '{command_type}'. Use 'act', 'extract', or 'observe'."
                
        except Exception as e:
            return f"Error executing Stagehand command: {str(e)}"
    
    def extract_product_data(self, product_selectors: Optional[Dict[str, str]] = None) -> str:
        """Extract structured product data using predefined selectors."""
        try:
            stagehand = self._get_stagehand()
            
            # Default extraction instruction for ecommerce products
            instruction = """
            Extract comprehensive product information from this page including:
            - Product title/name
            - Price (current and original if on sale)
            - Product description
            - Brand and model
            - Availability status
            - Product images (URLs)
            - Customer ratings and review count
            - Product specifications and features
            - Shipping information
            - Product variants (sizes, colors, etc.)
            
            Return the data in a structured JSON format.
            """
            
            result = stagehand.page.extract(instruction)
            
            # Try to format as structured JSON
            try:
                if isinstance(result, str):
                    parsed = json.loads(result)
                    return json.dumps(parsed, indent=2)
                else:
                    return json.dumps(result, indent=2, default=str)
            except (json.JSONDecodeError, TypeError):
                return str(result)
                
        except Exception as e:
            return f"Error extracting product data: {str(e)}"
    
    def close(self):
        """Close the Stagehand session."""
        if self._stagehand:
            try:
                print("🔄 Closing Browserbase session...")
                # Handle async close properly
                import asyncio
                try:
                    # Try to get existing event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create a task
                        asyncio.create_task(self._stagehand.close())
                    else:
                        # If loop is not running, run until complete
                        loop.run_until_complete(self._stagehand.close())
                except RuntimeError:
                    # No event loop, create new one
                    asyncio.run(self._stagehand.close())
                print("✅ Browserbase session closed successfully")
            except Exception as e:
                print(f"⚠️ Warning: Error closing Stagehand session: {e}")
            finally:
                self._stagehand = None
                self._current_url = None
        else:
            print("ℹ️ No active Stagehand session to close")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close()
