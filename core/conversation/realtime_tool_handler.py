import json
import threading
import asyncio
from json import JSONDecodeError
from typing import Dict, Any, Optional, Union, List, Literal, TypedDict
from websockets.legacy.client import WebSocketClientProtocol

from langchain_core.tools import BaseTool

from shared.logging_mixin import LoggingMixin
from plugins.tool_registry import ToolRegistry
from shared.event_bus import EventBus, EventType


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
        self._background_tasks = {}  # Track background tasks
        self._event_loop = None
        self.event_bus = EventBus.get_instance()

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

        # Store current event loop for background tasks
        self._event_loop = asyncio.get_event_loop()

        output: List[FunctionCallItem] = response["response"].get("output", [])

        for item in output:
            await self.process_function_call(item, connection)

    async def process_function_call(
        self, function_call_item: FunctionCallItem, connection: WebSocketClientProtocol
    ) -> None:
        """
        Process a single function call item and execute the corresponding tool.
        """
        function_name = function_call_item["name"]
        call_id = function_call_item["call_id"]
        arguments_str = function_call_item.get("arguments", "{}")

        self.logger.info(
            "Processing function call: %s with call_id: %s", function_name, call_id
        )
        self.most_recent_tool_call_id = call_id

        self.event_bus.publish(EventType.ASSISTANT_STARTED_TOOL_CALL)

        # Parse arguments
        try:
            arguments = json.loads(arguments_str)
        except JSONDecodeError as e:
            self.logger.error("Invalid JSON in arguments: %s", e)
            return

        # Get tool from registry
        tool = self.tool_registry.get_tool(function_name)

        if not tool:
            self.logger.error("Tool %s not found in registry", function_name)
            await self.send_function_result(
                call_id, {"error": f"Tool {function_name} not found"}, connection
            )
            await self.create_new_response(connection)

            self.event_bus.publish(EventType.ASSISTANT_COMPLETED_TOOL_CALL)
            return

        return_early_message = self.tool_registry.get_early_message(function_name)

        if not return_early_message:
            result = await self.execute_tool(function_name, arguments)
            await self.send_function_result(call_id, result, connection)
            await self.create_new_response(connection)

            self.event_bus.publish(
                EventType.ASSISTANT_COMPLETED_TOOL_CALL
            )
            return

        # Long-running tool execution flow
        self.logger.info(
            "Tool %s is long-running, returning early message: %s",
            function_name,
            return_early_message,
        )

        # Sende eine allgemeine Nachricht, dass der Tool-Call gestartet wurde,
        # anstatt einen function result
        await self.send_tool_started_message(
            return_early_message,
            connection,
        )

        self._execute_tool_in_background(
            tool, arguments, function_name, call_id, connection
        )

    async def send_tool_started_message(
        self,
        message: str,
        connection: WebSocketClientProtocol,
    ) -> None:
        """
        Send a message informing that a tool has started execution.
        """
        start_message = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": f"Informiere den Nutzer, dass das Tool ausgeführt wird mit einer Nachricht wie: '{message}'"
            }
        }

        await connection.send(json.dumps(start_message))

    def _execute_tool_in_background(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any],
        tool_name: str,
        call_id: str,
        connection: WebSocketClientProtocol,
    ) -> None:
        """
        Execute the tool in a background thread.
        """
        if call_id in self._background_tasks:
            self.logger.warning(
                "Tool execution with call_id %s is already in progress. Ignoring duplicate call.",
                call_id,
            )
            return

        # Create and start background thread
        thread = threading.Thread(
            target=self._run_background_task,
            args=(tool, arguments, tool_name, call_id, connection),
            name=f"tool-{tool_name}-{call_id}",
            daemon=True,  # Daemon thread to avoid blocking program exit
        )

        self._background_tasks[call_id] = thread
        thread.start()

        self.logger.info(
            "Started background execution for tool %s with call_id %s",
            tool_name,
            call_id,
        )

    def _run_background_task(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any],
        tool_name: str,
        call_id: str,
        connection: WebSocketClientProtocol,
    ) -> None:
        """
        Actual execution of the tool in a background thread.
        """
        try:
            # Create a new event loop for this thread
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()

            # Execute tool based on its capabilities
            if hasattr(tool, "arun"):
                self.logger.info(
                    "Running tool %s asynchronously in background", tool_name
                )
                result = loop.run_until_complete(tool.arun(tool_input=arguments))
                self.logger.info(
                    "Background async tool %s execution completed with result: %s",
                    tool_name,
                    self._truncate_result(result),
                )
            elif hasattr(tool, "invoke"):
                self.logger.info(
                    "Running tool %s synchronously in background", tool_name
                )
                result = tool.invoke(arguments)
                self.logger.info(
                    "Background sync tool %s execution completed with result: %s",
                    tool_name,
                    self._truncate_result(result),
                )
            else:
                result = {"error": "Tool has no supported background execution method"}
                self.logger.error(
                    "Background tool %s has neither arun nor invoke methods", tool_name
                )

            # Send result back to main thread
            self._send_result_to_main_thread(call_id, result, connection)

            # Emit completion event from background thread
            self._emit_completion_event_from_background(
                tool_name, call_id, result, True
            )

        except Exception as e:
            self.logger.error(
                "Error in background execution of tool %s: %s",
                tool_name,
                str(e),
                exc_info=True,
            )
            # Send error back through main thread
            error_result = {"error": f"{type(e).__name__}: {str(e)}"}
            self._send_result_to_main_thread(call_id, error_result, connection)

            # Emit completion event with error
            self._emit_completion_event_from_background(
                tool_name, call_id, error_result, False
            )
        finally:
            # Clean up task tracking
            if call_id in self._background_tasks:
                del self._background_tasks[call_id]

    def _send_result_to_main_thread(
        self, call_id: str, result: Any, connection: WebSocketClientProtocol
    ) -> None:
        """
        Send results from background thread to main thread.
        """
        if not self._event_loop or not self._event_loop.is_running():
            self.logger.error(
                "Cannot send background result: Main event loop not available or not running"
            )
            return

        future = asyncio.run_coroutine_threadsafe(
            self.send_background_result(call_id, result, connection), self._event_loop
        )

        try:
            # Wait for result to catch errors
            future.result(timeout=10)
            self.logger.info(
                "Background result for call_id %s successfully sent", call_id
            )
        except Exception as e:
            self.logger.error("Failed to send background result: %s", str(e))

    async def send_background_result(
        self, call_id: str, result: Any, connection: WebSocketClientProtocol
    ) -> None:
        """
        Send the result of a background tool execution.
        """
        self.logger.info(
            "Sending background result for call_id %s: %s",
            call_id,
            self._truncate_result(str(result)),
        )

        # Richtige Methode mit entsprechender ID verwenden
        await self.send_function_result(call_id, result, connection)

        self.logger.info("Sent background result as message")

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute the registered tool by name with given arguments.
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
        """
        try:
            if hasattr(tool, "arun"):
                return await tool.arun(tool_input=arguments)

            if hasattr(tool, "invoke"):
                return tool.invoke(arguments)

            return {"error": "Tool has no supported execution method"}
        except Exception as e:
            self.logger.error(
                "Error in tool execution for %s: %s", tool.name, str(e), exc_info=True
            )
            return {"error": f"{type(e).__name__}: {str(e)}"}

    async def send_function_result(
        self, call_id: str, result: Any, connection: WebSocketClientProtocol
    ) -> None:
        """
        Send the result of a function execution back to the client.
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
        await self.create_new_response(connection)

    def _convert_result_to_json_string(self, result: Any) -> str:
        """
        Safely convert a tool result to a JSON string.
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
        """
        self.logger.info("Creating new response after function result.")
        await connection.send(json.dumps({"type": "response.create"}))

    def _emit_completion_event_from_background(
        self, tool_name: str, call_id: str, result: Any, success: bool
    ) -> None:
        """
        Emit the tool completion event from a background thread.
        """
        event_data = {"tool_name": tool_name, "call_id": call_id, "success": success}

        # Add error info if appropriate
        if isinstance(result, dict) and "error" in result:
            event_data["error"] = result["error"]

        # Use thread-safe publishing method
        self.event_bus.publish(EventType.ASSISTANT_COMPLETED_TOOL_CALL, event_data)

    def _truncate_result(self, result: Union[str, Any], max_length: int = 100) -> str:
        """
        Truncate a result string for concise logging.
        """
        result_str = str(result)
        if len(result_str) <= max_length:
            return result_str

        return result_str[:max_length] + "..."
