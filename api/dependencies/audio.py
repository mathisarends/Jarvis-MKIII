from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.py_audio_player import PyAudioPlayer
from plugins.alarm.daylight_alarm import AlarmSystem

_audio_player = None
_alarm_system = None


def initialize_audio_system():
    """Initialize the audio system"""
    global _audio_player, _alarm_system
    AudioPlayerFactory.initialize_with(PyAudioPlayer)
    _alarm_system = AlarmSystem.get_instance()


def get_audio_player():
    """Dependency for audio player"""
    return AudioPlayerFactory.get_shared_instance()


def get_alarm_system():
    """Dependency for alarm system"""
    global _alarm_system
    if _alarm_system is None:
        _alarm_system = AlarmSystem.get_instance()
    return _alarm_system
