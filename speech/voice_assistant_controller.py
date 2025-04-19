import asyncio
import threading
import time
from enum import Enum, auto

from realtime.audio.microphone import PyAudioMicrophone
from realtime.audio.player import PyAudioPlayer
from realtime.realtime_api import OpenAIRealtimeAPI

from speech.wake_word_listener import WakeWordListener

from utils.logging_mixin import LoggingMixin

class AssistantState(Enum):
    """Enumeration of possible assistant states"""
    IDLE = auto()
    LISTENING = auto()
    RESPONDING = auto()


class VoiceAssistantController(LoggingMixin):
    """
    Controller for voice assistant that integrates wake word detection with OpenAI API.
    
    This class coordinates the flow between wake word detection and OpenAI interaction.
    """
    
    def __init__(self,
                 wake_word="jarvis",
                 sensitivity=0.8,
                 inactivity_timeout=5.0,
                 cooldown_period=1.0):
        """
        Initialize the voice assistant controller.
        
        Args:
            wake_word: The wake word to listen for
            sensitivity: Sensitivity for wake word detection (0.0-1.0)
            inactivity_timeout: Seconds of silence before returning to wake word mode
            cooldown_period: Seconds to wait after finishing a conversation
        """
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.inactivity_timeout = inactivity_timeout
        self.cooldown_period = cooldown_period
        
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
        
        self.logger.info("Voice Assistant Controller initialized with wake word: %s", wake_word)
    
    async def initialize(self):
        """Initialize all components of the voice assistant"""
        self.logger.info("Initializing voice assistant components...")
        
        try:
            self.wake_word_listener = WakeWordListener(
                wakeword=self.wake_word,
                sensitivity=self.sensitivity
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
        """Update the last activity timestamp and set activity event"""
        self.last_activity_time = time.time()
        self.activity_detected.set()
    
    def speech_activity_handler(self, response):
        """Handler for speech activity events from OpenAI API"""
        event_type = response.get('type', '')
        
        if event_type in ['input_audio_buffer.speech_started', 'input_audio_buffer.speech_detected']:
            self._register_activity()
            self.state = AssistantState.LISTENING
        
        elif event_type in ['response.text.delta', 'response.audio.delta']:
            self._register_activity()
            self.state = AssistantState.RESPONDING
    
    async def _monitor_inactivity(self):
        """Monitor for inactivity to determine when to stop listening"""
        while self.conversation_active and not self.should_stop:
            current_time = time.time()
            elapsed = current_time - self.last_activity_time
            
            if elapsed > self.inactivity_timeout and self.state == AssistantState.LISTENING:
                self.logger.info("Inactivity timeout (%ss) reached", self.inactivity_timeout)
                self.conversation_active = False
                break
                
            await asyncio.sleep(0.1)
    
    async def _handle_conversation(self):
        """Handle a single conversation after wake word detection"""
        self.logger.info("Wake word detected! Starting conversation...")
        self.conversation_active = True
        self.last_activity_time = time.time()
        self.state = AssistantState.LISTENING
        
        # Start audio components
        self.mic_stream.start_stream()
        self.audio_player.start()
        
        try:
            # Start inactivity monitor
            inactivity_task = asyncio.create_task(self._monitor_inactivity())
            
            await self.openai_api.setup_and_run(
                self.mic_stream, 
                self.audio_player,
                handle_transcript=self._handle_transcript
            )
            
            await inactivity_task
        
        except Exception as e:
            self.logger.error("Error during conversation: %s", e)
        finally:
            self.mic_stream.stop_stream()
            self.audio_player.stop()
            
            self.state = AssistantState.IDLE
            self.conversation_active = False
            
            self.logger.info("Conversation ended, cooldown for %s seconds...", self.cooldown_period)
            await asyncio.sleep(self.cooldown_period)
    
    def _handle_transcript(self, response):
        """Handle transcript responses from OpenAI API"""
        delta = response.get("delta", "")
        if not delta:
            return

        self._register_activity()

        self._transcript_text += delta
        
        # Direkt mit print, ohne newline (Zeilenumbruch)
        print(f"\rAssistant: {self._transcript_text}", end="", flush=True)
        
    
    async def run(self):
        """Run the voice assistant main loop"""
        if not await self.initialize():
            self.logger.error("Failed to initialize voice assistant")
            return
        
        self.logger.info("Voice assistant started. Listening for wake word: '%s'", self.wake_word)
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
        """Listen for wake word in a way that doesn't block the event loop"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.wake_word_listener.listen_for_wakeword)
    
    async def stop(self):
        """Stop the voice assistant gracefully"""
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