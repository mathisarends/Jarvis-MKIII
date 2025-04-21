"""
Implementation of an Event Bus system to avoid property drilling.
"""

from enum import Enum, auto
import asyncio
import inspect
from typing import Dict, List, Callable, Any


class EventType(Enum):
    """Enumeration for all possible event types."""

    USER_SPEECH_STARTED = auto()
    ASSISTANT_RESPONSE_COMPLETED = auto()
    TRANSCRIPT_UPDATED = auto()


class EventBus:
    """
    A central EventBus class that mediates events between components
    without them needing to know about each other.

    Features:
    - Singleton pattern ensures a single event bus throughout the application
    - Parameter-safe callback invocation handles different method signatures
    - Support for both synchronous and asynchronous event publishing
    """

    _instance = None
    _subscribers: Dict[EventType, List[Callable]]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {event_type: [] for event_type in EventType}
        return cls._instance

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Registers a callback for a specific event type.

        Args:
            event_type: The type of the event to subscribe to
            callback: The function to be called when the event is published
        """
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
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
        Publishes an event to all registered subscribers with parameter-safe invocation.

        Args:
            event_type: The type of the event
            data: Optional data to pass to subscribers
        """
        for callback in self._subscribers[event_type]:
            try:
                self._safe_invoke_callback(callback, data)
            except Exception as e:
                print(f"Error invoking callback for event {event_type}: {e}")

    async def publish_async(self, event_type: EventType, data: Any = None) -> None:
        """
        Publishes an event asynchronously to all registered subscribers with parameter-safe invocation.

        Args:
            event_type: The type of the event
            data: Optional data to pass to subscribers
        """
        for callback in self._subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await self._safe_invoke_async_callback(callback, data)
                else:
                    self._safe_invoke_callback(callback, data)
            except Exception as e:
                print(f"Error invoking async callback for event {event_type}: {e}")

    def _safe_invoke_callback(self, callback: Callable, data: Any = None) -> None:
        """
        Safely invokes a callback by checking its signature and passing appropriate parameters.

        Args:
            callback: The callback function to invoke
            data: The data to pass to the callback if its signature accepts it
        """
        sig = inspect.signature(callback)
        if len(sig.parameters) == 0:
            callback()
        else:
            callback(data)

    async def _safe_invoke_async_callback(
        self, callback: Callable, data: Any = None
    ) -> None:
        """
        Safely invokes an async callback by checking its signature and passing appropriate parameters.

        Args:
            callback: The async callback function to invoke
            data: The data to pass to the callback if its signature accepts it
        """
        sig = inspect.signature(callback)
        if len(sig.parameters) == 0:
            await callback()
        else:
            await callback(data)
