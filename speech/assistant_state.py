from enum import Enum, auto


class AssistantState(Enum):
    """Enumeration of possible assistant states"""

    IDLE = auto()
    LISTENING = auto()
    RESPONDING = auto()
