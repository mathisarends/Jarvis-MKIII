import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from core.audio.audio_player_factory import AudioPlayerFactory
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
    snooze_duration: int
    active: bool = True
    scheduled: bool = False
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
    
    def schedule_alarm(self, alarm_id: str, time_str: str, snooze_duration: int = 540) -> None:
        """
        Schedules an alarm for a specific time.
        
        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
            snooze_duration: Time in seconds between Wake-Up and Get-Up alarm (default: 9 minutes)
        """
        with self._scheduler_lock:
            alarm_time = self._parse_time(time_str)
            
            alarm_config = AlarmConfig(
                wake_up_time=alarm_time,
                snooze_duration=snooze_duration
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
        hour, minute = map(int, time_str.split(':'))
        now = datetime.now()
        alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if alarm_time <= now:
            alarm_time += timedelta(days=1)
        
        return alarm_time.timestamp()
    
    def _ensure_scheduler_running(self) -> None:
        """Ensures that the scheduler thread is running."""
        if not self._scheduler_thread or not self._scheduler_thread.is_alive():
            self._running = True
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
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
            args=[AlarmSound.WAKE_UP.value, alarm_id, AlarmStage.WAKE_UP]
        )
        wake_up_thread.daemon = True
        wake_up_thread.start()
        
        get_up_time = wake_up_time + config.snooze_duration
        delay_get_up = max(0, get_up_time - time.time())
        
        get_up_thread = threading.Timer(
            delay_get_up, 
            self._execute_alarm,
            args=[AlarmSound.GET_UP.value, alarm_id, AlarmStage.GET_UP]
        )
        get_up_thread.daemon = True
        get_up_thread.start()
        
        config.scheduled_threads = [wake_up_thread, get_up_thread]
        
        print(f"Alarm scheduled: WAKE_UP in {delay:.1f} seconds, GET_UP in {delay_get_up:.1f} seconds")
    
    def _execute_alarm(self, sound_id: str, alarm_id: str, stage: AlarmStage) -> None:
        """Executes an alarm and plays the corresponding sound."""
        if alarm_id not in self._scheduled_alarms:
            return
            
        config = self._scheduled_alarms[alarm_id]
        
        if not config.active:
            return
        
        print(f"Alarm triggered: {stage.value} with sound {sound_id}")
        
        for callback in self._callbacks.get(sound_id, []):
            try:
                callback()
            except Exception as e:
                print(f"Error executing callback for {sound_id}: {e}")
        
        if stage == AlarmStage.GET_UP:
            config.scheduled = False
            
            wake_up_time = config.wake_up_time
            next_day_time = wake_up_time + 86400
            config.wake_up_time = next_day_time


@dataclass
class AlarmSettings:
    """Settings for the alarm system"""
    snooze_duration: int = 540


class AlarmSystem(metaclass=SingletonMetaClass):
    """
    Main class of the alarm system that integrates AlarmManager and AudioPlayer.
    """
    
    def __init__(self, snooze_duration: int = 30):
        self._alarm_manager: AlarmManager = AlarmManager.get_instance()
        self._settings: AlarmSettings = AlarmSettings(snooze_duration=snooze_duration)
        self._active_alarms: Set[str] = set()
        self._setup_callbacks()
    
    @property
    def snooze_duration(self) -> int:
        """Returns the current snooze duration in seconds."""
        return self._settings.snooze_duration
    
    @snooze_duration.setter
    def snooze_duration(self, duration: int) -> None:
        """Sets the snooze duration in seconds."""
        if duration <= 0:
            raise ValueError("The snooze duration must be greater than 0.")
        self._settings.snooze_duration = duration
    
    def _setup_callbacks(self) -> None:
        """Sets up callbacks for the different sounds."""
        self._alarm_manager.register_callback(
            AlarmSound.WAKE_UP.value,
            lambda: AudioPlayerFactory.get_shared_instance().play_sound(AlarmSound.WAKE_UP.value)
        )
        
        self._alarm_manager.register_callback(
            AlarmSound.GET_UP.value,
            lambda: AudioPlayerFactory.get_shared_instance().play_sound(AlarmSound.GET_UP.value)
        )
    
    def schedule_alarm(self, alarm_id: str, time_str: str) -> None:
        """
        Schedules an alarm for a specific time.
        
        Args:
            alarm_id: Unique ID for the alarm
            time_str: Time in "HH:MM" format
        """
        self._alarm_manager.schedule_alarm(alarm_id, time_str, self._settings.snooze_duration)
        self._active_alarms.add(alarm_id)
    
    def cancel_alarm(self, alarm_id: str) -> None:
        """Cancels an active alarm."""
        self._alarm_manager.cancel_alarm(alarm_id)
        self._active_alarms.discard(alarm_id)


if __name__ == "__main__":
    from core.audio.py_audio_player import PyAudioPlayer

    AudioPlayerFactory.initialize_with(PyAudioPlayer)
    
    alarm_system = AlarmSystem.get_instance()
    alarm_system.snooze_duration = 30
    
    current_time = datetime.now()
    test_time = (current_time + timedelta(seconds=60)).strftime("%H:%M")
    
    print(f"Current: {current_time.strftime('%H:%M:%S')}")
    print(f"Alarm scheduled for: {test_time}")
    
    alarm_system.schedule_alarm("morning_alarm", test_time)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program terminated")