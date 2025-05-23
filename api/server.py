import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import alarms
from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.py_audio_player import PyAudioPlayer
from plugins.alarm.daylight_alarm import AlarmSystem

AudioPlayerFactory.initialize_with(PyAudioPlayer)
alarm_system = AlarmSystem.get_instance()

app = FastAPI(
    title="Jarvis Alarm API",
    description="API für Alarm Management mit Sound-Integration",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://192.168.178.64:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(alarms.router, prefix="/alarms", tags=["alarms"])


@app.get("/", tags=["health"])
def health_check():
    return {"message": "Jarvis Alarm API", "status": "healthy"}


if __name__ == "__main__":
    print("Starting FastAPI server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
