import os
import re
from datetime import datetime, time, timedelta
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.py_audio_player import PyAudioPlayer
from plugins.alarm.daylight_alarm import AlarmSystem

# Initialize audio system
AudioPlayerFactory.initialize_with(PyAudioPlayer)
alarm_system = AlarmSystem.get_instance()

# Create a FastAPI application
app = FastAPI(title="Jarvis Alarm API")

# Path to sounds directory
SOUNDS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "resources",
    "sounds"
)

class AlarmRequest(BaseModel):
    alarm_id: str = Field(..., description="Unique identifier for the alarm")
    time: str = Field(..., description="Time in HH:MM format or +X for X seconds from now")
    wake_up_sound_id: Optional[str] = Field(None, description="ID of the wake-up sound")
    get_up_sound_id: Optional[str] = Field(None, description="ID of the get-up sound")
    volume: float = Field(0.5, description="Volume level between 0.0 and 1.0", ge=0.0, le=1.0)
    max_brightness: float = Field(100, description="Maximum brightness between 0 and 100", ge=0, le=100)
    wake_up_timer_duration: int = Field(300, description="Duration in seconds between wake-up and get-up alarms", gt=0)

class AlarmCancelRequest(BaseModel):
    alarm_id: str = Field(..., description="ID of the alarm to cancel")

class AlarmListResponse(BaseModel):
    alarm_ids: list[str]

@app.get("/")
def hello_world():
    return {"message": "Jarvis Alarm API"}

@app.get("/alarms/sounds/wake-up")
def get_wake_up_sounds():
    """Get available wake-up sounds"""
    options = alarm_system.get_wake_up_sound_options()
    return [{"id": option.value, "label": option.label} for option in options]

@app.get("/alarms/sounds/get-up")
def get_get_up_sounds():
    """Get available get-up sounds"""
    options = alarm_system.get_get_up_sound_options()
    return [{"id": option.value, "label": option.label} for option in options]

@app.get("/alarms/options")
def get_alarm_options():
    """Get all alarm configuration options in a single endpoint"""
    wake_up_options = alarm_system.get_wake_up_sound_options()
    get_up_options = alarm_system.get_get_up_sound_options()
    
    return {
        "wake_up_sounds": [{"id": option.value, "label": option.label} for option in wake_up_options],
        "get_up_sounds": [{"id": option.value, "label": option.label} for option in get_up_options],
        "volume_range": {
            "min": 0.0,
            "max": 1.0,
            "default": 0.5
        },
        "brightness_range": {
            "min": 0,
            "max": 100,
            "default": 100
        }
    }

@app.get("/alarms/sounds")
def get_sound_file_by_query(sound_category: str = None, sound_id: str = None):
    """
    Get the MP3 file using query parameters.
    
    This endpoint can be used in two ways:
    1. ?sound_id=wake_up_sounds/wake-up-focus (full sound ID)
    2. ?sound_category=wake_up_sounds&sound_id=wake-up-focus (category and sound ID separately)
    
    Args:
        sound_category: Optional category of the sound
        sound_id: Either the full sound ID (with category) or just the filename part
        
    Returns:
        The MP3 file as a download
    """
    # Handle different query parameter combinations
    if sound_id and '/' in sound_id:
        # Full sound ID is provided
        category, filename = sound_id.split('/', 1)
    elif sound_category and sound_id:
        # Category and filename are provided separately
        category = sound_category
        filename = sound_id
    else:
        raise HTTPException(
            status_code=400, 
            detail="Invalid request. Use either ?sound_id=category/filename or ?sound_category=category&sound_id=filename"
        )
    
    full_sound_id = f"{category}/{filename}"
    
    # Validate sound ID
    wake_up_options = alarm_system.get_wake_up_sound_options()
    get_up_options = alarm_system.get_get_up_sound_options()
    
    valid_sound_ids = [option.value for option in wake_up_options] + [option.value for option in get_up_options]
    
    print(f"[Query] Looking for sound ID: '{full_sound_id}' in valid IDs: {valid_sound_ids}")
    
    if full_sound_id not in valid_sound_ids:
        raise HTTPException(status_code=404, detail=f"Sound ID '{full_sound_id}' not found")
    
    file_path = os.path.join(SOUNDS_DIR, category, f"{filename}.mp3")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Sound file not found for ID: '{full_sound_id}'")
    
    # Return the file as a download with the appropriate media type
    return FileResponse(
        path=file_path, 
        media_type="audio/mpeg",
        filename=f"{filename}.mp3"
    )

@app.get("/alarms", response_model=AlarmListResponse)
def list_alarms():
    """List all active alarms"""
    return {"alarm_ids": list(alarm_system._active_alarms.keys())}

@app.post("/alarms")
def create_alarm(alarm: AlarmRequest):
    """Create a new alarm"""
    # Validate time format
    if alarm.time.startswith('+'):
        try:
            seconds = int(alarm.time[1:])
            time_str = (datetime.now() + timedelta(seconds=seconds)).strftime("%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use +X for X seconds from now")
    else:
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', alarm.time):
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
        time_str = alarm.time
    
    # Configure wake up timer duration
    alarm_system.wake_up_timer_duration = alarm.wake_up_timer_duration
    
    # Check if alarm ID already exists
    if alarm.alarm_id in alarm_system._active_alarms:
        raise HTTPException(status_code=409, detail=f"Alarm with ID '{alarm.alarm_id}' already exists")
    
    # Schedule the alarm
    try:
        alarm_system.schedule_alarm(
            alarm.alarm_id,
            time_str,
            wake_up_sound_id=alarm.wake_up_sound_id,
            get_up_sound_id=alarm.get_up_sound_id,
            volume=alarm.volume,
            max_brightness=alarm.max_brightness
        )
        return {"message": f"Alarm scheduled for {time_str}", "alarm_id": alarm.alarm_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule alarm: {str(e)}")

@app.delete("/alarms/{alarm_id}")
def cancel_alarm(alarm_id: str):
    """Cancel an existing alarm"""
    if alarm_id not in alarm_system._active_alarms:
        raise HTTPException(status_code=404, detail=f"Alarm with ID '{alarm_id}' not found")
    
    try:
        alarm_system.cancel_alarm(alarm_id)
        return {"message": f"Alarm '{alarm_id}' canceled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel alarm: {str(e)}")

if __name__ == "__main__":
    print("Starting FastAPI server on http://localhost:8000")
    # Run the server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
