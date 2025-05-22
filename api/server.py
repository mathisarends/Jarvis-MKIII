import os
import re
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React Development Server (Create React App)
        "http://localhost:5173",    # Vite Development Server
        "http://192.168.178.64:5173",  # Deine spezifische IP
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Erlaubt alle HTTP-Methoden (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Erlaubt alle Headers
)

# Path to sounds directory
SOUNDS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
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


@app.post("/alarms/play/{sound_id:path}")
def play_sound(sound_id: str):
    """
    Play a sound using the audio player.
    
    Args:
        sound_id: The full sound ID (e.g., "wake_up_sounds/wake-up-focus")
        
    Returns:
        Success message with sound details
    """
    # Validate sound ID format
    if '/' not in sound_id:
        raise HTTPException(
            status_code=400, 
            detail="Invalid sound ID format. Use 'category/filename' (e.g., 'wake_up_sounds/wake-up-focus')"
        )
    
    # Split sound ID into category and filename
    try:
        category, filename = sound_id.split('/', 1)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid sound ID format. Use 'category/filename'"
        )
    
    # Validate sound ID against available options
    wake_up_options = alarm_system.get_wake_up_sound_options()
    get_up_options = alarm_system.get_get_up_sound_options()
    
    valid_sound_ids = [option.value for option in wake_up_options] + [option.value for option in get_up_options]
    
    print(f"[Play] Attempting to play sound ID: '{sound_id}' from valid IDs: {valid_sound_ids}")
    
    if sound_id not in valid_sound_ids:
        raise HTTPException(
            status_code=404, 
            detail=f"Sound ID '{sound_id}' not found. Available sounds: {valid_sound_ids}"
        )
    
    # Check if the file exists on disk
    file_path = os.path.join(SOUNDS_DIR, category, f"{filename}.mp3")
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Sound file not found on disk for ID: '{sound_id}'"
        )
    
    # Get the shared audio player instance and play the sound
    try:
        audio_player = AudioPlayerFactory.get_shared_instance()
        audio_player.play_sound(sound_id)
        
        return {
            "message": f"Successfully started playing sound: {filename}",
            "sound_id": sound_id,
            "category": category,
            "filename": filename
        }
        
    except Exception as e:
        print(f"[Play] Error playing sound '{sound_id}': {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to play sound '{sound_id}': {str(e)}"
        )
        
@app.post("/alarms/stop")
def stop_sound():
    """
    Stop the currently playing sound.
    
    Returns:
        Success message confirming sound was stopped
    """
    try:
        audio_player = AudioPlayerFactory.get_shared_instance()
        audio_player.stop_sound()
        
        return {
            "message": "Successfully stopped audio playback",
            "status": "stopped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Stop] Error stopping sound: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to stop sound: {str(e)}"
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
