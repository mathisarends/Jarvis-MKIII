from typing import Type, TypeVar, Optional

from realtime.audio.audio_player_base import AudioPlayer

T = TypeVar("T", bound="AudioPlayer")


class AudioPlayerFactory:
    _instance: Optional[AudioPlayer] = None

    @classmethod
    def get_instance(cls, strategy_cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = strategy_cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
