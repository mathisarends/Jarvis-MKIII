import asyncio
import logging
import os
import random
from dotenv import load_dotenv

from audio.py_audio_player import PyAudioPlayer
from audio.audio_player_factory import AudioPlayerFactory
from utils.logging_mixin import setup_logging
from speech.voice_assistant_controller import VoiceAssistantController


async def main():
    """Main entry point for the voice assistant application"""
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file")
        return

    if not os.getenv("PICO_ACCESS_KEY"):
        print("Error: PICO_ACCESS_KEY not found in .env file")
        return

    setup_logging()
    logger = logging.getLogger("main")

    logger.info("Starting voice assistant...")

    AudioPlayerFactory.initialize_with(PyAudioPlayer)

    voice_assistant = VoiceAssistantController(wake_word="jarvis", sensitivity=0.7)

    try:
        await voice_assistant.run()
        logger.info("Voice assistant is running...") # This print is important for interrupting logic (why idk)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected")
    finally:
        await voice_assistant.stop()
        logger.info("Application terminated")


if __name__ == "__main__":
    print("🎙️  Voice Assistant with Wake Word Detection")
    print("   Say the wake word to start a conversation")
    print("   Press Ctrl+C to exit")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nUser interrupted - program terminating.")
