import asyncio
import os

from core.audio.sonos_audio_player import SonosPlayer


async def main():
    """Test the Sonos queue functionality with pomodoro phrases."""

    player = SonosPlayer()

    # Update the sounds_dir to explicitly point to the pomodoro_phrases folder
    player.sounds_dir = os.path.join(
        player.project_dir, "resources", "sounds", "pomodoro_phrases"
    )
    print(f"Using sounds directory: {player.sounds_dir}")

    # Start the HTTP server and connect to the Sonos device
    player.start()

    # Wait a bit for initialization
    await asyncio.sleep(2)

    # Run the test
    success = player.test_sonos_queue_functionality()
    print(f"Test completed with {'success' if success else 'failure'}")

    # Wait for audio to finish
    await asyncio.sleep(30)

    # Clean up
    player.stop()
    print("Test finished")


if __name__ == "__main__":
    print("🔊 Testing Sonos Queue Functionality with Pomodoro Phrases")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nUser interrupted - program terminating.")
