import asyncio
import traceback
from enum import Enum, auto

from hueify import GroupsManager, HueBridge

from shared.logging_mixin import LoggingMixin
from shared.event_bus import EventBus, EventType


class LightState(Enum):
    """
    Defines the different lighting states based on the interaction flow.
    """

    IDLE = auto()  # Base state when nothing is happening
    ALERT = auto()  # Brightened state (wake word or user speaking)
    ASSISTANT_RESPONDING = auto()  # Slightly dimmed state during assistant response


class LightController(LoggingMixin):
    """
    Controller for Philips Hue lighting based on interaction states.

    Features:
    - Increases brightness when wake word is detected or user speaks
    - Slightly dims lights when assistant is responding
    - Returns to base state when system goes idle
    """

    def __init__(self, room_identifier="Zimmer 1"):
        """
        Initialize the LightController with basic settings.

        Args:
            room_identifier: The identifier of the room to control
        """
        # Store room identifier
        self.room_identifier = room_identifier

        # Initialize properties
        self.current_state = LightState.IDLE

        # Hue components
        self.bridge = None
        self.group_manager = None
        self.room_controller = None

        # Saved states
        self.idle_state_id = None
        self.alert_state_id = None

        # Configuration
        self.brightness_increase_percent = 10
        self.brightness_decrease_percent = 5
        self.transition_time_seconds = 0.5

        # Event bus will be initialized in register_events
        self.event_bus = None

    @classmethod
    async def create(cls, room_identifier="Zimmer 1") -> "LightController":
        """
        Asynchronous factory method to create and initialize a LightController.

        Args:
            room_identifier: The identifier of the room to control

        Returns:
            An initialized LightController instance
        """
        # Create instance using the normal constructor
        instance = cls(room_identifier)

        # Initialize Hue connection
        await instance._initialize_hue()

        # Register event handlers
        instance._register_events()

        instance.logger.info("Light Controller initialized")
        return instance

    async def _initialize_hue(self):
        """Initializes the connection to the Hue Bridge."""
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.logger.info("Connecting to Hue Bridge via auto-discovery")

            self.group_manager = GroupsManager(bridge=self.bridge)
            self.room_controller = await self.group_manager.get_controller(
                group_identifier=self.room_identifier
            )

            self.logger.info(
                "Successfully connected to Hue Bridge, controlling room: %s",
                self.room_controller.name,
            )

            # Save current state as idle state
            await self._save_idle_state()

        except Exception as e:
            self.logger.error("Error during Hue initialization: %s", e)
            self.bridge = None
            self.group_manager = None
            self.room_controller = None

    async def _save_idle_state(self):
        """Saves the current state as idle state."""
        if not self.room_controller:
            return

        try:
            self.idle_state_id = await self.room_controller.save_state()
            self.logger.info("Idle state saved with ID: %s", self.idle_state_id)
        except Exception as e:
            self.logger.error("Error saving idle state: %s", e)

    def _register_events(self):
        """Registers event handlers for interaction state changes."""
        self.event_bus = EventBus()

        self.event_bus.subscribe(
            event_type=EventType.WAKE_WORD_DETECTED,
            callback=self.on_wake_word_detected,
        )

        self.event_bus.subscribe(
            event_type=EventType.USER_SPEECH_STARTED,
            callback=self.on_user_speech_started,
        )

        self.event_bus.subscribe(
            event_type=EventType.ASSISTANT_STARTED_RESPONDING,
            callback=self.on_assistant_started_responding,
        )

        self.event_bus.subscribe(
            event_type=EventType.IDLE_TRANSITION,
            callback=self.on_system_idle,
        )

    def on_wake_word_detected(self):
        """
        Brightens the lights when wake word is detected.
        """
        asyncio.create_task(self.increase_brightness())
        self.current_state = LightState.ALERT
        self.logger.info("LIGHT: Switching to ALERT mode (wake word)")

    def on_user_speech_started(self):
        """
        Brightens the lights when user starts speaking after assistant response.
        """
        # Only increase brightness if coming from ASSISTANT_RESPONDING state
        if self.current_state == LightState.ASSISTANT_RESPONDING:
            asyncio.create_task(self.increase_brightness())
            self.current_state = LightState.ALERT
            self.logger.info("LIGHT: Switching to ALERT mode (user speaking)")

    def on_assistant_started_responding(self):
        """
        Slightly dims the lights when assistant starts responding.
        """
        asyncio.create_task(self.decrease_brightness())
        self.current_state = LightState.ASSISTANT_RESPONDING
        self.logger.info("LIGHT: Switching to ASSISTANT_RESPONDING mode")

    def on_system_idle(self):
        """
        Restores lights to original state when system becomes idle.
        """
        asyncio.create_task(self.restore_idle_state())
        self.current_state = LightState.IDLE
        self.logger.info("LIGHT: Switching to IDLE mode")

    async def increase_brightness(self):
        """Increases brightness for wake word or user speaking states."""
        if not self.room_controller:
            return

        try:
            # Save current state if we're coming from IDLE
            if self.current_state == LightState.IDLE:
                self.alert_state_id = await self.room_controller.save_state()

            # Increase brightness
            await self.room_controller.increase_brightness_percentage(
                increment=self.brightness_increase_percent,
                transition_time=self._seconds_to_transition_time(
                    self.transition_time_seconds
                ),
            )
            self.logger.info(
                "Brightness increased by %d%%",
                self.brightness_increase_percent,
            )
        except Exception as e:
            error_details = (
                f"Error increasing brightness: {e}\n{traceback.format_exc()}"
            )
            self.logger.error(error_details)

    async def decrease_brightness(self):
        """Slightly decreases brightness when assistant is responding."""
        if not self.room_controller:
            return

        try:
            await self.room_controller.decrease_brightness_percentage(
                decrement=self.brightness_decrease_percent,
                transition_time=self._seconds_to_transition_time(
                    self.transition_time_seconds
                ),
            )
            self.logger.info(
                "Brightness decreased by %d%% for assistant response",
                self.brightness_decrease_percent,
            )
        except Exception as e:
            error_details = (
                f"Error decreasing brightness: {e}\n{traceback.format_exc()}"
            )
            self.logger.error(error_details)

    async def restore_idle_state(self):
        """Restores lights to the saved idle state."""
        if not self.room_controller or not self.idle_state_id:
            return

        try:
            await self.room_controller.restore_state(
                self.idle_state_id,
                transition_time_seconds=self.transition_time_seconds,
            )
            self.logger.info("Restored lights to idle state")
        except Exception as e:
            error_details = f"Error restoring idle state: {e}\n{traceback.format_exc()}"
            self.logger.error(error_details)

    def _seconds_to_transition_time(self, seconds):
        """Converts seconds to Hue API 100ms units."""
        return max(1, round(seconds * 10))
