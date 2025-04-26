from typing import Dict, List, Any
from functools import cached_property

from utils.logging_mixin import LoggingMixin


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
