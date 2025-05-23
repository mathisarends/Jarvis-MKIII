from fastapi import APIRouter, Depends

from api.models.alarm_models import (AlarmOptions, CancelAlarmResponse,
                                     CreateAlarmRequest, CreateAlarmResponse,
                                     PlaySoundResponse, StopSoundResponse)
from api.services.alarm_service import AlarmService

alarm_router = APIRouter()


def get_alarm_service() -> AlarmService:
    """Dependency injection for alarm service"""
    return AlarmService()


@alarm_router.get("/")
def get_all_alarms(service: AlarmService = Depends(get_alarm_service)):
    """Get all alarms with their status (active/inactive/scheduled)"""
    return service.get_all_alarms()

@alarm_router.post("/", response_model=CreateAlarmResponse)
def create_alarm(
    request: CreateAlarmRequest, service: AlarmService = Depends(get_alarm_service)
):
    """Create a new alarm with the specified time"""
    return service.create_alarm(request)

@alarm_router.put("/{alarm_id}/toggle")
def toggle_alarm(
    alarm_id: str, 
    active: bool,
    service: AlarmService = Depends(get_alarm_service)
):
    """Toggle an alarm active/inactive"""
    return service.toggle_alarm(alarm_id, active)

@alarm_router.delete("/{alarm_id}")
def delete_alarm(
    alarm_id: str, 
    service: AlarmService = Depends(get_alarm_service)
):
    """Permanently delete an alarm"""
    return service.delete_alarm(alarm_id)


@alarm_router.get("/options", response_model=AlarmOptions)
def get_alarm_options(service: AlarmService = Depends(get_alarm_service)):
    """Get all alarm configuration options"""
    return service.get_alarm_options()


@alarm_router.post("/play/{sound_id:path}", response_model=PlaySoundResponse)
def play_sound(sound_id: str, service: AlarmService = Depends(get_alarm_service)):
    """Play a sound using the audio player"""
    return service.play_alarm_sound(sound_id)


@alarm_router.post("/stop", response_model=StopSoundResponse)
def stop_sound(service: AlarmService = Depends(get_alarm_service)):
    """Stop currently playing sound"""
    return service.stop_sound()

@alarm_router.delete("/alarms/{alarm_id}", response_model=CancelAlarmResponse)
def cancel_alarm(alarm_id: str, service: AlarmService = Depends(get_alarm_service)):
    """Cancel an existing alarm by its ID"""
    return service.cancel_alarm(alarm_id)
