from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.py_audio_player import PyAudioPlayer
from core.audio.sonos_audio_player import SonosPlayer

audio_system_router = APIRouter()

class AudioSystem(BaseModel):
    id: str
    name: str
    description: str
    active: bool

class AudioSystemsResponse(BaseModel):
    systems: List[AudioSystem]

class SwitchSystemRequest(BaseModel):
    system_id: str

REGISTERED_SYSTEMS = {
    "usb_speaker": {
        "class": PyAudioPlayer,
        "name": "USB-Lautsprecher",
        "description": "Computer Lautsprecher"
    },
    "sonos_era_100": {
        "class": SonosPlayer,
        "name": "Sonos Era 100", 
        "description": "Wohnzimmer Lautsprecher"
    }
}

def get_current_active_system() -> str:
    """Ermittelt welches System aktuell aktiv ist"""
    current_class = AudioPlayerFactory.get_current_strategy()
    for system_id, system_info in REGISTERED_SYSTEMS.items():
        if system_info["class"] == current_class:
            return system_id
    
    return "usb_speaker"

@audio_system_router.get("/systems", response_model=AudioSystemsResponse)
async def get_audio_systems():
    """Alle registrierten Audio-Systeme mit aktivem Status"""
    current_active = get_current_active_system()
    
    systems = []
    for system_id, system_info in REGISTERED_SYSTEMS.items():
        systems.append(AudioSystem(
            id=system_id,
            name=system_info["name"],
            description=system_info["description"],
            active=system_id == current_active
        ))
    
    return AudioSystemsResponse(systems=systems)

@audio_system_router.put("/{system_id}/activate")
async def switch_audio_system(system_id: str):
    """Zu anderem Audio-System wechseln"""
    if system_id not in REGISTERED_SYSTEMS:
        raise HTTPException(
            status_code=404,
            detail=f"Audio-System '{system_id}' nicht gefunden"
        )
    
    system_info = REGISTERED_SYSTEMS[system_id]
    
    try:
        AudioPlayerFactory.set_strategy(system_info["class"], play_test_sound=False)
        AudioPlayerFactory.get_shared_instance().play_sound("sound_check")
        
        return {
            "message": f"Erfolgreich zu {system_info['name']} gewechselt",
            "system_id": system_id,
            "system_name": system_info["name"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Wechseln zu '{system_id}': {str(e)}"
        )