import json
import asyncio
from typing import Optional, Callable, Dict, Any, List, cast

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
from realtime.websocket_manager import WebSocketManager
from speech.converstation_duration_tracker import ConversationDurationTracker
from tools.volume_tool import get_volume_tool, set_volume_tool
from tools.weather.weather_tool import get_weather
from tools.web_search_tool import web_search_tool
from tools.tool_registry import ToolRegistry

from utils.logging_mixin import LoggingMixin


class OpenAIRealtimeAPI(LoggingMixin):
    """
    Class for managing OpenAI Realtime API communications.
    With Tool-Registry integration.

    This class handles all the interaction with the OpenAI API including:
    - Managing the WebSocket communication through WebSocketManager
    - Sending audio data from the microphone
    - Processing responses including text, audio and tool calls
    """

    def __init__(self):
        """
        Initialize the OpenAI Realtime API client.
        All configuration is loaded from config files.
        """
        self.system_message = SYSTEM_MESSAGE
        self.voice = VOICE
        self.temperature = TEMPERATURE

        # Create WebSocket manager
        self.ws_manager = WebSocketManager(OPENAI_WEBSOCKET_URL, OPENAI_HEADERS)

        self.tool_registry = ToolRegistry()
        self._init_tool_registry()

        self.tool_handler = RealtimeToolHandler(self.tool_registry)
        self.audio_player = AudioPlayerFactory.get_shared_instance()

        # Initialisiere den Konversationsdauer-Tracker
        self.duration_tracker = ConversationDurationTracker()

        self._last_message_event_id = ""

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

    def _get_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Get the OpenAI-compatible tool schemas for all tools.

        Returns:
            List of OpenAI-compatible tool schemas
        """
        try:
            tools = self.tool_registry.get_openai_schema()
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
        if not await self.ws_manager.create_connection():
            return False

        self.duration_tracker.start_conversation()
        self.logger.info(
            "Started conversation tracking at %sms",
            self.duration_tracker.current_time_ms,
        )

        if not await self.initialize_session():
            await self.ws_manager.close()
            self.duration_tracker.end_conversation()
            return False

        try:
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
            # Beende den Tracker und protokolliere die Gesamtdauer
            duration = self.duration_tracker.end_conversation()
            self.logger.info(
                f"Conversation ended. Total duration: {duration}ms ({duration/1000:.2f}s)"
            )
            await self.ws_manager.close()

    async def initialize_session(self) -> bool:
        """
        Initialize a session with the OpenAI API.

        Returns:
            True if session was successfully initialized, False otherwise
        """
        if not self.ws_manager.is_connected():
            self.logger.error("No connection available for initializing session")
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
            success = await self.ws_manager.send_message(session_update)

            if success:
                self.logger.info("Session update sent successfully")
                return True

            self.logger.error("Failed to send session update")
            return False

        except Exception as e:
            self.logger.error("Error initializing session: %s", e)
            return False

    async def send_audio(self, mic_stream: PyAudioMicrophone) -> None:
        """
        Send audio data from the microphone to the OpenAI API.

        Args:
            mic_stream: A MicrophoneStream object that provides audio data
        """
        if not self.ws_manager.is_connected():
            self.logger.error("No connection available for sending audio")
            return

        try:
            self.logger.info("Starting audio transmission...")
            audio_chunks_sent = 0

            while mic_stream.is_active and self.ws_manager.is_connected():
                data = mic_stream.read_chunk()
                if not data:
                    await asyncio.sleep(0.01)
                    continue

                success = await self.ws_manager.send_binary(data)
                if success:
                    audio_chunks_sent += 1
                    if audio_chunks_sent % 100 == 0:
                        self.logger.debug("Audio chunks sent: %d", audio_chunks_sent)
                else:
                    self.logger.warning("Failed to send audio chunk")

                await asyncio.sleep(0.01)

        except asyncio.TimeoutError as e:
            self.logger.error("Timeout while sending audio: %s", e)
        except Exception as e:
            self.logger.error("Error while sending audio: %s", e)

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
        if not self.ws_manager.is_connected():
            self.logger.error("No connection available for processing responses")
            return

        # Define a message handler for the WebSocketManager
        async def message_handler(message: str) -> None:
            await self._process_single_message(
                message=message,
                handle_text=handle_text,
                handle_transcript=handle_transcript,
                event_handler=event_handler,
            )

        # Use the WebSocketManager to receive messages
        await self.ws_manager.receive_messages(
            message_handler=message_handler,
            should_continue=self.ws_manager.is_connected,
        )

    async def _process_single_message(
        self,
        message: str,
        handle_text: Optional[Callable[[Dict[str, Any]], None]],
        handle_transcript: Optional[Callable[[Dict[str, Any]], None]],
        event_handler: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        """
        Process a single message from the API stream with simplified error logging.

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
            self.logger.warning(
                "Expected key missing in message: %s | Message content: %s",
                e,
                message[:500],
            )
        except Exception as e:
            self.logger.error("Unexpected error processing message: %s", e)

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
            # Stoppe die Audio-Wiedergabe
            self.audio_player.clear_queue_and_stop()

        if event_type == "response.text.delta" and "delta" in response:
            if handle_text:
                handle_text(response)

        elif event_type == "response.audio.delta":
            self._handle_audio_delta(response)

        elif event_type == "response.audio_transcript.delta":
            if handle_transcript:
                handle_transcript(response)

        elif event_type == "response.done":
            # Speichere die Event-ID für spätere Truncate-Anfragen
            self._last_message_event_id = response.get("event_id", "")

            if not self._response_contains_tool_call(response):
                return

            await self.tool_handler.handle_function_call_in_response(
                response, self.ws_manager.connection
            )

        elif event_type == "conversation.item.truncated":
            # Bestätigung für erfolgreiches Truncation
            event_id = response.get("event_id", "unknown")
            self.logger.info("Truncation successful for event: %s", event_id)

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

    def _response_contains_tool_call(self, response: OpenAIRealtimeResponse) -> bool:
        """
        Check if the response contains a tool call.

        Args:
            response: The API response to check

        Returns:
            True if the response contains a tool call, False otherwise
        """
        return (
            response["type"] == "response.done"
            and "function_call" in response["response"]
            and response["response"]["function_call"] is not None
        )
