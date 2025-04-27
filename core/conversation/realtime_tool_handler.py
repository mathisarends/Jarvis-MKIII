import json
from json import JSONDecodeError
from typing import Dict, Any, Optional, Union, List, Literal, TypedDict
from websockets.legacy.client import WebSocketClientProtocol

from langchain_core.tools import BaseTool

from shared.logging_mixin import LoggingMixin
from plugins.tool_registry import ToolRegistry


class DoneResponseWithToolCall(TypedDict):
    """
    Represents a completed response that includes a tool call result.
    """

    type: Literal["response.done"]
    response: Dict[str, Any]


class FunctionCallItem(TypedDict):
    """
    Represents an item that triggers a function call.

    Attributes:
        type: A fixed string indicating this is a 'function_call' type.
        name: The optional name of the function to be called.
        call_id: A unique identifier for this function call.
        arguments: A serialized string (e.g., JSON) containing the arguments to pass to the function.
    """

    type: Literal["function_call"]
    name: Optional[str]
    call_id: str
    arguments: str


class RealtimeToolHandler(LoggingMixin):
    """
    Handles function calls in OpenAI Realtime API responses, executes tools,
    and sends the results back over a WebSocket connection.
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.most_recent_tool_call_id = ""

    async def handle_function_call_in_response(
        self, response: DoneResponseWithToolCall, connection: WebSocketClientProtocol
    ) -> None:
        """
        Process function calls found in a 'response.done' API response.

        Args:
            response: The typed API response containing function calls
            connection: WebSocket connection to send results back
        """
        if not connection:
            self.logger.error("No connection available.")
            return

        output: List[FunctionCallItem] = response["response"].get("output", [])

        for item in output:
            await self.process_function_call(item, connection)

    async def process_function_call(
        self, function_call_item: FunctionCallItem, connection: WebSocketClientProtocol
    ) -> None:
        """
        Process a single function call item and execute the corresponding tool.

        Args:
            function_call_item: Typed function call data
            connection: WebSocket connection to send results back
        """
        function_name = function_call_item["name"]
        call_id = function_call_item["call_id"]
        arguments_str = function_call_item.get("arguments", "{}")

        self.logger.info(
            "Processing function call: %s with call_id: %s", function_name, call_id
        )

        self.most_recent_tool_call_id = call_id

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
        Execute the registered tool by name with given arguments.

        Args:
            tool_name: Name of the tool as registered in the registry.
            arguments: Arguments passed to the tool.

        Returns:
            Result of the tool execution, or error information.
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
        except (AttributeError, TypeError, ValueError, KeyError) as e:
            self.logger.error(
                "Error executing tool %s: %s", tool_name, e, exc_info=True
            )
            return {"error": f"{type(e).__name__}: {str(e)}"}

    async def _execute_tool_with_dispatch(
        self, tool: BaseTool, arguments: Dict[str, Any]
    ) -> Any:
        """
        Run the tool using its available async or sync method.

        Args:
            tool: The tool instance to execute.
            arguments: Parameters to pass to the tool.

        Returns:
            Result from the tool method, or error message.
        """
        if hasattr(tool, "arun"):
            return await tool.arun(arguments)

        if hasattr(tool, "invoke"):
            return tool.invoke(arguments)

        return {"error": "Tool has no supported execution method"}

    def _get_main_parameter(
        self, tool: BaseTool, arguments: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Determine the main input value from arguments, based on schema.

        Args:
            tool: The tool to analyze.
            arguments: Provided arguments to match against the schema.

        Returns:
            The main parameter value or None if ambiguous.
        """
        param_name = self._get_tool_main_param_name(tool)

        if param_name and param_name in arguments:
            return arguments[param_name]

        if len(arguments) == 1:
            return next(iter(arguments.values()))

        return None

    def _get_tool_main_param_name(self, tool: BaseTool) -> Optional[str]:
        """
        Retrieve the primary argument name from the tool schema.

        Args:
            tool: The tool with a defined argument schema.

        Returns:
            Name of the main argument or None if not determinable.
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
            pass

        return None

    async def send_function_result(
        self, call_id: str, result: Any, connection: WebSocketClientProtocol
    ) -> None:
        """
        Send the result of a function execution back to the client.

        Args:
            call_id: Unique identifier of the function call.
            result: The computed or returned result.
            connection: WebSocket connection to send back data.
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
        Safely convert a tool result to a JSON string.

        Args:
            result: The output from the tool.

        Returns:
            A valid JSON string representation.
        """
        if isinstance(result, dict):
            return json.dumps(result)

        if not isinstance(result, str):
            return json.dumps({"result": str(result)})

        try:
            json.loads(result)
            return result
        except JSONDecodeError:
            return json.dumps({"result": result})

    async def create_new_response(self, connection: WebSocketClientProtocol) -> None:
        """
        Instruct the client to continue the conversation after a function result.

        Args:
            connection: The WebSocket connection to send the message.
        """
        self.logger.info("Creating new response after function result.")
        await connection.send(json.dumps({"type": "response.create"}))

    def _truncate_result(self, result: Union[str, Any], max_length: int = 100) -> str:
        """
        Truncate a result string for concise logging.

        Args:
            result: Full result string or object.
            max_length: Maximum length before truncating.

        Returns:
            A shortened string with ellipsis if needed.
        """
        result_str = str(result)
        return (
            result_str[:max_length] + "..."
            if len(result_str) > max_length
            else result_str
        )
