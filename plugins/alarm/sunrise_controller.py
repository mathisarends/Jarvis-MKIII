import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from hueify import GroupsManager, HueBridge

from shared.logging_mixin import LoggingMixin
from shared.singleton_meta_class import SingletonMetaClass


@dataclass
class SunriseConfig:
    """Konfiguration für den Tageslicht-Wecker."""
    scene_name: str = "Majestätischer Morgen"  # Name der Zielszene für den Sonnenaufgang
    room_name: str = "Schlafzimmer"  # Name des Raums/der Gruppe
    duration_seconds: int = 540  # Dauer des Sonnenaufgangs in Sekunden (9 Minuten)
    start_brightness_percent: float = 0.01  # Anfangshelligkeit (1% der Zielszene)
    enable_logging: bool = True  # Logging aktivieren/deaktivieren


class SunriseController(LoggingMixin, metaclass=SingletonMetaClass):
    """
    Controller für den Tageslicht-Wecker, der einen Sonnenaufgang mit Philips Hue simuliert.
    
    Verwendet die Hueify-Bibliothek für die Kommunikation mit der Hue Bridge und
    bietet eine einfache, saubere Schnittstelle zur Integration mit dem Alarmsystem.
    """
    
    def __init__(self, config: Optional[SunriseConfig] = None):
        """
        Initialisiert den SunriseController mit der gegebenen Konfiguration.
        
        Args:
            config: Optionale Konfiguration für den Sonnenaufgang.
                   Falls None, wird die Standardkonfiguration verwendet.
        """
        self.config = config or SunriseConfig()
        self.bridge: Optional[HueBridge] = None
        self.groups_manager: Optional[GroupsManager] = None
        self.running_sunrise: Optional[asyncio.Task] = None
        self._cancel_event = threading.Event()
        
        # Asynchrone Initialisierung starten
        threading.Thread(target=self._init_bridge, daemon=True).start()
    
    def _init_bridge(self) -> None:
        """
        Initialisiert die Verbindung zur Hue Bridge im Hintergrund.
        """
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.groups_manager = GroupsManager(self.bridge)
            self.logger.info("💡 Hueify Tageslicht-Wecker erfolgreich initialisiert")
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Verbinden mit der Hue Bridge: {e}")
    
    def start_sunrise(self, 
                     scene_name: Optional[str] = None, 
                     duration_seconds: Optional[int] = None) -> bool:
        """
        Startet den Sonnenaufgang-Effekt.
        
        Args:
            scene_name: Optionaler Name der Zielszene.
                        Falls None, wird die Szene aus der Konfiguration verwendet.
            duration_seconds: Optionale Dauer des Sonnenaufgangs in Sekunden.
                             Falls None, wird die Dauer aus der Konfiguration verwendet.
        
        Returns:
            True wenn der Sonnenaufgang erfolgreich gestartet wurde, False sonst.
        """
        # Prüfen, ob die Bridge initialisiert ist
        if not self.bridge or not self.groups_manager:
            self.logger.error("❌ Hue Bridge nicht initialisiert")
            return False
        
        # Konfiguration für diesen Sonnenaufgang festlegen
        actual_scene = scene_name or self.config.scene_name
        actual_duration = duration_seconds or self.config.duration_seconds
        
        # Sonnenaufgang-Prozess in eigenem Thread starten
        self._cancel_event.clear()
        threading.Thread(
            target=self._run_async_in_thread,
            args=(self._start_sunrise_async(actual_scene, actual_duration),),
            daemon=True
        ).start()
        
        self.logger.info(f"🌅 Starte Sonnenaufgang mit Szene '{actual_scene}' "
                        f"über {actual_duration} Sekunden")
        return True
    
    def stop_sunrise(self) -> None:
        """
        Stoppt den laufenden Sonnenaufgang.
        """
        self._cancel_event.set()
        self.logger.info("🛑 Sonnenaufgang gestoppt")
    
    def _run_async_in_thread(self, coro) -> None:
        """
        Führt eine asyncio-Coroutine in einem separaten Thread aus.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()
    
    async def _start_sunrise_async(self, scene_name: str, duration_seconds: int) -> None:
        """
        Asynchrone Methode zur Durchführung des Sonnenaufgangs.
        
        Args:
            scene_name: Name der Zielszene
            duration_seconds: Dauer des Sonnenaufgangs in Sekunden
        """
        try:
            # Controller für den konfigurierten Raum holen
            room_controller = await self.groups_manager.get_controller(self.config.room_name)
            
            # Ausgangszustand speichern für eventuelle Wiederherstellung
            initial_state_id = await room_controller.save_state("pre_sunrise_state")
            
            # Beginnen mit minimaler Helligkeit
            start_brightness = max(1, round(self.config.start_brightness_percent * 100))
            await room_controller.set_brightness_percentage(start_brightness, transition_time=1)
            
            # Szene aktivieren für Farbeinstellungen, aber mit niedriger Helligkeit
            await room_controller.activate_scene(scene_name)
            await asyncio.sleep(1)  # Kurz warten, damit die Szene aktiv wird
            
            # Anzahl der Schritte und Zeitintervall berechnen
            steps = 20  # Anzahl der Helligkeitsschritte
            step_duration = duration_seconds / steps
            current_brightness = start_brightness
            
            # Schrittweise die Helligkeit erhöhen
            for step in range(1, steps + 1):
                if self._cancel_event.is_set():
                    self.logger.info("🛑 Sonnenaufgang abgebrochen")
                    return
                
                # Neue Helligkeit berechnen (logarithmische Kurve für natürlicheren Effekt)
                progress = step / steps
                brightness_percent = start_brightness + (100 - start_brightness) * (progress ** 0.8)
                current_brightness = round(brightness_percent)
                
                # Helligkeit setzen mit sanftem Übergang
                transition_time = max(1, round(step_duration * 10))  # in 100ms Einheiten
                await room_controller.set_brightness_percentage(
                    current_brightness, 
                    transition_time=transition_time
                )
                
                # Log-Eintrag bei bestimmten Schritten
                if self.config.enable_logging and step % 5 == 0:
                    self.logger.info(f"🌅 Sonnenaufgang: {current_brightness}% Helligkeit erreicht")
                
                # Warten bis zum nächsten Schritt
                await asyncio.sleep(step_duration)
            
            self.logger.info("🌅 Sonnenaufgang abgeschlossen: 100% Helligkeit erreicht")
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Sonnenaufgang: {e}")


class SunriseAlarmAdapter:
    """
    Adapter zur Integration des SunriseControllers mit dem Alarmsystem.
    """
    
    def __init__(self):
        """
        Initialisiert den SunriseAlarmAdapter.
        """
        self.sunrise_controller = SunriseController.get_instance()
    
    def start_sunrise_for_alarm(self, 
                               scene_name: Optional[str] = None, 
                               duration_seconds: Optional[int] = None) -> None:
        """
        Startet den Sonnenaufgang für einen Alarm.
        
        Diese Methode kann vom Alarmsystem als Callback aufgerufen werden,
        wenn der Alarm ausgelöst wird.
        
        Args:
            scene_name: Optionaler Name der Zielszene
            duration_seconds: Optionale Dauer des Sonnenaufgangs in Sekunden
        """
        self.sunrise_controller.start_sunrise(scene_name, duration_seconds)
    
    def stop_sunrise(self) -> None:
        """
        Stoppt den laufenden Sonnenaufgang.
        
        Diese Methode kann vom Alarmsystem aufgerufen werden,
        wenn der Alarm abgebrochen wird.
        """
        self.sunrise_controller.stop_sunrise()


if __name__ == "__main__":
    config = SunriseConfig(
        scene_name="Majestätischer Morgen",
        room_name="Zimmer 1",
        duration_seconds=60,
        start_brightness_percent=0.01
    )
    
    controller = SunriseController(config)
    
    time.sleep(2)
    
    controller.start_sunrise()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop_sunrise()
        print("Programm beendet")