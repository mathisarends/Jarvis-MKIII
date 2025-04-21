import textwrap
from contextlib import asynccontextmanager
from notionary import NotionPageFactory, BlockElementRegistryBuilder

from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


# TODO: Dieses Clipbboard-Tool hier OP machen (Muss hier beim Start der Anwendung aufgerufen werden, um den Workflow zu beschleunigen)
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
    # Get transcript from voice assistant
    from speech.voice_assistant_controller import VoiceAssistantController
    
    voice_assistant_controller = VoiceAssistantController()
    transcript = voice_assistant_controller.full_transcript

    clipboard = ClipboardPage()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2,
        disable_streaming=True,
    )

    try:
        async with clipboard.session() as session:
            # Get the formatting system prompt
            formatting_prompt = session.get_formatting_system_prompt()

            # First, extract the relevant part from the transcript
            extraction_prompt = textwrap.dedent(
                f"""
You need to analyze a conversation transcript and extract ONLY the part that is relevant 
to the following topic/request:

"{prompt}"

Instructions:
1. Carefully identify the specific section(s) in the transcript that directly relate to this topic
2. Extract ONLY the relevant parts - ignore unrelated conversation
3. Preserve the dialogue format but include only what's needed for the topic
4. If nothing in the transcript relates to the topic, respond with "No relevant content found"

Here's the transcript:

{transcript}
"""
            )

            extraction_response = await llm.ainvoke(
                [HumanMessage(content=extraction_prompt)]
            )

            relevant_transcript = extraction_response.content.strip()

            if "No relevant content found" in relevant_transcript:
                return (
                    "Could not find relevant content in the transcript for this topic."
                )

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
Here's the prompt: {prompt}

And here's the relevant part of the conversation:

{relevant_transcript}

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

            await session.add_note(formatted_content)

            return "Successfully added note to Jarvis Clipboard in Notion."
    except Exception as e:
        error_type = type(e).__name__
        return f"Error creating clipboard entry ({error_type}): {e}"


class ClipboardPage:
    def __init__(self):
        """
        Initialize the ClipboardPage.
        """
        self.page = None

    async def initialize(self):
        """Initialize the Notion page."""
        self.page = await NotionPageFactory.from_page_name("Jarvis Clipboard")
        self.page.block_registry = (
            BlockElementRegistryBuilder()
            .start_minimal()
            .with_dividers()
            .with_todos()
            .with_code()
            .build()
        )

    @asynccontextmanager
    async def session(self):
        """
        Context manager for ClipboardPage session.
        Ensures the Notion page is properly initialized.
        """
        await self.initialize()
        yield self

    async def add_note(self, content):
        """
        Add a note to the Notion page.

        Args:
            content: Markdown content to add.
        """
        if not self.page:
            await self.initialize()

        await self.page.append_markdown(markdown=content)

    def get_formatting_system_prompt(self) -> str:
        """
        Format the prompt for Notion.
        """
        if not self.page:
            raise ValueError("Page not initialized. Call initialize() first.")

        return self.page.block_registry.generate_llm_prompt()
