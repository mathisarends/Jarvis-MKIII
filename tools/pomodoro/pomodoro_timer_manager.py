import random
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from audio.audio_player_factory import AudioPlayerFactory
from utils.logging_mixin import LoggingMixin
from utils.singleton_meta_class import SingletonMetaClass

class PomodoroTimerManager(LoggingMixin, metaclass=SingletonMetaClass):
    def __init__(self):
        self.duration_seconds = 0
        self.is_running = False
        self.start_time = None
        self.timer_thread = None
        self.end_time = None
        self.audio_player = AudioPlayerFactory.get_shared_instance()

    def start_timer(self, duration_minutes: int) -> bool:
        if self.is_running:
            self.logger.info("Ein Timer läuft bereits!")
            return False

        self.duration_seconds = duration_minutes * 60
        self.is_running = True
        self.start_time = time.time()
        self.end_time = datetime.now() + timedelta(minutes=duration_minutes)

        # Cancel any existing thread
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.cancel()

        self.timer_thread = threading.Timer(self.duration_seconds, self._play_alarm)
        self.timer_thread.daemon = True
        self.timer_thread.start()

        self.logger.info("Pomodoro-Timer gestartet für %d Minuten.", duration_minutes)
        return True

    def stop_timer(self) -> bool:
        if not self.is_running:
            self.logger.info("Kein Timer aktiv, der gestoppt werden könnte.")
            return False

        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.cancel()

        self.is_running = False
        self.logger.info("Pomodoro-Timer wurde gestoppt.")
        return True

    def _play_alarm(self) -> None:
        if not self.is_running:
            return

        self.logger.info("Zeit ist um! Pomodoro beendet.")

        random_number = random.randint(1, 7)
        sound_file = f"pomodoro_phrases/tts_pomodoro_phrases_{random_number}"
        self.audio_player.play_sound(sound_file)

        self.is_running = False

    def get_remaining_minutes(self) -> int:
        """
        Gibt die verbleibende Zeit des Timers in Minuten zurück.

        Returns:
            int: Verbleibende Minuten oder 0, wenn kein Timer aktiv ist
        """
        if not self.is_running:
            return 0

        elapsed_time = time.time() - self.start_time
        remaining_time = max(0, self.duration_seconds - elapsed_time)
        minutes = int(remaining_time // 60)

        return minutes

    def get_end_time_formatted(self) -> Optional[str]:
        """
        Get the expected end time of the timer.

        Returns:
            Formatted end time or None if no timer is running
        """
        if not self.is_running or not self.end_time:
            return None

        return self.end_time.strftime("%H:%M")
