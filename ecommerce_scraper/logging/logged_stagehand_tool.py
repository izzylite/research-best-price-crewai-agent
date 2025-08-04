"""
Logged Stagehand Tool - Wraps the EcommerceStagehandTool with comprehensive logging.
"""

import json
import time
from typing import Dict, Any, Optional
from ..tools.stagehand_tool import EcommerceStagehandTool
from .ai_logger import get_ai_logger


class LoggedStagehandTool:
    """Wrapper around EcommerceStagehandTool that logs all interactions."""
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize the logged Stagehand tool."""
        self.tool = EcommerceStagehandTool()
        self.logger = get_ai_logger(session_id)
        self.agent_name = "Unknown"  # Will be set by the agent using this tool
    
    def set_agent_name(self, agent_name: str):
        """Set the name of the agent using this tool."""
        self.agent_name = agent_name
    
    def _log_tool_call(self, method_name: str, input_data: Dict[str, Any], 
                      output: str, execution_time_ms: float, success: bool = True, 
                      error: Optional[str] = None):
        """Log a tool call with all relevant information."""
        self.logger.log_tool_call(
            agent_name=self.agent_name,
            tool_name=f"ecommerce_stagehand_tool.{method_name}",
            tool_input=input_data,
            tool_output=output,
            execution_time_ms=execution_time_ms,
            success=success,
            error=error
        )
    
    def _execute_with_logging(self, method_name: str, method_func, **kwargs):
        """Execute a method with comprehensive logging."""
        start_time = time.time()
        
        # Log the input
        input_data = {k: v for k, v in kwargs.items() if v is not None}
        
        try:
            # Execute the actual method
            result = method_func(**kwargs)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Log successful execution
            output_str = str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
            self._log_tool_call(
                method_name=method_name,
                input_data=input_data,
                output=output_str,
                execution_time_ms=execution_time_ms,
                success=True
            )
            
            return result
            
        except Exception as e:
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Log failed execution
            self._log_tool_call(
                method_name=method_name,
                input_data=input_data,
                output="",
                execution_time_ms=execution_time_ms,
                success=False,
                error=str(e)
            )
            
            # Re-raise the exception
            raise
    
    def navigate(self, url: str, wait_time: Optional[int] = None) -> str:
        """Navigate to a URL with logging."""
        return self._execute_with_logging(
            "navigate",
            self.tool.navigate,
            url=url,
            wait_time=wait_time
        )
    
    def act(self, instruction: str, url: Optional[str] = None, 
           wait_time: Optional[int] = None, variables: Optional[Dict[str, str]] = None,
           preview_only: bool = False) -> str:
        """Perform an action with logging."""
        return self._execute_with_logging(
            "act",
            self.tool.act,
            instruction=instruction,
            url=url,
            wait_time=wait_time,
            variables=variables,
            preview_only=preview_only
        )
    
    def extract(self, instruction: str, url: Optional[str] = None,
               selector: Optional[str] = None, wait_time: Optional[int] = None,
               use_cache: bool = False) -> str:
        """Extract data with logging."""
        return self._execute_with_logging(
            "extract",
            self.tool.extract,
            instruction=instruction,
            url=url,
            selector=selector,
            wait_time=wait_time,
            use_cache=use_cache
        )
    
    def observe(self, instruction: str, url: Optional[str] = None,
               selector: Optional[str] = None, wait_time: Optional[int] = None) -> str:
        """Observe elements with logging."""
        return self._execute_with_logging(
            "observe",
            self.tool.observe,
            instruction=instruction,
            url=url,
            selector=selector,
            wait_time=wait_time
        )
    
    def preview(self, instruction: str, url: Optional[str] = None,
               wait_time: Optional[int] = None) -> str:
        """Preview an action with logging."""
        return self._execute_with_logging(
            "preview",
            self.tool.preview,
            instruction=instruction,
            url=url,
            wait_time=wait_time
        )
    
    def run(self, instruction: str, url: Optional[str] = None,
           command_type: str = "act", selector: Optional[str] = None,
           wait_time: Optional[int] = None, variables: Optional[Dict[str, str]] = None,
           preview_only: bool = False, use_cache: bool = False) -> str:
        """Run a command with logging (main interface method)."""
        return self._execute_with_logging(
            "run",
            self.tool.run,
            instruction=instruction,
            url=url,
            command_type=command_type,
            selector=selector,
            wait_time=wait_time,
            variables=variables,
            preview_only=preview_only,
            use_cache=use_cache
        )
    
    def close(self):
        """Close the tool and log the closure."""
        try:
            self.tool.close()
            self.logger.log_tool_call(
                agent_name=self.agent_name,
                tool_name="ecommerce_stagehand_tool.close",
                tool_input={},
                tool_output="Tool closed successfully",
                success=True
            )
        except Exception as e:
            self.logger.log_tool_call(
                agent_name=self.agent_name,
                tool_name="ecommerce_stagehand_tool.close",
                tool_input={},
                tool_output="",
                success=False,
                error=str(e)
            )
            raise
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    # Delegate other attributes to the underlying tool
    def __getattr__(self, name):
        """Delegate unknown attributes to the underlying tool."""
        return getattr(self.tool, name)
