from contextlib import asynccontextmanager

from notionary import NotionPage


class ClipboardPage:
    def __init__(self):
        """
        Initialize the ClipboardPage.
        """
        self.page = None

    async def initialize(self):
        """Initialize the Notion page."""
        self.page = await NotionPage.from_page_name("Jarvis Clipboard")
        self.page.block_registry = (
            self.page.block_registry_builder
            .with_headings()
            .with_callouts()
            .with_paragraphs()
            .with_numbered_list()
            .with_bulleted_list()
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

        return self.page.block_registry.get_notion_markdown_syntax_prompt()
