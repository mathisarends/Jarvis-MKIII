import datetime
import textwrap
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from tools.weather.weather_client import WeatherClient


@tool
async def get_weather() -> str:
    """
    Retrieves current weather information based on automatically detected location.

    The tool uses IP-based geolocation to determine the user's current location
    and fetches the appropriate weather data. No parameters needed.

    Returns:
        str: A formatted summary of the current weather at the detected location in natural language.
    """
    client = WeatherClient()
    weather_lines = await client.fetch_weather_data()

    # Get current time
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2,
        streaming=False,
    )

    weather_text = "\n".join(weather_lines)

    # System-Prompt für natürliche Sprachausgabe
    system_prompt = textwrap.dedent(
        """
Du bist ein hochentwickelter KI-Assistent mit einem präzisen, effizienten Kommunikationsstil, ähnlich wie Jarvis (ohne 'Sir' zu verwenden).

Deine Aufgabe ist es, Wetterinformationen in eine natürliche, gesprochene Form umzuwandeln.

Beziehe dich auf den aktuellen Tag und die nächsten 24 Stunden.

Folgende Richtlinien solltest du beachten:
1. Sei präzise und direkt – vermittle die wichtigsten Informationen zuerst.
2. Halte die Antwort informativ und detailliert.
3. Verwende einen effizienten, selbstbewussten Ton.
4. Formuliere technisch präzise, aber verständlich.
5. Vermeide Füllwörter und überflüssige Höflichkeiten.
6. Hebe die aktuellen Bedingungen und relevante Veränderungen für die nächsten Stunden hervor.
7. Struktur: Aktuelle Bedingungen → Wichtige Änderungen → Empfehlungen (falls sinnvoll).

Gib die optimierte Antwort zurück, ohne Erklärungen oder zusätzlichen Text.
"""
    )

    human_prompt = textwrap.dedent(
        f"""
Es ist {current_time} Uhr.

Hier sind die Wetterdaten:

{weather_text}

Bitte wandle diese Informationen in eine natürliche, gesprochene Antwort um.
Falls die aktuelle Uhrzeit nach 18 Uhr liegt, erwähne auch kurz das Wetter für morgen.
"""
    )

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]
        )

        speech_result = response.content.strip()
        return speech_result
    except (ValueError, ConnectionError, TimeoutError) as e:
        error_type = type(e).__name__
        return f"Fehler bei der Wetterabfrage ({error_type}): {e}. Unformatierte Wetterdaten: {weather_text[:150]}..."
