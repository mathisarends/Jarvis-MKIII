import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from shared.singleton_meta_class import SingletonMetaClass


@dataclass
class SoundOption:
    """Represents a sound option with a human-readable label and a value for internal use."""

    label: str  # Human-readable name (e.g., "Focus", "Blossom")
    value: str  # Sound ID/path (e.g., "wake_up_sounds/wake-up-focus")


class SoundCategory(Enum):
    """Categories of alarm sounds"""

    WAKE_UP = "wake_up_sounds"
    GET_UP = "get_up_sounds"


class AlarmSoundManager(metaclass=SingletonMetaClass):
    """
    Manager for handling alarm sound options.
    Provides methods to discover and organize available alarm sounds.
    """

    def __init__(self, sounds_base_path: Optional[str] = None):
        """
        Initialize the sound manager with a base path to sound files.

        Args:
            sounds_base_path: Base directory containing sound subdirectories.
                             If None, will use default path in resources.
        """
        if sounds_base_path is None:
            self.sounds_base_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "resources",
                "sounds",
            )
        else:
            self.sounds_base_path = sounds_base_path

        self._sound_cache: Dict[SoundCategory, List[str]] = {}

    def get_wake_up_sound_options(self) -> List[SoundOption]:
        """
        Get all available wake-up sound options.

        Returns:
            List of SoundOption objects with label and value for each sound
        """
        return self._get_sound_options(SoundCategory.WAKE_UP)

    def get_get_up_sound_options(self) -> List[SoundOption]:
        """
        Get all available get-up sound options.

        Returns:
            List of SoundOption objects with label and value for each sound
        """
        return self._get_sound_options(SoundCategory.GET_UP)

    def _get_sound_options(self, category: SoundCategory) -> List[SoundOption]:
        """
        Helper method to get sound options for a specific category.

        Args:
            category: The sound category to get options for

        Returns:
            List of SoundOption objects with label and value for each sound
        """
        # Check if we have cached results
        if category not in self._sound_cache:
            self._refresh_sound_category(category)

        # Convert file names to SoundOption objects
        result = []
        for filename in self._sound_cache.get(category, []):
            sound_id = f"{category.value}/{os.path.splitext(filename)[0]}"
            display_name = self._format_display_name(filename)
            result.append(SoundOption(label=display_name, value=sound_id))

        return sorted(result, key=lambda x: x.label)

    def _refresh_sound_category(self, category: SoundCategory) -> None:
        """
        Scan the file system for sound files in the specified category.

        Args:
            category: The sound category to refresh
        """
        category_path = os.path.join(self.sounds_base_path, category.value)

        if not os.path.exists(category_path):
            self._sound_cache[category] = []
            return

        # Find all MP3 files in the category directory
        sound_files = [
            f
            for f in os.listdir(category_path)
            if f.endswith(".mp3") and os.path.isfile(os.path.join(category_path, f))
        ]

        self._sound_cache[category] = sound_files

    def _format_display_name(self, filename: str) -> str:
        """
        Format a filename into a user-friendly display name.

        Args:
            filename: The filename to format

        Returns:
            A formatted display name
        """
        # Remove file extension
        name = os.path.splitext(filename)[0]

        # Remove prefix (e.g., "wake-up-" or "get-up-")
        if "-" in name:
            parts = name.split("-")
            if len(parts) >= 3:  # For filenames like "wake-up-focus"
                name = "-".join(parts[2:])

        # Capitalize and replace underscores with spaces
        return name.replace("_", " ").capitalize()

    def refresh_all_sounds(self) -> None:
        """Refresh the cache for all sound categories."""
        for category in SoundCategory:
            self._refresh_sound_category(category)


if __name__ == "__main__":
    sound_manager = AlarmSoundManager()

    wake_up_options = sound_manager.get_wake_up_sound_options()
    print("Wake Up Sounds:")
    for option in wake_up_options:
        print(f"  - {option.label} (value: {option.value})")

    get_up_options = sound_manager.get_get_up_sound_options()
    print("\nGet Up Sounds:")
    for option in get_up_options:
        print(f"  - {option.label} (value: {option.value})")

    # Refresh all sounds
    sound_manager.refresh_all_sounds()
    print("\nAll sounds refreshed.")
