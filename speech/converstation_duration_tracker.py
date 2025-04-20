import time


class ConversationDurationTracker:
    """
    A simple class for tracking the duration of a conversation.

    Manages start and end time and provides methods to query the current
    conversation duration in milliseconds.
    """

    def __init__(self):
        """Initializes the tracker in an inactive state."""
        self._start_time_ms = 0
        self._active = False

    def start_conversation(self):
        """Starts tracking a new conversation."""
        self._start_time_ms = self._get_current_time_ms()
        self._active = True
        return self._start_time_ms

    def end_conversation(self):
        """
        Stops tracking the current conversation.

        Returns:
            int: Duration of the ended conversation in milliseconds
        """
        duration = self.duration_ms
        self._active = False
        return duration

    @staticmethod
    def _get_current_time_ms():
        """
        Returns the current time in milliseconds.

        Returns:
            int: Current time in milliseconds
        """
        return int(time.time() * 1000)

    @property
    def current_time_ms(self):
        """
        Property that returns the current time in milliseconds.

        Returns:
            int: Current time in milliseconds
        """
        return self._get_current_time_ms()

    @property
    def duration_ms(self):
        """
        Property that returns the current conversation duration in milliseconds.

        Returns:
            int: Duration in milliseconds or 0 if no conversation is active
        """
        if not self._active:
            return 0

        current_time = self._get_current_time_ms()
        return current_time - self._start_time_ms

    @property
    def is_active(self):
        """
        Property indicating whether a conversation is currently being tracked.

        Returns:
            bool: True if a conversation is active, otherwise False
        """
        return self._active
