class TranscriptManager:
    """Manages conversation transcripts"""

    def __init__(self):
        self._current_user = ""
        self._current_assistant = ""
        self.full_history = []

    @property
    def current_user(self):
        """Get the current user transcript"""
        return self._current_user

    @current_user.setter
    def current_user(self, value):
        """Set the current user transcript"""
        self._current_user = value

    @property
    def current_assistant(self):
        """Get the current assistant transcript"""
        return self._current_assistant

    @current_assistant.setter
    def current_assistant(self, value):
        """Set the current assistant transcript"""
        self._current_assistant = value

    def add_to_history(self, speaker, text):
        """Add a message to the full conversation history"""
        self.full_history.append((speaker, text))

    def get_formatted_history(self):
        """Get the full conversation history as formatted text"""
        result = ""
        for speaker, text in self.full_history:
            result += f"{speaker}: {text}\n\n"
        return result.strip()

    def reset_current(self):
        """Reset the current transcripts"""
        self._current_user = ""
        self._current_assistant = ""
