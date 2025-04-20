import json
import base64
import asyncio
import time
from typing import Optional, Callable, Dict, Any, List, cast
import websockets

from audio.audio_player_factory import AudioPlayerFactory
from audio.microphone import PyAudioMicrophone
from realtime.config import (
    OPENAI_WEBSOCKET_URL,
    OPENAI_HEADERS,
    SYSTEM_MESSAGE,
    TEMPERATURE,
    VOICE,
)
from realtime.realtime_tool_handler import RealtimeToolHandler
from realtime.typings import AudioDeltaResponse, OpenAIRealtimeResponse
from speech.converstation_duration_tracker import ConversationDurationTracker
from tools.volume_tool import get_volume_tool, set_volume_tool
from tools.weather.weather_tool import get_weather
from tools.web_search_tool import web_search_tool
from tools.tool_registry import ToolRegistry

from utils.logging_mixin import LoggingMixin


class OpenAIRealtimeAPI(LoggingMixin):
    """
    Class for managing OpenAI Realtime API connections and communications.
    With Tool-Registry integration.

    This class handles all the interaction with the OpenAI API including:
    - Establishing and maintaining WebSocket connections
    - Sending audio data from the microphone
    - Processing responses including text, audio and tool calls
    - Gracefully handling connection closures
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

        self.tool_registry = ToolRegistry()
        self._init_tool_registry()

        self.tool_handler = RealtimeToolHandler(self.tool_registry)
        self.audio_player = AudioPlayerFactory.get_shared_instance()
        
        self.duration_tracker = ConversationDurationTracker()
        self._last_item_id = None

        self.logger.info("OpenAI Realtime API class initialized")

    def _init_tool_registry(self) -> None:
        """
        Initialize the tool registry and register all available tools.
        """
        try:
            self.tool_registry.register_tool(get_weather)
            self.tool_registry.register_tool(web_search_tool)
            self.tool_registry.register_tool(set_volume_tool)
            self.tool_registry.register_tool(get_volume_tool)

            self.logger.info("All tools successfully registered")
        except Exception as e:
            self.logger.error("Failed to register tools: %s", e)

    def _get_openai_tools(
        self, tool_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
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
        mic_stream: PyAudioMicrophone,
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]] = None,
        event_handler: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> bool:
        """
        Set up the connection and run the main loop.

        Args:
            mic_stream: A MicrophoneStream object for audio input
            handle_transcript: Optional function to handle transcript responses
            event_handler: Optional function to handle special events

        Returns:
            True on successful execution, False on error
        """
        if not await self.create_connection():
            return False

        if not await self.initialize_session():
            await self.close()
            return False

        try:
            # Starte den ConversationDurationTracker für diese Konversation
            self.duration_tracker.start_conversation()
            self.logger.info("Started conversation tracking at %sms", self.duration_tracker.current_time_ms)
            
            # Reset item ID für diese neue Konversation
            self._last_item_id = None
            
            await asyncio.gather(
                self.send_audio(mic_stream),
                self.process_responses(
                    handle_transcript=handle_transcript,
                    event_handler=event_handler,
                ),
            )
            return True
        except asyncio.CancelledError:
            self.logger.info("Tasks were cancelled")
            return True
        finally:
            # Beende den Tracker und logge die Gesamtdauer
            duration = self.duration_tracker.end_conversation()
            self.logger.info("Conversation ended. Total duration: %dms (%.2fs)", duration, duration / 1000)
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

        except websockets.exceptions.InvalidStatusCode as e:
            self.logger.error("Invalid status code from WebSocket server: %s", e)
        except ConnectionRefusedError as e:
            self.logger.error("Connection refused: %s", e)
        except OSError as e:
            self.logger.error("OS-level connection error: %s", e)

    async def initialize_session(self) -> bool:
        """
        Initialize a session with the OpenAI API.

        Returns:
            True if session was successfully initialized, False otherwise
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
                "tools": self._get_openai_tools(),
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

    async def send_audio(self, mic_stream: PyAudioMicrophone) -> None:
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
                if not self.connection or self.connection.closed:
                    self.logger.info("Connection closed, stopping audio transmission")
                    break

                data = mic_stream.read_chunk()
                if not data:
                    await asyncio.sleep(0.01)
                    continue

                base64_audio = base64.b64encode(data).decode("utf-8")

                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio,
                }

                # Check connection before sending
                if not self.connection.closed:
                    await self.connection.send(json.dumps(audio_append))
                    audio_chunks_sent += 1

                    if audio_chunks_sent % 100 == 0:
                        self.logger.debug("Audio chunks sent: %d", audio_chunks_sent)
                else:
                    self.logger.info("Connection closed, stopping audio transmission")
                    break

                await asyncio.sleep(0.01)

        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info("WebSocket connection closed normally during audio send")
        except websockets.exceptions.ConnectionClosedError as e:
            if str(e).startswith("sent 1000 (OK)"):
                # Also normal behavior
                self.logger.info(
                    "WebSocket connection closed normally during audio send"
                )
            else:
                self.logger.error(
                    "WebSocket connection closed unexpectedly during audio send: %s", e
                )
        except asyncio.TimeoutError as e:
            self.logger.error("Timeout while sending audio: %s", e)

    async def process_responses(
        self,
        handle_text: Optional[Callable[[Dict[str, Any]], None]] = None,
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]] = None,
        event_handler: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        """
        Process responses from the OpenAI API.

        Args:
            handle_text: Optional function to handle text responses
            handle_transcript: Optional function to handle transcript responses
            event_handler: Optional function to handle special events
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return

        try:
            self.logger.info("Starting response processing...")
            async for message in self.connection:
                await self._process_single_message(
                    message=message,
                    handle_text=handle_text,
                    handle_transcript=handle_transcript,
                    event_handler=event_handler,
                )

        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info(
                "WebSocket connection closed normally during response processing"
            )
        except websockets.exceptions.ConnectionClosedError as e:
            if str(e).startswith("sent 1000 (OK)"):
                self.logger.info(
                    "WebSocket connection closed normally during response processing"
                )
            else:
                self.logger.error(
                    "WebSocket connection closed unexpectedly while waiting for responses: %s",
                    e,
                )
        except asyncio.TimeoutError as e:
            self.logger.error("Timeout while receiving responses: %s", e)

    async def close(self) -> None:
        """
        Close the WebSocket connection gracefully.
        """
        if not self.connection:
            return

        self.logger.info("Closing connection...")
        await self.connection.close()
        self.connection = None
        self.logger.info("Connection closed")

    async def _process_single_message(
        self,
        message: str,
        handle_text: Optional[Callable[[Dict[str, Any]], None]],
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]],
        event_handler: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        """
        Process a single message from the API stream.

        Args:
            message: The raw message string received from the API
            handle_text: Optional function to handle text responses
            handle_transcript: Optional function to handle transcript responses
            event_handler: Optional function to handle special events
        """
        try:
            self.logger.debug("Raw message received: %s...", message[:100])

            response = self._parse_response(message)
            if not response:
                return

            # Tracke item IDs für Truncation
            self._track_message_items(response)
            
            event_type = response.get("type", "")

            await self._route_event(
                event_type,
                response,
                handle_text,
                handle_transcript,
                event_handler,
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Received malformed JSON message: %s", e)
        except KeyError as e:
            self.logger.warning("Expected key missing in message: %s", e)

    def _track_message_items(self, response: OpenAIRealtimeResponse) -> None:
        """
        Verfolgt Message-Items vom Assistenten für spätere Truncation.
        
        Basierend auf der OpenAI Realtime API-Dokumentation werden die
        IDs der erzeugten Nachrichtenelemente nachverfolgt.
        """
        event_type = response.get("type", "")
        
        if event_type == "response.created":
            if "response" in response and "id" in response["response"]:
                self._last_item_id = response["response"]["id"]
                self.logger.debug("New response created: ID=%s", self._last_item_id)
        
        elif event_type == "response.output_item.added":
            if "item" in response and "id" in response["item"]:
                self._last_item_id = response["item"]["id"]
                self.logger.debug("Output item added: ID=%s", self._last_item_id)
        
        elif event_type == "response.content_part.added":
            if "item" in response and "id" in response["item"]:
                self._last_item_id = response["item"]["id"]
                self.logger.debug("Content part added: ID=%s", self._last_item_id)

    def _parse_response(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response and validate it's a dictionary.

        Args:
            message: The raw message string received from the API

        Returns:
            Parsed dictionary or None if parsing failed
        """
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
        response: OpenAIRealtimeResponse,
        handle_text: Optional[Callable[[Dict[str, Any]], None]],
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]],
        event_handler: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        """
        Route the event to the appropriate handler based on event type.

        Args:
            event_type: The type of event from the response
            response: The full response object
            handle_text: Optional function to handle text responses
            handle_transcript: Optional function to handle transcript responses
            event_handler: Optional function to handle special events (propagated to controller)
        """
        if event_handler:
            if event_type in ["input_audio_buffer.speech_started", "response.done"]:
                event_handler(event_type)

        # Then handle the events normally
        if event_type == "input_audio_buffer.speech_started":
            self.audio_player.clear_queue_and_stop()
            
            await self._handle_truncation()

        if event_type == "response.text.delta" and "delta" in response:
            if handle_text:
                handle_text(response)

        elif event_type == "response.audio.delta":
            self._handle_audio_delta(response)

        elif event_type == "response.audio_transcript.delta":
            if handle_transcript:
                handle_transcript(response)

        elif event_type == "response.done":
            self.logger.info("Response completed")

            await self.tool_handler.handle_function_call_in_response(
                response, self.connection
            )

        elif event_type == "conversation.item.truncated":
            # Bestätigung für erfolgreiches Truncation
            self.logger.info("Truncation successful: %s", response)

        elif event_type in ["error", "session.updated", "session.created"]:
            self.logger.info("Event received: %s", event_type)
            if event_type == "error":
                self.logger.error("API error: %s", response)

    def _handle_audio_delta(self, response: OpenAIRealtimeResponse) -> None:
        """
        Handle audio responses from OpenAI API.

        Args:
            response: The response containing audio data
        """
        if response["type"] != "response.audio.delta":
            return

        base64_audio = cast(AudioDeltaResponse, response)["delta"]
        if not base64_audio or not isinstance(base64_audio, str):
            return

        self.audio_player.add_audio_chunk(base64_audio)

    async def _handle_truncation(self):
        """
        Sendet ein truncate-Event, wenn eine Konversation aktiv ist und Audio abgespielt wird.
        Nutzt den ConversationDurationTracker, um die korrekte Zeitangabe zu ermitteln.
        """
        if not self.connection or self.connection.closed:
            self.logger.error("No connection available for truncation")
            return
            
        if not self._last_item_id:
            self.logger.debug("No active conversation item to truncate")
            return
        
        # Hole die aktuelle Zeit in Millisekunden seit Konversationsbeginn
        current_time_ms = self.duration_tracker.duration_ms
        
        truncate_event = {
            "type": "conversation.item.truncate",
            "item_id": self._last_item_id,
            "content_index": 0,
            "audio_end_ms": current_time_ms,
            "event_id": f"truncate_{int(time.time() * 1000)}"
        }
        
        try:
            self.logger.info(f"Sending truncation at {current_time_ms}ms for item {self._last_item_id}")
            await self.connection.send(json.dumps(truncate_event))
        except Exception as e:
            self.logger.error("Failed to send truncation event: %s", exc_info=e)