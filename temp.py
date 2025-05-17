from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.py_audio_player import PyAudioPlayer

if __name__ == "__main__":
    print("🔊 Testing Sonos Queue Functionality with Pomodoro Phrases")
    #
    player = AudioPlayerFactory.initialize_with(PyAudioPlayer)

    player.play_sound("audio_chunk_15.mp3")
