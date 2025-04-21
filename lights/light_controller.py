from utils.logging_mixin import LoggingMixin
from utils.event_bus import EventBus, EventType
from enum import Enum, auto


class LightColor(Enum):
    """Enumeration of possible light colors"""
    OFF = auto()
    BLUE = auto()
    RED = auto()


class LightController(LoggingMixin):
    """
    Controller for managing smart lights based on assistant state changes.
    
    This class responds to state changes in the voice assistant and
    controls connected lights accordingly.
    """
    
    def __init__(self):
        """Initialize the light controller and subscribe to relevant events."""
        self.current_color = LightColor.OFF
        self._register_events()
        self.logger.info("Light Controller initialized")
        
    def _register_events(self):
        """Register for state change events on the event bus."""
        self.event_bus = EventBus()
        self.event_bus.subscribe(EventType.STATE_CHANGED, self._handle_state_change)
    
    def _handle_state_change(self, state):
        """
        Handle assistant state changes and update lights accordingly.
        
        Args:
            state: The new AssistantState
        """
        # TODO: Langfristig sehe ich dieses Paket dann auch in einem eigenen Modul.
        from speech.voice_assistant_controller import AssistantState
        
        
        if state == AssistantState.LISTENING:
            self.set_light_color(LightColor.BLUE)
        elif state == AssistantState.RESPONDING:
            self.set_light_color(LightColor.RED)
        elif state == AssistantState.IDLE:
            self.set_light_color(LightColor.OFF)
    
    def set_light_color(self, color):
        """
        Set the light to the specified color.
        
        Args:
            color: LightColor enum value
        """
        if self.current_color == color:
            return
            
        self.current_color = color
        
        # Mock implementation - in a real setup, this would control actual lights
        if color == LightColor.BLUE:
            self.logger.info("LIGHT: Switching light to BLUE (Listening mode)")
            print("\n[LIGHT] Switching light to BLUE (Listening mode)")
        elif color == LightColor.RED:
            self.logger.info("LIGHT: Switching light to RED (Responding mode)")
            print("\n[LIGHT] Switching light to RED (Responding mode)")
        else:
            self.logger.info("LIGHT: Turning light OFF")
            print("\n[LIGHT] Turning light OFF")