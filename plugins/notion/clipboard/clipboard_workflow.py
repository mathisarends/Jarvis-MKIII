import textwrap
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from core.llm.llm_factory import LLMFactory
from plugins.notion.clipboard.clipboard_page import ClipboardPage


class ClipboardState(TypedDict):
    prompt: str
    transcript: str
    relevant_transcript: str
    formatted_content: str
    status: Literal["EXTRACTING", "FORMATTING", "DONE", "ERROR"]
    error: str


async def extract_relevant_content(state: ClipboardState) -> ClipboardState:
    """Extrahiert den relevanten Teil aus dem Transkript basierend auf dem Prompt."""
    try:
        llm = LLMFactory.create_gemini_flash()
        
        extraction_prompt = textwrap.dedent(
            f"""
You need to analyze a conversation transcript and extract ONLY the part that is relevant 
to the following topic/request:

"{state['prompt']}"

Instructions:
1. Carefully identify the specific section(s) in the transcript that directly relate to this topic
2. Extract ONLY the relevant parts - ignore unrelated conversation
3. Preserve the dialogue format but include only what's needed for the topic
4. If nothing in the transcript relates to the topic, respond with "No relevant content found"

Here's the transcript:

{state['transcript']}
"""
        )

        extraction_response = await llm.ainvoke(
            [HumanMessage(content=extraction_prompt)]
        )

        relevant_transcript = extraction_response.content.strip()
        
        return {
            **state, 
            "relevant_transcript": relevant_transcript,
            "status": "FORMATTING" if "No relevant content found" not in relevant_transcript else "DONE",
            "formatted_content": "Could not find relevant content in the transcript for this topic." if "No relevant content found" in relevant_transcript else ""
        }
    except Exception as e:
        error_type = type(e).__name__
        return {
            **state,
            "status": "ERROR",
            "error": f"Error extracting relevant content ({error_type}): {e}"
        }


async def format_and_save_content(state: ClipboardState) -> ClipboardState:
    """Formatiert den relevanten Inhalt als strukturierte Notiz und speichert diese in Notion."""
    try:
        llm = LLMFactory.create_gemini_flash()
        clipboard = ClipboardPage()
        
        async with clipboard.session() as session:
            # Get the formatting system prompt
            formatting_prompt = session.get_formatting_system_prompt()

            system_prompt = textwrap.dedent(
                f"""
You are an expert in knowledge management and note-taking.

Your task is to transform the relevant part of a conversation transcript into a well-structured, 
concise note for a Second Brain system in Notion.

{formatting_prompt}

Follow these guidelines:
1. Create a clear title that reflects the main topic
2. Include a brief summary/overview at the beginning
3. Extract and organize key ideas, insights, and facts
4. Use proper headings, bullet points, and formatting
5. Include any relevant action items or follow-ups
6. Be concise yet comprehensive - focus on valuable information
7. Maintain a neutral, professional tone

Format the output as clean Markdown suitable for Notion.
"""
            )

            human_prompt = textwrap.dedent(
                f"""
Here's the prompt: {state['prompt']}

And here's the relevant part of the conversation:

{state['relevant_transcript']}

Please create a well-structured note that captures the key information.
"""
            )

            response = await llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_prompt),
                ]
            )

            formatted_content = response.content.strip()
            
            # Speichern der Notiz in Notion
            await session.add_note(formatted_content)
            
            return {
                **state,
                "formatted_content": formatted_content,
                "status": "DONE"
            }
    except Exception as e:
        error_type = type(e).__name__
        return {
            **state,
            "status": "ERROR",
            "error": f"Error formatting and saving content ({error_type}): {e}"
        }


def create_clipboard_workflow():
    """Erstellt den LangGraph Workflow für das Clipboard Tool."""
    workflow = StateGraph(ClipboardState)
    
    workflow.add_node("extract_relevant_content", extract_relevant_content)
    workflow.add_node("format_and_save_content", format_and_save_content)
    
    # Korrekte Definition der bedingten Kanten
    workflow.add_conditional_edges(
        "extract_relevant_content",
        lambda state: "format_and_save" if state["status"] == "FORMATTING" else "end",
        {
            "format_and_save": "format_and_save_content",
            "end": END
        }
    )
    workflow.add_edge("format_and_save_content", END)
    
    workflow.set_entry_point("extract_relevant_content")
    
    return workflow.compile()