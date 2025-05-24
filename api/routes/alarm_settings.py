from fastapi import APIRouter, Depends, Query

from api.dependencies.audio import get_audio_player
from api.models.alarm_models import BrightnessRequest, SoundRequest, VolumeRequest
from api.models.scene_models import SceneActivationRequest, SceneActivationResponse
from api.services.alarm_service import AlarmService
from api.services.hue_service import HueService
from core.audio.audio_player_base import AudioPlayer

alarm_settings_router = APIRouter()


def get_alarm_service() -> AlarmService:
    """Dependency injection for alarm service"""
    return AlarmService()


def get_hue_service() -> HueService:
    """Dependency injection for Hue service"""
    return HueService()


@alarm_settings_router.get("/available-scenes")
async def get_available_scenes(
    room_name: str = "Zimmer 1",
    hue_service: HueService = Depends(get_hue_service),
):
    """Get all available scenes for the configured room"""
    return await hue_service.get_available_scenes(room_name)


@alarm_settings_router.post("/scenes/activate-temporarily")
async def set_wake_up_scene(
    request: SceneActivationRequest,
    alarm_service: AlarmService = Depends(get_alarm_service),
    hue_service: HueService = Depends(get_hue_service),
) -> SceneActivationResponse:
    """
    Temporarily activate a scene for a specified duration.

    The scene will be activated immediately and automatically restored
    to the previous state after the duration expires.
    """
    alarm_service.set_sunrise_scene(request.scene_name)

    await hue_service.temporarily_activate_scene(
        scene_name=request.scene_name, duration=request.duration
    )

    return SceneActivationResponse(
        message=f"Scene '{request.scene_name}' activated temporarily for {request.duration} seconds",
        scene_name=request.scene_name,
        duration=request.duration,
    )


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
