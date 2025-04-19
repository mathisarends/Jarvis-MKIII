import json
from json import JSONDecodeError
from typing import Dict, Any, Optional, Union

from utils.logging_mixin import LoggingMixin
from tools.tool_registry import ToolRegistry


class RealtimeToolHandler(LoggingMixin):
    """
    Handles function calls in OpenAI Realtime API responses, executes tools,
    and sends the results back over a WebSocket connection.
    """

    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize the RealtimeToolHandler with a tool registry.

        Args:
            tool_registry: Registry containing all available tools
        """
        self.tool_registry = tool_registry

    async def handle_function_call_in_response(
        self, response: Dict[str, Any], connection
    ) -> None:
        """
        Process function calls found in an API response and handle them.

        Args:
            response: The API response dictionary containing function calls
            connection: WebSocket connection to send results back
        """
        if not connection:
            self.logger.error("No connection available.")
            return

        output = response.get("response", {}).get("output", [])
        if not isinstance(output, list):
            self.logger.warning("Expected 'output' to be a list, got: %s", type(output))
            return

        for item in output:
            if not isinstance(item, dict):
                self.logger.warning(
                    "Expected item in output to be a dict, got: %s", type(item)
                )
                continue
            if item.get("type") == "function_call":
                await self.process_function_call(item, connection)

    async def process_function_call(
        self, function_call_item: Dict[str, Any], connection
    ) -> None:
        """
        Process a single function call item and execute the corresponding tool.

        Args:
            function_call_item: Dictionary containing function call details
            connection: WebSocket connection to send results back
        """
        function_name = function_call_item.get("name")
        call_id = function_call_item.get("call_id")
        arguments_str = function_call_item.get("arguments", "{}")
        print("arguments_str", arguments_str)

        if not function_name or not call_id:
            self.logger.error(
                "Function name or call_id is missing in the function call."
            )
            return

        self.logger.info(
            "Processing function call: %s with call_id: %s", function_name, call_id
        )

        try:
            arguments = json.loads(arguments_str)
        except JSONDecodeError as e:
            self.logger.error("Invalid JSON in arguments: %s", e)
            return

        result = await self.execute_tool(function_name, arguments)
        await self.send_function_result(call_id, result, connection)
        await self.create_new_response(connection)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with the provided arguments.

        Args:
            tool_name: The name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            The result of the tool execution or an error dict if execution fails
        """
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            self.logger.error("Tool %s not found in registry", tool_name)
            return {"error": f"Tool {tool_name} not found"}

        self.logger.info("Executing tool %s with arguments: %s", tool_name, arguments)

        try:
            result = await self._execute_tool_with_dispatch(tool, arguments)
            self.logger.info(
                "Tool %s execution result: %s", tool_name, self._truncate_result(result)
            )
            return result
        except AttributeError as e:
            self.logger.error(
                "Attribute error executing tool %s: %s", tool_name, e, exc_info=True
            )
            return {"error": f"Tool configuration error: {str(e)}"}
        except TypeError as e:
            self.logger.error(
                "Type error executing tool %s: %s", tool_name, e, exc_info=True
            )
            return {"error": f"Invalid argument type: {str(e)}"}
        except ValueError as e:
            self.logger.error(
                "Value error executing tool %s: %s", tool_name, e, exc_info=True
            )
            return {"error": f"Invalid value in arguments: {str(e)}"}
        except KeyError as e:
            self.logger.error(
                "Key error executing tool %s: %s", tool_name, e, exc_info=True
            )
            return {"error": f"Missing required argument: {str(e)}"}

    async def _execute_tool_with_dispatch(self, tool, arguments: Dict[str, Any]) -> Any:
        """
        Execute the appropriate tool method based on available parameters and tool interface.

        Args:
            tool: The tool object to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            The result of the tool execution
        """
        if hasattr(tool, "arun"):
            # LangChain BaseTool requires the first argument to be tool_input
            # We pass the entire arguments dictionary as that input
            return await tool.arun(arguments)
        elif hasattr(tool, "invoke"):
            # For invoke, we pass the arguments directly
            return tool.invoke(arguments)
        else:
            # Fallback for any other case
            return {"error": "Tool has no supported execution method"}

    def _get_main_parameter(self, tool, arguments: Dict[str, Any]) -> Optional[Any]:
        """
        Extract the main parameter from the arguments based on tool schema.

        Args:
            tool: The tool object to inspect
            arguments: Dictionary of arguments to analyze

        Returns:
            The main parameter value if found, None otherwise
        """
        param_name = self._get_tool_main_param_name(tool)

        if param_name and param_name in arguments:
            return arguments[param_name]

        if len(arguments) == 1:
            return next(iter(arguments.values()))

        return None

    def _get_tool_main_param_name(self, tool) -> Optional[str]:
        """
        Determine the main parameter name from the tool's schema.

        Args:
            tool: The tool object to inspect

        Returns:
            The name of the main parameter if found, None otherwise
        """
        if not hasattr(tool, "args_schema"):
            return None

        try:
            schema = tool.args_schema.schema()
            properties = schema.get("properties", {})

            if len(properties) == 1:
                return next(iter(properties.keys()))

            required = schema.get("required", [])
            if required:
                return required[0]
        except (AttributeError, TypeError):
            pass  # args_schema.schema() might not exist or be malformed

        return None

    async def send_function_result(self, call_id: str, result: Any, connection) -> None:
        """
        Send the function execution result back over the WebSocket connection.

        Args:
            call_id: The ID of the function call
            result: The result of the function execution
            connection: WebSocket connection to send results back
        """
        result_str = self._convert_result_to_json_string(result)
        function_output = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result_str,
            },
        }

        self.logger.info(
            "Sending function result for call_id %s: %s...",
            call_id,
            self._truncate_result(result_str),
        )

        await connection.send(json.dumps(function_output))

    def _convert_result_to_json_string(self, result: Any) -> str:
        """
        Convert any result object to a JSON string representation.

        Args:
            result: The result object to convert

        Returns:
            A JSON string representation of the result
        """
        if isinstance(result, dict):
            return json.dumps(result)
        elif not isinstance(result, str):
            return json.dumps({"result": str(result)})
        else:
            try:
                json.loads(result)
                return result
            except JSONDecodeError:
                return json.dumps({"result": result})

    async def create_new_response(self, connection) -> None:
        """
        Create a new response message after sending function results.

        Args:
            connection: WebSocket connection to send the message
        """
        response_create = {"type": "response.create"}

        self.logger.info("Creating new response after function result.")

        await connection.send(json.dumps(response_create))

    def _truncate_result(self, result: Union[str, Any], max_length: int = 100) -> str:
        """
        Truncate a string representation of a result for logging purposes.

        Args:
            result: The result to truncate
            max_length: Maximum length of the truncated string

        Returns:
            The truncated string
        """
        result_str = str(result)
        if len(result_str) > max_length:
            return result_str[:max_length] + "..."
        return result_str
