import base64
import threading
import queue
import os
from typing import override

import pyaudio
import pygame

from realtime.config import FORMAT, CHANNELS, CHUNK, RATE
from realtime.audio.base import AudioPlayerBase
from utils.logging_mixin import LoggingMixin
from utils.singleton_decorator import singleton


@singleton
class PyAudioPlayer(AudioPlayerBase, LoggingMixin):
    """PyAudio implementation of the AudioPlayerBase class with sound file playback"""

    def __init__(self, sounds_dir="sounds"):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.player_thread = None
        self.sounds_dir = sounds_dir

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
        Stop the current audio stream immediately and clear the audio queue.
        """
        self.logger.info("Speech started — clearing queue and stopping playback.")

        self.is_playing = False

        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                self.logger.error("Error closing stream: %s", e)
            finally:
                self.stream = None

        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

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
                    self.stream.write(chunk)
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error("Error playing audio: %s", e)

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
        self.logger.error("Audio player stopped")

    @override
    def play_sound(self, sound_name: str) -> bool:
        """
        Play a sound file asynchronously.

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

            threading.Thread(
                target=self.play_sound_blocking, args=(sound_name,), daemon=True
            ).start()

            return True

        except Exception as e:
            self.logger.error("Error starting sound playback %s: %s", sound_name, e)
            return False

    @override
    def play_sound_blocking(self, sound_name: str) -> bool:
        """
        Play an MP3 sound file and wait for it to complete.

        Args:
            sound_name: Name of the sound file (with or without .mp3 extension)

        Returns:
            True if playback successful, False otherwise
        """
        try:
            sound_path = self._get_sound_path(sound_name)

            if not os.path.exists(sound_path):
                self.logger.error("Sound file not found: %s", sound_path)
                return False

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            sound = pygame.mixer.Sound(sound_path)
            sound.play()

            while pygame.mixer.get_busy():
                pygame.time.wait(100)

            return True

        except Exception as e:
            self.logger.error("Error playing sound %s: %s", sound_name, e)
            return False
