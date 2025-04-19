import asyncio
from realtime.config import OPENAI_API_KEY
from realtime.audio.player import PyAudioPlayer
from realtime.audio.microphone import PyAudioMicrophone
from realtime.realtime_api import OpenAIRealtimeAPI

async def main():
    if not OPENAI_API_KEY:
        print("Fehler: OpenAI API-Key fehlt. Bitte in .env-Datei angeben.")
        return
    
    openai_api = OpenAIRealtimeAPI()
    
    mic_stream = PyAudioMicrophone()
    audio_player = PyAudioPlayer()
    
    # Streams starten
    mic_stream.start_stream()
    audio_player.start()
    
    try:
        def custom_transcript_handler(response):
            """Benutzerdefinierter Handler für Transkriptionen"""
            delta = response.get('delta', '')
            if delta:
                print(f"\n🎤 Du hast gesagt: {delta}", flush=True)
        
        await openai_api.setup_and_run(
            mic_stream, 
            audio_player,
            handle_transcript=custom_transcript_handler
        )
    finally:
        mic_stream.cleanup()
        audio_player.stop()

if __name__ == "__main__":
    print("OpenAI Realtime API Demo")
    print("Drücke Strg+C zum Beenden")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBenutzereingabe - Programm wird beendet.")