import base64
import threading
import queue
import os
import traceback
from typing import override

import numpy as np

import pyaudio
import pygame

from realtime.config import FORMAT, CHANNELS, CHUNK, RATE
from resources.audio.audio_player_base import AudioPlayer
from utils.event_bus import EventBus, EventType
from utils.logging_mixin import LoggingMixin


class PyAudioPlayer(AudioPlayer, LoggingMixin):
    """PyAudio implementation of the AudioPlayerBase class with sound file playback"""

    @override
    def __init__(self, sounds_dir="sounds"):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.player_thread = None
        self.sounds_dir = sounds_dir
        self.current_audio_data = bytes()
        self.volume = 1.0
        self.is_busy = False
        self.event_bus = EventBus()

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

    @override
    def clear_queue_and_stop(self):
        """
        Stop the current audio playback and clear the audio queue,
        but keep the stream and thread alive for future audio.
        """
        self.logger.info("Speech started — clearing queue.")

        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

        if self.stream and self.stream.is_active():
            try:
                self.stream.stop_stream()
                self.stream.start_stream()
            except Exception as e:
                self.logger.error("Error while pausing/resuming audio stream: %s", e)
                self._recreate_audio_stream()

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
            if self.stream:
                self.stream.close()

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
                # Get the next audio chunk
                chunk = self._get_next_audio_chunk()
                if not chunk:
                    continue

                # Process the chunk
                self._process_audio_chunk(chunk)

                # Mark task as done and check queue state
                self.audio_queue.task_done()
                self._check_queue_state()

            except queue.Empty:
                continue
            except Exception as e:
                self._handle_playback_error(e)

    def _get_next_audio_chunk(self):
        """Get the next audio chunk from the queue"""
        if self.audio_queue.empty() and not self.is_busy:
            try:
                return self.audio_queue.get(timeout=0.5)
            except queue.Empty:
                return None
        else:
            return self.audio_queue.get(timeout=0.5)

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
        self.stream.write(adjusted_chunk)

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
