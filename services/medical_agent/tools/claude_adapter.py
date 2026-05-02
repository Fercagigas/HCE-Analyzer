"""
Claude Tool Adapter Base Class

This module provides a base adapter class for converting tools to Claude-compatible format.
Claude uses LangChain's standard tool format, so this adapter ensures compatibility
and provides utility methods for tool management.
"""

import logging
from typing import Dict, Any, Optional, List, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ClaudeToolAdapter(ABC):
    """
    Base adapter class for Claude-compatible tools.
    
    This class provides methods to convert tools to Claude's expected format
    and handle input/output transformations. Claude uses LangChain's standard
    tool calling format, so tools that work with LangChain will work with Claude.
    """
    
    def __init__(self, tool_name: str, tool_description: str, args_schema: Type[BaseModel]):
        """
        Initialize the Claude tool adapter.
        
        Args:
            tool_name: Name of the tool
            tool_description: Description of what the tool does
            args_schema: Pydantic BaseModel defining the tool's input schema
        """
        self.tool_name = tool_name
        self.tool_description = tool_description
        self.args_schema = args_schema
        
        logger.info(f"ClaudeToolAdapter initialized for tool: {tool_name}")
    
    def to_claude_schema(self) -> Dict[str, Any]:
        """
        Convert tool to Claude-compatible schema.
        
        Claude uses LangChain's standard tool format, which includes:
        - name: Tool name
        - description: Tool description
        - parameters: JSON Schema of input parameters
        
        Returns:
            Dict with Claude-compatible tool schema
        """
        # Get JSON schema from Pydantic model
        schema = self.args_schema.model_json_schema()
        
        # Claude expects the schema in this format
        claude_schema = {
            "name": self.tool_name,
            "description": self.tool_description,
            "input_schema": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", [])
            }
        }
        
        logger.debug(f"Generated Claude schema for {self.tool_name}")
        return claude_schema
    
    def format_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format input data for tool execution.
        
        This method can be overridden to perform custom input transformations
        before the tool is executed.
        
        Args:
            input_data: Raw input data from Claude
            
        Returns:
            Formatted input data ready for tool execution
        """
        # Validate input against schema
        try:
            validated_input = self.args_schema(**input_data)
            return validated_input.model_dump()
        except Exception as e:
            logger.error(f"Input validation failed for {self.tool_name}: {e}")
            raise ValueError(f"Invalid input for {self.tool_name}: {str(e)}")
    
    def format_output(self, output_data: Any) -> str:
        """
        Format output data for Claude consumption.
        
        This method can be overridden to perform custom output transformations
        after the tool is executed.
        
        Args:
            output_data: Raw output from tool execution
            
        Returns:
            Formatted output as string for Claude
        """
        # Default: convert to string
        if isinstance(output_data, str):
            return output_data
        elif isinstance(output_data, dict):
            return self._format_dict_output(output_data)
        elif isinstance(output_data, list):
            return self._format_list_output(output_data)
        else:
            return str(output_data)
    
    def _format_dict_output(self, data: Dict[str, Any]) -> str:
        """
        Format dictionary output in a readable way.
        
        Args:
            data: Dictionary to format
            
        Returns:
            Formatted string representation
        """
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{key}:")
                lines.append(f"  {self.format_output(value)}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    def _format_list_output(self, data: List[Any]) -> str:
        """
        Format list output in a readable way.
        
        Args:
            data: List to format
            
        Returns:
            Formatted string representation
        """
        if not data:
            return "[]"
        
        lines = []
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines.append(f"{i}.")
                for key, value in item.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append(f"{i}. {item}")
        return "\n".join(lines)
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.
        
        This method must be implemented by subclasses to define
        the actual tool execution logic.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    def __call__(self, **kwargs) -> str:
        """
        Make the adapter callable for easy execution.
        
        This method handles the full execution flow:
        1. Format input
        2. Execute tool
        3. Format output
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Formatted tool output
        """
        try:
            # Format input
            formatted_input = self.format_input(kwargs)
            
            # Execute tool
            logger.info(f"Executing tool: {self.tool_name}")
            result = self.execute(**formatted_input)
            
            # Format output
            formatted_output = self.format_output(result)
            
            logger.info(f"Tool {self.tool_name} executed successfully")
            return formatted_output
            
        except Exception as e:
            error_msg = f"Error executing {self.tool_name}: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def get_langchain_tool(self):
        """
        Get a LangChain-compatible tool instance.
        
        This method returns a tool that can be used directly with
        LangChain's bind_tools() method for Claude.
        
        Returns:
            LangChain tool instance
        """
        from langchain_core.tools import StructuredTool
        
        return StructuredTool.from_function(
            func=self.execute,
            name=self.tool_name,
            description=self.tool_description,
            args_schema=self.args_schema,
            return_direct=False
        )


class ClaudeToolRegistry:
    """
    Registry for managing Claude-compatible tools.
    
    This class provides a centralized way to register and retrieve
    tools for use with Claude agents.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, ClaudeToolAdapter] = {}
        logger.info("ClaudeToolRegistry initialized")
    
    def register(self, tool: ClaudeToolAdapter):
        """
        Register a tool in the registry.
        
        Args:
            tool: ClaudeToolAdapter instance to register
        """
        self.tools[tool.tool_name] = tool
        logger.info(f"Registered tool: {tool.tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[ClaudeToolAdapter]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            ClaudeToolAdapter instance or None if not found
        """
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> List[ClaudeToolAdapter]:
        """
        Get all registered tools.
        
        Returns:
            List of all ClaudeToolAdapter instances
        """
        return list(self.tools.values())
    
    def get_claude_schemas(self) -> List[Dict[str, Any]]:
        """
        Get Claude-compatible schemas for all registered tools.
        
        Returns:
            List of Claude tool schemas
        """
        return [tool.to_claude_schema() for tool in self.tools.values()]
    
    def get_langchain_tools(self) -> List:
        """
        Get LangChain-compatible tools for all registered tools.
        
        Returns:
            List of LangChain tool instances
        """
        return [tool.get_langchain_tool() for tool in self.tools.values()]
    
    def clear(self):
        """Clear all registered tools."""
        self.tools.clear()
        logger.info("Tool registry cleared")
