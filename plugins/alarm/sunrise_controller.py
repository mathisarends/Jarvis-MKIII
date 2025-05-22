import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Optional

from hueify import GroupsManager, HueBridge

from shared.logging_mixin import LoggingMixin
from shared.singleton_meta_class import SingletonMetaClass


@dataclass
class SunriseConfig:
    """Configuration for the daylight alarm."""

    scene_name: str = "Majestätischer Morgen"
    room_name: str = "Zimmer 1"
    duration_seconds: int = 540
    start_brightness_percent: float = 0.01
    max_brightness_percent: float = 75.0
    enable_logging: bool = True


class SunriseController(LoggingMixin, metaclass=SingletonMetaClass):
    """
    Controller for the daylight alarm that simulates a sunrise with Philips Hue.

    Uses the Hueify library for communication with the Hue Bridge and
    provides a simple, clean interface for integration with the alarm system.
    """

    def __init__(self, config: Optional[SunriseConfig] = None):
        """
        Initializes the SunriseController with the given configuration.
        w
        Args:
            config: Optional configuration for the sunrise.
                   If None, the default configuration will be used.
        """
        self.config = config or SunriseConfig()
        self.bridge: Optional[HueBridge] = None
        self.groups_manager: Optional[GroupsManager] = None
        self.running_sunrise: Optional[asyncio.Task] = None
        self._cancel_event = threading.Event()

        # Start asynchronous initialization
        threading.Thread(target=self._init_bridge, daemon=True).start()

    def _init_bridge(self) -> None:
        """
        Initializes the connection to the Hue Bridge in the background.
        """
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.groups_manager = GroupsManager(self.bridge)
            self.logger.info("💡 Hueify daylight alarm successfully initialized")
        except Exception as e:
            self.logger.error(f"❌ Error connecting to the Hue Bridge: {e}")

    def start_sunrise(
        self,
        scene_name: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        max_brightness: Optional[float] = None,
    ) -> bool:
        """
        Starts the sunrise effect.

        Args:
            scene_name: Optional name of the target scene.
                        If None, the scene from the configuration will be used.
            duration_seconds: Optional duration of the sunrise in seconds.
                             If None, the duration from the configuration will be used.
            max_brightness: Optional maximum brightness in percent (0-100).
                           If None, the value from the configuration will be used.

        Returns:
            True if the sunrise was successfully started, False otherwise.
        """
        # Check if the Bridge is initialized
        if not self.bridge or not self.groups_manager:
            self.logger.error("❌ Hue Bridge not initialized")
            return False

        # Set configuration for this sunrise
        actual_scene = scene_name or self.config.scene_name
        actual_duration = duration_seconds or self.config.duration_seconds
        actual_max_brightness = max_brightness or self.config.max_brightness_percent

        # Start sunrise process in its own thread
        self._cancel_event.clear()
        threading.Thread(
            target=self._run_async_in_thread,
            args=(
                self._start_sunrise_async(
                    actual_scene, actual_duration, actual_max_brightness
                ),
            ),
            daemon=True,
        ).start()

        self.logger.info(
            f"🌅 Starting sunrise with scene '{actual_scene}' "
            f"over {actual_duration} seconds to {actual_max_brightness}% brightness"
        )
        return True

    def stop_sunrise(self) -> None:
        """
        Stops the running sunrise.
        """
        self._cancel_event.set()
        self.logger.info("🛑 Sunrise stopped")

    def _run_async_in_thread(self, coro) -> None:
        """
        Runs an asyncio coroutine in a separate thread.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _start_sunrise_async(
        self, scene_name: str, duration_seconds: int, max_brightness_percent: float
    ) -> None:
        """
        Asynchronous method for performing the sunrise.

        Args:
            scene_name: Name of the target scene
            duration_seconds: Duration of the sunrise in seconds
            max_brightness_percent: Maximum brightness in percent (0-100)
        """
        try:
            # Get controller for the configured room
            room_controller = await self.groups_manager.get_controller(
                self.config.room_name
            )

            # Save initial state for possible restoration
            initial_state_id = await room_controller.save_state("pre_sunrise_state")

            # Start with minimal brightness
            start_brightness = max(1, round(self.config.start_brightness_percent * 100))
            await room_controller.set_brightness_percentage(
                start_brightness, transition_time=1
            )

            # Activate scene for color settings, but with low brightness
            await room_controller.activate_scene(scene_name)
            await asyncio.sleep(1)  # Wait briefly for the scene to be active

            # Calculate number of steps and time interval
            steps = 20  # Number of brightness steps
            step_duration = duration_seconds / steps
            current_brightness = start_brightness

            # Limit maximum brightness to the specified value
            max_brightness = min(100, max(1, max_brightness_percent))

            # Gradually increase the brightness
            for step in range(1, steps + 1):
                if self._cancel_event.is_set():
                    self.logger.info("🛑 Sunrise aborted")
                    return

                # Calculate new brightness (logarithmic curve for a more natural effect)
                progress = step / steps
                brightness_percent = start_brightness + (
                    max_brightness - start_brightness
                ) * (progress**0.8)
                current_brightness = round(brightness_percent)

                # Set brightness with smooth transition
                transition_time = max(1, round(step_duration * 10))  # in 100ms units
                await room_controller.set_brightness_percentage(
                    current_brightness, transition_time=transition_time
                )

                # Log entry at certain steps
                if self.config.enable_logging and step % 5 == 0:
                    self.logger.info(
                        f"🌅 Sunrise: {current_brightness}% brightness reached"
                    )

                # Wait until the next step
                await asyncio.sleep(step_duration)

            # Ensure we reach exactly the target brightness at the end
            if current_brightness != max_brightness:
                await room_controller.set_brightness_percentage(
                    int(max_brightness), transition_time=10
                )

            self.logger.info(
                f"🌅 Sunrise completed: {max_brightness}% brightness reached"
            )

        except Exception as e:
            self.logger.error(f"❌ Error during sunrise: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

if __name__ == "__main__":
    config = SunriseConfig(
        scene_name="Majestätischer Morgen",
        room_name="Zimmer 1",
        duration_seconds=60,  # 1 minute for testing
        start_brightness_percent=0.01,
        max_brightness_percent=75.0,  # Only up to 75% brightness by default
    )

    controller = SunriseController(config)

    # Wait for the bridge connection to be established
    time.sleep(2)

    # Start sunrise (with optional maximum brightness override)
    controller.start_sunrise(max_brightness=65.0)  # Override config setting

    # Wait until the sunrise is complete
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop_sunrise()
        print("Program terminated")
