import asyncio
import traceback
from enum import Enum, auto

from hueify import GroupsManager, HueBridge

from utils.logging_mixin import LoggingMixin
from utils.event_bus import EventBus, EventType


class LightMode(Enum):
    """
    Defines the different lighting modes based on the interaction state of the voice assistant.

    These modes control how the lighting system should behave depending on whether the assistant
    is idle, actively listening, or responding.
    """

    WAKE_WORD_DETECTED = auto()
    """The microphone is active – typically triggered by the detection of a wake word."""

    ASSISTANT_RESPONDING = auto()
    """The assistant is responding to the user – subtle lighting effects should be applied."""

    LISTENING_FOR_WAKEWORD = auto()
    """The system is idle and listening for the wake word – lights remain in the normal state."""


class LightController(LoggingMixin):
    """
    Controller for Philips Hue lighting based on different interaction states.

    Adjusts lighting conditions based on three primary states:
    - WAKE_WORD_DETECTED: Increases brightness when the microphone is active
    - ASSISTANT_RESPODNDING: Applies subtle color changes when the assistant is speaking
    - LISTENING_FOR_WAKEWORD: Returns lights to the normal state when system is waiting for activation
    """

    def __init__(self):
        """Initializes the Light Controller and subscribes to events."""
        self.current_mode = LightMode.LISTENING_FOR_WAKEWORD
        self.loop = asyncio.get_event_loop()

        # Hue components
        self.bridge = None
        self.group_manager = None
        self.room_controller = None
        self.saved_normal_state_id = None
        self.saved_wake_word_detected_normal_state_id = None
        self.subtle_change_state_id = None

        self.brightness_change_percent = 10
        self.transition_time_seconds = 0.5

        self.loop.create_task(self._initialize_hue())
        self.logger.info("Light Controller initialized")

        self._register_events()

    async def _initialize_hue(self):
        """Initializes the connection to the Hue Bridge."""
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.logger.info("Connecting to Hue Bridge via auto-discovery")

            self.group_manager = GroupsManager(bridge=self.bridge)
            self.room_controller = await self.group_manager.get_controller(
                group_identifier="Zimmer 1"
            )

            self.logger.info(
                "Successfully connected to Hue Bridge, controlling room: %s",
                self.room_controller.name,
            )

            # Save current state as "normal"
            await self._save_normal_state()

        except Exception as e:
            self.logger.error("Error during Hue initialization: %s", e)
            self.bridge = None
            self.group_manager = None
            self.room_controller = None

    async def _save_normal_state(self):
        """Saves the current state as normal state."""
        if not self.room_controller:
            return

        try:
            self.saved_normal_state_id = await self.room_controller.save_state()
            self.logger.info(
                "Normal state saved with ID: %s", self.saved_normal_state_id
            )
        except Exception as e:
            self.logger.error("Error saving normal state: %s", e)

    def _register_events(self):
        """
        Registers event handlers for interaction state changes.
        Uses wrapper methods to properly handle async execution.
        """
        self.event_bus = EventBus()

        self.event_bus.subscribe(
            event_type=EventType.WAKE_WORD_DETECTED,
            callback=self._handle_wake_word_detected,
        )
        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_STARTED_RESPONDING,
            callback=self._handle_assistant_responding,
        )
        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_COMPLETED_RESPONDING,
            callback=self.refresh_normal_state,
        )
        self.event_bus.subscribe(
            event_type=EventType.IDLE_TRANSITION, callback=self._handle_idle_transition
        )

    def _handle_wake_word_detected(self):
        """
        Wrapper method for handling wake word detection events.
        Creates a task for the async method in the event loop.
        """
        self.loop.create_task(self.increase_brightness_on_wake_word_detected())
        self.current_mode = LightMode.WAKE_WORD_DETECTED
        self.logger.info("LIGHT: Switching to WAKE_WORD_DETECTED mode")

    def _handle_assistant_responding(self):
        """
        Wrapper method for handling assistant response events.
        Creates a task for the async method in the event loop.
        """
        self.loop.create_task(self.subtle_light_change_on_assistant_response())
        self.current_mode = LightMode.ASSISTANT_RESPONDING
        self.logger.info("LIGHT: Switching to ASSISTANT_RESPODNDING mode")

    def _handle_assistant_completed_responding(self):
        self.loop.create_task(self.subtle_light_change_on_assistant_response())
        self.current_mode = LightMode.WAKE_WORD_DETECTED
        self.logger.info("LIGHT: Switching to ASSISTANT_RESPODNDING mode")

    async def _restore_normale_increased_brightness_state(self):
        await self.room_controller.restore_state(
            self.saved_wake_word_detected_normal_state_id,
        )

    def _handle_idle_transition(self):
        """
        Wrapper method for handling idle transition events.
        Creates a task for the async method in the event loop.
        """
        if (
            self.current_mode == LightMode.ASSISTANT_RESPONDING
            and self.subtle_change_state_id
        ):
            self.loop.create_task(self.revert_subtle_light_change())
        elif self.current_mode == LightMode.WAKE_WORD_DETECTED:
            self.loop.create_task(self.decrease_brightness_on_idle_transition())

        self.current_mode = LightMode.LISTENING_FOR_WAKEWORD
        self.logger.info("LIGHT: Switching to LISTENING_FOR_WAKEWORD mode")

    async def increase_brightness_on_wake_word_detected(self):
        """Increases brightness when wake word is detected."""
        try:
            await self.room_controller.increase_brightness_percentage(
                increment=self.brightness_change_percent,
                transition_time=self._seconds_to_transition_time(
                    self.transition_time_seconds
                ),
            )
            self.logger.info(
                "Brightness increased by %d%% for wake word detection",
                self.brightness_change_percent,
            )
        except Exception as e:
            error_details = (
                f"Error increasing brightness: {e}\n{traceback.format_exc()}"
            )
            self.logger.error(error_details)

    async def decrease_brightness_on_idle_transition(self):
        """Decreases brightness when transitioning to idle state."""
        try:
            self.saved_wake_word_detected_normal_state_id = (
                await self.room_controller.save_state()
            )

            await self.room_controller.decrease_brightness_percentage(
                decrement=self.brightness_change_percent,
                transition_time=self._seconds_to_transition_time(
                    self.transition_time_seconds
                ),
            )
            self.logger.info(
                "Brightness decreased by %d%% returning to idle",
                self.brightness_change_percent,
            )
        except Exception as e:
            error_details = (
                f"Error decreasing brightness: {e}\n{traceback.format_exc()}"
            )
            self.logger.error(error_details)

    async def subtle_light_change_on_assistant_response(self):
        """Applies subtle color changes when assistant is responding."""
        try:
            self.saved_wake_word_detected_normal_state_id = (
                await self.room_controller.save_state()
            )
            self.subtle_change_state_id = (
                await self.room_controller.subtle_light_change(
                    base_hue_shift=5000,
                    hue_variation=2000,
                    sat_adjustment=20,
                    sat_variation=10,
                    transition_time_seconds=self.transition_time_seconds,
                )
            )
            self.logger.info("Applied subtle color changes for assistant response")
        except Exception as e:
            error_details = (
                f"Error applying subtle light changes: {e}\n{traceback.format_exc()}"
            )
            self.logger.error(error_details)
            self.subtle_change_state_id = None

    async def revert_subtle_light_change(self):
        """Reverts the subtle color changes."""
        try:
            await self.room_controller.restore_state(
                self.subtle_change_state_id,
                transition_time_seconds=self.transition_time_seconds,
            )
            self.logger.info("Reverted subtle color changes")
            self.subtle_change_state_id = None
        except Exception as e:
            error_details = (
                f"Error reverting subtle light changes: {e}\n{traceback.format_exc()}"
            )
            self.logger.error(error_details)

    def _seconds_to_transition_time(self, seconds):
        """Converts seconds to Hue API 100ms units."""
        return max(1, round(seconds * 10))

    async def refresh_normal_state(self):
        """
        Updates the stored 'normal' state to the current light state.
        """
        self.logger.info("Assistant stopped responding, refreshing normal state")
        await self.room_controller.restore_state(save_id=self.saved_wake_word_detected_normal_state_id)
        self.logger.info("Normal state updated to current light state")
