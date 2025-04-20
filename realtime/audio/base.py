from abc import ABC, abstractmethod
import os


class AudioPlayerBase(ABC):
    """Abstract base class for audio players"""

    sounds_dir = "sounds"

    @abstractmethod
    def start(self):
        """Start the audio player"""

    @abstractmethod
    def clear_queue_and_stop(self):
        """Stop the current audio stream immediately and clear the audio queue."""

    @abstractmethod
    def add_audio_chunk(self, base64_audio):
        """Add a base64 encoded audio chunk to be played"""

    @abstractmethod
    def stop(self):
        """Stop the audio player and clean up resources"""

    @abstractmethod
    def play_sound(self, sound_name: str) -> bool:
        """
        Play a sound file by name.
        """

    @abstractmethod
    def play_sound_blocking(self, sound_name: str) -> bool:
        """
        Play a sound file and wait for it to finish.
        """

    def _get_sound_path(self, sound_name: str) -> str:
        """Get the full path to a sound file"""
        if sound_name.endswith(".mp3"):
            filename = sound_name
        else:
            filename = f"{sound_name}.mp3"

        return os.path.join(self.sounds_dir, filename)
