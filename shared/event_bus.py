"""
Implementation of an Event Bus system to avoid property drilling.
"""

from enum import Enum, auto
import asyncio
import inspect
import threading
from typing import Dict, List, Callable, Any

from shared.singleton_meta_class import SingletonMetaClass


class EventType(Enum):
    """
    Enumeration for all possible event types in the voice assistant system.
    These events drive the interaction flow between user and assistant.
    """

    USER_SPEECH_STARTED = auto()
    """Triggered when the user begins speaking after wake word detection."""

    USER_SPEECH_ENDED = auto()
    """Triggered when the user stops speaking, indicating input is complete."""

    ASSISTANT_RESPONSE_COMPLETED = auto()
    """Triggered when all processing of the assistant's response is finished."""

    USER_INPUT_TRANSCRIPTION_COMPLETED = auto()
    """Triggered when the speech-to-text transcription of user input is complete."""

    ASSISTANT_STARTED_RESPONDING = auto()
    """Triggered when the assistant begins generating/speaking its response."""

    ASSISTANT_COMPLETED_RESPONDING = auto()
    """Triggered when the assistant finishes speaking its response."""

    WAKE_WORD_DETECTED = auto()
    """Triggered when the system detects the wake word that activates the assistant."""

    IDLE_TRANSITION = auto()
    """Triggered when the system returns to idle state after completed interaction or timeout."""


class EventBus(metaclass=SingletonMetaClass):
    """
    A central EventBus class that mediates events between components
    without them needing to know about each other.

    Features:
    - Singleton pattern ensures a single event bus throughout the application
    - Parameter-safe callback invocation handles different method signatures
    - Support for both synchronous and asynchronous event publishing
    """

    _subscribers: Dict[EventType, List[Callable]]

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }

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

    def publish_async_from_thread(
        self, event_type: EventType, data: Any = None
    ) -> None:
        """
        Thread-safe method to asynchronously publish events.
        Can be called from synchronous contexts.

        Args:
            event_type: The type of the event
            data: Optional data to pass to subscribers
        """
        sync_subscribers = [
            cb
            for cb in self._subscribers[event_type]
            if not asyncio.iscoroutinefunction(cb)
        ]

        for callback in sync_subscribers:
            try:
                self._safe_invoke_callback(callback, data)
            except Exception as e:
                print(f"Error invoking sync callback from thread: {e}")

        async_subscribers = [
            cb
            for cb in self._subscribers[event_type]
            if asyncio.iscoroutinefunction(cb)
        ]

        if not async_subscribers:
            return

        try:
            if threading.current_thread() is not threading.main_thread():
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(
                    lambda: self._schedule_async_callbacks(async_subscribers, data)
                )
            else:
                self._schedule_async_callbacks(async_subscribers, data)

        except Exception as e:
            print(f"Error in publish_async_from_thread: {e}")
            # Fallback: Verwende synchrones Publishen
            self.publish(event_type, data)

    def _schedule_async_callbacks(self, callbacks, data):
        """
        Schedules the execution of asynchronous callbacks in the current event loop.

        Args:
            callbacks: List of async callbacks to be executed
            data: Data to be passed to each callback
        """
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._execute_async_callbacks(callbacks, data))
        except Exception as e:
            print(f"Error scheduling async callbacks: {e}")

    async def _execute_async_callbacks(self, callbacks, data):
        """
        Executes asynchronous callbacks.

        Args:
            callbacks: List of async callbacks to be executed
            data: Data to be passed to each callback
        """
        for callback in callbacks:
            try:
                await self._safe_invoke_async_callback(callback, data)
            except Exception as e:
                print(f"Error executing async callback: {e}")

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
