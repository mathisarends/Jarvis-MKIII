import asyncio
import websockets

from audio.microphone import PyAudioMicrophone
from audio.audio_player_factory import AudioPlayerFactory
from realtime.realtime_api import OpenAIRealtimeAPI
from speech.assistant_state import AssistantState
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
        self.current = ""
        self.full = ""

    def reset_current(self):
        """Reset the current transcript"""
        self.current = ""

    def update(self, delta):
        """Update transcripts with new text"""
        if not delta:
            return

        self.current += delta
        self.full += delta

    def display_current(self):
        """Display the current transcript to user"""
        print(f"\rAssistant: {self.current}", end="", flush=True)


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
        # Initialize configuration
        self.config = AssistantConfig(
            wake_word=wake_word,
            sensitivity=sensitivity,
            idle_timeout=idle_timeout,
            language=language,
        )

        # Komponenten
        self.wake_word_listener = None
        self.openai_api = None
        self.mic_stream = None
        self.audio_player = AudioPlayerFactory.get_shared_instance()

        self.transcript = TranscriptManager()

        self._state = AssistantState.IDLE
        self._conversation_active = False
        self._should_stop = False

        self._setup_event_bus()

        self.logger.info(
            "Voice Assistant Controller initialized with wake word: %s", wake_word
        )

    @property
    def state(self):
        """Current state of the assistant"""
        return self._state

    @state.setter
    def state(self, new_state):
        """Set the assistant state and publish state change event"""
        if hasattr(self, "_state") and self._state == new_state:
            return

        self._state = new_state

        if hasattr(self, "event_bus"):
            self.logger.debug("State changed to: %s", new_state)

    def _setup_event_bus(self):
        """Registriere Event-Handler"""
        self.event_bus = EventBus()

        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_STARTED_RESPONDING,
            callback=self._handle_audio_playback_started,
        )
        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_COMPLETED_RESPONDING,
            callback=self._handle_audio_playback_stopped,
        )

        # Spracherkennung
        self.event_bus.subscribe(
            EventType.USER_SPEECH_STARTED, self._handle_user_speech_started
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

        # Main assistant loop
        await self._run_detection_loop()

    async def _run_detection_loop(self):
        """Main loop for wake word detection and conversation handling"""
        while not self._should_stop:
            try:
                self.state = AssistantState.IDLE

                print("next iteration as it should be")

                wake_word_detected = (
                    await self.wake_word_listener.listen_for_wakeword_async()
                )

                if wake_word_detected:
                    self.audio_player.play_sound("wake_word")
                    self.event_bus.publish(EventType.WAKE_WORD_DETECTED)
                    self.state = AssistantState.LISTENING
                    await self._handle_conversation()
                    print("post converstation")

            except asyncio.CancelledError:
                self.logger.info("Voice assistant task cancelled")
                break
            except Exception as e:
                self.logger.error("Error in voice assistant loop: %s", e)
                await asyncio.sleep(1)

    async def _handle_conversation(self):
        """Manage a single conversation from start to finish"""
        self._start_conversation()

        while self._conversation_active and not self._should_stop:
            try:
                await self._process_speech_with_api()
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                self.logger.info("API processing task cancelled")
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.warning("WebSocket connection closed: %s", e)
            except Exception as e:
                self.logger.error("Error during API processing: %s", type(e).__name__)

            if not (self._conversation_active and not self._should_stop):
                self.logger.info(
                    "Exiting conversation loop (_conversation_active=%s, _should_stop=%s)",
                    self._conversation_active,
                    self._should_stop,
                )
                break

        self._end_conversation()
        self.logger.info("Conversation ended, returning to main loop")

    def _start_conversation(self):
        """Konversation initialisieren"""
        self._conversation_active = True
        self.state = AssistantState.LISTENING
        self.transcript.reset_current()
        self.mic_stream.start_stream()
        self.audio_player.start()

    def _end_conversation(self):
        """Konversation beenden und Ressourcen freigeben"""
        self.mic_stream.stop_stream()
        self.audio_player.stop()
        self.state = AssistantState.IDLE
        self._conversation_active = False

        self.logger.info("Returning to wake word listening mode")

    async def _process_speech_with_api(self):
        """Audio zur API senden und Antwort verarbeiten"""
        return await self.openai_api.setup_and_run(
            mic_stream=self.mic_stream,
        )

    def _handle_user_speech_started(self):
        """Handler für Beginn der Benutzereingabe"""
        self.state = AssistantState.LISTENING
        self.logger.debug("User speech detected")

        # Audio abbrechen
        self.audio_player.clear_queue_and_stop()

    def _handle_assistant_response_completed(self, transcript_text):
        """Handler für abgeschlossene Antwort des Assistenten"""
        if transcript_text:
            self.transcript.current = transcript_text

        self.logger.info("Assistant response completed: '%s'", transcript_text)

    def _handle_audio_playback_started(self):
        """Handler für Start der Audio-Wiedergabe"""
        self.state = AssistantState.RESPONDING
        self.logger.debug("Audio playback started")

    def _handle_audio_playback_stopped(self):
        """Handler für Ende der Audio-Wiedergabe"""
        # Zurück zum LISTENING-State, wenn keine Audio-Wiedergabe aktiv ist
        if self.state == AssistantState.RESPONDING:
            self.state = AssistantState.LISTENING
            self.logger.debug("Audio playback stopped, back to listening mode")

    async def stop(self):
        """Sprachassistenten stoppen und Ressourcen freigeben"""
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
