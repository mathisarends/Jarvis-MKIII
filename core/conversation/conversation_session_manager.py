from typing import Any, Dict, List

from core.websocket.websocket_manager import WebSocketManager
from shared.logging_mixin import LoggingMixin


class ConversationSessionManager(LoggingMixin):
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
    ):
        self.ws_manager = ws_manager
        self.system_message = system_message
        self.voice = voice
        self.temperature = temperature
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
