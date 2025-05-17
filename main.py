import asyncio
import logging
import os

from dotenv import load_dotenv

from core.audio.audio_player_factory import AudioPlayerFactory

""" from core.audio.py_audio_player import PyAudioPlayer """
from core.audio.py_audio_player import PyAudioPlayer
from core.audio.sonos_audio_player import SonosPlayer
from core.speech.voice_assistant_controller import VoiceAssistantController
from shared.logging_mixin import setup_logging


async def main():
    """Main entry point for the voice assistant application"""
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file")
        return

    setup_logging()
    logger = logging.getLogger("main")

    logger.info("Starting voice assistant...")

    AudioPlayerFactory.initialize_with(SonosPlayer)
    """ await LightController.create() """

    try:
        voice_assistant = VoiceAssistantController(
            wake_word="picovoice", sensitivity=0.7
        )
        await voice_assistant.run()
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
