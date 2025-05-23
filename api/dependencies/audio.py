from core.audio.audio_player_base import AudioPlayer
from core.audio.audio_player_factory import AudioPlayerFactory


def get_audio_player() -> AudioPlayer:
    """Dependency for audio player"""
    return AudioPlayerFactory.get_shared_instance()
