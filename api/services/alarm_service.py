import os
import re
from datetime import datetime, timedelta

from fastapi import HTTPException

from api.dependencies.audio import get_alarm_system, get_audio_player
from api.models.alarm_models import (AlarmOptions, BrightnessRange,
                                     SoundOption, VolumeRange)


class AlarmService:
    def __init__(self):
        self.alarm_system = get_alarm_system()
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

    def play_sound(self, sound_id: str) -> dict:
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

    def get_global_settings(self) -> dict:
        """Get all global alarm settings"""
        try:
            settings = self.alarm_system.get_global_settings()
            return settings
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get settings: {str(e)}"
            )

    def create_alarm(self, alarm_id: str, time: str) -> dict:
        """Create a new alarm with global settings"""
        # Validate alarm_id
        if not alarm_id or not alarm_id.strip():
            raise HTTPException(status_code=400, detail="Alarm ID cannot be empty")
        
        if len(alarm_id) > 50:
            raise HTTPException(status_code=400, detail="Alarm ID too long (max 50 characters)")

        # Process time format
        try:
            time_str = self._process_time_input(time)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check if alarm already exists
        try:
            active_alarms = self.get_active_alarms()
            if alarm_id in active_alarms:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Alarm with ID '{alarm_id}' already exists"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to check existing alarms: {str(e)}"
            )

        # Create the alarm
        try:
            self.alarm_system.schedule_alarm(alarm_id, time_str)
            
            # Get current global settings for response
            settings = self.alarm_system.get_global_settings()
            
            return {
                "message": f"Alarm '{alarm_id}' scheduled for {time_str}",
                "alarm_id": alarm_id,
                "time": time_str,
                "settings_used": {
                    "wake_up_sound": settings["wake_up_sound_id"],
                    "get_up_sound": settings["get_up_sound_id"],
                    "volume": settings["volume"],
                    "brightness": settings["max_brightness"],
                    "wake_up_duration": "9 minutes (fixed)",
                    "sunrise": "enabled (always)"
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to create alarm: {str(e)}"
            )

    def cancel_alarm(self, alarm_id: str) -> dict:
        """Cancel an existing alarm"""
        if not alarm_id or not alarm_id.strip():
            raise HTTPException(status_code=400, detail="Alarm ID cannot be empty")

        try:
            active_alarms = self.get_active_alarms()
            if alarm_id not in active_alarms:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Alarm with ID '{alarm_id}' not found"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to check alarm existence: {str(e)}"
            )

        try:
            self.alarm_system.cancel_alarm(alarm_id)
            return {
                "message": f"Alarm '{alarm_id}' canceled successfully",
                "alarm_id": alarm_id
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to cancel alarm: {str(e)}"
            )

    def _process_time_input(self, time_input: str) -> str:
        """Process time input and convert to HH:MM format"""
        if not time_input or not time_input.strip():
            raise ValueError("Time cannot be empty")

        time_input = time_input.strip()

        if time_input.startswith('+'):
            try:
                seconds = int(time_input[1:])
                if seconds <= 0 or seconds > 86400:
                    raise ValueError("Seconds must be between 1 and 86400")
                
                future_time = datetime.now() + timedelta(seconds=seconds)
                return future_time.strftime("%H:%M")
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError("Invalid relative time format. Use +X for X seconds from now")
                raise e

        else:
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', time_input):
                raise ValueError("Invalid time format. Use HH:MM or +X")
            return time_input