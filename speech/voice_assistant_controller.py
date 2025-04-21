from enum import Enum, auto
import asyncio
import threading
import time
import traceback
import websockets

from audio.microphone import PyAudioMicrophone
from audio.audio_player_factory import AudioPlayerFactory
from realtime.realtime_api import OpenAIRealtimeAPI
from speech.wake_word_listener import WakeWordListener

from utils.logging_mixin import LoggingMixin
from utils.speech_duration_estimator import SpeechDurationEstimator


# TODO: Herausfinden, warum ich den hier nicht mehr unterbrechen kann.
class AssistantState(Enum):
    """Enumeration of possible assistant states"""

    IDLE = auto()
    LISTENING = auto()
    RESPONDING = auto()


class VoiceAssistantController(LoggingMixin):
    """
    Controller for voice assistant that integrates wake word detection with OpenAI API.

    This class coordinates the flow between wake word detection and OpenAI interaction,
    managing the conversation lifecycle including:
    - Wake word detection
    - Managing conversation state
    - Processing conversation responses
    - Providing a continuous listening loop

    Timeout and duration estimation logic is handled by ConversationTimeoutManager.
    """

    def __init__(
        self,
        wake_word="jarvis",
        sensitivity=0.8,
        initial_wait=5.0,
        post_response_wait=7.0,
        language="de",
    ):
        """
        Initialize the voice assistant controller.

        Args:
            wake_word: The wake word to listen for
            sensitivity: Sensitivity for wake word detection (0.0-1.0)
            initial_wait: Seconds to wait initially after wake word before timing out
            post_response_wait: Additional seconds to wait after estimated response time
            language: Language code for speech duration estimation
        """
        self.wake_word = wake_word
        self.sensitivity = sensitivity

        # Create the timeout manager with our settings
        self.timeout_manager = ConversationTimeoutManager(
            initial_wait=initial_wait,
            post_response_wait=post_response_wait,
            language=language,
        )

        self.wake_word_listener = None
        self.openai_api = None
        self.mic_stream = None
        self.audio_player = AudioPlayerFactory.get_shared_instance()

        self.state = AssistantState.IDLE
        self.activity_detected = threading.Event()
        self.conversation_active = False
        self.should_stop = False

        self._transcript_text = ""

        self.logger.info(
            "Voice Assistant Controller initialized with wake word: %s", wake_word
        )

    async def initialize(self):
        """
        Initialize all components of the voice assistant.

        Returns:
            True if initialization was successful, False otherwise
        """
        self.logger.info("Initializing voice assistant components...")

        try:
            self.wake_word_listener = WakeWordListener(
                wakeword=self.wake_word, sensitivity=self.sensitivity
            )
        except Exception as e:
            self.logger.error("Failed to initialize wake word listener: %s", e)
            return False

        self.openai_api = OpenAIRealtimeAPI()

        # Initialize audio components
        self.mic_stream = PyAudioMicrophone()

        self.logger.info("Voice assistant components initialized successfully")
        return True

    async def run(self):
        """
        Run the voice assistant main loop.
        This is the main entry point that starts the continuous wake word detection
        and conversation handling cycle.
        """
        if not await self.initialize():
            self.logger.error("Failed to initialize voice assistant")
            return

        self.logger.info(
            "Voice assistant started. Listening for wake word: '%s'", self.wake_word
        )
        self.should_stop = False

        while not self.should_stop:
            try:
                self.state = AssistantState.IDLE

                wake_word_detected = await self._listen_for_wake_word_async()

                if wake_word_detected:
                    self.audio_player.play_sound("wake_word")
                    await self._handle_conversation()

            except asyncio.CancelledError:
                self.logger.info("Voice assistant task cancelled")
                break
            except Exception as e:
                self.logger.error("Error in voice assistant loop: %s", e)
                await asyncio.sleep(1)

    async def stop(self):
        """
        Stop the voice assistant gracefully.
        Cleans up all resources and stops all ongoing processes.
        """
        self.logger.info("Stopping voice assistant...")
        self.should_stop = True
        self.conversation_active = False

        if self.wake_word_listener:
            self.wake_word_listener.cleanup()

        if self.mic_stream:
            self.mic_stream.cleanup()

        if self.audio_player:
            self.audio_player.stop()

        self.logger.info("Voice assistant stopped")

    async def stop_current_conversation(self):
        """
        Stop the current conversation and return to wake word listening mode.
        This can be called from external components to interrupt the conversation.
        """
        if self.state != AssistantState.IDLE:
            self.logger.info("Manually stopping current conversation")
            self.conversation_active = False

    def speech_activity_handler(self, response):
        """
        Handler for speech activity events from OpenAI API.

        Args:
            response: The event response from the API
        """
        event_type = response.get("type", "")

        if event_type in [
            "input_audio_buffer.speech_started",
            "input_audio_buffer.speech_detected",
        ]:
            self._register_activity()
            self.state = AssistantState.LISTENING
            self.timeout_manager.handle_speech_started()

        elif event_type in ["response.text.delta", "response.audio.delta"]:
            self._register_activity()
            self.state = AssistantState.RESPONDING
            self.timeout_manager.handle_response_delta()


    def _register_activity(self):
        """
        Update the last activity timestamp and set activity event.
        Called whenever user or assistant activity is detected.
        """
        self.timeout_manager.register_activity()
        self.activity_detected.set()

    def _handle_api_event(self, event_type: str):
        """
        Handle special events from the OpenAI API.
        """
        self.logger.info("API EVENT RECEIVED: %s", event_type)

        if event_type == "input_audio_buffer.speech_started":
            # Reset transcription when user starts speaking
            self._transcript_text = ""
            self.state = AssistantState.LISTENING
            self.timeout_manager.handle_speech_started()

        elif event_type == "response.done":
            self.logger.info("Response completed event received")
            # Handle response done in timeout manager
            self.timeout_manager.handle_response_done(self._transcript_text)
            self.state = AssistantState.RESPONDING

    def _handle_transcript(self, response):
        """
        Handle transcript responses from OpenAI API.

        Args:
            response: The transcript response from the API
        """
        delta = response.get("delta", "")
        if not delta:
            return

        self._register_activity()
        self._transcript_text += delta

        print(f"\rAssistant: {self._transcript_text}", end="", flush=True)

    async def _monitor_inactivity(self):
        """
        Monitor for inactivity to determine when to stop listening.
        Uses the timeout manager to determine if the conversation should timeout.
        """
        while self.conversation_active and not self.should_stop:
            # Check with timeout manager if we should timeout
            should_timeout, reason = self.timeout_manager.should_timeout()

            if should_timeout:
                self.logger.info("Timeout detected: %s", reason)
                self.conversation_active = False
                break

            # Small sleep to prevent CPU thrashing
            await asyncio.sleep(0.1)

    async def _listen_for_wake_word_async(self):
        """
        Listen for wake word in a way that doesn't block the event loop.

        Returns:
            True if wake word was detected, False otherwise
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.wake_word_listener.listen_for_wakeword
        )

    async def _handle_conversation(self):
        """
        Handle a single conversation after wake word detection.
        Manages the entire conversation lifecycle from wake word detection to completion.
        """
        self.logger.info("Wake word detected! Starting conversation...")
        self._prepare_conversation()

        # Main conversation loop - runs as long as the conversation is active
        while self.conversation_active and not self.should_stop:
            try:
                inactivity_task = asyncio.create_task(self._monitor_inactivity())
                api_task = asyncio.create_task(self._start_api_processing())

                # Wait for one of the tasks to complete
                done, pending = await asyncio.wait(
                    [inactivity_task, api_task], return_when=asyncio.FIRST_COMPLETED
                )

                self.logger.debug(
                    "Tasks completed: %d, pending: %d", len(done), len(pending)
                )

                # Handle completed tasks
                should_continue = await self._handle_completed_tasks(done)

                # Break the loop only if the conversation was explicitly ended
                if not should_continue:
                    self.logger.info("Conversation ending as requested")
                    break

                # Cancel pending tasks
                await self._cancel_pending_tasks(pending)

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                self.logger.info("Conversation handling was cancelled")
                break
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.warning("WebSocket connection closed: %s", e)
                break
            except OSError as e:
                self.logger.error("OS error during conversation: %s", e)
                break
            except Exception as e:
                self.logger.error(
                    "Unexpected error during conversation: %s - %s", type(e).__name__, e
                )
                self.logger.debug(traceback.format_exc())
                break

        # After exiting the loop
        self._cleanup_conversation()

    def _prepare_conversation(self):
        """Set up conversation state and required components"""
        self.conversation_active = True
        self.state = AssistantState.LISTENING
        self._transcript_text = ""
        self.timeout_manager.reset()
        self.mic_stream.start_stream()
        self.audio_player.start()

    async def _start_api_processing(self):
        """Start the OpenAI API processing"""
        return await self.openai_api.setup_and_run(
            mic_stream=self.mic_stream,
            handle_transcript=self._handle_transcript,
            event_handler=self._handle_api_event,
        )

    # TODO: not very clean
    async def _handle_completed_tasks(self, done):
        """
        Handle tasks that have completed.

        Args:
            done: Set of completed tasks

        Returns:
            bool: True if conversation should continue, False if it should end
        """
        for task in done:
            task_name = (
                "Inactivity monitor"
                if task._coro.__name__ == "_monitor_inactivity"
                else "API task"
            )
            self.logger.info("%s completed", task_name)

            try:
                task.result()

                # If inactivity monitor ended, end the conversation
                if task_name == "Inactivity monitor":
                    self.logger.info("Conversation ended due to inactivity")
                    self.conversation_active = False
                    return False

            except (asyncio.CancelledError, websockets.exceptions.ConnectionClosedOK):
                self.logger.info("%s ended normally", task_name)
                
            except Exception as e:
                self.logger.error(
                    "Error in %s: %s - %s", task_name, type(e).__name__, e
                )

        # If conversation was explicitly ended
        if not self.conversation_active:
            return False

        # The critical change: For API task end AND truncation, continue conversation
        if task_name == "API task":
            return True

        # For unexpected conditions or API task end without truncation
        # (normal end of the API task), end the conversation
        return False

    async def _cancel_pending_tasks(self, pending):
        """Cancel any pending tasks"""
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.warning(
                    "Error while cancelling task: %s - %s", type(e).__name__, e
                )

    def _cleanup_conversation(self):
        """Clean up resources after conversation ends"""
        self.mic_stream.stop_stream()
        self.audio_player.stop()
        self.state = AssistantState.IDLE
        self.conversation_active = False
        self.truncation_occurred = False
        self.logger.info("Returning to wake word listening mode")


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
        self._user_speech_active = False
        self._response_done = False
        self._expected_response_end_time = 0

    def reset(self):
        """Reset the manager for a new conversation"""
        self.state = AssistantState.LISTENING
        self.last_activity_time = time.time()
        self._had_speech_activity = False
        self._user_speech_active = False
        self._response_done = False
        self._expected_response_end_time = 0

    def register_activity(self):
        """Register activity to reset inactivity timer"""
        self.last_activity_time = time.time()

        # Reset user_speech_active flag when in LISTENING state
        # This ensures the flag is properly reset after speech ends
        if self.state == AssistantState.LISTENING:
            self._user_speech_active = True
        else:
            # If we're in RESPONDING state, make sure user isn't considered actively speaking
            self._user_speech_active = False

    def handle_speech_started(self):
        """Handle speech started event"""
        self.register_activity()
        self.state = AssistantState.LISTENING
        self._user_speech_active = True
        self._had_speech_activity = True
        self.logger.debug("Speech activity detected, set state to LISTENING")

    def handle_response_delta(self):
        """Handle response delta event"""
        self.register_activity()
        self.state = AssistantState.RESPONDING
        # Important: Set user speech inactive when assistant starts responding
        self._user_speech_active = False

    def handle_response_done(self, transcript_text) -> float:
        """
        Handle response done event

        Args:
            transcript_text: The transcript text to use for duration estimation

        Returns:
            float: The expected end time timestamp
        """
        self._response_done = True
        # Explicitly set user speech to inactive
        self._user_speech_active = False

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
        if self._user_speech_active and self.state == AssistantState.LISTENING:
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
