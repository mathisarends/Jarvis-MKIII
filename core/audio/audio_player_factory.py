from typing import ClassVar, Optional, Type, TypeVar, cast

from core.audio.audio_player_base import AudioPlayer

T = TypeVar("T", bound="AudioPlayer")


# Überlegen ob man das hier auch wirklich braucht aber ich könnte mir schon vorstellen.
class AudioPlayerFactory:
    """
    Factory for managing a singleton instance of an AudioPlayer.

    This factory ensures that only one audio player instance exists throughout the
    application. The audio player implementation must be initialized once with
    initialize_with() before get_shared_instance() can be called.
    """

    _instance: ClassVar[Optional[AudioPlayer]] = None
    _player_class: ClassVar[Optional[Type[AudioPlayer]]] = None

    @classmethod
    def initialize_with(cls, player_class: Type[T], play_sound=True) -> T:
        """
        Initialize the audio player singleton with the specified implementation.

        This method must be called once before get_shared_instance() can be used.

        Args:
            player_class: The AudioPlayer implementation class to instantiate

        Returns:
            The singleton instance of the audio player

        Raises:
            TypeError: If trying to initialize with a different class than already set
        """
        if cls._instance is not None:
            if player_class is not cls._player_class:
                raise TypeError(
                    f"Cannot change player class from {cls._player_class.__name__} "
                    f"to {player_class.__name__} without reset. "
                    f"Call AudioPlayerFactory.reset() first."
                )
            return cast(T, cls._instance)

        cls._instance = player_class()
        cls._player_class = player_class

        cls._instance.start()

        if play_sound:
            cls._instance.play_sound("startup")

        return cast(T, cls._instance)

    @classmethod
    def get_shared_instance(cls, player_class: Optional[Type[T]] = None) -> AudioPlayer:
        """
        Get the shared audio player instance.

        Args:
            player_class: Optional player class for first-time initialization.
                          If provided on first call, equivalent to calling initialize_with().

        Returns:
            The singleton instance of the audio player

        Raises:
            ValueError: If no instance exists and no player_class is provided
        """
        if cls._instance is None:
            if player_class is None:
                raise ValueError(
                    "No audio player has been initialized. "
                    "Call AudioPlayerFactory.initialize_with(YourPlayerClass) first, "
                    "or provide player_class parameter."
                )
            return cls.initialize_with(player_class)

        if player_class is not None and player_class is not cls._player_class:
            raise TypeError(
                f"Requested {player_class.__name__} but active player is {cls._player_class.__name__}. "
                f"Call AudioPlayerFactory.reset() first to change implementation."
            )

        return cls._instance
    
    @classmethod
    def set_strategy(cls, new_player_class: Type[T], play_test_sound: bool = True) -> T:
        """
        Switch to a different audio player strategy at runtime.
        
        This method safely transitions from the current audio player to a new one:
        1. Stops the current player
        2. Creates and starts the new player
        3. Optionally plays a test sound
        4. If anything fails, attempts to restore the previous player

        Args:
            new_player_class: The new AudioPlayer implementation class to switch to
            play_test_sound: Whether to play a test sound after switching

        Returns:
            The new audio player instance

        Raises:
            ValueError: If no player is currently initialized
            RuntimeError: If the strategy switch fails and rollback also fails
        """
        if cls._instance is None:
            raise ValueError(
                "No audio player is currently initialized. "
                "Call AudioPlayerFactory.initialize_with() first."
            )

        if new_player_class is cls._player_class:
            return cast(T, cls._instance)

        old_instance = cls._instance
        old_player_class = cls._player_class

        try:
            if hasattr(old_instance, 'stop'):
                old_instance.stop()

            cls._instance = new_player_class()
            cls._player_class = new_player_class
            
            cls._instance.start()

            if play_test_sound:
                cls._instance.play_sound("system_switch")

            return cast(T, cls._instance)

        except Exception as e:
            # Rollback on failure
            cls._instance = old_instance
            cls._player_class = old_player_class
            
            try:
                # Try to restart the old player
                if hasattr(old_instance, 'start'):
                    old_instance.start()
            except Exception as rollback_error:
                # Critical failure - both new and old player failed
                cls._instance = None
                cls._player_class = None
                raise RuntimeError(
                    f"Audio player strategy switch failed: {str(e)}. "
                    f"Rollback also failed: {str(rollback_error)}. "
                    f"No audio player is active."
                ) from e

            # Re-raise original exception after successful rollback
            raise RuntimeError(
                f"Failed to switch to {new_player_class.__name__}: {str(e)}. "
                f"Rolled back to {old_player_class.__name__}."
            ) from e

    @classmethod
    def get_current_strategy(cls) -> Optional[Type[AudioPlayer]]:
        """
        Get the currently active audio player strategy class.

        Returns:
            The class of the currently active audio player, or None if not initialized
        """
        return cls._player_class

    @classmethod
    def reset(cls) -> None:
        """
        Reset the factory by clearing the current instance and player class.

        This allows creating a new player instance with a different class.
        Useful for testing or when switching audio backends.
        """
        cls._instance = None
        cls._player_class = None
