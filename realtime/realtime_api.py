import json
import asyncio
from typing import Dict, Any, List, cast

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
from tools.pomodoro.pomodoro_tool import (
    get_pomodoro_status,
    start_pomodoro_timer,
    stop_pomodoro_timer,
)
from tools.volume_tool import get_volume_tool, set_volume_tool
from tools.weather.weather_tool import get_weather
from tools.web_search_tool import web_search_tool
from tools.tool_registry import ToolRegistry

from utils.logging_mixin import LoggingMixin
from utils.event_bus import EventBus, EventType


class OpenAIRealtimeAPI(LoggingMixin):
    """
    Class for managing OpenAI Realtime API communications.
    With Tool-Registry integration and Event-Bus for communication.

    This class handles all the interaction with the OpenAI API including:
    - Managing the WebSocket communication through WebSocketManager
    - Sending audio data from the microphone
    - Processing responses including text, audio and tool calls
    - Publishing events to the EventBus
    """

    def __init__(self):
        """
        Initialize the OpenAI Realtime API client.
        All configuration is loaded from config files.
        """
        self.system_message = SYSTEM_MESSAGE
        self.voice = VOICE
        self.temperature = TEMPERATURE

        self.ws_manager = WebSocketManager(OPENAI_WEBSOCKET_URL, OPENAI_HEADERS)

        self.tool_registry = ToolRegistry()
        self._init_tool_registry()

        self.tool_handler = RealtimeToolHandler(self.tool_registry)
        self.audio_player = AudioPlayerFactory.get_shared_instance()
        
        self.event_bus = EventBus()

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
            self.tool_registry.register_tool(start_pomodoro_timer)
            self.tool_registry.register_tool(stop_pomodoro_timer)
            self.tool_registry.register_tool(get_pomodoro_status)

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
    ) -> bool:
        """
        Set up the connection and run the main loop.
        Uses the EventBus for communication with other components.

        Args:
            mic_stream: A MicrophoneStream object for audio input

        Returns:
            True on successful execution, False on error
        """
        if not await self.ws_manager.create_connection():
            return False

        if not await self.initialize_session():
            await self.ws_manager.close()
            return False

        try:
            await asyncio.gather(
                self.send_audio(mic_stream),
                self.process_responses(),
            )

            return True
        except asyncio.CancelledError:
            self.logger.info("Tasks were cancelled")
            return True
        finally:
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


    async def process_responses(self) -> None:
        """
        Process responses from the OpenAI API and publish events to the EventBus.
        Simplified version with reduced boilerplate.
        """
        if not self.ws_manager.is_connected():
            self.logger.error("No connection available for processing responses")
            return


        await self.ws_manager.receive_messages(
            message_handler=self._handle_message,
            should_continue=self.ws_manager.is_connected,
        )
        
    async def _handle_message(self, message: str) -> None:
        """
        Process a single message from the WebSocket stream and route it to the appropriate handler.
        
        Args:
            message: The raw message string received from the API
        """
        try:
            self.logger.debug("Raw message received: %s...", message[:100])
            
            response = json.loads(message)
            
            if not isinstance(response, dict):
                self.logger.warning("Response is not a dictionary: %s", type(response))
                return
                
            event_type = response.get("type", "")
            await self._route_event(event_type, response)
                
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


    async def _route_event(self, event_type: str, response: OpenAIRealtimeResponse):
        """
        Route the event to the appropriate handler based on event type.
        Uses EventBus to publish events to subscribers.

        Args:
            event_type: The type of event from the response
            response: The full response object
        """
        if event_type == "input_audio_buffer.speech_started":
            self.logger.info("User speech started event received")
            self.audio_player.clear_queue_and_stop()
            await self.event_bus.publish_async(EventType.USER_SPEECH_STARTED)
            return

        if event_type == "response.done":
            self.logger.info("Assistant response completed event received")
            await self.event_bus.publish_async(EventType.ASSISTANT_RESPONSE_COMPLETED)

            if self._response_contains_tool_call(response):
                await self.tool_handler.handle_function_call_in_response(
                    response, self.ws_manager.connection
                )
            return

        if event_type == "response.audio.delta":
            self._handle_audio_delta(response)
            return

        if event_type == "response.audio_transcript.delta":
            await self.event_bus.publish_async(EventType.TRANSCRIPT_UPDATED, response)
            return

        if event_type == "conversation.item.truncated":
            event_id = response.get("event_id", "unknown")
            self.logger.info("Truncation successful for event: %s", event_id)
            return

        if event_type in ["error", "session.updated", "session.created"]:
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

    def _response_contains_tool_call(self, response):
        """
        Check if the response contains a tool call.

        Args:
            response: The API response to check

        Returns:
            True if the response contains a tool call, False otherwise
        """
        if response["type"] != "response.done":
            return False

        if "response" not in response:
            return False

        if "output" not in response["response"]:
            return False

        output_items = response["response"]["output"]
        if not isinstance(output_items, list) or not output_items:
            return False

        for item in output_items:
            if item.get("type") == "function_call":
                return True

        return False