from typing import Dict, Any

from realtime.config import (
    OPENAI_WEBSOCKET_URL,
    OPENAI_HEADERS,
    SYSTEM_MESSAGE,
    TEMPERATURE,
    TRANSCRIPTION_MODEL,
    VOICE,
)
from realtime.realtime_tool_handler import RealtimeToolHandler
from realtime.response_audio_handler import ResponseAudioHandler
from realtime.typings.done_message import DoneMessage
from realtime.websocket_manager import WebSocketManager

from utils.logging_mixin import LoggingMixin
from utils.event_bus import EventBus, EventType


class EventRouter(LoggingMixin):
    """
    Processes and routes events based on their type.
    Separates routing logic from the main class.
    """

    def __init__(
        self,
        event_bus: EventBus,
        audio_handler: ResponseAudioHandler,
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
