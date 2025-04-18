import os
import json
import base64
import asyncio
import websockets
import pyaudio
import wave
import io
import threading
import queue
from dotenv import load_dotenv

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = 'alloy'
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000  # Increased from 16000 to 24000 to match OpenAI's output

# Important event types to log
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created', 'session.updated'
]

class AudioPlayer:
    """Handle playing of audio chunks received from OpenAI"""
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.player_thread = None
    
    def start(self):
        """Start the audio player thread"""
        self.is_playing = True
        # Using 24000 Hz for playback based on OpenAI's default sample rate
        # This is likely 24000 Hz for the Alloy voice
        output_rate = 24000
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=output_rate,  # Use 24000 Hz for playback
            output=True,
            frames_per_buffer=CHUNK
        )
        self.player_thread = threading.Thread(target=self._play_audio_loop)
        self.player_thread.daemon = True
        self.player_thread.start()
        print(f"Audio player started with sample rate: {output_rate} Hz")
    
    def _play_audio_loop(self):
        """Thread loop for playing audio chunks"""
        while self.is_playing:
            try:
                # Get audio chunk with a timeout to allow thread to terminate
                chunk = self.audio_queue.get(timeout=0.5)
                if chunk:
                    self.stream.write(chunk)
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error playing audio: {e}")
    
    def add_audio_chunk(self, base64_audio):
        """Add a base64 encoded audio chunk to the playback queue"""
        try:
            # Decode base64 audio to binary
            audio_data = base64.b64decode(base64_audio)
            # Uncomment to see size of each audio chunk:
            # print(f"Adding audio chunk: {len(audio_data)} bytes")
            self.audio_queue.put(audio_data)
        except Exception as e:
            print(f"Error processing audio chunk: {e}")
    
    def stop(self):
        """Stop the audio player"""
        self.is_playing = False
        if self.player_thread:
            self.player_thread.join(timeout=2.0)
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.p.terminate()
        print("Audio player stopped")


class MicrophoneStream:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_active = False
        self.audio_data = []
        
    def start_stream(self):
        """Start the microphone stream"""
        if self.stream is not None:
            self.stop_stream()
            
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        self.is_active = True
        self.audio_data = []
        print("Microphone stream started")
        
    def stop_stream(self):
        """Stop the microphone stream"""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.is_active = False
        print("Microphone stream stopped")
        
    def read_chunk(self):
        """Read a chunk of audio data from the microphone"""
        if self.stream and self.is_active:
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            self.audio_data.append(data)
            return data
        return None
    
    def cleanup(self):
        """Free resources"""
        self.stop_stream()
        self.p.terminate()


async def initialize_session(openai_ws):
    """Initialize the session with OpenAI"""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "pcm16",  # Format for input audio
            "output_audio_format": "pcm16", # Format must be a string, not an object
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Sending session update...')
    await openai_ws.send(json.dumps(session_update))


async def send_audio_to_openai(mic_stream, openai_ws):
    """Send audio data from the microphone to OpenAI"""
    try:
        while mic_stream.is_active:
            data = mic_stream.read_chunk()
            if data:
                # Encode audio data as Base64
                base64_audio = base64.b64encode(data).decode('utf-8')
                
                # Event to append audio data to the buffer
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio
                }
                await openai_ws.send(json.dumps(audio_append))
            
            # Small pause to reduce CPU load
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"Error sending audio: {e}")


async def process_openai_responses(openai_ws, audio_player):
    """Receive and process responses from OpenAI"""
    try:
        async for message in openai_ws:
            # Debug the raw message to see what we're receiving
            print(f"DEBUG - Raw message: {message[:100]}...")  # Print first 100 chars to avoid flooding console
            
            try:
                response = json.loads(message)
                # Check if response is actually a dictionary
                if not isinstance(response, dict):
                    print(f"Warning: Response is not a dictionary, it's a {type(response)}")
                    continue
                
                event_type = response.get('type', '')
                
                # Log important events
                if event_type in LOG_EVENT_TYPES:
                    print(f"Event received: {event_type}")
                    if event_type == 'error':
                        print("ERROR:", response)
                
                # Process text output
                if event_type == 'response.text.delta' and 'delta' in response:
                    if isinstance(response['delta'], dict):
                        text = response['delta'].get('text', '')
                        if text:
                            print(f"AI: {text}", end="", flush=True)
                
                # Process audio output - FIXED!
                if event_type == 'response.audio.delta':
                    # The 'delta' field directly contains the base64 audio in this event type
                    base64_audio = response.get('delta', '')
                    if base64_audio and isinstance(base64_audio, str):
                        audio_player.add_audio_chunk(base64_audio)
                        print(".", end="", flush=True)  # Indicates audio was received
                
                # End of response
                if event_type == 'response.done':
                    print("\n--- Response completed ---")
                    
            except json.JSONDecodeError:
                print("Warning: Received non-JSON message from server")
    
    except Exception as e:
        print(f"Error processing OpenAI responses: {e}")
        import traceback
        traceback.print_exc()  # Print the full stack trace for better debugging


async def main():
    """Main function"""
    # Check API key
    if not OPENAI_API_KEY:
        print("Error: OpenAI API key missing. Please specify in .env file.")
        return
    
    print("Connecting to OpenAI Realtime API...")
    
    try:
        # Establish WebSocket connection to OpenAI with the functioning URL
        async with websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            print("Connection established!")
            
            # Initialize session
            await initialize_session(openai_ws)
            
            # Create microphone stream
            mic_stream = MicrophoneStream()
            mic_stream.start_stream()
            
            # Create audio player
            audio_player = AudioPlayer()
            audio_player.start()
            
            try:
                # Run both tasks in parallel
                await asyncio.gather(
                    send_audio_to_openai(mic_stream, openai_ws),
                    process_openai_responses(openai_ws, audio_player)
                )
            except asyncio.CancelledError:
                print("Tasks cancelled")
            finally:
                mic_stream.cleanup()
                audio_player.stop()
    
    except Exception as e:
        print(f"Connection error: {e}")


if __name__ == "__main__":
    print("OpenAI Realtime API Microphone Demo")
    print("Press Ctrl+C to exit")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nUser interrupt - program terminating.")