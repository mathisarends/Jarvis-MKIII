import textwrap
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

from core.audio.audio_player_base import AudioPlayer
from core.audio.audio_player_factory import AudioPlayerFactory
from core.llm.llm_factory import LLMFactory


@tool
async def set_volume_tool(volume_instruction: str) -> str:
    """
    Set the audio player volume using natural language instructions.

    Process any volume-related request in natural language and adjust the system volume accordingly.
    The tool can understand various formats like percentages, fractions, or descriptive terms
    in multiple languages.

    Examples:
        - "Set volume to 50%"
        - "Turn the volume to 3 out of 10"
        - "Stelle die Lautstärke auf 30 Prozent"

    Args:
        volume_instruction: Natural language instruction about changing the volume

    Returns:
        A confirmation message with the new volume level
    """
    llm = LLMFactory.create_gemini_flash()

    system_prompt = textwrap.dedent(
        """
        Du bist ein Sprachparser für ein Lautstärke-Steuerungssystem, das mehrere Sprachen unterstützt.
        
        Deine Aufgabe ist es, aus einer natürlichsprachigen Anfrage eine präzise Lautstärkeeinstellung zu extrahieren.
        
        Erkenne aus der Anfrage die gewünschte Lautstärke und gib AUSSCHLIESSLICH einen Float-Wert zwischen 0.0 und 1.0 zurück:
        - Prozentwerte werden als Dezimalwert zurückgegeben (50% = 0.5)
        - Brüche werden entsprechend umgerechnet (3/10 = 0.3)
        - Beschreibungen wie "maximum", "volle Lautstärke", "máximo" entsprechen 1.0
        - "minimum", "lautlos", "mute", "silencio" entsprechen 0.0
        - "mittel", "medium", "medio" entsprechen 0.5
        - Relative Änderungen wie "lauter", "louder", "más alto" um etwa 0.2 erhöhen
        - Relative Änderungen wie "leiser", "quieter", "más bajo" um etwa 0.2 senken
        
        Gib AUSSCHLIESSLICH den numerischen Wert zurück. Keine Erklärungen, keine Einheiten, keine Texte.
        """
    )

    human_prompt = f"Anweisung zur Lautstärke: {volume_instruction}"

    try:
        # Get the current volume for relative adjustments (used by the LLM)
        audio_player: AudioPlayer = AudioPlayerFactory.get_shared_instance()
        current_volume = audio_player.get_volume_level()

        human_prompt += f"\nAktuelle Lautstärke: {current_volume:.2f}"

        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]
        )

        volume_str = response.content.strip()

        try:
            volume_value = float(volume_str)

            volume_value = max(0.0, min(1.0, volume_value))

            new_volume = audio_player.set_volume_level(volume_value)
            percent = int(new_volume * 100)

            return f"Volume set to {percent}%"

        except ValueError:
            new_volume = audio_player.set_volume_level(0.5)
            return "Volume set to 50% (default)"

    except Exception:
        audio_player = AudioPlayerFactory.get_shared_instance()
        new_volume = audio_player.set_volume_level(0.5)
        return "Volume set to 50% (default)"


@tool
def get_volume_tool() -> str:
    """
    Get the current audio player volume level.

    Returns:
        The current volume level as a percentage
    """
    audio_player = AudioPlayerFactory.get_shared_instance()
    current_volume = audio_player.get_volume_level()
    percent = int(current_volume * 100)
    return f"Current volume is {percent}%"
