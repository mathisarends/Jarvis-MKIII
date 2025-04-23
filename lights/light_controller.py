import asyncio
import traceback
from enum import Enum, auto

from hueify import GroupsManager, HueBridge

from utils.logging_mixin import LoggingMixin
from utils.event_bus import EventBus, EventType


class LightMode(Enum):
    """Vereinfachte Light-Modi"""
    AUDIO_PLAYING = auto()  # Audio wird abgespielt
    NORMAL = auto()         # Kein Audio


class LightController(LoggingMixin):
    """
    Controller für Philips Hue Beleuchtung basierend auf Audio-Wiedergabe.
    
    Erhöht die Helligkeit, wenn Audio abgespielt wird, und
    stellt die normale Helligkeit wieder her, wenn keine Wiedergabe erfolgt.
    """

    def __init__(self):
        """Initialisiert den Light Controller und abonniert Audio-Events."""
        self.current_mode = LightMode.NORMAL
        self.loop = asyncio.get_event_loop()

        # Hue-Komponenten
        self.bridge = None
        self.group_manager = None
        self.room_controller = None
        self.saved_normal_state_id = None

        # Events abonnieren
        self._register_events()
        
        # Hue-Verbindung initialisieren
        self.loop.create_task(self._initialize_hue())
        self.logger.info("Light Controller initialisiert")

    async def _initialize_hue(self):
        """Initialisiert die Verbindung zur Hue Bridge."""
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.logger.info("Verbinde zur Hue Bridge mittels Auto-Discovery")

            self.group_manager = GroupsManager(bridge=self.bridge)
            self.room_controller = await self.group_manager.get_controller(
                group_identifier="Zimmer 1"
            )

            self.logger.info(f"Erfolgreich mit Hue Bridge verbunden, kontrolliere Raum: {self.room_controller.name}")

            # Aktuellen Zustand als "normal" speichern
            await self._save_normal_state()

        except Exception as e:
            self.logger.error(f"Fehler bei Hue-Initialisierung: {e}")
            self.bridge = None
            self.group_manager = None
            self.room_controller = None

    async def _save_normal_state(self):
        """Speichert den aktuellen Zustand als normalen Zustand."""
        if not self.room_controller:
            return

        try:
            self.saved_normal_state_id = await self.room_controller.save_state()
            self.logger.info(f"Normaler Zustand gespeichert mit ID: {self.saved_normal_state_id}")
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des normalen Zustands: {e}")

    def _register_events(self):
        """Registriert Event-Handler für Audio-Events."""
        self.event_bus = EventBus()
        
        # Audio-Events abonnieren
        self.event_bus.subscribe(EventType.AUDIO_PLAYBACK_STARTED, self._handle_audio_started)
        self.event_bus.subscribe(EventType.AUDIO_PLAYBACK_STOPPED, self._handle_audio_stopped)

    def _handle_audio_started(self):
        """Handler für Audio-Start-Event."""
        self.set_light_mode(LightMode.AUDIO_PLAYING)
        
    def _handle_audio_stopped(self):
        """Handler für Audio-Stop-Event."""
        self.set_light_mode(LightMode.NORMAL)

    def set_light_mode(self, mode):
        """
        Setzt den Lichtmodus.

        Args:
            mode: LightMode Enum-Wert
        """
        if self.current_mode == mode:
            return

        self.current_mode = mode
        self.loop.create_task(self._update_lights(mode))
        self.logger.info(f"LICHT: Wechsle zu {mode.name} Modus")

    async def _update_lights(self, mode):
        """
        Aktualisiert die Beleuchtung basierend auf dem Modus.

        Args:
            mode: LightMode Enum-Wert
        """
        if not self.room_controller:
            self.logger.warning("Hue nicht initialisiert, kann Lichter nicht steuern")
            return

        try:
            if mode == LightMode.AUDIO_PLAYING:
                # Bei Audio-Wiedergabe, Helligkeit um 25% erhöhen
                await self.room_controller.increase_brightness_percentage(
                    increment=25, transition_time=self._seconds_to_transition_time(0.5)
                )
                self.logger.info("Helligkeit für Audio-Wiedergabe erhöht")

            elif mode == LightMode.NORMAL:
                # Zurück zum normalen Zustand
                if not self.saved_normal_state_id:
                    self.logger.warning("Kein gespeicherter Normalzustand verfügbar")
                    return

                await self.room_controller.restore_state(
                    self.saved_normal_state_id, transition_time_seconds=1.0
                )
                self.logger.info("Normalen Beleuchtungszustand wiederhergestellt")

        except Exception as e:
            error_details = f"Fehler bei Lichtsteuerung: {e}\n{traceback.format_exc()}"
            self.logger.error(error_details)

    def _seconds_to_transition_time(self, seconds):
        """Konvertiert Sekunden in Hue API 100ms-Einheiten."""
        return max(1, round(seconds * 10))

    async def refresh_normal_state(self):
        """
        Aktualisiert den gespeicherten 'normalen' Zustand auf den aktuellen Lichtzustand.
        """
        await self._save_normal_state()
        self.logger.info("Normalzustand auf aktuellen Lichtzustand aktualisiert")