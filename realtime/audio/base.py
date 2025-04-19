from abc import ABC, abstractmethod

class AudioPlayerBase(ABC):
    """Abstract base class for audio players"""
    
    @abstractmethod
    def start(self):
        """Start the audio player"""
    
    @abstractmethod
    def add_audio_chunk(self, base64_audio):
        """Add a base64 encoded audio chunk to be played"""
    
    @abstractmethod
    def stop(self):
        """Stop the audio player and clean up resources"""


class MicrophoneBase(ABC):
    """Abstract base class for microphone input"""
    
    @abstractmethod
    def start_stream(self):
        """Start the microphone stream"""
    
    @abstractmethod
    def stop_stream(self):
        """Stop the microphone stream"""
    
    @abstractmethod
    def read_chunk(self):
        """Read a chunk of audio data from the microphone"""
    
    @abstractmethod
    def cleanup(self):
        """Clean up resources"""