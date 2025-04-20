import base64
import threading
import queue
import os
from typing import override

import numpy as np

import pyaudio
import pygame

from audio.audio_player_base import AudioPlayer
from realtime.config import FORMAT, CHANNELS, CHUNK, RATE
from utils.logging_mixin import LoggingMixin


class PyAudioPlayer(AudioPlayer, LoggingMixin):
    """PyAudio implementation of the AudioPlayerBase class with sound file playback"""

    def __init__(self, sounds_dir="sounds"):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.player_thread = None
        self.sounds_dir = sounds_dir
        self.current_audio_data = bytes()
        self.volume = 1.0

    @override
    def start(self):
        """Start the audio player thread"""
        self.is_playing = True
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
        )
        self.player_thread = threading.Thread(target=self._play_audio_loop)
        self.player_thread.daemon = True
        self.player_thread.start()
        self.logger.info("Audio player started with sample rate: %d Hz", RATE)

    def clear_queue_and_stop(self):
        """
        Stop the current audio stream and clear the audio queue.
        """
        self.logger.info("Speech started — clearing queue.")

        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

        # Restart the audio system
        self.is_playing = True
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
        )

        if not self.player_thread or not self.player_thread.is_alive():
            self.player_thread = threading.Thread(target=self._play_audio_loop)
            self.player_thread.daemon = True
            self.player_thread.start()

        self.logger.info("Audio player reset and ready.")

    def _play_audio_loop(self):
        """Thread loop for playing audio chunks"""
        while self.is_playing:
            try:
                chunk = self.audio_queue.get(timeout=0.5)
                if chunk:
                    adjusted_chunk = self._adjust_volume(chunk)
                    # Store the current chunk
                    self.current_audio_data = adjusted_chunk
                    self.stream.write(adjusted_chunk)
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error("Error playing audio: %s", e)

    def _adjust_volume(self, audio_chunk):
        """Adjust the volume of an audio chunk"""
        if abs(self.volume - 1.0) < 1e-6:
            return audio_chunk

        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)

            # Apply volume adjustment
            adjusted_array = (audio_array * self.volume).astype(np.int16)

            # Convert back to bytes
            return adjusted_array.tobytes()
        except Exception as e:
            self.logger.error("Error adjusting volume: %s", e)
            return audio_chunk

    @override
    def add_audio_chunk(self, base64_audio):
        """Add a base64 encoded audio chunk to the playback queue"""
        try:
            audio_data = base64.b64decode(base64_audio)
            self.audio_queue.put(audio_data)
        except Exception as e:
            self.logger.error("Error processing audio chunk: %s", e)

    @override
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
        self.logger.info("Audio player stopped")

    @override
    def play_sound(self, sound_name: str) -> bool:
        """
        Play a sound file asynchronously (non-blocking).

        Args:
            sound_name: Name of the sound file (with or without .mp3 extension)

        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            sound_path = self._get_sound_path(sound_name)

            if not os.path.exists(sound_path):
                self.logger.warning("Sound file not found: %s", sound_path)
                return False

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            # Get sound object and adjust volume
            sound = pygame.mixer.Sound(sound_path)
            sound.set_volume(self.volume)
            sound.play()

            return True

        except Exception as e:
            self.logger.error("Error playing sound %s: %s", sound_name, e)
            return False

    @override
    def set_volume_level(self, volume: float):
        """
        Set the volume level for the audio player.

        Args:
            volume: Volume level between 0.0 (mute) and 1.0 (maximum)
        """
        self.volume = max(0.0, min(1.0, volume))
        self.logger.info("Volume set to: %.2f", self.volume)

        # Update pygame mixer volume if initialized
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(self.volume)

        return self.volume

    @override
    def get_volume_level(self) -> float:
        """
        Get the current volume level of the audio player.

        Returns:
            The current volume level between 0.0 and 1.0
        """
        return self.volume
