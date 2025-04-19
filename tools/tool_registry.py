import json
import inspect

from typing import List, Dict, Any, Optional, Callable
from langchain.tools import BaseTool

from utils.logging_mixin import LoggingMixin
from utils.singleton_decorator import singleton

from langchain.tools import tool


@singleton
class ToolRegistry(LoggingMixin):
    """
    Registry for LangChain tools that manages them and can convert them into OpenAI function format.
    """

    def __init__(self):
        """Initializes an empty tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._converter = LangChainToOpenAIConverter()

    def register_tool(self, tool: BaseTool) -> None:
        """
        Registers a single tool in the registry.

        Args:
            tool: A LangChain tool

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"A tool with the name '{tool.name}' is already registered.")

        self._tools[tool.name] = tool
        self.logger.info("Tool '%s' successfully registered.", tool.name)

    def register_tools(self, tools: List[BaseTool]) -> None:
        """
        Registers multiple tools at once.

        Args:
            tools: A list of LangChain tools

        Raises:
            ValueError: If any tool name already exists in the registry
        """
        duplicate_names = set(tool.name for tool in tools) & set(self._tools.keys())
        if duplicate_names:
            raise ValueError(f"The following tool names are already registered: {', '.join(duplicate_names)}")

        for tool in tools:
            self._tools[tool.name] = tool

        self.logger.info("%d tools successfully registered.", len(tools))

    def unregister_tool(self, tool_name: str) -> bool:
        """
        Removes a tool from the registry.

        Args:
            tool_name: The name of the tool to remove

        Returns:
            bool: True if the tool was removed, False if it didn't exist
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            self.logger.info("Tool '%s' removed from registry.", tool_name)
            return True

        self.logger.warning("Tool '%s' could not be removed because it is not in the registry.", tool_name)
        return False

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Retrieves a registered tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Optional[BaseTool]: The tool if found, otherwise None
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """
        Lists all registered tool names.

        Returns:
            List[str]: A list of registered tool names
        """
        return list(self._tools.keys())

    def get_all_tools(self) -> List[BaseTool]:
        """
        Returns all registered tools.

        Returns:
            List[BaseTool]: A list of registered tools
        """
        return list(self._tools.values())

    def get_openai_schema(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Converts registered tools into OpenAI-compatible function schemas.

        Args:
            tool_names: Optional; if provided, only convert tools with these names

        Returns:
            List[Dict]: A list of OpenAI function schemas

        Raises:
            ValueError: If any of the specified tools are not found in the registry
        """
        if tool_names is None:
            tools_to_convert = self.get_all_tools()
        else:
            missing_tools = set(tool_names) - set(self._tools.keys())
            if missing_tools:
                raise ValueError(f"The following tools are not in the registry: {', '.join(missing_tools)}")

            tools_to_convert = [self._tools[name] for name in tool_names]

        return self._converter.convert_tools(tools_to_convert)

    def has_tool(self, tool_name: str) -> bool:
        """
        Checks if a tool with the given name is registered.

        Args:
            tool_name: Name of the tool to check

        Returns:
            bool: True if registered, False otherwise
        """
        return tool_name in self._tools


class LangChainToOpenAIConverter(LoggingMixin):
    """
    Class for converting LangChain tools into OpenAI function-compatible schemas.
    """

    def convert_tool(self, lc_tool: BaseTool) -> Dict[str, Any]:
        """
        Converts a single LangChain tool into an OpenAI function schema.

        Args:
            lc_tool: A LangChain tool instance

        Returns:
            Dict: An OpenAI function schema dictionary
        """
        parameters = self._extract_parameters(lc_tool)

        return {
            "type": "function",
            "name": lc_tool.name,
            "description": lc_tool.description or "No description provided.",
            "parameters": parameters
        }

    def convert_tools(self, lc_tools: List[BaseTool]) -> List[Dict[str, Any]]:
        """
        Converts multiple LangChain tools into OpenAI function schemas.

        Args:
            lc_tools: List of LangChain tool instances

        Returns:
            List[Dict]: A list of OpenAI-compatible function schemas
        """
        return [self.convert_tool(tool) for tool in lc_tools]

    def _extract_parameters(self, lc_tool: BaseTool) -> Dict[str, Any]:
        """
        Extracts parameters from a LangChain tool.

        Args:
            lc_tool: A LangChain tool

        Returns:
            Dict: OpenAI-style parameters dictionary
        """
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

        if hasattr(lc_tool, 'args_schema'):
            try:
                schema = lc_tool.args_schema.schema()
                if 'properties' in schema:
                    parameters['properties'] = {
                        key: {
                            **val,
                            "description": val.get("description", key.replace('_', ' ').capitalize())
                        } for key, val in schema['properties'].items()
                    }
                if 'required' in schema:
                    parameters['required'] = schema['required']
            except (AttributeError, TypeError):
                self.logger.debug("Failed to extract schema from tool '%s', using default.", lc_tool.name)

        elif hasattr(lc_tool, '_run') and callable(lc_tool._run):
            try:
                sig = inspect.signature(lc_tool._run)
                for param_name, param in sig.parameters.items():
                    if param_name != 'self':
                        param_type = "string"
                        if param.annotation != inspect.Parameter.empty:
                            if param.annotation == str:
                                param_type = "string"
                            elif param.annotation in (int, float):
                                param_type = "number"
                            elif param.annotation == bool:
                                param_type = "boolean"
                            elif param.annotation == dict:
                                param_type = "object"
                            elif param.annotation == list:
                                param_type = "array"

                        parameters['properties'][param_name] = {
                            "type": param_type,
                            "description": f"{param_name.replace('_', ' ').capitalize()}"
                        }

                        if param.default == inspect.Parameter.empty:
                            parameters['required'].append(param_name)
            except (AttributeError, TypeError):
                self.logger.debug("Failed to extract function signature from tool '%s'.", lc_tool.name)

        return parameters


def register_as_tool():
    """
    Decorator for automatically registering a function as a tool.

    Args:
        registry_instance: Optional custom registry, defaults to the singleton instance

    Returns:
        Callable: Decorator to convert a function to a tool and register it
    """
    def decorator(func: Callable):

        tool_instance = tool(func)
        
        registry = ToolRegistry()
        registry.register_tool(tool_instance)

        return tool_instance

    return decorator