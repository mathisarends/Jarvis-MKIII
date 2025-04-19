import json
import base64
import asyncio
import websockets
from realtime.config import (
    OPENAI_WEBSOCKET_URL, 
    OPENAI_HEADERS, 
    SYSTEM_MESSAGE, 
    VOICE
)

async def initialize_session(openai_ws):
    """Initialize the session with OpenAI"""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Sending session update...')
    await openai_ws.send(json.dumps(session_update))

async def create_openai_connection():
    """Create and return a WebSocket connection to OpenAI"""
    try:
        connection = await websockets.connect(
            OPENAI_WEBSOCKET_URL,
            extra_headers=OPENAI_HEADERS
        )
        print("Connection established!")
        return connection
    except Exception as e:
        print(f"Connection error: {e}")
        return None

async def send_audio_to_openai(mic_stream, openai_ws):
    """Send audio data from the microphone to OpenAI"""
    try:
        while mic_stream.is_active:
            data = mic_stream.read_chunk()
            if data:
                # Encode audio data as Base64
                base64_audio = base64.b64encode(data).decode('utf-8')
                
                # Event to append audio data to the buffer
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio
                }
                await openai_ws.send(json.dumps(audio_append))
            
            # Small pause to reduce CPU load
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"Error sending audio: {e}")