from fastapi import APIRouter, Depends
from pydantic import Field

from api.models.alarm_models import (AlarmOptions, BrightnessRequest,
                                     PlaySoundResponse, SoundRequest,
                                     StopSoundResponse, VolumeRequest)
from api.services.alarm_service import AlarmService

router = APIRouter()


def get_alarm_service() -> AlarmService:
    """Dependency injection for alarm service"""
    return AlarmService()


@router.get("/options", response_model=AlarmOptions)
def get_alarm_options(service: AlarmService = Depends(get_alarm_service)):
    """Get all alarm configuration options"""
    return service.get_alarm_options()


@router.post("/play/{sound_id:path}", response_model=PlaySoundResponse)
def play_sound(sound_id: str, service: AlarmService = Depends(get_alarm_service)):
    """Play a sound using the audio player"""
    return service.play_sound(sound_id)


@router.post("/stop", response_model=StopSoundResponse)
def stop_sound(service: AlarmService = Depends(get_alarm_service)):
    """Stop currently playing sound"""
    return service.stop_sound()


@router.get("/settings")
def get_global_settings(service: AlarmService = Depends(get_alarm_service)):
    """Get the global alarm settings that apply to all alarms"""
    return service.get_global_settings()


@router.put("/settings/brightness")
def set_brightness(
    request: BrightnessRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Set the global brightness for all alarms"""
    return service.set_brightness(request.brightness)


@router.put("/settings/volume")
def set_volume(
    request: VolumeRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Set the global volume for all alarms"""
    return service.set_volume(request.volume)


@router.put("/settings/wake-up-sound")
def set_wake_up_sound(
    request: SoundRequest,
    service: AlarmService = Depends(get_alarm_service)
):
    """Set the global wake-up sound for all alarms"""
    return service.set_wake_up_sound(request.sound_id)


def set_wake_up_sound(
    request: SoundRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Set the global wake-up sound for all alarms"""
    return service.set_wake_up_sound(request.sound_id)


@router.put("/settings/get-up-sound")
def set_get_up_sound(
    request: SoundRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Set the global get-up sound for all alarms"""
    return service.set_get_up_sound(request.sound_id)
