from fastapi import APIRouter, Depends

from api.dependencies.audio import get_audio_player
from api.models.alarm_models import (BrightnessRequest, SoundRequest,
                                     VolumeRequest)
from api.services.alarm_service import AlarmService
from core.audio.audio_player_base import AudioPlayer

alarm_settings_router = APIRouter()


def get_alarm_service() -> AlarmService:
    """Dependency injection for alarm service"""
    return AlarmService()


@alarm_settings_router.get("/")
def get_global_settings(service: AlarmService = Depends(get_alarm_service)):
    """Get the global alarm settings that apply to all alarms"""
    return service.get_global_settings()


@alarm_settings_router.put("/brightness")
def set_brightness(
    request: BrightnessRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Set the global brightness for all alarms"""
    return service.set_brightness(request.brightness)


@alarm_settings_router.put("/volume")
def set_volume(
    request: VolumeRequest,
    service: AlarmService = Depends(get_alarm_service),
    audio_player: AudioPlayer = Depends(get_audio_player),
):
    """Set the global volume for all alarms"""
    audio_player.set_volume_level(request.volume)   
    audio_player.play_sound("sound_check")
    return service.set_volume(request.volume)


@alarm_settings_router.put("/wake-up-sound")
def set_wake_up_sound(
    request: SoundRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Set the global wake-up sound for all alarms"""
    return service.set_wake_up_sound(request.sound_id)


@alarm_settings_router.put("/get-up-sound")
def set_get_up_sound(
    request: SoundRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Set the global get-up sound for all alarms"""
    return service.set_get_up_sound(request.sound_id)
