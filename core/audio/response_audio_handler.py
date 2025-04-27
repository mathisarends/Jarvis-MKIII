import asyncio
from typing import Any, Dict
from core.websocket.websocket_manager import WebSocketManager
from core.audio.audio_player_base import AudioPlayer
from core.audio.microphone import PyAudioMicrophone
from shared.logging_mixin import LoggingMixin


class ResponseAudioHandler(LoggingMixin):
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
