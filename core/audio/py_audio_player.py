import base64
import time
import threading
import queue
import os
import traceback
from typing import override

import numpy as np

import pyaudio
import pygame

from resources.config import FORMAT, CHANNELS, CHUNK, RATE
from core.audio.audio_player_base import AudioPlayer
from shared.event_bus import EventBus, EventType
from shared.logging_mixin import LoggingMixin


class PyAudioPlayer(AudioPlayer, LoggingMixin):
    """PyAudio implementation of the AudioPlayerBase class with sound file playback"""

    @override
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.player_thread = None
        self.current_audio_data = bytes()
        self.volume = 1.0
        self.is_busy = False
        self.event_bus = EventBus()
        self.stream_lock = threading.Lock()

    @override
    def start(self):
        """Start the audio player thread"""
        self.is_playing = True
        with self.stream_lock:
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

    @override
    def clear_queue_and_stop(self):
        """
        Stop the current audio playback and clear the audio queue,
        but keep the stream and thread alive for future audio.
        """
        self.logger.info("Speech started — clearing queue.")

        # Queue leeren
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

        # Stream sofort stoppen
        with self.stream_lock:
            if self.stream and self.stream.is_active():
                try:
                    self.stream.stop_stream()
                    time.sleep(0.05)
                    self.stream.start_stream()
                except Exception as e:
                    self.logger.error(
                        "Error while pausing/resuming audio stream: %s", e
                    )
                    self._recreate_audio_stream()

        # Sofort Status zurücksetzen
        if self.is_busy:
            self.is_busy = False
            self.current_audio_data = bytes()
            self._safely_notify_playback_completed()

        self.logger.info("Audio queue cleared, stream kept alive.")

    @override
    def set_volume_level(self, volume: float):
        """
        Set the volume level for the audio player.

        Args:
            volume: Volume level between 0.0 (mute) and 1.0 (maximum)
        """
        self.volume = max(0.0, min(1.0, volume))
        self.logger.info("Volume set to: %.2f", self.volume)

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
        with self.stream_lock:
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

            sound = pygame.mixer.Sound(sound_path)
            sound.set_volume(self.volume)
            sound.play()

            return True

        except Exception as e:
            self.logger.error("Error playing sound %s: %s", sound_name, e)
            return False

    def _recreate_audio_stream(self):
        """Recreate the audio stream if there was an error"""
        try:
            with self.stream_lock:
                if self.stream:
                    try:
                        self.stream.close()
                    except Exception as e:
                        self.logger.warning(
                            "Error closing stream during recreation: %s", e
                        )

                try:
                    self.stream = self.p.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        output=True,
                        frames_per_buffer=CHUNK,
                    )
                except Exception as e:
                    self.logger.error("Failed to open new stream: %s", e)
                    # Versuche PyAudio neu zu initialisieren
                    self.p.terminate()
                    self.p = pyaudio.PyAudio()
                    self.stream = self.p.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        output=True,
                        frames_per_buffer=CHUNK,
                    )
        except Exception as e:
            self.logger.error("Failed to recreate audio stream: %s", e)

    def _play_audio_loop(self):
        """Thread loop for playing audio chunks"""
        while self.is_playing:
            try:
                chunk = self._get_next_audio_chunk()
                if not chunk:
                    continue

                self._process_audio_chunk(chunk)

                self.audio_queue.task_done()
                self._check_queue_state()

            except queue.Empty:
                continue
            except Exception as e:
                self._handle_playback_error(e)

    def _get_next_audio_chunk(self):
        """Get the next audio chunk from the queue"""
        try:
            # Kürzeres Timeout für schnelleres Reagieren
            return self.audio_queue.get(timeout=0.1)
        except queue.Empty:
            return None

    def _process_audio_chunk(self, chunk):
        """Process and play an audio chunk"""
        if not chunk:
            return

        was_busy = self.is_busy
        self.is_busy = True

        if not was_busy:
            self.event_bus.publish_async_from_thread(
                EventType.ASSISTANT_STARTED_RESPONDING
            )
            self.logger.debug("Audio playback started")

        adjusted_chunk = self._adjust_volume(chunk)
        self.current_audio_data = adjusted_chunk

        try:
            with self.stream_lock:
                if self.stream and self.stream.is_active():
                    self.stream.write(adjusted_chunk)
                else:
                    self.logger.warning("Stream not active, skipping chunk")
                    self._recreate_audio_stream()
        except OSError as e:
            self.logger.error("Stream write error: %s", e)
            self._recreate_audio_stream()

            if self.is_playing:
                self.audio_queue.put(chunk)
        except Exception as e:
            self.logger.error("Unexpected error in stream write: %s", e)
            self._recreate_audio_stream()

    def _check_queue_state(self):
        """Check the queue state and notify if playback is completed"""
        if self.audio_queue.empty() and self.is_busy:
            self.is_busy = False
            self.current_audio_data = bytes()
            self._safely_notify_playback_completed()

    def _handle_playback_error(self, error):
        """Handle any errors during playback"""
        error_traceback = traceback.format_exc()
        self.logger.error(
            "Error playing audio: %s\nTraceback:\n%s", error, error_traceback
        )

        # Versuche den Stream neu zu erstellen, wenn ein Fehler auftritt
        self._recreate_audio_stream()

        if self.is_busy:
            self.is_busy = False
            try:
                self.event_bus.publish(EventType.ASSISTANT_COMPLETED_RESPONDING)
            except Exception as e:
                self.logger.error("Failed to publish playback complete event: %s", e)

    def _adjust_volume(self, audio_chunk):
        """Adjust the volume of an audio chunk"""
        if abs(self.volume - 1.0) < 1e-6:
            return audio_chunk

        try:
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            adjusted_array = (audio_array * self.volume).astype(np.int16)
            return adjusted_array.tobytes()
        except Exception as e:
            self.logger.error("Error adjusting volume: %s", e)
            return audio_chunk

    def _get_sound_path(self, sound_name):
        """Get the full path to a sound file"""
        if not sound_name.endswith(".mp3"):
            sound_name += ".mp3"
        return os.path.join(self.sounds_dir, sound_name)

    def _safely_notify_playback_completed(self):
        """Send playback completed event in a thread-safe way"""
        try:
            self.event_bus.publish_async_from_thread(
                EventType.ASSISTANT_COMPLETED_RESPONDING
            )
            self.logger.debug("Audio playback stopped (event sent)")
        except Exception as e:
            self.logger.warning("Failed to send event from thread: %s", e)
            try:
                self.event_bus.publish(EventType.ASSISTANT_COMPLETED_RESPONDING)
                self.logger.debug("Audio playback stopped (event sent via fallback)")
            except Exception as e2:
                self.logger.error("Failed to send event via fallback: %s", e2)
