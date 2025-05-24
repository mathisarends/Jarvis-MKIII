import os
import re
from datetime import datetime

from fastapi import HTTPException

from api.dependencies.audio import get_audio_player
from api.models.alarm_models import (AlarmOptions, BrightnessRange,
                                     CreateAlarmRequest, SoundOption,
                                     VolumeRange)
from plugins.alarm.daylight_alarm import AlarmSystem


class AlarmService:
    def __init__(self):
        self.alarm_system: AlarmSystem = AlarmSystem.get_instance()
        self.sounds_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..",
            "resources",
            "sounds",
        )

    def get_alarm_options(self) -> AlarmOptions:
        """Get all alarm configuration options"""
        wake_up_options = self.alarm_system.get_wake_up_sound_options()
        get_up_options = self.alarm_system.get_get_up_sound_options()

        return AlarmOptions(
            wake_up_sounds=[
                SoundOption(id=option.value, label=option.label)
                for option in wake_up_options
            ],
            get_up_sounds=[
                SoundOption(id=option.value, label=option.label)
                for option in get_up_options
            ],
            volume_range=VolumeRange(),
            brightness_range=BrightnessRange(),
        )

    def validate_sound_id(self, sound_id: str) -> tuple[str, str]:
        """Validate and parse sound ID"""
        try:
            category, filename = sound_id.split("/", 1)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid sound ID format. Use 'category/filename'",
            )

        # Validate against available options
        wake_up_options = self.alarm_system.get_wake_up_sound_options()
        get_up_options = self.alarm_system.get_get_up_sound_options()

        valid_sound_ids = [option.value for option in wake_up_options] + [
            option.value for option in get_up_options
        ]

        if sound_id not in valid_sound_ids:
            raise HTTPException(
                status_code=404, detail=f"Sound ID '{sound_id}' not found"
            )

        # Check file exists
        file_path = os.path.join(self.sounds_dir, category, f"{filename}.mp3")
        print(f"Checking file path: {file_path}")
        if not os.path.exists(file_path):
            print("sound file not found")
            raise HTTPException(
                status_code=404, detail=f"Sound file not found for ID: '{sound_id}'"
            )

        return category, filename

    def play_alarm_sound(self, sound_id: str) -> dict:
        """Play a sound"""
        category, filename = self.validate_sound_id(sound_id)

        try:
            audio_player = get_audio_player()
            audio_player.play_sound(sound_id)

            return {
                "message": f"Successfully started playing sound: {filename}",
                "sound_id": sound_id,
                "category": category,
                "filename": filename,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to play sound '{sound_id}': {str(e)}"
            )

    def stop_sound(self) -> dict:
        """Stop currently playing sound"""
        try:
            audio_player = get_audio_player()
            audio_player.stop_sound()

            return {
                "message": "Successfully stopped audio playback",
                "status": "stopped",
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to stop sound: {str(e)}"
            )

    def set_brightness(self, brightness: float) -> dict:
        """Set the global brightness for all alarms"""
        try:
            self.alarm_system.set_max_brightness(brightness)
            return {
                "message": f"Brightness set to {brightness}%",
                "brightness": brightness,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set brightness: {str(e)}"
            )

    def set_volume(self, volume: float) -> dict:
        """Set the global volume for all alarms"""
        try:
            self.alarm_system.set_volume(volume)
            return {"message": f"Volume set to {volume}", "volume": volume}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set volume: {str(e)}"
            )

    def set_wake_up_sound(self, sound_id: str) -> dict:
        """Set the global wake-up sound for all alarms"""
        try:
            self.alarm_system.set_wake_up_sound(sound_id)
            return {
                "message": f"Wake-up sound set to {sound_id}",
                "wake_up_sound_id": sound_id,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set wake-up sound: {str(e)}"
            )

    def set_get_up_sound(self, sound_id: str) -> dict:
        """Set the global get-up sound for all alarms"""
        try:
            self.alarm_system.set_get_up_sound(sound_id)
            return {
                "message": f"Get-up sound set to {sound_id}",
                "get_up_sound_id": sound_id,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set get-up sound: {str(e)}"
            )

    def set_sunrise_scene(self, scene_name: str) -> dict:
        """Set the global sunrise scene for all alarms"""
        try:
            self.alarm_system.set_sunrise_scene(scene_name)
            return {
                "message": f"Sunrise scene set to {scene_name}",
                "sunrise_scene": scene_name,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set sunrise scene: {str(e)}"
            )

    def get_global_settings(self) -> dict:
        """Get all global alarm settings"""
        try:
            settings = self.alarm_system.get_global_settings()
            return settings
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get settings: {str(e)}"
            )

    def create_alarm(self, request: CreateAlarmRequest) -> dict:
        """Create a new alarm with auto-generated ID based on time"""

        alarm_id = self._generate_alarm_id(request.time)

        try:
            self.alarm_system.schedule_alarm(alarm_id, request.time)

            return {
                "message": f"Alarm scheduled for {request.time}",
                "alarm_id": alarm_id,
                "time": request.time,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create alarm: {str(e)}"
            )

    def get_all_alarms(self) -> dict:
        """Get all alarms with their status"""
        try:
            alarms = self.alarm_system.get_all_alarms()

            return {
                "alarms": [
                    {
                        "alarm_id": alarm.alarm_id,
                        "time": alarm.time_str,
                        "active": alarm.active,
                        "scheduled": alarm.scheduled,
                        "next_execution": (
                            alarm.next_execution.isoformat()
                            if alarm.next_execution
                            else None
                        ),
                        "time_until": (
                            self._calculate_time_until(alarm.next_execution)
                            if alarm.next_execution
                            else None
                        ),
                    }
                    for alarm in alarms
                ],
                "global_settings": self.alarm_system.get_global_settings(),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get alarms: {str(e)}"
            )

    def toggle_alarm(self, alarm_id: str, active: bool) -> dict:
        """Toggle an alarm active/inactive"""
        try:
            alarm_info = self.alarm_system.toggle_alarm(alarm_id, active)

            return {
                "message": f"Alarm {alarm_id} {'activated' if active else 'deactivated'}",
                "alarm_id": alarm_info.alarm_id,
                "time": alarm_info.time_str,
                "active": alarm_info.active,
                "scheduled": alarm_info.scheduled,
                "next_execution": (
                    alarm_info.next_execution.isoformat()
                    if alarm_info.next_execution
                    else None
                ),
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to toggle alarm: {str(e)}"
            )

    def delete_alarm(self, alarm_id: str) -> dict:
        """Permanently delete an alarm"""
        try:
            self.alarm_system.delete_alarm(alarm_id)

            return {
                "message": f"Alarm {alarm_id} deleted permanently",
                "alarm_id": alarm_id,
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete alarm: {str(e)}"
            )

    def create_alarm(self, request: CreateAlarmRequest) -> dict:
        """Create a new alarm with auto-generated ID based on time"""

        alarm_id = self._generate_alarm_id(request.time)

        try:
            alarm_info = self.alarm_system.create_alarm(alarm_id, request.time)

            settings = self.alarm_system.get_global_settings()

            return {
                "message": f"Alarm created for {request.time}",
                "alarm_id": alarm_info.alarm_id,
                "time": alarm_info.time_str,
                "active": alarm_info.active,
                "scheduled": alarm_info.scheduled,
                "next_execution": (
                    alarm_info.next_execution.isoformat()
                    if alarm_info.next_execution
                    else None
                ),
                "settings_used": {
                    "wake_up_sound": settings["wake_up_sound_id"],
                    "get_up_sound": settings["get_up_sound_id"],
                    "volume": settings["volume"],
                    "brightness": settings["max_brightness"],
                    "wake_up_duration": "9 minutes (fixed)",
                    "sunrise": "enabled (always)",
                },
            }
        except ValueError as e:
            if "already exists" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail=f"Alarm for time '{request.time}' already exists",
                )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create alarm: {str(e)}"
            )

    def _calculate_time_until(self, next_execution: datetime) -> str:
        """Calculate human-readable time until next execution"""
        if not next_execution:
            return None

        now = datetime.now()
        delta = next_execution - now

        if delta.total_seconds() < 0:
            return "Past due"

        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"

        return f"{minutes}m"

    def _generate_alarm_id(self, time_str: str) -> str:
        """Generate alarm ID from time string"""
        time_clean = time_str.replace(":", "_")
        return f"alarm_{time_clean}"
