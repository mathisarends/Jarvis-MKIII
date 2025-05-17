from __future__ import annotations

import asyncio
import threading
import time
from functools import cached_property
from typing import Any, Dict, List

from core.audio.response_audio_handler import ResponseAudioHandler
from core.conversation.realtime_tool_handler import RealtimeToolHandler
from core.websocket.websocket_manager import WebSocketManager
from shared.event_bus import EventBus, EventType
from shared.logging_mixin import LoggingMixin


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
    def from_json(cls, json_data: Dict[str, Any]) -> DoneMessage:
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

        self.vad_enabled = True
        self.last_vad_enable_time = 0.0

        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_COMPLETED_RESPONDING,
            callback=self.enable_vad_wrapper,
        )

    async def process_event(self, event_type: str, response: Dict[str, Any]) -> None:
        """
        Processes an event based on its type using early returns.

        Args:
            event_type: The type of the event
            response: The complete response object
        """
        match event_type:
            case "response.done":
                await self._handle_response_done(response)

            case "input_audio_buffer.speech_started":
                if self.vad_enabled:
                    await self._handle_speech_started()

            case "input_audio_buffer.speech_stopped":
                await self._handle_speech_stopped()

            case "conversation.item.input_audio_transcription.completed":
                self._handle_transcription_completed(response)

            case "response.audio.delta":
                self.audio_handler.handle_audio_delta(response)

            case "conversation.item.truncated":
                self.logger.info("Conversation item truncated event received")

            case "error" | "session.updated" | "session.created":
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
        """Processes speech_started events with protection against false triggers"""
        self.logger.info("User speech input started")

        self.audio_handler.stop_playback()
        self.event_bus.publish(EventType.USER_SPEECH_STARTED)

    async def _handle_speech_stopped(self) -> None:
        """Processes speech_stopped events"""
        await self._disable_vad()
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

    async def _disable_vad(self) -> None:
        """
        Disable VAD when the assistant starts speaking to prevent self-triggering.
        """
        if not self.vad_enabled:
            return

        self.logger.info("Assistant started speaking - disabling VAD")

        try:
            await self.ws_manager.send_message(
                {"type": "session.update", "session": {"turn_detection": None}}
            )
            self.vad_enabled = False
            print("[VAD] VAD disabled successfully")
            self.logger.debug("VAD disabled during assistant speech")
        except Exception as e:
            print(f"[VAD] ERROR: Failed to disable VAD: {e}")
            self.logger.error(f"Failed to disable VAD: {e}")

    def enable_vad_wrapper(self, data=None):
        print("[VAD] Event received: ASSISTANT_COMPLETED_RESPONDING")

        threading.Thread(target=self._run_enable_vad_in_thread).start()

    def _run_enable_vad_in_thread(self):
        """Führt _enable_vad in einem separaten Thread aus"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(self._enable_vad())
            loop.close()
        except Exception as e:
            print(f"[VAD] ERROR: Failed to enable VAD in thread: {e}")
            self.logger.error(f"Failed to enable VAD in thread: {e}")

    async def _enable_vad(self, data=None) -> None:
        """
        Re-enable VAD when the assistant stops speaking, with delay and protection.
        """
        if self.vad_enabled:
            return

        delay_seconds = 1.0
        await asyncio.sleep(delay_seconds)

        self.logger.info("Executing delayed VAD re-enable")

        self.last_vad_enable_time = time.time()

        session_update = {
            "type": "session.update",
            "session": {"turn_detection": {"type": "server_vad"}},
        }

        try:
            await self.ws_manager.send_message(session_update)
            self.vad_enabled = True
            self.logger.info("VAD re-enabled after assistant speech")
        except Exception as e:
            print(f"[VAD] ERROR: Failed to re-enable VAD: {e}")
            self.logger.error(f"Failed to re-enable VAD: {e}")
