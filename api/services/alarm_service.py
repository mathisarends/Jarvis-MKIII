import os

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
