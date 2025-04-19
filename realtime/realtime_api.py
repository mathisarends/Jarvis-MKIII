import json
import base64
import asyncio
import traceback
from typing import Optional, Callable, Dict, Any, List
import websockets

from realtime.audio.base import AudioPlayerBase

from realtime.config import (
    OPENAI_WEBSOCKET_URL,
    OPENAI_HEADERS,
    SYSTEM_MESSAGE,
    TEMPERATURE,
    VOICE,
)
from tools.time_tool import get_current_time
from utils.logging_mixin import LoggingMixin
from tools.tool_registry import ToolRegistry
from tools.weather.weather_tool import get_weather


class OpenAIRealtimeAPI(LoggingMixin):
    """
    Class for managing OpenAI Realtime API connections and communications.
    With Tool-Registry integration.
    """

    NO_CONNECTION_ERROR_MSG = "No connection available. Call create_connection() first."

    def __init__(self):
        """
        Initialize the OpenAI Realtime API client.
        All configuration is loaded from config files.
        """
        self.system_message = SYSTEM_MESSAGE
        self.voice = VOICE
        self.temperature = TEMPERATURE
        self.websocket_url = OPENAI_WEBSOCKET_URL
        self.headers = OPENAI_HEADERS
        self.connection = None
        
        # Initialize tool registry
        self._init_tool_registry()
        
        self.logger.info("OpenAI Realtime API class initialized")

    def _init_tool_registry(self) -> None:
        """
        Initialize the tool registry and register the weather tool.
        This is a private method that sets up all available tools.
        """
        self.tool_registry = ToolRegistry()
        
        self.tool_registry.register_tool(get_weather)
        self.tool_registry.register_tool(get_current_time)


    def _get_openai_tools(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get the OpenAI-compatible tool schemas for specified tools or all tools.
        
        Args:
            tool_names: Optional list of tool names to include, if None, all tools are included
            
        Returns:
            List of OpenAI-compatible tool schemas
        """
        try:
            tools = self.tool_registry.get_openai_schema(tool_names)
            self.logger.debug("Retrieved %d tools for OpenAI", len(tools))
            return tools
        except Exception as e:
            self.logger.error("Error getting OpenAI tools: %s", e)
            return []

    async def setup_and_run(
        self,
        mic_stream,
        audio_player: AudioPlayerBase,
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        """
        Set up the connection and run the main loop.

        Args:
            mic_stream: A MicrophoneStream object for audio input
            audio_player: An AudioPlayer object for audio playback
            handle_transcript: Optional function to handle transcript responses

        Returns:
            True on successful execution, False on error
        """
        if not await self.create_connection():
            return False

        if not await self.initialize_session():
            await self.close()
            return False

        try:
            await asyncio.gather(
                self.send_audio(mic_stream),
                self.process_responses(
                    audio_player=audio_player,
                    handle_transcript=handle_transcript,
                ),
            )
            return True
        except asyncio.CancelledError:
            self.logger.info("Tasks were cancelled")
            return True
        except Exception as e:
            self.logger.error("Error in main loop: %s", e)
            self.logger.error(traceback.format_exc())
            return False
        finally:
            await self.close()

    async def create_connection(self) -> Optional[websockets.WebSocketClientProtocol]:
        """
        Create a WebSocket connection to the OpenAI API.

        Returns:
            The WebSocket connection or None on error
        """
        try:
            self.logger.info("Establishing connection to %s...", self.websocket_url)
            self.connection = await websockets.connect(
                self.websocket_url, extra_headers=self.headers
            )
            self.logger.info("Connection successfully established!")
            return self.connection
        except Exception as e:
            self.logger.error("Connection error: %s", e)
            return None

    async def initialize_session(self) -> bool:
        """ Initialize a session with the OpenAI API.
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return False
        
        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "voice": self.voice,
                "instructions": self.system_message,
                "modalities": ["text", "audio"],
                "temperature": self.temperature,
                "tools": self._get_openai_tools()
            },
        }

        try:
            self.logger.info("Sending session update...")
            await self.connection.send(json.dumps(session_update))
            self.logger.info("Session update sent successfully")
            return True
        except Exception as e:
            self.logger.error("Error initializing session: %s", e)
            return False
        
    async def send_audio(self, mic_stream) -> None:
        """
        Send audio data from the microphone to the OpenAI API.

        Args:
            mic_stream: A MicrophoneStream object that provides audio data
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return

        try:
            self.logger.info("Starting audio transmission...")
            audio_chunks_sent = 0

            while mic_stream.is_active:
                data = mic_stream.read_chunk()
                if not data:
                    await asyncio.sleep(0.01)
                    continue

                base64_audio = base64.b64encode(data).decode("utf-8")

                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio,
                }

                await self.connection.send(json.dumps(audio_append))
                audio_chunks_sent += 1

                if audio_chunks_sent % 100 == 0:
                    self.logger.debug("Audio chunks sent: %d", audio_chunks_sent)

                await asyncio.sleep(0.01)

        except Exception as e:
            self.logger.error("Error sending audio: %s", e)

    async def process_responses(
        self,
        audio_player: AudioPlayerBase,
        handle_text: Optional[Callable[[Dict[str, Any]], None]] = None,
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """
        Process responses from the OpenAI API.

        Args:
            audio_player: An AudioPlayer object for audio playback
            handle_text: Optional function to handle text responses
            handle_transcript: Optional function to handle transcript responses
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return

        try:
            self.logger.info("Starting response processing...")
            async for message in self.connection:
                await self._process_single_message(
                    message, audio_player, handle_text, handle_transcript
                )

        except Exception as e:
            self.logger.error("Error processing responses: %s", e)
            self.logger.error(traceback.format_exc())

    async def close(self) -> None:
        """Close the connection"""
        if not self.connection:
            return

        self.logger.info("Closing connection...")
        await self.connection.close()
        self.connection = None
        self.logger.info("Connection closed")

    async def _process_single_message(
        self,
        message: str,
        audio_player: AudioPlayerBase,
        handle_text: Optional[Callable[[Dict[str, Any]], None]],
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]],
    ) -> None:
        """Process a single message from the API stream"""
        try:
            self.logger.debug("Raw message received: %s...", message[:100])

            response = self._parse_response(message)
            if not response:
                return

            event_type = response.get("type", "")

            # Handle different event types
            await self._route_event(
                event_type, response, audio_player, handle_text, handle_transcript
            )

        except Exception as e:
            self.logger.error("Error processing single message: %s", e)

    def _parse_response(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response and validate it's a dictionary"""
        try:
            response = json.loads(message)

            if not isinstance(response, dict):
                self.logger.warning(
                    "Warning: Response is not a dictionary, it's %s",
                    type(response),
                )
                return None

            return response

        except json.JSONDecodeError:
            self.logger.warning("Warning: Received non-JSON message from server")
            return None

    async def _route_event(
        self,
        event_type: str,
        response: Dict[str, Any],
        audio_player: AudioPlayerBase,
        handle_text: Optional[Callable[[Dict[str, Any]], None]],
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]],
    ) -> None:
        """Route the event to the appropriate handler based on event type"""

        if event_type == "input_audio_buffer.speech_started":
            audio_player.clear_queue_and_stop()

        if event_type == "response.text.delta" and "delta" in response:
            if handle_text:
                handle_text(response)

        elif event_type == "response.audio.delta":
            self._handle_audio_delta(response, audio_player)

        elif event_type == "response.audio_transcript.delta":
            if handle_transcript:
                handle_transcript(response)

        elif event_type == "response.done":
            self.logger.info("Response completed")
            
            # Check if there's a function call in the response
            await self._handle_function_call_in_response(response)

        elif event_type in ["error", "session.updated", "session.created"]:
            self.logger.info("Event received: %s", event_type)
            if event_type == "error":
                self.logger.error("API error: %s", response)

    async def _handle_function_call_in_response(self, response: Dict[str, Any]) -> None:
        """
        Handle function call if present in the response.done event.
        
        Args:
            response: The response.done event data
        """
        try:
            # Extract output from response
            output = response.get("response", {}).get("output", [])
            
            # Check if there's any function_call in the output
            for item in output:
                if item.get("type") == "function_call":
                    await self._process_function_call(item)
        
        except Exception as e:
            self.logger.error("Error processing function call: %s", e)
            self.logger.error(traceback.format_exc())

    async def _process_function_call(self, function_call_item: Dict[str, Any]) -> None:
        """
        Process a function call item and send the result back to the API.
        
        Args:
            function_call_item: The function call item from the response
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return
            
        try:
            function_name = function_call_item.get("name")
            call_id = function_call_item.get("call_id")
            arguments_str = function_call_item.get("arguments", "{}")
            
            if not function_name or not call_id:
                self.logger.error("Missing function name or call_id in function call")
                return
                
            self.logger.info(f"Processing function call: {function_name} with call_id: {call_id}")
            
            # Parse the arguments
            arguments = json.loads(arguments_str)
            
            # Execute the function
            result = await self._execute_tool(function_name, arguments)
            
            # Send the result back to the API
            await self._send_function_result(call_id, result)
            
            # Create a new response after sending the function result
            await self._create_new_response()
            
        except Exception as e:
            self.logger.error(f"Error processing function {function_name}: {e}")
            self.logger.error(traceback.format_exc())

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with the given arguments.
        
        Args:
            tool_name: The name of the tool to execute
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool execution
        """
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            self.logger.error(f"Tool {tool_name} not found in registry")
            return {"error": f"Tool {tool_name} not found"}
            
        self.logger.info(f"Executing tool {tool_name} with arguments: {arguments}")
        
        try:
            if hasattr(tool, "arun"):
                # arun erwartet entweder ein einzelnes Argument oder ein Dictionary als erstes Argument
                # Wenn es keine Argumente gibt, rufen wir es ohne auf
                if not arguments:
                    result = await tool.arun({})
                # Wenn es genau ein Argument gibt mit Namen "tool_input"
                elif "tool_input" in arguments and len(arguments) == 1:
                    result = await tool.arun(arguments["tool_input"])
                # Ansonsten übergeben wir das gesamte Dictionary als tool_input
                else:
                    result = await tool.arun(arguments)
            # Für asynchrone invoke-Methode
            elif asyncio.iscoroutinefunction(getattr(tool, "invoke", None)):
                result = await tool.invoke(arguments)
            # Für synchrone Ausführung
            else:
                result = tool.invoke(arguments)
                
            self.logger.info(f"Tool {tool_name} execution result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}

    async def _send_function_result(self, call_id: str, result: Any) -> None:
        """
        Send the function call result back to the API.
        
        Args:
            call_id: The call_id from the function_call item
            result: The result of the function execution
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return
            
        try:
            # Convert result to string if it's not already
            if isinstance(result, dict):
                result_str = json.dumps(result)
            elif not isinstance(result, str):
                result_str = json.dumps({"result": str(result)})
            else:
                # If it's already a string, make sure it's valid JSON
                try:
                    json.loads(result)
                    result_str = result
                except json.JSONDecodeError:
                    # If not valid JSON, wrap it
                    result_str = json.dumps({"result": result})
            
            # Create the function call output message
            function_output = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result_str
                }
            }
            
            self.logger.info(f"Sending function result for call_id {call_id}: {result_str[:100]}...")
            
            # Send the function result
            await self.connection.send(json.dumps(function_output))
            
        except Exception as e:
            self.logger.error(f"Error sending function result: {e}")
            self.logger.error(traceback.format_exc())

    async def _create_new_response(self) -> None:
        """
        Create a new response after sending a function result.
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return
            
        try:
            # Create a new response
            response_create = {
                "type": "response.create"
            }
            
            self.logger.info("Creating new response after function call result")
            
            # Send the response create message
            await self.connection.send(json.dumps(response_create))
            
        except Exception as e:
            self.logger.error(f"Error creating new response: {e}")
            self.logger.error(traceback.format_exc())

    def _handle_audio_delta(self, response, audio_player: AudioPlayerBase) -> None:
        """Handle audio responses from OpenAI API"""
        base64_audio = response.get("delta", "")
        if not base64_audio or not isinstance(base64_audio, str):
            return

        audio_player.add_audio_chunk(base64_audio)