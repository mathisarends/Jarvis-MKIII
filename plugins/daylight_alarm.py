import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.py_audio_player import PyAudioPlayer
from shared.singleton_meta_class import SingletonMetaClass


class AlarmSound(Enum):
    """Enum für die verfügbaren Alarmtöne."""
    WAKE_UP = "wake_up_sounds/wake-up-focus"
    GET_UP = "get_up_sounds/get-up-blossom"


class AlarmType(Enum):
    """Enum für die Alarmtypen."""
    WAKE_UP = "wake_up"
    GET_UP = "get_up"


class AlarmManager(metaclass=SingletonMetaClass):
    """
    Verwaltet Alarme mit verschiedenen Klingeltönen.
    Implementiert als Singleton über die SingletonMetaClass.
    """
    
    def __init__(self):
        self._alarms: Dict[str, Dict[str, Any]] = {}
        self._alarm_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._callbacks: Dict[AlarmType, List[Callable]] = {
            AlarmType.WAKE_UP: [],
            AlarmType.GET_UP: []
        }
        
    def set_alarm(self, alarm_id: str, wake_time: float, get_up_time: Optional[float] = None):
        """
        Setzt einen Alarm mit einer Weckzeit und optional einer Aufstehzeit.
        
        Args:
            alarm_id: Eindeutige ID für den Alarm
            wake_time: Zeitpunkt für den ersten Alarm (WAKE_UP) in Sekunden seit Epoch
            get_up_time: Optionaler Zeitpunkt für den zweiten Alarm (GET_UP) in Sekunden seit Epoch
        """
        alarm_config = {
            "wake_time": wake_time,
            "get_up_time": get_up_time,
            "active": True
        }
        
        self._alarms[alarm_id] = alarm_config
        
        # Starte den Alarm-Thread, falls er noch nicht läuft
        if not self._running:
            self._start_alarm_thread()
    
    def cancel_alarm(self, alarm_id: str):
        """Bricht einen aktiven Alarm ab."""
        if alarm_id in self._alarms:
            del self._alarms[alarm_id]
            
            # Stoppe den Thread, wenn keine Alarme mehr aktiv sind
            if not self._alarms and self._running:
                self._running = False
    
    def register_callback(self, alarm_type: AlarmType, callback: Callable):
        """
        Registriert einen Callback für einen bestimmten Alarmtyp.
        
        Args:
            alarm_type: Der Typ des Alarms (WAKE_UP oder GET_UP)
            callback: Eine aufrufbare Funktion, die ausgeführt wird, wenn der Alarm ausgelöst wird
        """
        self._callbacks[alarm_type].append(callback)
    
    def _start_alarm_thread(self):
        """Startet den Thread, der die Alarme überwacht."""
        self._running = True
        self._alarm_thread = threading.Thread(target=self._alarm_loop, daemon=True)
        self._alarm_thread.start()
    
    def _alarm_loop(self):
        """Die Hauptschleife, die Alarme überwacht und auslöst."""
        while self._running:
            current_time = time.time()
            alarms_to_remove = []
            
            for alarm_id, config in self._alarms.items():
                if not config["active"]:
                    continue
                    
                # Prüfe, ob es Zeit für den WAKE_UP-Alarm ist
                if config["wake_time"] <= current_time:
                    self._trigger_alarm(AlarmType.WAKE_UP)
                    
                    # Wenn es keinen GET_UP-Alarm gibt, entferne diesen Alarm
                    if config["get_up_time"] is None:
                        alarms_to_remove.append(alarm_id)
                    else:
                        # Aktualisiere den Alarm, um den WAKE_UP nicht mehr auszulösen
                        config["wake_time"] = float('inf')
                
                # Prüfe, ob es Zeit für den GET_UP-Alarm ist
                if config["get_up_time"] is not None and config["get_up_time"] <= current_time:
                    self._trigger_alarm(AlarmType.GET_UP)
                    alarms_to_remove.append(alarm_id)
            
            # Entferne abgelaufene Alarme
            for alarm_id in alarms_to_remove:
                self.cancel_alarm(alarm_id)
                
            # Kurze Pause, um CPU-Last zu reduzieren
            time.sleep(0.1)
    
    def _trigger_alarm(self, alarm_type: AlarmType):
        """Löst einen Alarm aus und ruft alle registrierten Callbacks auf."""
        # Rufe alle Callbacks für diesen Alarmtyp auf
        for callback in self._callbacks[alarm_type]:
            try:
                callback()
            except Exception as e:
                print(f"Fehler beim Aufruf des Callbacks für {alarm_type}: {e}")

class AlarmSystem(metaclass=SingletonMetaClass):
    """
    Hauptklasse des Alarmsystems, die AlarmManager und SoundPlayer integriert.
    Implementiert als Singleton über die SingletonMetaClass.
    """
    
    def __init__(self):
        self._alarm_manager = AlarmManager.get_instance()
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Richtet die Callbacks für die verschiedenen Alarmtypen ein."""
        
        self._alarm_manager.register_callback(
            AlarmType.WAKE_UP,
            lambda: AudioPlayerFactory.get_shared_instance().play_sound(AlarmSound.WAKE_UP.value)
        )
        
        self._alarm_manager.register_callback(
            AlarmType.GET_UP,
            lambda: AudioPlayerFactory.get_shared_instance().play_sound(AlarmSound.GET_UP.value)
        )
    
    def schedule_alarm(self, alarm_id: str, wake_time: float, get_up_time: Optional[float] = None):
        """
        Plant einen Alarm mit Wake-Up und optionalem Get-Up-Sound.
        
        Args:
            alarm_id: Eindeutige ID für den Alarm
            wake_time: Zeitpunkt für den Wake-Up-Alarm in Sekunden seit Epoch
            get_up_time: Optionaler Zeitpunkt für den Get-Up-Alarm in Sekunden seit Epoch
        """
        self._alarm_manager.set_alarm(alarm_id, wake_time, get_up_time)
    
    def cancel_alarm(self, alarm_id: str):
        """Bricht einen aktiven Alarm ab."""
        self._alarm_manager.cancel_alarm(alarm_id)


# Beispiel zur Verwendung des Moduls
if __name__ == "__main__":
    AudioPlayerFactory.initialize_with(PyAudioPlayer)
    alarm_system = AlarmSystem.get_instance()
    
    # Aktuelle Zeit + 5 Sekunden für den Wake-Up-Alarm
    wake_time = time.time() + 5
    # Aktuelle Zeit + 10 Sekunden für den Get-Up-Alarm
    get_up_time = time.time() + 10
    
    # Alarm planen
    alarm_system.schedule_alarm("test_alarm", wake_time, get_up_time)
    
    print(f"Alarm geplant: Wake-Up in 5 Sekunden, Get-Up in 10 Sekunden")
    
    # Hauptthread am Leben halten, damit der Daemon-Thread arbeiten kann
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Programm beendet")