from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable, Dict, Any

DEFAULT_WAKE_SOUND = "wake-up-focus"
DEFAULT_GET_UP_SOUND = "get-up-blossom"

@dataclass
class AlarmConfig:
    """Konfiguration für den Alarm-Manager."""

    wake_up_duration: int = 30
    get_up_duration: int = 40
    snooze_duration: int = 540
    fade_out_duration: float = 2.0
    use_light_alarm: bool = True
    light_scene_name: str = "Majestätischer Morgen"
    default_wake_up_sound = "wake-up-focus"
    default_get_up_sound = "get-up-blossom"


class AlarmItem:
    def __init__(
        self,
        id: int,
        time: datetime,
        wake_sound_id: str,
        get_up_sound_id: str,
        callback: Optional[Callable] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.time = time
        self.wake_sound_id = wake_sound_id
        self.get_up_sound_id = get_up_sound_id
        self.callback = callback
        self.extra = (
            extra or {}
        )
        self.triggered = False
