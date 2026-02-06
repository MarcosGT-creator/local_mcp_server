"""
Tool and prompt registration helpers for MCP server.
"""

import inspect
from typing import Any, List
from fastmcp.tools.tool import Tool
from fastmcp.prompts.prompt import Prompt
from src.utils.logger import logger


def register_tools_from_module(mcp_instance: Any, module: Any, module_name: str) -> int:
    """
    Register all public functions from a module as MCP tools.
    
    Args:
        mcp_instance: FastMCP instance to register tools with
        module: Python module containing tool functions
        module_name: Name of module for logging
        
    Returns:
        Number of tools registered
    """
    registered = 0
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Skip private functions (starting with _) and imported functions
        if not name.startswith("_") and obj.__module__ == module.__name__:
            mcp_instance.add_tool(Tool.from_function(fn=obj))
            registered += 1
    
    logger.info(f"Registered {registered} {module_name} tools")
    return registered


def register_prompts_from_module(mcp_instance: Any, module: Any, module_name: str) -> int:
    """
    Register all public functions from a module as MCP prompts.
    
    Args:
        mcp_instance: FastMCP instance to register prompts with
        module: Python module containing prompt functions
        module_name: Name of module for logging
        
    Returns:
        Number of prompts registered
    """
    registered = 0
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Skip private functions (starting with _) and imported functions
        if not name.startswith("_") and obj.__module__ == module.__name__:
            mcp_instance.add_prompt(Prompt.from_function(fn=obj))
            registered += 1
    
    logger.info(f"Registered {registered} {module_name} prompts")
    return registered


def register_all_tools_and_prompts(
    mcp_instance: Any,
    tool_modules: List[tuple],  # List of (module, name) tuples
    prompt_module: List[tuple]
) -> dict:
    """
    Register all tools and prompts from multiple modules.
    
    Args:
        mcp_instance: FastMCP instance
        tool_modules: List of (module, module_name) tuples
        prompt_module: List[tuple]
        
    Returns:
        Dictionary with registration statistics
    """
    stats = {"tools": 0, "prompts": 0}
    
    # Register tools from all modules
    for module, name in tool_modules:
        stats["tools"] += register_tools_from_module(mcp_instance, module, name)
    
    # Register prompts if provided
    for module, name in prompt_module:
        stats["prompts"] += register_prompts_from_module(mcp_instance, module, name)

    return stats
