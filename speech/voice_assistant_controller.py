import asyncio
import websockets
import time

from audio.microphone import PyAudioMicrophone
from audio.audio_player_factory import AudioPlayerFactory
from realtime.realtime_api import OpenAIRealtimeAPI
from speech.wake_word_listener import WakeWordListener

from utils.event_bus import EventBus, EventType
from utils.logging_mixin import LoggingMixin
from utils.singleton_decorator import singleton


class AssistantConfig:
    """Configuration for the voice assistant"""

    def __init__(
        self,
        wake_word="jarvis",
        sensitivity=0.8,
        idle_timeout=5.0,
        language="de",
    ):
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.idle_timeout = idle_timeout
        self.language = language


class TranscriptManager:
    """Manages conversation transcripts"""

    def __init__(self):
        self._current = ""
        self.full = ""

    @property
    def current(self):
        """Get the current transcript"""
        return self._current

    @current.setter
    def current(self, value):
        """Set the current transcript"""
        self._current = value

    def reset_current(self):
        """Reset the current transcript"""
        self._current = ""


@singleton
class VoiceAssistantController(LoggingMixin):
    """
    Controller for voice assistant that integrates wake word detection with OpenAI API.

    Uses EventBus for state management and coordination between components.
    """

    def __init__(
        self,
        wake_word="jarvis",
        sensitivity=0.8,
        idle_timeout=8,
        language="de",
    ):
        """Initialize the voice assistant controller"""
        self.config = AssistantConfig(
            wake_word=wake_word,
            sensitivity=sensitivity,
            idle_timeout=idle_timeout,
            language=language,
        )

        self.wake_word_listener = None
        self.openai_api = None
        self.mic_stream = None
        self.audio_player = AudioPlayerFactory.get_shared_instance()

        self.transcript = TranscriptManager()

        self._conversation_active = False
        self._should_stop = False
        self._user_is_speaking = False
        self._assistant_is_speaking = False

        self._last_activity_time = 0

        self._setup_event_bus()

        self.logger.info(
            "Voice Assistant Controller initialized with wake word: %s", wake_word
        )

    def _setup_event_bus(self):
        """Register event handlers"""
        self.event_bus = EventBus()

        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_STARTED_RESPONDING,
            callback=self._handle_audio_playback_started,
        )
        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_COMPLETED_RESPONDING,
            callback=self._handle_audio_playback_stopped,
        )

        self.event_bus.subscribe(
            EventType.USER_SPEECH_STARTED, self._handle_user_speech_started
        )
        self.event_bus.subscribe(
            EventType.USER_SPEECH_ENDED, self._handle_user_speech_ended
        )

        self.event_bus.subscribe(
            EventType.ASSISTANT_RESPONSE_COMPLETED,
            self._handle_assistant_response_completed,
        )

    async def initialize(self):
        """Initialize all voice assistant components"""
        self.logger.info("Initializing voice assistant components...")

        try:
            self.wake_word_listener = WakeWordListener(
                wakeword=self.config.wake_word, sensitivity=self.config.sensitivity
            )

            self.openai_api = OpenAIRealtimeAPI()
            self.mic_stream = PyAudioMicrophone()

            self.logger.info("Voice assistant components initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize voice assistant: %s", e)
            return False

    async def run(self):
        """Run the main voice assistant loop"""
        if not await self.initialize():
            self.logger.error("Failed to initialize voice assistant")
            return

        self.logger.info(
            "Voice assistant started. Listening for wake word: '%s'",
            self.config.wake_word,
        )
        self._should_stop = False

        await self._run_detection_loop()

    async def _run_detection_loop(self):
        """Main loop for wake word detection and conversation handling"""
        while not self._should_stop:
            try:
                wake_word_detected = (
                    await self.wake_word_listener.listen_for_wakeword_async()
                )

                self.logger.info("Listening for wake word...")

                if wake_word_detected:
                    self.audio_player.play_sound("wake_word")
                    self.event_bus.publish(EventType.WAKE_WORD_DETECTED)
                    await self._handle_conversation()
                    self.event_bus.publish(EventType.IDLE_TRANSITION)

            except asyncio.CancelledError:
                self.logger.info("Voice assistant task cancelled")
                break
            except Exception as e:
                self.logger.error("Error in voice assistant loop: %s", e)
                await asyncio.sleep(1)

    async def _handle_conversation(self):
        """Manage a single conversation from start to finish"""
        self._start_conversation()

        # Erstelle einen separaten Task für die Timeout-Überwachung
        timeout_task = asyncio.create_task(self._monitor_timeout())
        api_task = asyncio.create_task(self._process_speech_with_api())

        try:
            done, pending = await asyncio.wait(
                [api_task, timeout_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            self.logger.error("Error in conversation handling: %s", e)

        finally:
            self._end_conversation()
            self.logger.info("Conversation ended, returning to main loop")

    async def _monitor_timeout(self):
        """Monitor idle timeout in a separate task"""
        while self._conversation_active and not self._should_stop:
            if self._user_is_speaking or self._assistant_is_speaking:
                await asyncio.sleep(0.5)
                continue

            idle_time = time.time() - self._last_activity_time

            if idle_time > self.config.idle_timeout:
                self.logger.info(
                    "Idle timeout reached after %.1f seconds. Ending conversation.",
                    idle_time,
                )
                self._conversation_active = False
                return

            await asyncio.sleep(0.5)

    def _start_conversation(self):
        """Initialize conversation"""
        self._conversation_active = True
        self._user_is_speaking = False
        self._assistant_is_speaking = False
        self._update_activity_time()
        self.transcript.reset_current()
        self.mic_stream.start_stream()
        self.audio_player.start()

    def _end_conversation(self):
        """End conversation and free resources"""
        self._conversation_active = False
        self._user_is_speaking = False
        self._assistant_is_speaking = False
        self.mic_stream.stop_stream()
        self.audio_player.stop()

    async def _process_speech_with_api(self):
        """Send audio to API and process response"""
        return await self.openai_api.setup_and_run(
            mic_stream=self.mic_stream,
        )

    def _update_activity_time(self):
        """Update the last activity timestamp"""
        self.logger.info("Updating last activity time")
        self._last_activity_time = time.time()

    def _handle_user_speech_started(self):
        """Handler for start of user speech"""
        self.logger.debug("User speech detected")
        self._user_is_speaking = True
        self._update_activity_time()

        # Cancel audio playback when user starts speaking
        self.audio_player.clear_queue_and_stop()

    def _handle_user_speech_ended(self):
        """Handler for end of user speech"""
        self.logger.debug("User speech ended")
        self._user_is_speaking = False
        self._update_activity_time()

    def _handle_assistant_response_completed(self, transcript_text):
        """Handler for completed assistant response"""
        if transcript_text:
            self.transcript.current = transcript_text

        self.logger.info("Assistant response completed: '%s'", transcript_text)
        self._update_activity_time()

    def _handle_audio_playback_started(self):
        """Handler for start of audio playback"""
        self.logger.debug("Audio playback started")
        self._assistant_is_speaking = True
        self._update_activity_time()

    def _handle_audio_playback_stopped(self):
        """Handler for end of audio playback"""
        self.logger.info("Assistant stopped responding")
        self._assistant_is_speaking = False
        self._update_activity_time()

    async def stop(self):
        """Stop voice assistant and release resources"""
        self.logger.info("Stopping voice assistant...")
        self._should_stop = True
        self._conversation_active = False

        if self.wake_word_listener:
            self.wake_word_listener.cleanup()

        if self.mic_stream:
            self.mic_stream.cleanup()

        if self.audio_player:
            self.audio_player.stop()

        self.logger.info("Voice assistant stopped")
