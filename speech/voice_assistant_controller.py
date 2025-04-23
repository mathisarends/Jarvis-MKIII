import asyncio
import time
import traceback
import websockets

from audio.microphone import PyAudioMicrophone
from audio.audio_player_factory import AudioPlayerFactory
from realtime.realtime_api import OpenAIRealtimeAPI
from speech.assistant_state import AssistantState
from speech.wake_word_listener import WakeWordListener

from utils.event_bus import EventBus, EventType
from utils.logging_mixin import LoggingMixin
from utils.singleton_decorator import singleton
from utils.speech_duration_estimator import SpeechDurationEstimator


class AssistantConfig:
    """Configuration for the voice assistant"""

    def __init__(
        self,
        wake_word="jarvis",
        sensitivity=0.8,
        initial_wait=5.0,
        post_response_wait=10.0,
        language="de",
    ):
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.initial_wait = initial_wait
        self.post_response_wait = post_response_wait
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

    This class orchestrates the conversation flow between:
    1. Wake word detection
    2. User speech listening
    3. API interaction
    4. Response playback
    """

    def __init__(
        self,
        wake_word="jarvis",
        sensitivity=0.8,
        initial_wait=5.0,
        post_response_wait=10.0,
        language="de",
    ):
        """Initialize the voice assistant controller"""
        # Initialize configuration
        self.config = AssistantConfig(
            wake_word=wake_word,
            sensitivity=sensitivity,
            initial_wait=initial_wait,
            post_response_wait=post_response_wait,
            language=language,
        )

        self.wake_word_listener = None
        self.openai_api = None
        self.mic_stream = None
        self.audio_player = AudioPlayerFactory.get_shared_instance()
        self.timeout_manager = ConversationTimeoutManager(
            initial_wait=initial_wait,
            post_response_wait=post_response_wait,
            language=language,
        )

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
            self.event_bus.publish(EventType.STATE_CHANGED, new_state)

    def _setup_event_bus(self):
        """Configure event bus subscriptions"""
        self.event_bus = EventBus()

        self.event_bus.subscribe(
            EventType.USER_SPEECH_STARTED, self.timeout_manager.handle_speech_started
        )
        self.event_bus.subscribe(
            EventType.ASSISTANT_RESPONSE_COMPLETED,
            self._handle_assistant_response_completed,
        )
        self.event_bus.subscribe(
            EventType.TRANSCRIPT_UPDATED, self._handle_transcript_update
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

                wake_word_detected = (
                    await self.wake_word_listener.listen_for_wakeword_async()
                )

                if wake_word_detected:
                    self.audio_player.play_sound("wake_word")
                    self.state = AssistantState.LISTENING

                    await self._handle_conversation_lifecycle()

            except asyncio.CancelledError:
                self.logger.info("Voice assistant task cancelled")
                break
            except Exception as e:
                self.logger.error("Error in voice assistant loop: %s", e)
                await asyncio.sleep(1)

    async def _handle_conversation_lifecycle(self):
        """Manage a single conversation from start to finish"""
        self.logger.info("Wake word detected! Starting conversation...")

        self._start_conversation()

        inactivity_monitor = asyncio.create_task(self._monitor_conversation_activity())

        while self._conversation_active and not self._should_stop:
            try:
                await self._process_speech_with_api()
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                self.logger.info("API processing task cancelled")
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.warning("WebSocket connection closed: %s", e)
            except Exception as e:
                self.logger.error(
                    "Error during API processing: %s - %s", type(e).__name__, e
                )
                self.logger.debug(traceback.format_exc())

        self.logger.info("Conversation ended")

        if not inactivity_monitor.done():
            inactivity_monitor.cancel()
            try:
                await inactivity_monitor
            except asyncio.CancelledError:
                pass

        # Clean up conversation resources
        self._end_conversation()

    def _start_conversation(self):
        """Set up a new conversation"""
        self._conversation_active = True
        self.state = AssistantState.LISTENING
        self.transcript.reset_current()
        self.timeout_manager.reset()
        self.mic_stream.start_stream()
        self.audio_player.start()

    def _end_conversation(self):
        """Clean up conversation resources"""
        self.mic_stream.stop_stream()
        self.audio_player.stop()
        self.state = AssistantState.IDLE
        self._conversation_active = False
        self.logger.info("Returning to wake word listening mode")

    async def _process_speech_with_api(self):
        """Send audio to API and process response"""
        return await self.openai_api.setup_and_run(
            mic_stream=self.mic_stream,
        )

    async def _monitor_conversation_activity(self):
        """Monitor for inactivity to determine when to end conversation"""
        try:
            while self._conversation_active and not self._should_stop:
                should_timeout, reason = self.timeout_manager.should_timeout()

                if should_timeout:
                    self.logger.info("Timeout detected: %s", reason)
                    self._conversation_active = False
                    break

                await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error("Error in activity monitor: %s - %s", type(e).__name__, e)
            self._conversation_active = False

    def _handle_assistant_response_completed(self, transcript_text):
        """Handle when assistant response is complete"""
        if transcript_text:
            self.transcript.current = transcript_text

        self.timeout_manager.handle_response_done(self.transcript.current)

        self.state = AssistantState.RESPONDING

    def _handle_transcript_update(self, response):
        """Process transcript updates from the API"""
        delta = response.get("delta", "")
        if not delta:
            return

        self.transcript.update(delta)
        self.transcript.display_current()

    async def stop(self):
        """Stop the voice assistant and cleanup resources"""
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

    async def stop_current_conversation(self):
        """Manually stop the current conversation"""
        if self.state != AssistantState.IDLE:
            self.logger.info("Manually stopping current conversation")
            self._conversation_active = False


class ConversationTimeoutManager(LoggingMixin):
    """
    Manages the timeout logic for voice assistant conversations.

    This class handles:
    - Initial wait timeout for when wake word is detected but no speech follows
    - Unlimited listening time when user is actively speaking
    - Estimated response duration calculation and timeout
    - Response generation timeout
    """

    def __init__(
        self,
        initial_wait=5.0,
        post_response_wait=7.0,
        language="de",
    ):
        """
        Initialize the conversation timeout manager.

        Args:
            initial_wait: Seconds to wait initially after wake word before timing out
            post_response_wait: Additional seconds to wait after estimated response time
            language: Language code for speech duration estimation
            logger: Optional logger instance to use (will create one if not provided)
        """
        self.initial_wait = initial_wait
        self.post_response_wait = post_response_wait

        self.speech_estimator = SpeechDurationEstimator(language=language)

        self.state = AssistantState.IDLE
        self.last_activity_time = 0
        self._had_speech_activity = False
        self._response_done = False
        self._expected_response_end_time = 0

    def reset(self):
        """Reset the manager for a new conversation"""
        self.state = AssistantState.LISTENING
        self.last_activity_time = time.time()
        self._had_speech_activity = False
        self._response_done = False
        self._expected_response_end_time = 0

    def handle_speech_started(self):
        """Handle speech started event"""
        self.state = AssistantState.LISTENING
        self._had_speech_activity = True
        self.logger.debug("Speech activity detected, set state to LISTENING")

    def handle_response_done(self, transcript_text) -> float:
        """
        Handle response done event

        Args:
            transcript_text: The transcript text to use for duration estimation

        Returns:
            float: The expected end time timestamp
        """
        self._response_done = True

        # Update the expected response end time based on the transcript
        if transcript_text:
            # Calculate speech duration estimate
            estimated_duration = self.speech_estimator.estimate_duration(
                transcript_text
            )

            # Add buffer time for speech synthesis and playback
            total_response_time = estimated_duration + self.post_response_wait

            # Set the expected end time (from now)
            self._expected_response_end_time = time.time() + total_response_time

            self.logger.info("Response transcript: '%s'", transcript_text)
            self.logger.info(
                "Estimated speech duration: %.2f seconds + %.2f buffer = %.2f seconds total",
                estimated_duration,
                self.post_response_wait,
                total_response_time,
            )
        else:
            self._expected_response_end_time = time.time() + self.post_response_wait
            self.logger.info(
                "No transcript available, using minimum wait time: %.2f seconds",
                self.post_response_wait,
            )

        self.state = AssistantState.RESPONDING

        return self._expected_response_end_time

    def should_timeout(self):
        """
        Check if the conversation should time out based on current state and conditions.

        Returns:
            tuple: (bool, str) - (should_timeout, reason)
        """
        current_time = time.time()

        # Case 1: User is actively speaking - never timeout
        if self.state == AssistantState.LISTENING:
            self.logger.debug("User is actively speaking, not timing out")
            return False, ""

        # Case 2: Listening state but no speech activity detected yet
        if self.state == AssistantState.LISTENING and not self._had_speech_activity:
            elapsed = current_time - self.last_activity_time
            if elapsed > self.initial_wait:
                reason = f"No speech detected for {self.initial_wait} seconds after wake word"
                return True, reason

        # Case 3: Responding state - check response completion timeout
        if self.state == AssistantState.RESPONDING:
            # Case 3a: Response is done, check if expected speaking time has elapsed
            if self._response_done:
                time_left = self._expected_response_end_time - current_time

                self.logger.debug(
                    "Current time: %.2f, Expected end time: %.2f, Time left: %.2f seconds",
                    current_time,
                    self._expected_response_end_time,
                    time_left,
                )

                if current_time >= self._expected_response_end_time:
                    return (
                        True,
                        f"Response completion timeout reached after estimated speech duration (buffer: {self.post_response_wait}s)",
                    )
            # Case 3b: Response generation timeout
            elif current_time - self.last_activity_time > self.initial_wait * 2:
                return (
                    True,
                    f"Response generation timeout ({self.initial_wait * 2}s) reached",
                )

        # Default: don't timeout
        return False, ""
