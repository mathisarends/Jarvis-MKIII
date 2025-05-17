import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from core.audio.audio_player_factory import AudioPlayerFactory
from plugins.alarm.alarm_sound_manager import (AlarmSoundManager,
                                               SoundCategory, SoundOption)
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
    wake_up_sound_id: str = "wake_up_sounds/wake-up-focus"  # Default wake-up sound
    get_up_sound_id: str = "get_up_sounds/get-up-blossom"  # Default get-up sound
    volume: float = 1.0  # Default full volume (0.0 to 1.0)


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
                wake_up_sound_id=wake_up_sound_id or AlarmSoundConfig().wake_up_sound_id,
                get_up_sound_id=get_up_sound_id or AlarmSoundConfig().get_up_sound_id,
                volume=volume
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

    def schedule_random_alarm(
        self,
        alarm_id: str,
        time_str: str,
        wake_up_timer_duration: int = 540,
        use_sunrise: bool = True,
        max_brightness: float = 75.0,
        volume: float = 1.0,
    ) -> None:
        """
        Schedules an alarm with randomly selected sounds.

        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
            wake_up_timer_duration: Time in seconds between first and second alarm
            use_sunrise: Whether to enable the sunrise simulation
            max_brightness: Maximum brightness for sunrise (0-100)
            volume: Volume level for alarm sounds (0.0 to 1.0)
        """
        # Get all available sound options
        wake_up_options = self._sound_manager.get_wake_up_sound_options()
        get_up_options = self._sound_manager.get_get_up_sound_options()

        # Select random sounds if options are available
        wake_up_sound_id = random.choice(wake_up_options).value if wake_up_options else AlarmSoundConfig().wake_up_sound_id
        get_up_sound_id = random.choice(get_up_options).value if get_up_options else AlarmSoundConfig().get_up_sound_id

        # Schedule the alarm with random sounds
        self.schedule_alarm(
            alarm_id=alarm_id,
            time_str=time_str,
            wake_up_timer_duration=wake_up_timer_duration,
            use_sunrise=use_sunrise,
            max_brightness=max_brightness,
            wake_up_sound_id=wake_up_sound_id,
            get_up_sound_id=get_up_sound_id,
            volume=volume
        )

        print(f"Random alarm scheduled with sounds: Wake-Up: {wake_up_sound_id}, Get-Up: {get_up_sound_id}")

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

    def register_callback(self, sound_id: str, callback: Callable[[], Any]) -> None:
        """
        Registers a callback for a specific sound.

        Args:
            sound_id: ID of the sound
            callback: Function to call when the sound is played
        """
        if sound_id not in self._callbacks:
            self._callbacks[sound_id] = []

        self._callbacks[sound_id].append(callback)

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
            self.logger.info(f"Playing sound {sound_id} with volume {config.sounds.volume:.2f}")
            AudioPlayerFactory.get_shared_instance().play_sound(sound_id, volume=config.sounds.volume)

@dataclass
class AlarmSettings:
    """Settings for the alarm system"""
    wake_up_timer_duration: int = 540
    use_sunrise: bool = True
    max_brightness: float = 75.0
    volume: float = 1.0
    wake_up_sound_id: Optional[str] = None
    get_up_sound_id: Optional[str] = None


class AlarmSystem(LoggingMixin, metaclass=SingletonMetaClass):
    """
    Main class of the alarm system that integrates AlarmManager and AudioPlayer.
    """

    def __init__(self, wake_up_timer_duration: int = 30, use_sunrise: bool = True):
        self._alarm_manager: AlarmManager = AlarmManager.get_instance()
        self._settings: AlarmSettings = AlarmSettings(
            wake_up_timer_duration=wake_up_timer_duration, 
            use_sunrise=use_sunrise
        )
        self._active_alarms: Set[str] = set()
        self._sound_manager = AlarmSoundManager()

    @property
    def wake_up_timer_duration(self) -> int:
        """Returns the current duration between first and second alarm in seconds."""
        return self._settings.wake_up_timer_duration

    @wake_up_timer_duration.setter
    def wake_up_timer_duration(self, duration: int) -> None:
        """Sets the duration between first and second alarm in seconds."""
        if duration <= 0:
            raise ValueError("The wake up timer duration must be greater than 0.")
        self._settings.wake_up_timer_duration = duration

    @property
    def use_sunrise(self) -> bool:
        """Returns whether sunrise is enabled."""
        return self._settings.use_sunrise

    @use_sunrise.setter
    def use_sunrise(self, enabled: bool) -> None:
        """Enables or disables the sunrise feature."""
        self._settings.use_sunrise = enabled

    @property
    def max_brightness(self) -> float:
        """Returns the maximum brightness for sunrise."""
        return self._settings.max_brightness

    @max_brightness.setter
    def max_brightness(self, brightness: float) -> None:
        """Sets the maximum brightness for sunrise."""
        if brightness <= 0 or brightness > 100:
            raise ValueError("Brightness must be between 0 and 100.")
        self._settings.max_brightness = brightness

    @property
    def volume(self) -> float:
        """Returns the volume level for alarms."""
        return self._settings.volume

    @volume.setter
    def volume(self, level: float) -> None:
        """Sets the volume level for alarms."""
        if level < 0.0 or level > 1.0:
            raise ValueError("Volume must be between 0.0 and 1.0.")
        self._settings.volume = level

    @property
    def wake_up_sound_id(self) -> Optional[str]:
        """Returns the current wake-up sound ID."""
        return self._settings.wake_up_sound_id

    @wake_up_sound_id.setter
    def wake_up_sound_id(self, sound_id: str) -> None:
        """Sets the wake-up sound ID."""
        self._settings.wake_up_sound_id = sound_id

    @property
    def get_up_sound_id(self) -> Optional[str]:
        """Returns the current get-up sound ID."""
        return self._settings.get_up_sound_id

    @get_up_sound_id.setter
    def get_up_sound_id(self, sound_id: str) -> None:
        """Sets the get-up sound ID."""
        self._settings.get_up_sound_id = sound_id

    def get_wake_up_sound_options(self):
        """Get all available wake-up sound options."""
        return self._alarm_manager.get_wake_up_sound_options()

    def get_get_up_sound_options(self):
        """Get all available get-up sound options."""
        return self._alarm_manager.get_get_up_sound_options()

    def schedule_alarm(
        self,
        alarm_id: str,
        time_str: str,
        use_sunrise: Optional[bool] = None,
        max_brightness: Optional[float] = None,
        wake_up_sound_id: Optional[str] = None,
        get_up_sound_id: Optional[str] = None,
        volume: Optional[float] = None,
    ) -> None:
        """
        Schedules an alarm for a specific time.

        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
            use_sunrise: Whether to enable the sunrise simulation
            max_brightness: Maximum brightness for sunrise (0-100)
            wake_up_sound_id: Sound ID for wake-up alarm
            get_up_sound_id: Sound ID for get-up alarm
            volume: Volume level for alarm sounds (0.0 to 1.0)
        """
        use_sunrise_val = self._settings.use_sunrise if use_sunrise is None else use_sunrise
        brightness_val = max_brightness or self._settings.max_brightness
        wake_sound = wake_up_sound_id or self._settings.wake_up_sound_id
        get_sound = get_up_sound_id or self._settings.get_up_sound_id
        volume_val = volume if volume is not None else self._settings.volume

        self.logger.info("Scheduling alarm '%s' at %s with configuration:", alarm_id, time_str)
        self.logger.info("  - Wake-up timer duration: %d seconds", self._settings.wake_up_timer_duration)
        self.logger.info("  - Wake-up sound: %s", wake_sound or "Default")
        self.logger.info("  - Get-up sound: %s", get_sound or "Default")
        self.logger.info("  - Sunrise: %s", "Enabled" if use_sunrise_val else "Disabled")
        self.logger.info("  - Maximum brightness: %.1f%%", brightness_val)
        self.logger.info("  - Volume: %.2f", volume_val)

        self._alarm_manager.schedule_alarm(
            alarm_id,
            time_str,
            self._settings.wake_up_timer_duration,
            use_sunrise_val,
            brightness_val,
            wake_sound,
            get_sound,
            volume_val,
        )
        self._active_alarms.add(alarm_id)
        self.logger.info("Alarm '%s' successfully scheduled", alarm_id)

    def schedule_random_alarm(
        self,
        alarm_id: str,
        time_str: str,
        use_sunrise: Optional[bool] = None,
        max_brightness: Optional[float] = None,
        volume: Optional[float] = None,
    ) -> None:
        """
        Schedules an alarm with randomly selected sounds.

        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
            use_sunrise: Whether to enable the sunrise simulation
            max_brightness: Maximum brightness for sunrise (0-100)
            volume: Volume level for alarm sounds (0.0 to 1.0)
        """
        use_sunrise_val = self._settings.use_sunrise if use_sunrise is None else use_sunrise
        brightness_val = max_brightness or self._settings.max_brightness
        volume_val = volume if volume is not None else self._settings.volume

        self.logger.info("Scheduling random alarm '%s' at %s with configuration:", alarm_id, time_str)
        self.logger.info("  - Wake-up timer duration: %d seconds", self._settings.wake_up_timer_duration)
        self.logger.info("  - Sounds: Random selection")
        self.logger.info("  - Sunrise: %s", "Enabled" if use_sunrise_val else "Disabled")
        self.logger.info("  - Maximum brightness: %.1f%%", brightness_val)
        self.logger.info("  - Volume: %.2f", volume_val)

        self._alarm_manager.schedule_random_alarm(
            alarm_id,
            time_str,
            self._settings.wake_up_timer_duration,
            use_sunrise_val,
            brightness_val,
            volume_val,
        )
        self._active_alarms.add(alarm_id)
        self.logger.info("Random alarm '%s' successfully scheduled", alarm_id)

    def cancel_alarm(self, alarm_id: str) -> None:
        """Cancels an active alarm."""
        self._alarm_manager.cancel_alarm(alarm_id)
        self._active_alarms.discard(alarm_id)