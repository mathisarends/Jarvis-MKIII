import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from core.audio.audio_player_factory import AudioPlayerFactory
from plugins.alarm.alarm_sound_manager import AlarmSoundManager
from plugins.alarm.sunrise_controller import SunriseConfig, SunriseController
from shared.logging_mixin import LoggingMixin
from shared.singleton_meta_class import SingletonMetaClass


class AlarmStage(Enum):
    """Alarm stages"""

    WAKE_UP = "wake_up"
    GET_UP = "get_up"


@dataclass
class AlarmInfo:
    """Information about an alarm"""

    alarm_id: str
    time_str: str  # "07:30"
    active: bool  # User has enabled this alarm
    scheduled: bool = False  # System has scheduled this alarm
    next_execution: Optional[datetime] = None  # When it will next trigger


@dataclass
class AlarmConfig:
    """Runtime configuration for a scheduled alarm"""

    wake_up_time: float
    scheduled_threads: List[threading.Timer] = field(default_factory=list)


class AlarmManager(LoggingMixin, metaclass=SingletonMetaClass):
    """
    Manages scheduled alarms with an efficient scheduling implementation.
    All settings come from AlarmSystem at runtime.
    """

    def __init__(self):
        self._scheduled_alarms: Dict[str, AlarmConfig] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_lock: threading.Lock = threading.Lock()
        self._running: bool = False
        self._callbacks: Dict[str, List[Callable[[], Any]]] = {}
        self._sound_manager = AlarmSoundManager()

        # Reference to get current settings
        self._alarm_system: Optional["AlarmSystem"] = None

        # ✅ Sunrise controller wird jetzt dynamisch erstellt
        self._sunrise_controller: Optional[SunriseController] = None

    def set_alarm_system_reference(self, alarm_system: "AlarmSystem") -> None:
        """Set reference to AlarmSystem for getting current settings"""
        self._alarm_system = alarm_system

    def _get_sunrise_controller(self) -> SunriseController:
        """Get current sunrise controller with up-to-date settings"""
        if not self._alarm_system:
            raise RuntimeError("AlarmSystem reference not set")

        settings = self._alarm_system.get_global_settings()

        # ✅ Sunrise controller bei jedem Aufruf mit aktuellen Settings erstellen
        return SunriseController.get_instance(
            SunriseConfig(
                scene_name=settings["sunrise_scene_name"],
                room_name=settings["room_name"],
                start_brightness_percent=settings["start_brightness_percent"],
                max_brightness_percent=settings["max_brightness"],
            )
        )

    def cancel_alarm(self, alarm_id: str) -> None:
        """Cancels a scheduled alarm."""
        with self._scheduler_lock:
            if alarm_id in self._scheduled_alarms:
                config = self._scheduled_alarms[alarm_id]

                # Cancel all timers
                for thread in config.scheduled_threads:
                    if thread.is_alive():
                        thread.cancel()

                # ✅ Stop sunrise mit aktueller Konfiguration
                if self._alarm_system:
                    try:
                        sunrise_controller = self._get_sunrise_controller()
                        sunrise_controller.stop_sunrise()
                    except Exception as e:
                        self.logger.error(f"Failed to stop sunrise: {e}")

                del self._scheduled_alarms[alarm_id]

    def schedule_alarm(self, alarm_id: str, time_str: str) -> None:
        """
        Schedules an alarm for a specific time.
        Settings are fetched from AlarmSystem at execution time.
        """
        with self._scheduler_lock:
            alarm_time = self._parse_time(time_str)

            alarm_config = AlarmConfig(wake_up_time=alarm_time)
            self._scheduled_alarms[alarm_id] = alarm_config

            self._ensure_scheduler_running()
            self._schedule_alarm_execution(alarm_id)

    def is_scheduled(self, alarm_id: str) -> bool:
        """Check if alarm is currently scheduled"""
        return alarm_id in self._scheduled_alarms

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
        """Main scheduler loop."""
        while self._running:
            time.sleep(60)  # Check every minute

    def _schedule_alarm_execution(self, alarm_id: str) -> None:
        """Schedules the execution of an alarm using timers."""
        if alarm_id not in self._scheduled_alarms:
            return

        config = self._scheduled_alarms[alarm_id]

        # Get current settings
        settings = (
            self._alarm_system.get_global_settings() if self._alarm_system else {}
        )
        wake_up_timer_duration = settings.get("wake_up_timer_duration", 540)

        wake_up_time = config.wake_up_time
        delay = max(0, wake_up_time - time.time())

        wake_up_thread = threading.Timer(
            delay,
            self._execute_alarm,
            args=[alarm_id, AlarmStage.WAKE_UP],
        )
        wake_up_thread.daemon = True
        wake_up_thread.start()

        get_up_time = wake_up_time + wake_up_timer_duration
        delay_get_up = max(0, get_up_time - time.time())

        get_up_thread = threading.Timer(
            delay_get_up,
            self._execute_alarm,
            args=[alarm_id, AlarmStage.GET_UP],
        )
        get_up_thread.daemon = True
        get_up_thread.start()

        config.scheduled_threads = [wake_up_thread, get_up_thread]

        print(
            f"Alarm {alarm_id} scheduled: WAKE_UP in {delay:.1f}s, GET_UP in {delay_get_up:.1f}s"
        )

    def _execute_alarm(self, alarm_id: str, stage: AlarmStage) -> None:
        """Executes an alarm using CURRENT settings."""
        if alarm_id not in self._scheduled_alarms:
            return

        if not self._alarm_system:
            self.logger.error("No AlarmSystem reference available")
            return

        settings = self._alarm_system.get_global_settings()

        sound_id = (
            settings["wake_up_sound_id"]
            if stage == AlarmStage.WAKE_UP
            else settings["get_up_sound_id"]
        )

        self.logger.info(
            f"Alarm {alarm_id} triggered: {stage.value} with sound {sound_id}"
        )

        # ✅ Start sunrise mit aktuellen Settings
        if stage == AlarmStage.WAKE_UP and settings["use_sunrise"]:
            try:
                sunrise_controller = self._get_sunrise_controller()
                sunrise_controller.start_sunrise(
                    duration_seconds=settings["wake_up_timer_duration"],
                    max_brightness=settings["max_brightness"],
                )
            except Exception as e:
                self.logger.error(f"Failed to start sunrise: {e}")

        AudioPlayerFactory.get_shared_instance().play_sound(sound_id)

        if stage == AlarmStage.GET_UP:
            self._alarm_system.reschedule_alarm_for_tomorrow(alarm_id)


@dataclass
class GlobalAlarmSettings:
    """Global settings for all alarms"""

    wake_up_timer_duration: int = 540
    use_sunrise: bool = True
    max_brightness: float = 75.0
    volume: float = 0.5
    wake_up_sound_id: str = "wake_up_sounds/wake-up-focus"
    get_up_sound_id: str = "get_up_sounds/get-up-blossom"

    sunrise_scene_name: str = "Majestätischer Morgen"
    start_brightness_percent: float = 0.01
    room_name: str = "Zimmer 1"


class AlarmSystem(LoggingMixin, metaclass=SingletonMetaClass):
    """
    Enhanced alarm system with active/inactive management.
    Supports multiple persistent alarms that can be toggled on/off.
    """

    def __init__(self):
        self._alarm_manager: AlarmManager = AlarmManager.get_instance()
        self._settings: GlobalAlarmSettings = GlobalAlarmSettings()
        self._all_alarms: Dict[str, AlarmInfo] = {}  # All alarms (active and inactive)
        self._sound_manager = AlarmSoundManager()

        # Set reference so AlarmManager can get current settings
        self._alarm_manager.set_alarm_system_reference(self)

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

    def get_wake_up_sound_options(self):
        """Get all available wake-up sound options."""
        return self._alarm_manager.get_wake_up_sound_options()

    def get_get_up_sound_options(self):
        """Get all available get-up sound options."""
        return self._alarm_manager.get_get_up_sound_options()

    def get_global_settings(self) -> dict:
        """Get all global settings as a dictionary."""
        return {
            "wake_up_timer_duration": self._settings.wake_up_timer_duration,
            "use_sunrise": self._settings.use_sunrise,
            "max_brightness": self._settings.max_brightness,
            "volume": self._settings.volume,
            "wake_up_sound_id": self._settings.wake_up_sound_id,
            "get_up_sound_id": self._settings.get_up_sound_id,
        }

    def create_alarm(self, alarm_id: str, time_str: str) -> AlarmInfo:
        """Create a new alarm (active by default)"""
        if alarm_id in self._all_alarms:
            raise ValueError(f"Alarm {alarm_id} already exists")

        alarm_info = AlarmInfo(alarm_id=alarm_id, time_str=time_str, active=True)

        self._all_alarms[alarm_id] = alarm_info
        self._schedule_if_needed(alarm_info)

        self.logger.info(f"Created alarm {alarm_id} for {time_str}")
        return alarm_info

    def get_all_alarms(self) -> List[AlarmInfo]:
        """Get all alarms with their status"""
        alarms = []
        for alarm_info in self._all_alarms.values():
            # Update scheduled status
            alarm_info.scheduled = self._alarm_manager.is_scheduled(alarm_info.alarm_id)

            # Calculate next execution time
            if alarm_info.active:
                alarm_info.next_execution = self._calculate_next_execution(
                    alarm_info.time_str
                )
            else:
                alarm_info.next_execution = None

            alarms.append(alarm_info)

        # Sort by time
        return sorted(alarms, key=lambda a: a.time_str)

    def toggle_alarm(self, alarm_id: str, active: bool) -> AlarmInfo:
        """Toggle an alarm active/inactive"""
        if alarm_id not in self._all_alarms:
            raise ValueError(f"Alarm {alarm_id} not found")

        alarm_info = self._all_alarms[alarm_id]
        old_active = alarm_info.active
        alarm_info.active = active

        if active and not old_active:
            # Activating alarm
            self._schedule_if_needed(alarm_info)
            self.logger.info(f"Activated alarm {alarm_id}")
        elif not active and old_active:
            # Deactivating alarm
            self._alarm_manager.cancel_alarm(alarm_id)
            alarm_info.scheduled = False
            self.logger.info(f"Deactivated alarm {alarm_id}")

        return alarm_info

    def delete_alarm(self, alarm_id: str) -> None:
        """Permanently delete an alarm"""
        if alarm_id not in self._all_alarms:
            raise ValueError(f"Alarm {alarm_id} not found")

        # Cancel if scheduled
        self._alarm_manager.cancel_alarm(alarm_id)

        # Remove from storage
        del self._all_alarms[alarm_id]
        self.logger.info(f"Deleted alarm {alarm_id}")

    def reschedule_alarm_for_tomorrow(self, alarm_id: str) -> None:
        """Reschedule an alarm for tomorrow (called after execution)"""
        if alarm_id in self._all_alarms:
            alarm_info = self._all_alarms[alarm_id]
            if alarm_info.active:
                # Reschedule for tomorrow
                self._alarm_manager.cancel_alarm(alarm_id)
                self._schedule_if_needed(alarm_info)
                self.logger.info(f"Rescheduled alarm {alarm_id} for tomorrow")

    def set_sunrise_scene(self, scene_name: str) -> None:
        """Set the scene used for sunrise simulation."""
        if not scene_name or not scene_name.strip():
            raise ValueError("Scene name cannot be empty.")

        old_value = self._settings.sunrise_scene_name
        self._settings.sunrise_scene_name = scene_name
        self.logger.info(f"Sunrise scene updated: {old_value} → {scene_name}")

    def _schedule_if_needed(self, alarm_info: AlarmInfo) -> None:
        """Schedule alarm if it should be active"""
        if not alarm_info.active:
            return

        # Check if it's for today and hasn't passed yet
        next_time = self._calculate_next_execution(alarm_info.time_str)

        if next_time:
            self._alarm_manager.schedule_alarm(alarm_info.alarm_id, alarm_info.time_str)
            alarm_info.scheduled = True
            alarm_info.next_execution = next_time

    def _calculate_next_execution(self, time_str: str) -> Optional[datetime]:
        """Calculate when this alarm will next execute"""
        try:
            hour, minute = map(int, time_str.split(":"))
            now = datetime.now()
            alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if alarm_time <= now:
                alarm_time += timedelta(days=1)

            return alarm_time
        except:
            return None
