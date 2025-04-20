import asyncio
import threading
import time
import traceback
import websockets
from enum import Enum, auto

from realtime.audio.microphone import PyAudioMicrophone
from realtime.audio.player import PyAudioPlayer
from realtime.realtime_api import OpenAIRealtimeAPI
from speech.wake_word_listener import WakeWordListener

from utils.logging_mixin import LoggingMixin
from utils.speech_duration_estimator import SpeechDurationEstimator


class AssistantState(Enum):
    """Enumeration of possible assistant states"""

    IDLE = auto()  # Waiting for wake word
    LISTENING = auto()  # Actively listening to user input
    RESPONDING = auto()  # Processing or delivering a response


class VoiceAssistantController(LoggingMixin):
    """
    Controller for voice assistant that integrates wake word detection with OpenAI API.

    This class coordinates the flow between wake word detection and OpenAI interaction,
    managing the conversation lifecycle including:
    - Wake word detection
    - Managing conversation state
    - Handling user inactivity
    - Processing conversation responses
    - Providing a continuous listening loop
    - Estimating speech duration to allow proper time for responses
    """

    def __init__(
        self,
        wake_word="jarvis",
        sensitivity=0.8,
        initial_wait=5.0,
        post_response_wait=7.0,
        cooldown_period=1.0,
    ):
        """
        Initialize the voice assistant controller.

        Args:
            wake_word: The wake word to listen for
            sensitivity: Sensitivity for wake word detection (0.0-1.0)
            initial_wait: Seconds to wait initially after wake word before timing out
            post_response_wait: Additional seconds to wait after estimated response time
            cooldown_period: Seconds to wait after finishing a conversation
            language: Language code for speech duration estimation
        """
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.initial_wait = initial_wait  # Renamed parameter
        self.post_response_wait = post_response_wait
        self.cooldown_period = cooldown_period

        self.speech_estimator = SpeechDurationEstimator(language="de")

        self.wake_word_listener = None
        self.openai_api = None
        self.mic_stream = None
        self.audio_player = None

        self.state = AssistantState.IDLE
        self.last_activity_time = 0
        self.activity_detected = threading.Event()
        self.conversation_active = False
        self.should_stop = False

        self._transcript_text = ""
        self._response_done = False
        self._expected_response_end_time = 0
        
        self._response_started_at = 0
        self._is_responding = False
        self._user_speech_active = False  # New flag to track if user is actively speaking

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
        self.audio_player = PyAudioPlayer()

        self.logger.info("Voice assistant components initialized successfully")
        return True

    def _register_activity(self):
        """
        Update the last activity timestamp and set activity event.
        Called whenever user or assistant activity is detected.
        """
        self.last_activity_time = time.time()
        self.activity_detected.set()

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
            self._user_speech_active = True  # Set flag that user is speaking
            self._had_speech_activity = True  # Mark that we've had speech in this conversation
            self.logger.debug("Speech activity detected, set state to LISTENING")

        elif event_type in ["response.text.delta", "response.audio.delta"]:
            self._register_activity()
            self.state = AssistantState.RESPONDING
            self.logger.debug("Response delta received, set state to RESPONDING")
            
            # If this is the first response chunk, note the start time
            if not self._is_responding:
                self._is_responding = True
                self._response_started_at = time.time()

    def _handle_api_event(self, event_type: str):
        """
        Handle special events from the OpenAI API.
        
        Args:
            event_type: The type of event
            response: The full response object
        """
        if event_type == "input_audio_buffer.speech_started":
            self.logger.info("User speech started")
            # Reset transcription when user starts speaking
            self._transcript_text = ""
            self._is_responding = False
            self._user_speech_active = True  # Set flag that user is speaking
            self._had_speech_activity = True  # Mark that we've had speech in this conversation
            self.state = AssistantState.LISTENING
            
        elif event_type == "response.done":
            self.logger.info("Response completed event received")
            self._response_done = True
            # Don't set _user_speech_active to False here
            # We want to keep track that speech happened in this conversation
            
            # Update the expected response end time based on the transcript
            if self._transcript_text:
                # Calculate speech duration estimate
                estimated_duration = self.speech_estimator.estimate_duration(self._transcript_text)
                
                # Add buffer time for speech synthesis and playback
                total_response_time = estimated_duration + self.post_response_wait
                
                # Set the expected end time (from now)
                self._expected_response_end_time = time.time() + total_response_time
                
                self.logger.info(
                    "Response transcript: '%s'", self._transcript_text
                )
                self.logger.info(
                    "Estimated speech duration: %.2f seconds + %.2f buffer = %.2f seconds total", 
                    estimated_duration, 
                    self.post_response_wait,
                    total_response_time
                )
                
                # Ensure we're in RESPONDING state for the inactivity monitor
                self.state = AssistantState.RESPONDING
            else:
                # If no transcript, use a minimal default time
                self._expected_response_end_time = time.time() + self.post_response_wait
                self.logger.info(
                    "No transcript available, using minimum wait time: %.2f seconds", 
                    self.post_response_wait
                )
                # Ensure we're in RESPONDING state for the inactivity monitor
                self.state = AssistantState.RESPONDING

    async def _monitor_inactivity(self):
        """
        Monitor for inactivity to determine when to stop listening.
        New logic:
        - When user is speaking, no timeout is applied
        - If user never spoke and no activity for initial_wait period, end conversation
        - If user already spoke in this conversation, don't time out in LISTENING state
        - After response.done, wait for estimated speech duration + buffer
        """
        while self.conversation_active and not self.should_stop:
            current_time = time.time()
            
            # Different logic based on current state
            if self.state == AssistantState.LISTENING:
                if self._user_speech_active:
                    # If user is actively speaking, do nothing - let them speak indefinitely
                    pass
                elif not self._had_speech_activity:
                    # Only apply timeout if we've never detected speech in this conversation
                    # (This handles cases where wake word is detected but no speech follows)
                    elapsed = current_time - self.last_activity_time
                    if elapsed > self.initial_wait:
                        self.logger.info(
                            "No speech detected for %s seconds after wake word, ending listening mode", 
                            self.initial_wait
                        )
                        self.conversation_active = False
                        break
                # If speech happened at some point but not active now, keep listening without timeout
                    
            elif self.state == AssistantState.RESPONDING:
                # If we've received the response.done event
                if self._response_done:
                    # Log the current time and expected end time for debugging
                    self.logger.debug(
                        "Current time: %.2f, Expected end time: %.2f, Difference: %.2f seconds",
                        current_time, 
                        self._expected_response_end_time,
                        self._expected_response_end_time - current_time
                    )
                    
                    # Check if we've waited long enough for the speech to be spoken
                    if current_time >= self._expected_response_end_time:
                        self.logger.info(
                            "Response completion timeout reached after estimated speech duration"
                        )
                        self.conversation_active = False
                        break
                # If still generating response but no activity for a while
                elif current_time - self.last_activity_time > self.initial_wait * 2:
                    self.logger.info(
                        "Response generation timeout (%ss) reached",
                        self.initial_wait * 2
                    )
                    self.conversation_active = False
                    break
            else:
                self.logger.debug("Current state: %s", self.state)

            await asyncio.sleep(0.1)
                    
            if self.state == AssistantState.RESPONDING:
                # If we've received the response.done event
                if self._response_done:
                    # Check if we've waited long enough for the speech to be spoken
                    if current_time >= self._expected_response_end_time:
                        self.logger.info(
                            "Response completion timeout reached after estimated speech duration"
                        )
                        self.conversation_active = False
                        break
                # If still generating response but no activity for a while
                elif current_time - self.last_activity_time > self.initial_wait * 2:
                    self.logger.info(
                        "Response generation timeout (%ss) reached",
                        self.initial_wait * 2
                    )
                    self.conversation_active = False
                    break

            await asyncio.sleep(0.1)

    async def _handle_conversation(self):
        """
        Handle a single conversation after wake word detection.
        Manages the entire conversation lifecycle from wake word detection to completion.
        """
        self.logger.info("Wake word detected! Starting conversation...")
        self.conversation_active = True
        self.last_activity_time = time.time()
        self.state = AssistantState.LISTENING
        
        # Reset conversation state
        self._transcript_text = ""
        self._response_done = False
        self._is_responding = False
        self._user_speech_active = False
        self._had_speech_activity = False  # New flag to track if we've had any speech in this conversation

        # Start audio components
        self.mic_stream.start_stream()
        self.audio_player.start()

        try:
            # Run inactivity monitor and API tasks concurrently
            inactivity_task = asyncio.create_task(self._monitor_inactivity())
            api_task = asyncio.create_task(self.openai_api.setup_and_run(
                self.mic_stream,
                self.audio_player,
                handle_transcript=self._handle_transcript,
                event_handler=self._handle_api_event,
            ))
            
            # Wait for any task to complete
            done, pending = await asyncio.wait(
                [inactivity_task, api_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Check which task completed and log appropriate information
            for completed_task in done:
                if completed_task == inactivity_task:
                    self.logger.info("Conversation ended due to inactivity")
                elif completed_task == api_task:
                    self.logger.info("API task completed naturally")
                
                # Check for exceptions in completed tasks
                try:
                    completed_task.result()
                except asyncio.CancelledError:
                    self.logger.info("Task was cancelled")
                except websockets.exceptions.ConnectionClosedOK:
                    self.logger.info("WebSocket connection closed normally")
                except websockets.exceptions.ConnectionClosedError as e:
                    self.logger.warning("WebSocket connection closed with error: %s", e)
                except Exception as e:
                    self.logger.error("Error in completed task: %s - %s", type(e).__name__, e)
            
            # Cancel remaining tasks gracefully
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.debug("Successfully cancelled pending task")
                except Exception as e:
                    self.logger.warning("Error while cancelling task: %s - %s", type(e).__name__, e)

        # Handle specific exceptions with more detailed information
        except asyncio.CancelledError:
            self.logger.info("Conversation handling was cancelled")
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.warning("WebSocket connection closed: %s", e)
        except OSError as e:
            self.logger.error("OS error during conversation: %s", e)
        except Exception as e:
            # Still have a catch-all, but with better type information
            self.logger.error("Unexpected error during conversation: %s - %s", type(e).__name__, e)
            self.logger.debug(traceback.format_exc())
        finally:
            # Clean up resources
            self.mic_stream.stop_stream()
            self.audio_player.stop()

            self.state = AssistantState.IDLE
            self.conversation_active = False

            self.logger.info(
                "Conversation ended, cooldown for %s seconds...", self.cooldown_period
            )
            await asyncio.sleep(self.cooldown_period)
            
            self.logger.info("Returning to wake word listening mode")

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

        # Print without newline for a continuous display
        print(f"\rAssistant: {self._transcript_text}", end="", flush=True)

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

        if self.openai_api:
            await self.openai_api.close()

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