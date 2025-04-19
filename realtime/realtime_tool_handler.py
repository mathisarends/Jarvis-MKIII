import json
import traceback
from typing import Dict, Any, Optional, Union

from utils.logging_mixin import LoggingMixin
from tools.tool_registry import ToolRegistry


class RealtimeToolHandler(LoggingMixin):
    """
    Class for managing tool invocations in the OpenAI Realtime API.

    This class handles processing of function calls, executing the corresponding tools,
    and sending the results back to the API.
    """

    def __init__(self, tool_registry: ToolRegistry):
        """
        Initializes the tool handler.

        Args:
            tool_registry: The tool registry that manages available tools.
        """
        self.tool_registry = tool_registry

    async def handle_function_call_in_response(
        self,
        response: Dict[str, Any],
        connection
    ) -> None:
        """
        Processes a function call in a response.done message.

        Args:
            response: The response.done message.
            connection: The WebSocket connection to the API.
        """
        if not connection:
            self.logger.error("No connection available.")
            return

        try:
            output = response.get("response", {}).get("output", [])

            for item in output:
                if item.get("type") == "function_call":
                    await self.process_function_call(item, connection)

        except Exception as e:
            self.logger.error("Error while processing function call: %s", e)
            self.logger.error(traceback.format_exc())

    async def process_function_call(
        self,
        function_call_item: Dict[str, Any],
        connection
    ) -> None:
        """
        Processes a single function call.

        Args:
            function_call_item: The function call item from the response.
            connection: The WebSocket connection to the API.
        """
        try:
            function_name = function_call_item.get("name")
            call_id = function_call_item.get("call_id")
            arguments_str = function_call_item.get("arguments", "{}")

            if not function_name or not call_id:
                self.logger.error("Function name or call_id is missing in the function call.")
                return

            self.logger.info("Processing function call: %s with call_id: %s",
                             function_name, call_id)

            arguments = json.loads(arguments_str)
            result = await self.execute_tool(function_name, arguments)
            await self.send_function_result(call_id, result, connection)
            await self.create_new_response(connection)

        except Exception as e:
            self.logger.error("Error while processing function %s: %s", function_name, e)
            self.logger.error(traceback.format_exc())

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a tool by name with the given arguments.

        Args:
            tool_name: The name of the tool to execute.
            arguments: Arguments to pass to the tool.

        Returns:
            The result of the tool execution.
        """
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            self.logger.error("Tool %s not found in registry", tool_name)
            return {"error": f"Tool {tool_name} not found"}

        self.logger.info("Executing tool %s with arguments: %s", tool_name, arguments)

        try:
            result = await self._execute_tool_with_dispatch(tool, arguments)
            self.logger.info("Tool %s execution result: %s",
                             tool_name, self._truncate_result(result))
            return result
        except Exception as e:
            self.logger.error("Error executing tool %s: %s", tool_name, e)
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}

    async def _execute_tool_with_dispatch(self, tool, arguments: Dict[str, Any]) -> Any:
        """
        Executes a tool using a generic dispatch strategy based on tool capabilities.

        Args:
            tool: The tool object.
            tool_name: The name of the tool.
            arguments: Arguments to use for the execution.

        Returns:
            The result of the tool execution.
        """
        main_param = self._get_main_parameter(tool, arguments)

        if main_param is not None:
            if hasattr(tool, "arun"):
                return await tool.arun(main_param)
            return tool.invoke(main_param)

        if hasattr(tool, "arun"):
            return await tool.arun(arguments if arguments else "")

        return tool.invoke(arguments if arguments else "")

    def _get_main_parameter(self, tool, arguments: Dict[str, Any]) -> Optional[Any]:
        """
        Determines the main parameter value for a tool from its schema and arguments.

        Args:
            tool: The tool.
            arguments: Arguments passed in.

        Returns:
            The main parameter value or None.
        """
        param_name = self._get_tool_main_param_name(tool)

        if param_name and param_name in arguments:
            return arguments[param_name]

        if len(arguments) == 1:
            return next(iter(arguments.values()))

        return None

    def _get_tool_main_param_name(self, tool) -> Optional[str]:
        """
        Gets the name of the main parameter from a tool's schema.

        Args:
            tool: The tool object.

        Returns:
            The name of the main parameter or None.
        """
        try:
            if not hasattr(tool, "args_schema"):
                return None

            schema = tool.args_schema.schema()
            properties = schema.get("properties", {})

            if len(properties) == 1:
                return next(iter(properties.keys()))

            required = schema.get("required", [])
            if required:
                return required[0]

            return None
        except Exception:
            return None

    async def send_function_result(self, call_id: str, result: Any, connection) -> None:
        """
        Sends the function call result back to the API.

        Args:
            call_id: The call_id of the function call.
            result: The result of the tool execution.
            connection: The WebSocket connection to the API.
        """
        try:
            result_str = self._convert_result_to_json_string(result)
            function_output = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result_str
                }
            }

            self.logger.info("Sending function result for call_id %s: %s...",
                             call_id, self._truncate_result(result_str))

            await connection.send(json.dumps(function_output))

        except Exception as e:
            self.logger.error("Error sending function result: %s", e)
            self.logger.error(traceback.format_exc())

    def _convert_result_to_json_string(self, result: Any) -> str:
        """
        Converts a result to a valid JSON string.

        Args:
            result: The result to convert.

        Returns:
            A valid JSON string.
        """
        if isinstance(result, dict):
            return json.dumps(result)
        elif not isinstance(result, str):
            return json.dumps({"result": str(result)})
        else:
            try:
                json.loads(result)
                return result
            except json.JSONDecodeError:
                return json.dumps({"result": result})

    def _truncate_result(self, result: Union[str, Any], max_length: int = 100) -> str:
        """
        Truncates a result string for logging.

        Args:
            result: The result to truncate.
            max_length: Maximum length of the output.

        Returns:
            The truncated result as a string.
        """
        result_str = str(result)
        if len(result_str) > max_length:
            return result_str[:max_length] + "..."
        return result_str

    async def create_new_response(self, connection) -> None:
        """
        Creates a new response after sending a function result.

        Args:
            connection: The WebSocket connection to the API.
        """
        try:
            response_create = {
                "type": "response.create"
            }

            self.logger.info("Creating new response after function result.")

            await connection.send(json.dumps(response_create))

        except Exception as e:
            self.logger.error("Error creating new response: %s", e)
            self.logger.error(traceback.format_exc())
