import json
import base64
from typing import Optional, Dict, Any, Callable
import websockets
import asyncio

from utils.logging_mixin import LoggingMixin


class WebSocketManager(LoggingMixin):
    """
    Class for managing WebSocket connections.
    Handles the creation, management, and closing of WebSocket connections
    as well as sending and receiving messages.
    """

    NO_CONNECTION_ERROR_MSG = "No connection available. Call create_connection() first."

    def __init__(self, websocket_url: str, headers: Dict[str, str]):
        """
        Initialize the WebSocket Manager.

        Args:
            websocket_url: The URL for the WebSocket connection
            headers: HTTP headers to use for the connection
        """
        self.websocket_url = websocket_url
        self.headers = headers
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.logger.info("WebSocketManager initialized")

    async def create_connection(self) -> Optional[websockets.WebSocketClientProtocol]:
        """
        Create a WebSocket connection.

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
        return None

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a JSON message through the WebSocket connection.

        Args:
            message: Dictionary to be sent as JSON

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return False

        try:
            await self.connection.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error("Error sending message: %s", e)
            return False

    async def send_binary(self, data: bytes, encoding: str = "base64") -> bool:
        """
        Send binary data through the WebSocket connection.
        For audio streaming, data is typically encoded in base64.

        Args:
            data: Binary data to send
            encoding: Encoding method (default: base64)

        Returns:
            True if data was sent successfully, False otherwise
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return False

        try:
            if encoding == "base64":
                base64_data = base64.b64encode(data).decode("utf-8")
                message = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_data,
                }
                return await self.send_message(message)

            self.logger.error("Unsupported encoding: %s", encoding)
            return False
        except Exception as e:
            self.logger.error("Error sending binary data: %s", e)
            return False

    async def send_truncate_message(self, event_id: str, audio_end_ms: int) -> bool:
        """
        Send a message to truncate the audio stream.

        Args:
            event_id: Unique identifier for the event
            audio_end_ms: End time in milliseconds for the audio stream

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            self.logger.info(
                "Truncate parameters - event_id: %s, audio_end_ms: %s",
                event_id,
                audio_end_ms,
            )

            """ message = {
                "type": "conversation.item.truncate",
                "event_id": event_id,
                "audio_end_ms": audio_end_ms,
            }
            
            self.logger.debug("Sending truncate message: %s", message)
            
            return await self.send_message(message) """

        except Exception as e:
            self.logger.error("Error sending truncate message: %s", e)
            return False

    async def receive_messages(
        self,
        message_handler: Callable[[str], Any],
        should_continue: Callable[[], bool] = lambda: True,
    ) -> None:
        """
        Continuously receive and process messages from the WebSocket connection.

        Args:
            message_handler: Function to process received messages
            should_continue: Function that returns whether to continue receiving messages
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return

        try:
            self.logger.info("Starting message reception...")
            async for message in self.connection:
                await message_handler(message)
                if not should_continue():
                    break

        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info(
                "WebSocket connection closed normally during message reception"
            )
        except websockets.exceptions.ConnectionClosedError as e:
            if str(e).startswith("sent 1000 (OK)"):
                self.logger.info(
                    "WebSocket connection closed normally during message reception"
                )
            else:
                self.logger.error(
                    "WebSocket connection closed unexpectedly during message reception: %s",
                    e,
                )
        except asyncio.TimeoutError as e:
            self.logger.error("Timeout while receiving messages: %s", e)

    async def close(self) -> None:
        """
        Close the WebSocket connection gracefully.
        """
        if not self.connection:
            return

        try:
            self.logger.info("Closing connection...")
            await self.connection.close()
            self.connection = None
            self.logger.info("Connection closed")
        except Exception as e:
            self.logger.error("Error closing connection: %s", e)

    def is_connected(self) -> bool:
        """
        Check if the WebSocket connection is established and open.

        Returns:
            True if connected, False otherwise
        """
        return self.connection is not None and not self.connection.closed
