
import asyncio
from typing import Optional, List
from langchain.tools import tool

from tools.weather.weather_client import WeatherClient

@tool
async def get_weather(city: Optional[str] = None) -> str:
    """
    Ruft Wetterinformationen für einen bestimmten Standort ab oder verwendet den IP-basierten Standort.
    
    Args:
        city: Optional. Name der Stadt für die Wetterabfrage. 
              Wenn nicht angegeben, wird der Standort über die IP-Adresse ermittelt.
    
    Returns:
        Eine formatierte Wetterzusammenfassung
    """
    client = WeatherClient(city=city)
    weather_lines = await client.fetch_weather_data()
    
    return "\n".join(weather_lines)