import asyncio
from typing import Any, Dict, List

from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.microphone import PyAudioMicrophone
from core.audio.response_audio_handler import ResponseAudioHandler
from core.conversation.conversation_session_manager import ConversationSessionManager
from core.conversation.event_router import EventRouter
from core.conversation.realtime_tool_handler import RealtimeToolHandler
from core.websocket.websocket_manager import WebSocketManager
from plugins.notion.clipboard.clipboard_tool import clipboard_tool
from plugins.tool_registry import ToolRegistry
from plugins.weather.weather_tool import get_weather
from resources.config import (
    OPENAI_HEADERS,
    OPENAI_WEBSOCKET_URL,
    SYSTEM_MESSAGE,
    TEMPERATURE,
    VOICE,
)
from shared.event_bus import EventBus
from shared.logging_mixin import LoggingMixin


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
        self.system_message = SYSTEM_MESSAGE
        self.voice = VOICE
        self.temperature = TEMPERATURE

        self.event_bus = EventBus()
        self.tool_registry = ToolRegistry.get_instance()
        self._init_tool_registry()
        self.audio_player = AudioPlayerFactory.get_shared_instance()

        self.tool_handler = RealtimeToolHandler(self.tool_registry)

        self.event_router = EventRouter(self.event_bus, None, self.tool_handler, None)

        self.ws_manager = WebSocketManager(
            OPENAI_WEBSOCKET_URL, OPENAI_HEADERS, self.event_router
        )

        self.audio_handler = ResponseAudioHandler(self.ws_manager, self.audio_player)
        self.event_router.audio_handler = self.audio_handler
        self.event_router.ws_manager = self.ws_manager

        self.session_manager = ConversationSessionManager(
            self.ws_manager,
            self.system_message,
            self.voice,
            self.temperature,
        )

    # TODO: Registry hier optinal mit dem Pomodoro-Timer verknü
    def _init_tool_registry(self) -> None:
        """
        Initializes the tool registry and registers all available tools.
        """
        try:
            """self.tool_registry.register_tool(stop_conversation_tool)"""
            """ self.tool_registry.register_tool(web_search_tool) """

            self.tool_registry.register_tool(get_weather)
            self.tool_registry.register_tool(
                tool=clipboard_tool,
                return_early_message="Clipboard content wird erstellt. Ich melde mich wenn ich fertig bin.",
            )
            """ self.tool_registry.register_tool(set_volume_tool)
            self.tool_registry.register_tool(get_volume_tool) """

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
            should_continue=self.ws_manager.is_connected,
        )
