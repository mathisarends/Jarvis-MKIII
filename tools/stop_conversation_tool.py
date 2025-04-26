import time
import threading
from langchain.tools import tool


@tool
def stop_conversation_tool() -> str:
    """
    Stops the current voice assistant conversation explicitly after playing a goodbye sound.

    Use this tool when the user explicitly requests to end the conversation by
    saying "stop" or otherwise clearly expressing they want to terminate the interaction.
    Only invoke this tool in response to a direct stop command or equivalent expression.

    Returns:
        A confirmation message that the conversation has been stopped
    """
    from speech.voice_assistant_controller import VoiceAssistantController

    def delayed_stop():
        time.sleep(4)
        controller = VoiceAssistantController.get_instance()
        controller.stop_conversation_loop()

    stop_thread = threading.Thread(target=delayed_stop)
    stop_thread.daemon = True
    stop_thread.start()

    return "Conversation will end in a few seconds."
