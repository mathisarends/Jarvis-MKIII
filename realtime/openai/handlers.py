import json
import traceback
from realtime.config import LOG_EVENT_TYPES

async def process_openai_responses(openai_ws, audio_player):
    """Receive and process responses from OpenAI"""
    try:
        async for message in openai_ws:
            # Debug the raw message to see what we're receiving (truncated to avoid flooding)
            print(f"DEBUG - Raw message: {message[:100]}...")
            
            try:
                response = json.loads(message)
                # Check if response is actually a dictionary
                if not isinstance(response, dict):
                    print(f"Warning: Response is not a dictionary, it's a {type(response)}")
                    continue
                
                event_type = response.get('type', '')
                
                # Log important events
                if event_type in LOG_EVENT_TYPES:
                    print(f"Event received: {event_type}")
                    if event_type == 'error':
                        print("ERROR:", response)
                
                # Process text output
                if event_type == 'response.text.delta' and 'delta' in response:
                    handle_text_response(response)
                
                # Process audio output
                if event_type == 'response.audio.delta':
                    handle_audio_response(response, audio_player)
                
                # End of response
                if event_type == 'response.done':
                    print("\n--- Response completed ---")
                    
            except json.JSONDecodeError:
                print("Warning: Received non-JSON message from server")
    
    except Exception as e:
        print(f"Error processing OpenAI responses: {e}")
        traceback.print_exc()  # Print the full stack trace for better debugging


def handle_text_response(response):
    """Handle text responses from OpenAI"""
    if isinstance(response.get('delta'), dict):
        text = response['delta'].get('text', '')
        if text:
            print(f"AI: {text}", end="", flush=True)


def handle_audio_response(response, audio_player):
    """Handle audio responses from OpenAI"""
    base64_audio = response.get('delta', '')
    if base64_audio and isinstance(base64_audio, str):
        audio_player.add_audio_chunk(base64_audio)
        print(".", end="", flush=True)  # Indicates audio was received