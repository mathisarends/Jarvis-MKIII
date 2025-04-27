from langchain.tools import tool
from plugins.notion.clipboard.clipboard_workflow import create_clipboard_workflow

@tool
async def clipboard_tool(prompt: str) -> str:
    """
    Creates a structured entry in Notion's Jarvis Clipboard page based on the provided prompt
    and transcript from voice conversations.

    Args:
        prompt: A prompt describing what to write about, e.g. "Write a clipboard entry about XYZ topic"

    Returns:
        str: A confirmation message that the entry was added to Notion.
    """
    from core.speech.voice_assistant_controller import VoiceAssistantController

    voice_assistant_controller = VoiceAssistantController.get_instance()
    transcript = voice_assistant_controller.transcript.get_formatted_history()
    
    workflow = create_clipboard_workflow()
    
    initial_state = {
        "prompt": prompt,
        "transcript": transcript,
        "relevant_transcript": "",
        "formatted_content": "",
        "status": "EXTRACTING",
        "error": ""
    }
    
    result = await workflow.ainvoke(initial_state)
    
    if result["status"] == "ERROR":
        return result["error"]
    if result["status"] == "DONE" and not result["formatted_content"]:
        return "Could not find relevant content in the transcript for this topic."
    return "Successfully added note to Jarvis Clipboard in Notion."