import json
import base64
import asyncio
import traceback
import websockets
from realtime.config import (
    OPENAI_WEBSOCKET_URL, 
    OPENAI_HEADERS, 
    SYSTEM_MESSAGE, 
    VOICE
)
from utils.logging_mixin import LoggingMixin

class OpenAIRealtimeAPI(LoggingMixin):
    """
    Class for managing OpenAI Realtime API connections and communications.
    """
    
    NO_CONNECTION_ERROR_MSG = "No connection available. Call create_connection() first."
    
    def __init__(self, 
                 system_message=SYSTEM_MESSAGE, 
                 voice=VOICE, 
                 temperature=0.8,
                 websocket_url=OPENAI_WEBSOCKET_URL,
                 headers=OPENAI_HEADERS):
        """
        Initialize the OpenAI Realtime API client.
        
        Args:
            system_message: System instructions for the assistant
            voice: Voice to use for audio responses
            temperature: Temperature setting for generation
            websocket_url: WebSocket URL for the connection
            headers: Headers for authentication
        """
        self.system_message = system_message
        self.voice = voice
        self.temperature = temperature
        self.websocket_url = websocket_url
        self.headers = headers
        self.connection = None
        self.logger.info("OpenAI Realtime API class initialized")
    
    async def create_connection(self):
        """
        Create a WebSocket connection to the OpenAI API.
        
        Returns:
            The WebSocket connection or None on error
        """
        try:
            self.logger.info("Establishing connection to %s...", self.websocket_url)
            self.connection = await websockets.connect(
                self.websocket_url,
                extra_headers=self.headers
            )
            self.logger.info("Connection successfully established!")
            return self.connection
        except Exception as e:
            self.logger.error("Connection error: %s", e)
            return None
    
    async def initialize_session(self):
        """
        Initialize a session with the OpenAI API.
        
        Returns:
            True on success, False on error
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return False
        
        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "voice": self.voice,
                "instructions": self.system_message,
                "modalities": ["text", "audio"],
                "temperature": self.temperature,
            }
        }
        
        try:
            self.logger.info('Sending session update...')
            await self.connection.send(json.dumps(session_update))
            self.logger.info('Session update sent successfully')
            return True
        except Exception as e:
            self.logger.error("Error initializing session: %s", e)
            return False
    
    async def send_audio(self, mic_stream):
        """
        Send audio data from the microphone to the OpenAI API.
        
        Args:
            mic_stream: A MicrophoneStream object that provides audio data
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return
        
        try:
            self.logger.info("Starting audio transmission...")
            audio_chunks_sent = 0
            
            while mic_stream.is_active:
                data = mic_stream.read_chunk()
                if not data:
                    await asyncio.sleep(0.01)
                    continue
                    
                base64_audio = base64.b64encode(data).decode('utf-8')
                
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio
                }
                
                await self.connection.send(json.dumps(audio_append))
                audio_chunks_sent += 1
                
                if audio_chunks_sent % 100 == 0:
                    self.logger.debug("Audio chunks sent: %d", audio_chunks_sent)
                
                # Small pause to reduce CPU load
                await asyncio.sleep(0.01)
                
        except Exception as e:
            self.logger.error("Error sending audio: %s", e)
    
    async def process_responses(self, audio_player, handle_text=None, handle_audio=None, handle_transcript=None):
        """
        Process responses from the OpenAI API.
        
        Args:
            audio_player: An AudioPlayer object for audio playback
            handle_text: Optional function to handle text responses
            handle_audio: Optional function to handle audio responses
            handle_transcript: Optional function to handle transcript responses
        """
        if not self.connection:
            self.logger.error(self.NO_CONNECTION_ERROR_MSG)
            return
        
        try:
            self.logger.info("Starting response processing...")
            
            async for message in self.connection:
                try:
                    # Debug log with truncated message
                    self.logger.debug("Raw message received: %s...", message[:100])
                    
                    response = json.loads(message)
                    
                    # Check if response is actually a dictionary
                    if not isinstance(response, dict):
                        self.logger.warning("Warning: Response is not a dictionary, it's %s", type(response))
                        continue
                    
                    event_type = response.get('type', '')
                    
                    # Process text response
                    if event_type == 'response.text.delta' and 'delta' in response:
                        if handle_text:
                            handle_text(response)
                        else:
                            self._default_text_handler(response)
                    
                    # Process audio response
                    elif event_type == 'response.audio.delta':
                        if handle_audio:
                            handle_audio(response, audio_player)
                        else:
                            self._default_audio_handler(response, audio_player)
                    
                    # Process transcript response
                    elif event_type == 'response.audio_transcript.delta':
                        if handle_transcript:
                            handle_transcript(response)
                        else:
                            self._default_transcript_handler(response)
                    
                    # End of response
                    elif event_type == 'response.done':
                        self.logger.info("Response completed")
                    
                    # Log important events
                    elif event_type in ['error', 'session.updated', 'session.created']:
                        self.logger.info("Event received: %s", event_type)
                        if event_type == 'error':
                            self.logger.error("API error: %s", response)
                    
                except json.JSONDecodeError:
                    self.logger.warning("Warning: Received non-JSON message from server")
                
        except Exception as e:
            self.logger.error("Error processing responses: %s", e)
            self.logger.error(traceback.format_exc())
    
    def _default_text_handler(self, response):
        """Default handler for text responses"""
        if not isinstance(response.get('delta'), dict):
            return
            
        text = response['delta'].get('text', '')
        if text:
            print(f"AI: {text}", end="", flush=True)
    
    def _default_audio_handler(self, response, audio_player):
        """Default handler for audio responses"""
        base64_audio = response.get('delta', '')
        if not base64_audio or not isinstance(base64_audio, str):
            return
            
        audio_player.add_audio_chunk(base64_audio)
        print(".", end="", flush=True)
    
    def _default_transcript_handler(self, response):
        """Default handler for transcript responses"""
        delta = response.get('delta', '')
        if not delta:
            return
            
        response_id = response.get('response_id', 'unknown')
        print(f"\nTRANSCRIPT [{response_id[:8]}]: {delta}", flush=True)
    
    async def close(self):
        """Close the connection"""
        if not self.connection:
            return
            
        self.logger.info("Closing connection...")
        await self.connection.close()
        self.connection = None
        self.logger.info("Connection closed")
    
    async def setup_and_run(self, mic_stream, audio_player, handle_text=None, handle_audio=None, handle_transcript=None):
        """
        Set up the connection and run the main loop.
        
        Args:
            mic_stream: A MicrophoneStream object for audio input
            audio_player: An AudioPlayer object for audio playback
            handle_text: Optional function to handle text responses
            handle_audio: Optional function to handle audio responses
            handle_transcript: Optional function to handle transcript responses
            
        Returns:
            True on successful execution, False on error
        """
        # Establish connection
        if not await self.create_connection():
            return False
        
        # Initialize session
        if not await self.initialize_session():
            await self.close()
            return False
        
        try:
            await asyncio.gather(
                self.send_audio(mic_stream),
                self.process_responses(audio_player, handle_text, handle_audio, handle_transcript)
            )
            return True
        except asyncio.CancelledError:
            self.logger.info("Tasks were cancelled")
            return True
        except Exception as e:
            self.logger.error("Error in main loop: %s", e)
            self.logger.error(traceback.format_exc())
            return False
        finally:
            await self.close()