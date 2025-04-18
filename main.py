import os
import json
import base64
import asyncio
import websockets
import pyaudio
import wave
from dotenv import load_dotenv

load_dotenv()

# Konfiguration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = 'alloy'
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Wichtige Event-Typen zum Loggen
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created', 'session.updated'
]

class MicrophoneStream:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_active = False
        self.audio_data = []
        
    def start_stream(self):
        """Mikrofon-Stream starten"""
        if self.stream is not None:
            self.stop_stream()
            
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        self.is_active = True
        self.audio_data = []
        print("Mikrofon-Stream gestartet")
        
    def stop_stream(self):
        """Mikrofon-Stream stoppen"""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.is_active = False
        print("Mikrofon-Stream gestoppt")
        
    def read_chunk(self):
        """Ein Chunk Audiodaten vom Mikrofon lesen"""
        if self.stream and self.is_active:
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            self.audio_data.append(data)
            return data
        return None
    
    def cleanup(self):
        """Ressourcen freigeben"""
        self.stop_stream()
        self.p.terminate()

async def initialize_session(openai_ws):
    """Initialisiere die Session mit OpenAI"""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "pcm16",  # Korrigiertes Format
            "output_audio_format": "pcm16", # Korrigiertes Format
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Session-Update wird gesendet...')
    await openai_ws.send(json.dumps(session_update))

async def send_audio_to_openai(mic_stream, openai_ws):
    """Audiodaten vom Mikrofon an OpenAI senden"""
    try:
        while mic_stream.is_active:
            data = mic_stream.read_chunk()
            if data:
                # Audio-Daten als Base64 kodieren
                base64_audio = base64.b64encode(data).decode('utf-8')
                
                # Event zum Anhängen von Audiodaten an den Puffer
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio
                }
                await openai_ws.send(json.dumps(audio_append))
            
            # Kleine Pause, um CPU-Last zu reduzieren
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"Fehler beim Senden von Audio: {e}")

async def process_openai_responses(openai_ws):
    """Empfange und verarbeite Antworten von OpenAI"""
    try:
        async for message in openai_ws:
            response = json.loads(message)
            event_type = response.get('type', '')
            
            # Wichtige Events loggen
            if event_type in LOG_EVENT_TYPES:
                print(f"Event empfangen: {event_type}")
                if event_type == 'error':
                    print("FEHLER:", response)
            
            # Text-Ausgabe verarbeiten
            if event_type == 'response.text.delta' and 'delta' in response:
                text = response['delta'].get('text', '')
                if text:
                    print(f"AI: {text}", end="", flush=True)
            
            # Audio-Ausgabe verarbeiten
            if event_type == 'response.audio.delta' and 'delta' in response:
                # Hier würden Sie den Audio-Ausgang abspielen
                # Für dieses einfache Beispiel geben wir nur aus, dass Audio empfangen wurde
                print(".", end="", flush=True)  # Zeigt an, dass Audio empfangen wurde
            
            # Ende einer Antwort
            if event_type == 'response.done':
                print("\n--- Antwort abgeschlossen ---")
    
    except Exception as e:
        print(f"Fehler bei der Verarbeitung der OpenAI-Antworten: {e}")

async def main():
    """Hauptfunktion"""
    # API-Schlüssel prüfen
    if not OPENAI_API_KEY:
        print("Fehler: OpenAI API-Schlüssel fehlt. Bitte in .env-Datei angeben.")
        return
    
    print("Verbindung zur OpenAI Realtime API wird hergestellt...")
    
    try:
        # WebSocket-Verbindung zu OpenAI mit der funktionierenden URL herstellen
        async with websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            print("Verbindung hergestellt!")
            
            # Session initialisieren
            await initialize_session(openai_ws)
            
            # Mikrofon-Stream erstellen
            mic_stream = MicrophoneStream()
            mic_stream.start_stream()
            
            try:
                # Beide Aufgaben parallel ausführen
                await asyncio.gather(
                    send_audio_to_openai(mic_stream, openai_ws),
                    process_openai_responses(openai_ws)
                )
            except asyncio.CancelledError:
                print("Aufgaben abgebrochen")
            finally:
                mic_stream.cleanup()
    
    except Exception as e:
        print(f"Fehler bei der Verbindung: {e}")

if __name__ == "__main__":
    print("OpenAI Realtime API Mikrofon-Demo")
    print("Drücken Sie Ctrl+C zum Beenden")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBenutzerabbruch - Programm wird beendet.")