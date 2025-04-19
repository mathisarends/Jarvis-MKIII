import base64
import threading
import queue
from typing import override
import pyaudio
from realtime.config import FORMAT, CHANNELS, CHUNK
from realtime.audio.base import AudioPlayerBase

class PyAudioPlayer(AudioPlayerBase):
    """PyAudio implementation of the AudioPlayerBase class"""
    def __init__(self, sample_rate=24000):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.player_thread = None
        self.sample_rate = sample_rate
    
    def start(self):
        """Start the audio player thread"""
        self.is_playing = True
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=CHUNK
        )
        self.player_thread = threading.Thread(target=self._play_audio_loop)
        self.player_thread.daemon = True
        self.player_thread.start()
        print(f"Audio player started with sample rate: {self.sample_rate} Hz")
    
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


# Example of an alternative implementation (not functional, just for illustration)
class FileAudioPlayer(AudioPlayerBase):
    """Implementation that saves audio chunks to a file instead of playing them"""
    def __init__(self, output_file="output.wav"):
        self.output_file = output_file
        self.audio_chunks = []
        self.is_active = False
    
    def start(self):
        self.is_active = True
        self.audio_chunks = []
        print(f"File audio player started, will save to {self.output_file}")
    
    def add_audio_chunk(self, base64_audio):
        if self.is_active:
            audio_data = base64.b64decode(base64_audio)
            self.audio_chunks.append(audio_data)
    
    def stop(self):
        self.is_active = False
        # Here you would implement saving all chunks to a WAV file
        print(f"File audio player stopped, saved {len(self.audio_chunks)} chunks")