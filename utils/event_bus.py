"""
Implementation of an Event Bus system to avoid property drilling.
"""
from enum import Enum, auto
import asyncio
from typing import Dict, List, Callable, Any


class EventType(Enum):
    """Enumeration for all possible event types."""
    USER_SPEECH_STARTED = auto()
    ASSISTANT_RESPONSE_COMPLETED = auto()
    TRANSCRIPT_UPDATED = auto()
    WAKE_WORD_DETECTED = auto()


class EventBus:
    """
    A central EventBus class that mediates events between components
    without them needing to know about each other.
    """
    _instance = None
    _subscribers: Dict[EventType, List[Callable[[Any], None]]]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {event_type: [] for event_type in EventType}
        return cls._instance

    def subscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> None:
        """
        Registers a callback for a specific event type.
        
        Args:
            event_type: The type of the event to subscribe to
            callback: The function to be called when the event is published
        """
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> None:
        """
        Removes a callback for a specific event type.
        
        Args:
            event_type: The type of the event to unsubscribe from
            callback: The callback function to remove
        """
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event_type: EventType, data: Any = None) -> None:
        """
        Publishes an event to all registered subscribers.
        
        Args:
            event_type: The type of the event
            data: Optional data to pass to subscribers
        """
        for callback in self._subscribers[event_type]:
            callback(data)

    async def publish_async(self, event_type: EventType, data: Any = None) -> None:
        """
        Publishes an event asynchronously to all registered subscribers.
        
        Args:
            event_type: The type of the event
            data: Optional data to pass to subscribers
        """
        for callback in self._subscribers[event_type]:
            if asyncio.iscoroutinefunction(callback):
                return await callback(data)
            
            # Otherwise, execute it directly (optionally wrap in executor if heavy)
            callback(data)
