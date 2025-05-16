import asyncio
import base64
import json
from typing import Any, Callable, Dict, Optional

import websockets

from shared.logging_mixin import LoggingMixin


class WebSocketManager(LoggingMixin):
    """
    Class for managing WebSocket connections.
    Handles the creation, management, and closing of WebSocket connections
    as well as sending and receiving messages.
    """

    NO_CONNECTION_ERROR_MSG = "No connection available. Call create_connection() first."

    def __init__(self, websocket_url: str, headers: Dict[str, str], event_router=None):
        """
        Initialize the WebSocket Manager.

        Args:
            websocket_url: URL for the WebSocket connection
            headers: HTTP headers for the connection
            event_router: Optional EventRouter for processing events
        """
        self.websocket_url = websocket_url
        self.headers = headers
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.event_router = event_router
        self.logger.info("WebSocketManager initialized")

    async def create_connection(self) -> Optional[websockets.WebSocketClientProtocol]:
        """
        Create a WebSocket connection.
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

    async def receive_messages(
        self,
        message_handler: Optional[Callable[[str], Any]] = None,
        should_continue: Callable[[], bool] = lambda: True,
    ) -> None:
        """
        Continuously receive and process messages from the WebSocket connection.

        Args:
            message_handler: Optional function to process received messages
            should_continue: Function that returns whether to continue receiving messages
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return

        try:
            self.logger.info("Starting message reception...")
            async for message in self.connection:
                if message_handler:
                    await message_handler(message)
                elif self.event_router:
                    await self._process_websocket_message(message)
                else:
                    self.logger.warning("No message handler or event router available")

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
        """
        return self.connection is not None and not self.connection.closed

    async def _process_websocket_message(self, message: str) -> None:
        """
        Process incoming WebSocket messages and route events.

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
