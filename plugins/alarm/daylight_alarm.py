import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from core.audio.audio_player_factory import AudioPlayerFactory
from plugins.alarm.sunrise_controller import SunriseConfig, SunriseController
from shared.singleton_meta_class import SingletonMetaClass


class AlarmSound(Enum):
    """Available alarm sounds"""

    WAKE_UP = "wake_up_sounds/wake-up-focus"
    GET_UP = "get_up_sounds/get-up-blossom"


class AlarmStage(Enum):
    """Alarm stages"""

    WAKE_UP = "wake_up"
    GET_UP = "get_up"


@dataclass
class AlarmConfig:
    """Configuration for a single alarm"""

    wake_up_time: float
    wake_up_timer_duration: int  # Renamed from snooze_duration for clarity
    active: bool = True
    scheduled: bool = False
    use_sunrise: bool = True
    max_brightness: float = 75.0
    scheduled_threads: List[threading.Timer] = field(default_factory=list)


class AlarmManager(metaclass=SingletonMetaClass):
    """
    Manages alarms with an efficient scheduling implementation.
    """

    def __init__(self):
        self._scheduled_alarms: Dict[str, AlarmConfig] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_lock: threading.Lock = threading.Lock()
        self._running: bool = False
        self._callbacks: Dict[str, List[Callable[[], Any]]] = {}

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
    ) -> None:
        """
        Schedules an alarm for a specific time.

        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
            wake_up_timer_duration: Time in seconds between first and second alarm (default: 9 minutes)
            use_sunrise: Whether to enable the sunrise simulation
            max_brightness: Maximum brightness for sunrise (0-100)
        """
        with self._scheduler_lock:
            alarm_time = self._parse_time(time_str)

            alarm_config = AlarmConfig(
                wake_up_time=alarm_time,
                wake_up_timer_duration=wake_up_timer_duration,
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

    def register_callback(self, sound_id: str, callback: Callable[[], Any]) -> None:
        """
        Registers a callback for a specific sound.

        Args:
            sound_id: ID of the sound (e.g., AlarmSound.WAKE_UP.value)
            callback: Function to call when the sound is played
        """
        if sound_id not in self._callbacks:
            self._callbacks[sound_id] = []

        self._callbacks[sound_id].append(callback)

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
            args=[AlarmSound.WAKE_UP.value, alarm_id, AlarmStage.WAKE_UP],
        )
        wake_up_thread.daemon = True
        wake_up_thread.start()

        get_up_time = wake_up_time + config.wake_up_timer_duration
        delay_get_up = max(0, get_up_time - time.time())

        get_up_thread = threading.Timer(
            delay_get_up,
            self._execute_alarm,
            args=[AlarmSound.GET_UP.value, alarm_id, AlarmStage.GET_UP],
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

        print(f"Alarm triggered: {stage.value} with sound {sound_id}")

        # If this is the WAKE_UP stage and sunrise is enabled, start the sunrise
        if stage == AlarmStage.WAKE_UP and config.use_sunrise:
            # Start the sunrise simulation with the alarm's timer duration
            self._sunrise_controller.start_sunrise(
                duration_seconds=config.wake_up_timer_duration,
                max_brightness=config.max_brightness,
            )

        # Execute any registered callbacks
        for callback in self._callbacks.get(sound_id, []):
            try:
                callback()
            except Exception as e:
                print(f"Error executing callback for {sound_id}: {e}")

        # If this is the final stage, reset for the next day
        if stage == AlarmStage.GET_UP:
            config.scheduled = False

            wake_up_time = config.wake_up_time
            next_day_time = wake_up_time + 86400
            config.wake_up_time = next_day_time


@dataclass
class AlarmSettings:
    """Settings for the alarm system"""

    wake_up_timer_duration: int = 540  # Renamed from snooze_duration
    use_sunrise: bool = True
    max_brightness: float = 75.0


class AlarmSystem(metaclass=SingletonMetaClass):
    """
    Main class of the alarm system that integrates AlarmManager and AudioPlayer.
    """

    def __init__(self, wake_up_timer_duration: int = 30, use_sunrise: bool = True):
        self._alarm_manager: AlarmManager = AlarmManager.get_instance()
        self._settings: AlarmSettings = AlarmSettings(
            wake_up_timer_duration=wake_up_timer_duration, use_sunrise=use_sunrise
        )
        self._active_alarms: Set[str] = set()
        self._setup_callbacks()

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

    def _setup_callbacks(self) -> None:
        """Sets up callbacks for the different sounds."""
        self._alarm_manager.register_callback(
            AlarmSound.WAKE_UP.value,
            lambda: AudioPlayerFactory.get_shared_instance().play_sound(
                AlarmSound.WAKE_UP.value
            ),
        )

        self._alarm_manager.register_callback(
            AlarmSound.GET_UP.value,
            lambda: AudioPlayerFactory.get_shared_instance().play_sound(
                AlarmSound.GET_UP.value
            ),
        )

    def schedule_alarm(
        self,
        alarm_id: str,
        time_str: str,
        use_sunrise: Optional[bool] = None,
        max_brightness: Optional[float] = None,
    ) -> None:
        """
        Schedules an alarm for a specific time.

        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
            use_sunrise: Whether to enable the sunrise simulation (default: use system setting)
            max_brightness: Optional maximum brightness (0-100) (default: use system setting)
        """
        # Use system settings as defaults
        use_sunrise_val = (
            self._settings.use_sunrise if use_sunrise is None else use_sunrise
        )
        brightness_val = max_brightness or self._settings.max_brightness

        self._alarm_manager.schedule_alarm(
            alarm_id,
            time_str,
            self._settings.wake_up_timer_duration,
            use_sunrise_val,
            brightness_val,
        )
        self._active_alarms.add(alarm_id)

    def cancel_alarm(self, alarm_id: str) -> None:
        """Cancels an active alarm."""
        self._alarm_manager.cancel_alarm(alarm_id)
        self._active_alarms.discard(alarm_id)


if __name__ == "__main__":
    from core.audio.py_audio_player import PyAudioPlayer

    AudioPlayerFactory.initialize_with(PyAudioPlayer)

    # Initialize alarm system with sunrise enabled
    alarm_system = AlarmSystem.get_instance()
    alarm_system.wake_up_timer_duration = 30  # 30 seconds for testing
    alarm_system.use_sunrise = True
    alarm_system.max_brightness = 75.0

    # Schedule an alarm for testing
    current_time = datetime.now()
    test_time = (current_time + timedelta(seconds=50)).strftime("%H:%M")

    print(f"Current: {current_time.strftime('%H:%M:%S')}")
    print(f"Alarm scheduled for: {test_time}")
    print(f"Wake-up timer duration: {alarm_system.wake_up_timer_duration} seconds")
    print(f"Sunrise enabled: {alarm_system.use_sunrise}")
    print(f"Maximum brightness: {alarm_system.max_brightness}%")

    # Schedule the alarm with default sunrise settings
    alarm_system.schedule_alarm("morning_alarm", test_time)

    # Wait for the alarm to trigger
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        alarm_system.cancel_alarm("morning_alarm")
        print("Program terminated")
