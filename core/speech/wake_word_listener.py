import logging
import os
import threading

import numpy as np
import pvporcupine
import pyaudio


class WakeWordListener:
    def __init__(self, wakeword="picovoice", sensitivity=0.8):
        self.logger = logging.getLogger(self.__class__.__name__)

        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0")

        self.logger.info(
            "🔧 Initializing Wake Word Listener with word: %s (Sensitivity: %.1f)",
            wakeword,
            sensitivity,
        )

        access_key = os.getenv("PICO_ACCESS_KEY")
        if not access_key:
            raise ValueError("PICO_ACCESS_KEY not found in .env file")

        self.wakeword = wakeword
        self.handle = pvporcupine.create(
            access_key=access_key, keywords=[wakeword], sensitivities=[0.8]
        )

        self.pa_input = pyaudio.PyAudio()
        self.stream = self.pa_input.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=self.handle.frame_length,
            stream_callback=self._audio_callback,
        )

        self.is_listening = False
        self.should_stop = False
        self._detection_event = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio processing"""
        if self.is_listening and not self.should_stop:
            pcm = np.frombuffer(in_data, dtype=np.int16)
            keyword_index = self.handle.process(pcm)

            if keyword_index >= 0:
                self._detection_event.set()

        return (in_data, pyaudio.paContinue)

    async def listen_for_wakeword_async(self):
        """
        Asynchronous version of listen_for_wakeword that doesn't block the event loop.

        Returns:
            True if wake word was detected, False otherwise
        """
        import asyncio

        self._detection_event.clear()
        self.is_listening = True

        if not self.stream.is_active():
            self.stream.start_stream()

        while not self.should_stop:
            detected = self._detection_event.is_set()
            if detected:
                self._detection_event.clear()
                return True

            await asyncio.sleep(0.1)

        return False

    def cleanup(self):
        self.logger.info("🧹 Cleaning up Wake Word Listener...")
        self.should_stop = True
        self.is_listening = False

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pa_input:
            self.pa_input.terminate()
        if self.handle:
            self.handle.delete()

        self.logger.info("✅ Wake Word Listener successfully shut down")
