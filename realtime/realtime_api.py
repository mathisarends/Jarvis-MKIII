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
from realtime.realtime_tool_handler import RealtimeToolHandler
from tools.weather.weather_tool import get_weather
from tools.web_search_tool import web_search_tool
from tools.tool_registry import ToolRegistry

from utils.logging_mixin import LoggingMixin


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

        self.tool_registry = ToolRegistry()
        self._init_tool_registry()

        self.tool_handler = RealtimeToolHandler(self.tool_registry)

        self.logger.info("OpenAI Realtime API class initialized")

    def _init_tool_registry(self) -> None:
        """
        Initialize the tool registry and register all available tools.
        """
        try:
            self.tool_registry.register_tool(get_weather)
            self.tool_registry.register_tool(web_search_tool)

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

        except websockets.exceptions.InvalidStatusCode as e:
            self.logger.error("Invalid status code from WebSocket server: %s", e)
        except ConnectionRefusedError as e:
            self.logger.error("Connection refused: %s", e)
        except OSError as e:
            self.logger.error("OS-level connection error: %s", e)

    async def initialize_session(self) -> bool:
        """Initialize a session with the OpenAI API."""
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

        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.error(
                "WebSocket connection closed unexpectedly during audio send: %s", e
            )
        except asyncio.TimeoutError as e:
            self.logger.error("Timeout while sending audio: %s", e)

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

        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.error(
                "WebSocket connection closed while waiting for responses: %s", e
            )
        except asyncio.TimeoutError as e:
            self.logger.error("Timeout while receiving responses: %s", e)

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

            await self._route_event(
                event_type, response, audio_player, handle_text, handle_transcript
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Received malformed JSON message: %s", e)
        except KeyError as e:
            self.logger.warning("Expected key missing in message: %s", e)

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

            await self.tool_handler.handle_function_call_in_response(
                response, self.connection
            )

        elif event_type in ["error", "session.updated", "session.created"]:
            self.logger.info("Event received: %s", event_type)
            if event_type == "error":
                self.logger.error("API error: %s", response)

    def _handle_audio_delta(self, response, audio_player: AudioPlayerBase) -> None:
        """Handle audio responses from OpenAI API"""
        base64_audio = response.get("delta", "")
        if not base64_audio or not isinstance(base64_audio, str):
            return

        audio_player.add_audio_chunk(base64_audio)
