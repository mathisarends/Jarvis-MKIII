from typing import Type, TypeVar, Optional, ClassVar, cast

from audio.audio_player_base import AudioPlayer

T = TypeVar("T", bound="AudioPlayer")


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
    def reset(cls) -> None:
        """
        Reset the factory by clearing the current instance and player class.

        This allows creating a new player instance with a different class.
        Useful for testing or when switching audio backends.
        """
        cls._instance = None
        cls._player_class = None
