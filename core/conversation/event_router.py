from typing import Dict, Any, List
from functools import cached_property

from core.conversation.realtime_tool_handler import RealtimeToolHandler
from core.audio.response_audio_handler import ResponseAudioHandler
from core.websocket.websocket_manager import WebSocketManager

from shared.logging_mixin import LoggingMixin
from shared.event_bus import EventBus, EventType


class DoneMessage(LoggingMixin):
    """
    A class representing a 'response.done' message from the OpenAI API with lazy evaluation.
    """

    def __init__(self, response_data: Dict[str, Any]):
        """
        Initialize a DoneMessage from raw API response data.
        If the event type matches we can assume the json structure - for now atleast :)
        """
        self.raw_response = response_data

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "DoneMessage":
        """
        Create a DoneMessage instance from JSON data.
        """
        return cls(json_data)

    @cached_property
    def message_item_id(self) -> str:
        """
        Extract the message item ID from the raw response.
        Lazy evaluated and cached on first access.
        """
        try:
            output_items = self.raw_response.get("response", {}).get("output", [])

            if not isinstance(output_items, list) or not output_items:
                self.logger.debug("Output items is not a valid list")
                return ""

            for item in output_items:
                if item.get("type") == "message" and "id" in item:
                    return item["id"]

            self.logger.debug("No message item with ID found in output items")
            return ""
        except Exception as e:
            self.logger.error("Error extracting message item ID: %s", e)
            return ""

    @cached_property
    def transcript(self) -> str:
        """
        Extract the text content from the message.
        Supports both text-type content and audio-type content with transcripts.
        Lazy evaluated and cached on first access.
        """
        try:
            output_items = self.raw_response.get("response", {}).get("output", [])
            if not isinstance(output_items, list) or not output_items:
                self.logger.debug("Output items is not a valid list")
                return ""

            message_item = self._find_message_item(output_items)
            if not message_item:
                self.logger.debug("No message item found in output items")
                return ""

            content_items = message_item.get("content", [])
            if not isinstance(content_items, list) or not content_items:
                self.logger.debug("Content items is not a valid list")
                return ""

            text_parts = self._extract_text_parts(content_items)
            result = "".join(text_parts)

            self.logger.debug("Extracted message text: '%s'", result)
            return result

        except Exception as e:
            self.logger.error("Error extracting message text: %s", e)
            return ""

    def _find_message_item(self, output_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Find the message item in the output items.

        Args:
            output_items: List of output items

        Returns:
            The message item or an empty dict if not found
        """
        for item in output_items:
            if item.get("type") == "message" and "content" in item:
                return item
        return {}

    def _extract_text_parts(self, content_items: List[Dict[str, Any]]) -> List[str]:
        """
        Extract text parts from content items.

        Args:
            content_items: List of content items

        Returns:
            List of extracted text parts
        """
        text_parts = []

        for content_item in content_items:
            # Handle text-type content
            if content_item.get("type") == "text":
                text_part = content_item.get("text", "")
                if text_part:
                    self.logger.debug("Found text content: '%s'", text_part)
                    text_parts.append(text_part)

            # Handle audio-type content with transcript
            elif content_item.get("type") == "audio" and "transcript" in content_item:
                transcript = content_item.get("transcript", "")
                if transcript:
                    self.logger.debug("Found audio transcript: '%s'", transcript)
                    text_parts.append(transcript)

        return text_parts

    @cached_property
    def contains_tool_call(self) -> bool:
        """
        Check if the response contains any tool calls.
        Lazy evaluated and cached on first access.

        Returns:
            True if the response contains a tool call, False otherwise
        """
        try:
            if self.raw_response.get("type") != "response.done":
                return False

            output_items = self.raw_response.get("response", {}).get("output", [])

            if not isinstance(output_items, list) or not output_items:
                return False

            for item in output_items:
                if item.get("type") == "function_call":
                    return True

            return False
        except Exception as e:
            self.logger.error("Error checking for tool calls: %s", e)
            return False


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
            self._handle_speech_stopped()
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

        if done_message.contains_tool_call:
            await self.tool_handler.handle_function_call_in_response(
                response, self.ws_manager.connection
            )
        else:
            self.event_bus.publish(
                EventType.ASSISTANT_RESPONSE_COMPLETED, data=done_message.transcript
            )

    async def _handle_speech_started(self) -> None:
        """Processes speech_started events"""
        self.logger.info("User speech input started")

        self.audio_handler.stop_playback()
        self.event_bus.publish(EventType.USER_SPEECH_STARTED)

    def _handle_speech_stopped(self) -> None:
        """Processes speech_stopped events"""
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
