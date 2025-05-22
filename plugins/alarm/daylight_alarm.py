import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from core.audio.audio_player_factory import AudioPlayerFactory
from plugins.alarm.alarm_sound_manager import (
    AlarmSoundManager,
    SoundCategory,
    SoundOption,
)
from plugins.alarm.sunrise_controller import SunriseConfig, SunriseController
from shared.logging_mixin import LoggingMixin
from shared.singleton_meta_class import SingletonMetaClass


class AlarmStage(Enum):
    """Alarm stages"""

    WAKE_UP = "wake_up"
    GET_UP = "get_up"


@dataclass
class AlarmSoundConfig:
    """Configuration for alarm sounds"""

    wake_up_sound_id: str = "wake_up_sounds/wake-up-focus"
    get_up_sound_id: str = "get_up_sounds/get-up-blossom"
    volume: float = 1.0


@dataclass
class AlarmConfig:
    """Configuration for a single alarm"""

    wake_up_time: float
    wake_up_timer_duration: int
    sounds: AlarmSoundConfig = field(default_factory=AlarmSoundConfig)
    active: bool = True
    scheduled: bool = False
    use_sunrise: bool = True
    max_brightness: float = 75.0
    scheduled_threads: List[threading.Timer] = field(default_factory=list)


class AlarmManager(LoggingMixin, metaclass=SingletonMetaClass):
    """
    Manages alarms with an efficient scheduling implementation.
    """

    def __init__(self):
        self._scheduled_alarms: Dict[str, AlarmConfig] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_lock: threading.Lock = threading.Lock()
        self._running: bool = False
        self._callbacks: Dict[str, List[Callable[[], Any]]] = {}
        self._sound_manager = AlarmSoundManager()

        # Initialize the external sunrise controller
        self._sunrise_controller = SunriseController.get_instance(
            SunriseConfig(
                scene_name="Majestätischer Morgen",
                room_name="Zimmer 1",
                start_brightness_percent=0.01,
                max_brightness_percent=75.0,
            )
        )

    def schedule_alarm(
        self,
        alarm_id: str,
        time_str: str,
        wake_up_timer_duration: int = 540,
        use_sunrise: bool = True,
        max_brightness: float = 75.0,
        wake_up_sound_id: Optional[str] = None,
        get_up_sound_id: Optional[str] = None,
        volume: float = 1.0,
    ) -> None:
        """
        Schedules an alarm for a specific time.

        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
            wake_up_timer_duration: Time in seconds between first and second alarm (default: 9 minutes)
            use_sunrise: Whether to enable the sunrise simulation
            max_brightness: Maximum brightness for sunrise (0-100)
            wake_up_sound_id: Sound ID for the wake-up alarm (default: use default sound)
            get_up_sound_id: Sound ID for the get-up alarm (default: use default sound)
            volume: Volume level for alarm sounds (0.0 to 1.0)
        """
        with self._scheduler_lock:
            alarm_time = self._parse_time(time_str)

            # Create sound configuration
            sound_config = AlarmSoundConfig(
                wake_up_sound_id=wake_up_sound_id
                or AlarmSoundConfig().wake_up_sound_id,
                get_up_sound_id=get_up_sound_id or AlarmSoundConfig().get_up_sound_id,
                volume=volume,
            )

            alarm_config = AlarmConfig(
                wake_up_time=alarm_time,
                wake_up_timer_duration=wake_up_timer_duration,
                sounds=sound_config,
                use_sunrise=use_sunrise,
                max_brightness=max_brightness,
            )

            self._scheduled_alarms[alarm_id] = alarm_config

            self._ensure_scheduler_running()

            self._schedule_alarm_execution(alarm_id)

    def cancel_alarm(self, alarm_id: str) -> None:
        """Cancels an active alarm."""
        with self._scheduler_lock:
            if alarm_id in self._scheduled_alarms:
                config = self._scheduled_alarms[alarm_id]

                for thread in config.scheduled_threads:
                    if thread.is_alive():
                        config.active = False

                # Stop any running sunrise
                self._sunrise_controller.stop_sunrise()

                del self._scheduled_alarms[alarm_id]

    def get_wake_up_sound_options(self):
        """Get all available wake-up sound options."""
        return self._sound_manager.get_wake_up_sound_options()

    def get_get_up_sound_options(self):
        """Get all available get-up sound options."""
        return self._sound_manager.get_get_up_sound_options()

    def _parse_time(self, time_str: str) -> float:
        """Converts a time string in 'HH:MM' format to a Unix timestamp."""
        hour, minute = map(int, time_str.split(":"))
        now = datetime.now()
        alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if alarm_time <= now:
            alarm_time += timedelta(days=1)

        return alarm_time.timestamp()

    def _ensure_scheduler_running(self) -> None:
        """Ensures that the scheduler thread is running."""
        if not self._scheduler_thread or not self._scheduler_thread.is_alive():
            self._running = True
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self._scheduler_thread.start()

    def _scheduler_loop(self) -> None:
        """
        Main loop of the scheduler that regularly checks for alarms to be scheduled.
        This loop only checks infrequently (every 60 seconds) as the actual execution
        is done using timer threads.
        """
        while self._running:
            with self._scheduler_lock:
                for alarm_id, config in self._scheduled_alarms.items():
                    if not config.scheduled and config.active:
                        self._schedule_alarm_execution(alarm_id)

            time.sleep(60)

    def _schedule_alarm_execution(self, alarm_id: str) -> None:
        """Schedules the execution of an alarm using timers."""
        if alarm_id not in self._scheduled_alarms:
            return

        config = self._scheduled_alarms[alarm_id]
        if not config.active:
            return

        config.scheduled = True

        wake_up_time = config.wake_up_time
        delay = max(0, wake_up_time - time.time())

        wake_up_thread = threading.Timer(
            delay,
            self._execute_alarm,
            args=[config.sounds.wake_up_sound_id, alarm_id, AlarmStage.WAKE_UP],
        )
        wake_up_thread.daemon = True
        wake_up_thread.start()

        get_up_time = wake_up_time + config.wake_up_timer_duration
        delay_get_up = max(0, get_up_time - time.time())

        get_up_thread = threading.Timer(
            delay_get_up,
            self._execute_alarm,
            args=[config.sounds.get_up_sound_id, alarm_id, AlarmStage.GET_UP],
        )
        get_up_thread.daemon = True
        get_up_thread.start()

        config.scheduled_threads = [wake_up_thread, get_up_thread]

        print(
            f"Alarm scheduled: WAKE_UP in {delay:.1f} seconds, GET_UP in {delay_get_up:.1f} seconds"
        )

    def _execute_alarm(self, sound_id: str, alarm_id: str, stage: AlarmStage) -> None:
        """Executes an alarm and plays the corresponding sound."""
        if alarm_id not in self._scheduled_alarms:
            return

        config = self._scheduled_alarms[alarm_id]

        if not config.active:
            return

        self.logger.info(f"Alarm triggered: {stage.value} with sound {sound_id}")

        if stage == AlarmStage.WAKE_UP and config.use_sunrise:
            self._sunrise_controller.start_sunrise(
                duration_seconds=config.wake_up_timer_duration,
                max_brightness=config.max_brightness,
            )

        # If no specific callbacks registered, play the sound directly with the specified volume
        if sound_id not in self._callbacks or not self._callbacks[sound_id]:
            self.logger.info(
                f"Playing sound {sound_id} with volume {config.sounds.volume:.2f}"
            )
            AudioPlayerFactory.get_shared_instance().play_sound(
                sound_id, volume=config.sounds.volume
            )


@dataclass
class GlobalAlarmSettings:
    """Global settings for all alarms"""

    wake_up_timer_duration: int = 540  # 9 minutes, always fixed
    use_sunrise: bool = True  # Always enabled
    max_brightness: float = 75.0  # Global brightness for all alarms
    volume: float = 0.5  # Global volume for all alarms
    wake_up_sound_id: str = "wake_up_sounds/wake-up-focus"  # Global wake-up sound
    get_up_sound_id: str = "get_up_sounds/get-up-blossom"  # Global get-up sound


class AlarmSystem(LoggingMixin, metaclass=SingletonMetaClass):
    """
    Simplified alarm system with global settings.
    All alarms use the same config, only differ by time.
    """

    def __init__(self):
        self._alarm_manager: AlarmManager = AlarmManager.get_instance()
        self._settings: GlobalAlarmSettings = GlobalAlarmSettings()
        self._active_alarms: Set[str] = set()
        self._sound_manager = AlarmSoundManager()

    @property
    def wake_up_timer_duration(self) -> int:
        """Returns the fixed duration between first and second alarm (9 minutes)."""
        return self._settings.wake_up_timer_duration

    @wake_up_timer_duration.setter
    def wake_up_timer_duration(self, duration: int) -> None:
        """Sets the duration - but it's always 9 minutes for consistency."""
        self.logger.warning(
            "Wake-up timer duration is fixed at 9 minutes (540 seconds)"
        )

    @property
    def max_brightness(self) -> float:
        """Returns the global maximum brightness for all alarms."""
        return self._settings.max_brightness

    @property
    def volume(self) -> float:
        """Returns the global volume level for all alarms."""
        return self._settings.volume

    @property
    def wake_up_sound_id(self) -> str:
        """Returns the global wake-up sound for all alarms."""
        return self._settings.wake_up_sound_id

    @property
    def get_up_sound_id(self) -> str:
        """Returns the global get-up sound for all alarms."""
        return self._settings.get_up_sound_id

    def set_max_brightness(self, brightness: float) -> None:
        """Set the global maximum brightness for all alarms."""
        if brightness <= 0 or brightness > 100:
            raise ValueError("Brightness must be between 0 and 100.")

        old_value = self._settings.max_brightness
        self._settings.max_brightness = brightness

        self.logger.info(f"Global brightness updated: {old_value} → {brightness}")

    def set_volume(self, volume: float) -> None:
        """Set the global volume level for all alarms."""
        if volume < 0.0 or volume > 1.0:
            raise ValueError("Volume must be between 0.0 and 1.0.")

        old_value = self._settings.volume
        self._settings.volume = volume

        self.logger.info(f"Global volume updated: {old_value} → {volume}")

    def set_wake_up_sound(self, sound_id: str) -> None:
        """Set the global wake-up sound for all alarms."""
        if not sound_id or not sound_id.strip():
            raise ValueError("Sound ID cannot be empty.")

        old_value = self._settings.wake_up_sound_id
        self._settings.wake_up_sound_id = sound_id

        self.logger.info(f"Global wake-up sound updated: {old_value} → {sound_id}")

    def set_get_up_sound(self, sound_id: str) -> None:
        """Set the global get-up sound for all alarms."""
        if not sound_id or not sound_id.strip():
            raise ValueError("Sound ID cannot be empty.")

        old_value = self._settings.get_up_sound_id
        self._settings.get_up_sound_id = sound_id

        self.logger.info(f"Global get-up sound updated: {old_value} → {sound_id}")

    def get_global_settings(self) -> dict:
        """Get all global settings as a dictionary (useful for API responses)."""
        return {
            "wake_up_timer_duration": self._settings.wake_up_timer_duration,
            "use_sunrise": self._settings.use_sunrise,
            "max_brightness": self._settings.max_brightness,
            "volume": self._settings.volume,
            "wake_up_sound_id": self._settings.wake_up_sound_id,
            "get_up_sound_id": self._settings.get_up_sound_id,
        }

    def update_global_settings(self, settings: dict) -> None:
        """Update multiple global settings at once."""
        if "max_brightness" in settings:
            self.set_max_brightness(settings["max_brightness"])

        if "volume" in settings:
            self.set_volume(settings["volume"])

        if "wake_up_sound_id" in settings:
            self.set_wake_up_sound(settings["wake_up_sound_id"])

        if "get_up_sound_id" in settings:
            self.set_get_up_sound(settings["get_up_sound_id"])

    def get_wake_up_sound_options(self):
        """Get all available wake-up sound options."""
        return self._alarm_manager.get_wake_up_sound_options()

    def get_get_up_sound_options(self):
        """Get all available get-up sound options."""
        return self._alarm_manager.get_get_up_sound_options()

    def schedule_alarm(self, alarm_id: str, time_str: str) -> None:
        """
        Schedule an alarm with global settings.
        All alarms use the same config, only time differs.

        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
        """
        self.logger.info(
            "Scheduling alarm '%s' at %s with global settings:", alarm_id, time_str
        )
        self.logger.info(
            "  - Wake-up timer duration: %d seconds (fixed)",
            self._settings.wake_up_timer_duration,
        )
        self.logger.info("  - Wake-up sound: %s", self._settings.wake_up_sound_id)
        self.logger.info("  - Get-up sound: %s", self._settings.get_up_sound_id)
        self.logger.info("  - Sunrise: %s (always enabled)", "Enabled")
        self.logger.info(
            "  - Maximum brightness: %.1f%%", self._settings.max_brightness
        )
        self.logger.info("  - Volume: %.2f", self._settings.volume)

        # Use global settings for all parameters
        self._alarm_manager.schedule_alarm(
            alarm_id=alarm_id,
            time_str=time_str,
            wake_up_timer_duration=self._settings.wake_up_timer_duration,  # Always 9 minutes
            use_sunrise=self._settings.use_sunrise,  # Always True
            max_brightness=self._settings.max_brightness,  # Global setting
            wake_up_sound_id=self._settings.wake_up_sound_id,  # Global setting
            get_up_sound_id=self._settings.get_up_sound_id,  # Global setting
            volume=self._settings.volume,  # Global setting
        )

        self._active_alarms.add(alarm_id)
        self.logger.info(
            "Alarm '%s' successfully scheduled with global config", alarm_id
        )

    def cancel_alarm(self, alarm_id: str) -> None:
        """Cancel an active alarm."""
        self.logger.info(f"Canceling alarm: {alarm_id}")
        self._alarm_manager.cancel_alarm(alarm_id)
        self._active_alarms.discard(alarm_id)
        self.logger.info(f"Alarm '{alarm_id}' successfully canceled")

    def get_active_alarms(self) -> Set[str]:
        """Get all active alarm IDs."""
        return self._active_alarms.copy()

    def has_active_alarms(self) -> bool:
        """Check if there are any active alarms."""
        return len(self._active_alarms) > 0

    def get_alarm_count(self) -> int:
        """Get the number of active alarms."""
        return len(self._active_alarms)
