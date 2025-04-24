import random
from langchain.tools import tool

from audio.audio_player_factory import AudioPlayerFactory


@tool
def stop_conversation_tool() -> str:
    """
    Stops the current voice assistant conversation explicitly.
    
    Use this tool when the user explicitly requests to end the conversation by
    saying "stop" or otherwise clearly expressing they want to terminate the interaction.
    Only invoke this tool in response to a direct stop command or equivalent expression.
    
    Returns:
        A confirmation message that the conversation has been stopped
    """
    from speech.voice_assistant_controller import VoiceAssistantController
    
    controller = VoiceAssistantController()
    controller.stop_conversation_loop()
    
    audio_player = AudioPlayerFactory.get_shared_instance()
    
    random_number = random.randint(1, 6)
    sound_file = f"conversation_end_phrases/tts_conversation_end_{random_number}"
    audio_player.play_sound(sound_file)
    
    
    return "Conversation stopped."
    
