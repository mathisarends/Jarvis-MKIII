import re
from typing import Optional

from pydantic import BaseModel, Field, validator


class SoundOption(BaseModel):
    id: str
    label: str


class VolumeRange(BaseModel):
    min: float = 0.0
    max: float = 1.0
    default: float = 0.5


class BrightnessRange(BaseModel):
    min: int = 0
    max: int = 100
    default: int = 100


class AlarmOptions(BaseModel):
    wake_up_sounds: list[SoundOption]
    get_up_sounds: list[SoundOption]
    volume_range: VolumeRange
    brightness_range: BrightnessRange


class AlarmRequest(BaseModel):
    alarm_id: str = Field(
        ..., min_length=1, max_length=50, description="Unique identifier for the alarm"
    )
    time: str = Field(
        ..., description="Time in HH:MM format or +X for X seconds from now"
    )
    wake_up_sound_id: Optional[str] = Field(None, description="ID of the wake-up sound")
    get_up_sound_id: Optional[str] = Field(None, description="ID of the get-up sound")
    volume: float = Field(
        0.5, ge=0.0, le=1.0, description="Volume level between 0.0 and 1.0"
    )
    max_brightness: float = Field(
        100, ge=0, le=100, description="Maximum brightness between 0 and 100"
    )
    wake_up_timer_duration: int = Field(
        300,
        gt=0,
        le=3600,
        description="Duration in seconds between wake-up and get-up alarms",
    )

    @validator("time")
    def validate_time_format(cls, v):
        if v.startswith("+"):
            try:
                seconds = int(v[1:])
                if seconds <= 0 or seconds > 86400:
                    raise ValueError("Seconds must be between 1 and 86400")
                return v
            except ValueError:
                raise ValueError(
                    "Invalid relative time format. Use +X for X seconds from now"
                )
        else:
            if not re.match(r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$", v):
                raise ValueError("Invalid time format. Use HH:MM")
            return v


class PlaySoundResponse(BaseModel):
    message: str
    sound_id: str
    category: str
    filename: str


class StopSoundResponse(BaseModel):
    message: str
    status: str


class BrightnessRequest(BaseModel):
    brightness: float = Field(
        ..., ge=0, le=100, description="Brightness value between 0 and 100"
    )


class VolumeRequest(BaseModel):
    volume: float = Field(
        ..., ge=0.0, le=1.0, description="Volume value between 0.0 and 1.0"
    )


class SoundRequest(BaseModel):
    sound_id: str = Field(..., min_length=1, description="Sound ID")
