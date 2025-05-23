from fastapi import APIRouter, Depends

from api.dependencies.audio import get_audio_player
from api.models.alarm_models import (AlarmOptions, BrightnessRequest,
                                     CancelAlarmResponse, CreateAlarmRequest,
                                     CreateAlarmResponse, PlaySoundResponse,
                                     SoundRequest, StopSoundResponse,
                                     VolumeRequest)
from api.services.alarm_service import AlarmService
from core.audio.audio_player_base import AudioPlayer

router = APIRouter()


def get_alarm_service() -> AlarmService:
    """Dependency injection for alarm service"""
    return AlarmService()


@router.get("/")
def get_all_alarms(service: AlarmService = Depends(get_alarm_service)):
    """Get all alarms with their status (active/inactive/scheduled)"""
    return service.get_all_alarms()

@router.post("/", response_model=CreateAlarmResponse)
def create_alarm(
    request: CreateAlarmRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Create a new alarm with the specified time"""
    return service.create_alarm(request)

@router.put("/{alarm_id}/toggle")
def toggle_alarm(
    alarm_id: str, 
    active: bool,
    service: AlarmService = Depends(get_alarm_service)
):
    """Toggle an alarm active/inactive"""
    return service.toggle_alarm(alarm_id, active)

@router.delete("/{alarm_id}")
def delete_alarm(
    alarm_id: str, 
    service: AlarmService = Depends(get_alarm_service)
):
    """Permanently delete an alarm"""
    return service.delete_alarm(alarm_id)

# Alternative toggle endpoint mit Request Body
from pydantic import BaseModel


class ToggleAlarmRequest(BaseModel):
    active: bool

@router.put("/alarms/{alarm_id}")
def toggle_alarm_with_body(
    alarm_id: str,
    request: ToggleAlarmRequest,
    service: AlarmService = Depends(get_alarm_service)
):
    """Toggle an alarm active/inactive with request body"""
    return service.toggle_alarm(alarm_id, request.active)


@router.get("/options", response_model=AlarmOptions)
def get_alarm_options(service: AlarmService = Depends(get_alarm_service)):
    """Get all alarm configuration options"""
    return service.get_alarm_options()


@router.post("/play/{sound_id:path}", response_model=PlaySoundResponse)
def play_sound(sound_id: str, service: AlarmService = Depends(get_alarm_service)):
    """Play a sound using the audio player"""
    return service.play_alarm_sound(sound_id)


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
    request: VolumeRequest,
    service: AlarmService = Depends(get_alarm_service),
    audio_player: AudioPlayer = Depends(get_audio_player),
):
    """Set the global volume for all alarms"""
    audio_player.play_sound("sound_check", volume=request.volume)
    return service.set_volume(request.volume)


@router.put("/settings/wake-up-sound")
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


@router.delete("/alarms/{alarm_id}", response_model=CancelAlarmResponse)
def cancel_alarm(alarm_id: str, service: AlarmService = Depends(get_alarm_service)):
    """Cancel an existing alarm by its ID"""
    return service.cancel_alarm(alarm_id)
