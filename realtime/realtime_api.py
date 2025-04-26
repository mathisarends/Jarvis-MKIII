import json
import asyncio
from typing import Dict, Any, List

from audio.audio_player_base import AudioPlayer
from audio.audio_player_factory import AudioPlayerFactory
from audio.microphone import PyAudioMicrophone
from realtime.config import (
    OPENAI_WEBSOCKET_URL,
    OPENAI_HEADERS,
    SYSTEM_MESSAGE,
    TEMPERATURE,
    TRANSCRIPTION_MODEL,
    VOICE,
)
from realtime.realtime_tool_handler import RealtimeToolHandler
from realtime.typings.done_message import DoneMessage
from realtime.websocket_manager import WebSocketManager
from tools.stop_conversation_tool import stop_conversation_tool
from tools.pomodoro.pomodoro_tool import (
    pomodoro_tool,
)
from tools.weather.weather_tool import get_weather
from tools.web_search_tool import web_search_tool
from tools.clipboard_tool import clipboard_tool
from tools.volume_tool import set_volume_tool, get_volume_tool
from tools.tool_registry import ToolRegistry

from utils.logging_mixin import LoggingMixin
from utils.event_bus import EventBus, EventType


class SessionManager(LoggingMixin):
    """
    Manages OpenAI API session details and configuration.
    Separates session configuration from the main class.
    """

    def __init__(
        self,
        ws_manager: WebSocketManager,
        system_message: str,
        voice: str,
        temperature: float,
        transcription_model: str,
    ):
        self.ws_manager = ws_manager
        self.system_message = system_message
        self.voice = voice
        self.temperature = temperature
        self.transcription_model = transcription_model
        self.logger.info("SessionManager initialized")

    def build_session_config(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates the session configuration for the OpenAI API.
        """
        return {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "voice": self.voice,
                "instructions": self.system_message,
                "modalities": ["text", "audio"],
                "temperature": self.temperature,
                "tools": tools,
                "input_audio_transcription": {
                    "model": self.transcription_model,
                    "prompt": "Die Spracheingabe erfolgt hauptsächlich auf Deutsch, enthält jedoch häufig englische Fachbegriffe aus dem Bereich der Programmierung. Bitte transkribiere entsprechend.",
                },
            },
        }

    async def initialize_session(self, tools: List[Dict[str, Any]]) -> bool:
        """
        Initializes a session with the OpenAI API.

        Args:
            tools: List of tool schemas for the API

        Returns:
            True if initialization was successful, False otherwise
        """
        if not self.ws_manager.is_connected():
            self.logger.error("No connection available for session initialization")
            return False

        session_update = self.build_session_config(tools)

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


class AudioHandler(LoggingMixin):
    """
    Manages audio processing, both for sending and receiving.
    Separates audio logic from the main class.
    """

    def __init__(self, ws_manager: WebSocketManager, audio_player: AudioPlayer):
        self.ws_manager = ws_manager
        self.audio_player = audio_player
        self.logger.info("AudioHandler initialized")

    async def send_audio_stream(self, mic_stream: PyAudioMicrophone) -> None:
        """
        Sends audio data from the microphone to the OpenAI API.

        Args:
            mic_stream: A MicrophoneStream object that provides audio data
        """
        if not self.ws_manager.is_connected():
            self.logger.error("No connection available for audio transmission")
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

    def handle_audio_delta(self, response: Dict[str, Any]) -> None:
        """
        Processes audio responses from the OpenAI API.

        Args:
            response: The response containing audio data
        """
        base64_audio = response.get("delta", "")
        if not base64_audio or not isinstance(base64_audio, str):
            return

        self.audio_player.add_audio_chunk(base64_audio)

    def stop_playback(self) -> None:
        """
        Stops audio playback.
        """
        self.audio_player.clear_queue_and_stop()


class EventRouter(LoggingMixin):
    """
    Processes and routes events based on their type.
    Separates routing logic from the main class.
    """

    def __init__(
        self,
        event_bus: EventBus,
        audio_handler: AudioHandler,
        tool_handler: RealtimeToolHandler,
        ws_manager: WebSocketManager,
    ):
        self.event_bus = event_bus
        self.audio_handler = audio_handler
        self.tool_handler = tool_handler
        self.ws_manager = ws_manager
        self._current_response_start_time_ms: int = 0
        self._last_assistant_message_item_id: str = ""

    async def process_event(self, event_type: str, response: Dict[str, Any]) -> None:
        """
        Processes an event based on its type using early returns.

        Args:
            event_type: The type of the event
            response: The complete response object
        """
        # Using early returns for cleaner control flow
        if event_type == "response.done":
            await self._handle_response_done(response)
            return

        if event_type == "input_audio_buffer.speech_started":
            await self._handle_speech_started()
            return

        if event_type == "input_audio_buffer.speech_stopped":
            self._handle_speech_stopped(response)
            return

        if event_type == "conversation.item.input_audio_transcription.completed":
            self._handle_transcription_completed(response)
            return

        if event_type == "response.audio.delta":
            self.audio_handler.handle_audio_delta(response)
            return

        if event_type == "conversation.item.truncated":
            self.logger.info("Conversation item truncated event received")
            return

        if event_type in ["error", "session.updated", "session.created"]:
            self._handle_system_event(event_type, response)

    async def _handle_response_done(self, response: Dict[str, Any]) -> None:
        """Processes response.done events"""
        self.logger.info("Assistant response completed")
        done_message = DoneMessage.from_json(response)

        self.event_bus.publish(
            EventType.ASSISTANT_RESPONSE_COMPLETED, data=done_message.transcript
        )

        self._last_assistant_message_item_id = done_message.message_item_id

        if done_message.contains_tool_call:
            await self.tool_handler.handle_function_call_in_response(
                response, self.ws_manager.connection
            )

    async def _handle_speech_started(self) -> None:
        """Processes speech_started events"""
        self.logger.info("User speech input started")

        self.audio_handler.stop_playback()
        self.event_bus.publish(EventType.USER_SPEECH_STARTED)

    def _handle_speech_stopped(self, response: Dict[str, Any]) -> None:
        """Processes speech_stopped events"""
        self._current_response_start_time_ms = response.get("audio_end_ms", 0)
        self.event_bus.publish(event_type=EventType.USER_SPEECH_ENDED)

    def _handle_transcription_completed(self, response: Dict[str, Any]) -> None:
        """Processes transcription_completed events"""
        user_input_transcript = response.get("transcript", "")
        self.event_bus.publish(
            event_type=EventType.USER_INPUT_TRANSCRIPTION_COMPLETED,
            data=user_input_transcript,
        )

    def _handle_system_event(self, event_type: str, response: Dict[str, Any]) -> None:
        """Processes system events"""
        self.logger.info("Event received: %s", event_type)
        if event_type == "error":
            self.logger.error("API error: %s", response)


class MessageParser(LoggingMixin):
    """
    Parses and processes incoming websocket messages.
    """

    def __init__(self, event_router: EventRouter):
        self.event_router = event_router
        self.logger.info("MessageParser initialized")

    async def parse_message(self, message: str) -> None:
        """
        Parses an incoming message from the WebSocket.

        Args:
            message: The raw message from the WebSocket
        """
        try:
            self.logger.debug("Raw message received: %s...", message[:100])

            response = json.loads(message)

            if not isinstance(response, dict):
                self.logger.warning("Response is not a dictionary: %s", type(response))
                return

            event_type = response.get("type", "")
            await self.event_router.process_event(event_type, response)

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


class OpenAIRealtimeAPI(LoggingMixin):
    """
    Main class for managing OpenAI Realtime API communication.
    Acts as a facade for the various components.
    """

    def __init__(self):
        """
        Initializes the OpenAI Realtime API client.
        All configuration is loaded from configuration files.
        """
        # Load configuration
        self.system_message = SYSTEM_MESSAGE
        self.voice = VOICE
        self.temperature = TEMPERATURE
        self.transcription_model = TRANSCRIPTION_MODEL

        # Create components
        self.ws_manager = WebSocketManager(OPENAI_WEBSOCKET_URL, OPENAI_HEADERS)
        self.tool_registry = ToolRegistry.get_instance()
        self._init_tool_registry()
        self.event_bus = EventBus()
        self.audio_player = AudioPlayerFactory.get_shared_instance()

        # Create specialized handlers
        self.tool_handler = RealtimeToolHandler(self.tool_registry)
        self.audio_handler = AudioHandler(self.ws_manager, self.audio_player)
        self.event_router = EventRouter(
            self.event_bus, self.audio_handler, self.tool_handler, self.ws_manager
        )
        self.session_manager = SessionManager(
            self.ws_manager,
            self.system_message,
            self.voice,
            self.temperature,
            self.transcription_model,
        )
        self.message_parser = MessageParser(self.event_router)

    def _init_tool_registry(self) -> None:
        """
        Initializes the tool registry and registers all available tools.
        """
        try:
            self.tool_registry.register_tool(stop_conversation_tool)
            self.tool_registry.register_tool(get_weather)
            self.tool_registry.register_tool(web_search_tool)
            self.tool_registry.register_tool(pomodoro_tool)
            self.tool_registry.register_tool(clipboard_tool)
            self.tool_registry.register_tool(set_volume_tool)
            self.tool_registry.register_tool(get_volume_tool)

            self.logger.info("All tools successfully registered")
        except Exception as e:
            self.logger.error("Failed to register tools: %s", e)

    def _get_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Gets the OpenAI-compatible tool schemas for all tools.

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

    async def setup_and_run(self, mic_stream: PyAudioMicrophone) -> bool:
        """
        Sets up the connection and runs the main loop.
        Uses the EventBus for communication with other components.

        Args:
            mic_stream: A MicrophoneStream object for audio input

        Returns:
            True on successful execution, False on error
        """
        if not await self.ws_manager.create_connection():
            return False

        if not await self.session_manager.initialize_session(self._get_openai_tools()):
            await self.ws_manager.close()
            return False

        try:
            await asyncio.gather(
                self.audio_handler.send_audio_stream(mic_stream),
                self.process_responses(),
            )

            return True
        except asyncio.CancelledError:
            self.logger.info("Tasks were cancelled")
            return True
        finally:
            await self.ws_manager.close()

    async def process_responses(self) -> None:
        """
        Processes responses from the OpenAI API and publishes events to the EventBus.
        """
        if not self.ws_manager.is_connected():
            self.logger.error("No connection available for processing responses")
            return

        await self.ws_manager.receive_messages(
            message_handler=self.message_parser.parse_message,
            should_continue=self.ws_manager.is_connected,
        )
