from langchain.tools import tool

from tools.weather.weather_client import WeatherClient

@tool
async def get_weather() -> str:
    """
    Retrieves current weather information based on automatically detected location.
    
    The tool uses IP-based geolocation to determine the user's current location
    and fetches the appropriate weather data. No parameters needed.
    
    Returns:
        str: A formatted summary of the current weather at the detected location.
    """
    client = WeatherClient()
    weather_lines = await client.fetch_weather_data()

    return "\n".join(weather_lines)