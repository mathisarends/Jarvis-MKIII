import inspect

from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool

from utils.logging_mixin import LoggingMixin
from utils.singleton_meta_class import SingletonMetaClass


class ToolRegistry(LoggingMixin, metaclass=SingletonMetaClass):
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
        """
        if tool.name in self._tools:
            raise ValueError(
                f"A tool with the name '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool
        self.logger.info("Tool '%s' successfully registered.", tool.name)

    def unregister_tool(self, tool_name: str) -> bool:
        """
        Removes a tool from the registry.
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            self.logger.info("Tool '%s' removed from registry.", tool_name)
            return True

        self.logger.warning(
            "Tool '%s' could not be removed because it is not in the registry.",
            tool_name,
        )
        return False

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Retrieves a registered tool by name.
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """
        Lists all registered tool names.

        """
        return list(self._tools.keys())

    def get_all_tools(self) -> List[BaseTool]:
        """
        Returns all registered tools.

        Returns:
            List[BaseTool]: A list of registered tools
        """
        return list(self._tools.values())

    def get_openai_schema(self) -> List[Dict[str, Any]]:
        """
        Converts registered tools into OpenAI-compatible function schemas.

        Returns:
            List[Dict]: A list of OpenAI function schemas
        """
        tools_to_convert = self.get_all_tools()
        return self._converter.convert_tools(tools_to_convert)


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
            "parameters": parameters,
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
        Extracts parameters from a LangChain tool with early returns and cleaner structure.

        Args:
            lc_tool: A LangChain tool

        Returns:
            Dict: OpenAI-style parameters dictionary
        """
        parameters = {"type": "object", "properties": {}, "required": []}

        if hasattr(lc_tool, "args_schema"):
            schema_params = self._extract_from_schema(lc_tool)
            if schema_params:
                return schema_params

        # Verwendung von öffentlicher Methode statt geschützter _run-Methode
        if hasattr(lc_tool, "run") and callable(getattr(lc_tool, "run")):
            sig_params = self._extract_from_signature(lc_tool, method_name="run")
            if sig_params:
                return sig_params

        return parameters

    def _extract_from_schema(self, lc_tool: BaseTool) -> Optional[Dict[str, Any]]:
        """
        Extract parameters from a tool's args_schema.

        Args:
            lc_tool: A LangChain tool

        Returns:
            Optional[Dict]: Parameters dictionary or None if extraction failed
        """
        parameters = {"type": "object", "properties": {}, "required": []}

        try:
            schema = lc_tool.args_schema.schema()

            if "properties" in schema:
                parameters["properties"] = {
                    key: {
                        **val,
                        "description": val.get(
                            "description", key.replace("_", " ").capitalize()
                        ),
                    }
                    for key, val in schema["properties"].items()
                }

            if "required" in schema:
                parameters["required"] = schema["required"]

            return parameters
        except (AttributeError, TypeError):
            self.logger.debug("Failed to extract schema from tool '%s'", lc_tool.name)
            return None

    def _extract_from_signature(
        self, lc_tool: BaseTool, method_name: str = "run"
    ) -> Optional[Dict[str, Any]]:
        """
        Extract parameters from a tool's function signature.

        Args:
            lc_tool: A LangChain tool
            method_name: Name of the method to extract signature from (default: "run")

        Returns:
            Optional[Dict]: Parameters dictionary or None if extraction failed
        """
        parameters = {"type": "object", "properties": {}, "required": []}

        try:
            # Verwende getattr um auf die Methode zuzugreifen
            method = getattr(lc_tool, method_name)
            sig = inspect.signature(method)

            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                param_type = self._get_param_type(param.annotation)

                parameters["properties"][param_name] = {
                    "type": param_type,
                    "description": f"{param_name.replace('_', ' ').capitalize()}",
                }

                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)

            return parameters
        except (AttributeError, TypeError):
            self.logger.debug(
                "Failed to extract function signature from tool '%s' method '%s'",
                lc_tool.name,
                method_name,
            )
            return None

    def _get_param_type(self, annotation) -> str:
        """
        Determine OpenAI parameter type from Python type annotation.

        Args:
            annotation: Python type annotation

        Returns:
            str: Corresponding OpenAI parameter type
        """
        if annotation == inspect.Parameter.empty:
            return "string"
        if annotation == str:
            return "string"
        if annotation in (int, float):
            return "number"
        if annotation == bool:
            return "boolean"
        if annotation == dict:
            return "object"
        if annotation == list:
            return "array"

        annotation_str = str(annotation)
        if "typing.Optional" in annotation_str:
            return self._get_optional_type(annotation_str)

        return "string"

    def _get_optional_type(self, annotation_str: str) -> str:
        """
        Extract the type from an Optional type annotation.

        Args:
            annotation_str: String representation of the Optional type annotation

        Returns:
            str: Corresponding OpenAI parameter type for the inner type
        """
        inner_type = annotation_str.split("[")[1].split("]")[0]

        if "str" in inner_type:
            return "string"
        if "int" in inner_type or "float" in inner_type:
            return "number"
        if "bool" in inner_type:
            return "boolean"
        if "dict" in inner_type:
            return "object"
        if "list" in inner_type:
            return "array"

        return "string"
