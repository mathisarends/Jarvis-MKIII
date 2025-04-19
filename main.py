import asyncio
import traceback

from realtime.audio.microphone import PyAudioMicrophone
from realtime.audio.player import PyAudioPlayer
from realtime.config import OPENAI_API_KEY
from realtime.openai.handlers import process_openai_responses
from realtime.openai.session import create_openai_connection, initialize_session, send_audio_to_openai


async def main():
    """Main function"""
    # Check API key
    if not OPENAI_API_KEY:
        print("Error: OpenAI API key missing. Please specify in .env file.")
        return
    
    print("Connecting to OpenAI Realtime API...")
    
    # Establish WebSocket connection to OpenAI
    openai_ws = await create_openai_connection()
    if not openai_ws:
        return
    
    try:
        await initialize_session(openai_ws)
        
        mic_stream = PyAudioMicrophone()
        mic_stream.start_stream()
        
        audio_player = PyAudioPlayer()
        audio_player.start()
        
        try:
            await asyncio.gather(
                send_audio_to_openai(mic_stream, openai_ws),
                process_openai_responses(openai_ws, audio_player)
            )
        except asyncio.CancelledError:
            print("Tasks cancelled")
        finally:
            mic_stream.cleanup()
            audio_player.stop()
            await openai_ws.close()
    
    except Exception as e:
        print(f"Error in main loop: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("OpenAI Realtime API Microphone Demo")
    print("Press Ctrl+C to exit")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nUser interrupt - program terminating.")