from typing import List, Optional
import python_weather
import aiohttp
import asyncio


class WeatherClient:
    def __init__(self, city: Optional[str] = None):
        """
        Initialisiert den Weather Client.

        :param city: Optionaler Stadtname. Wenn None, wird IP-basierte Geolokalisierung verwendet.
        """
        self.city = city

    async def _get_location_from_ip(self) -> str:
        """Ermittelt den Standort basierend auf der IP-Adresse."""
        async with aiohttp.ClientSession() as session:
            # Kostenloser Dienst ohne API-Key
            async with session.get("https://ipinfo.io/json") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("city", "Unknown City")

    async def _fetch_weather(self):
        """Fetches weather data asynchronously."""
        # Falls keine Stadt gesetzt ist, ermittle sie über die IP
        if not self.city:
            self.city = await self._get_location_from_ip()

        async with python_weather.Client(unit=python_weather.METRIC) as client:
            return await client.get(self.city)

    async def fetch_weather_data(self) -> List[str]:
        """Fetches weather data and handles errors."""
        try:
            weather = await self._fetch_weather()
            output = [
                f"Wetter in {self.city}:",
                f"Aktuelle Temperatur: {weather.temperature}°C",
            ]

            # Original Format mit daily und hourly Daten
            for daily in weather:
                output.append(str(daily))
                for hourly in daily:
                    output.append(f" --> {hourly!r}")

            return output

        except Exception as e:
            return [f"❌ Fehler beim Abrufen der Wetterdaten: {str(e)}"]


# Beispiel zur Verwendung
async def main():
    weather_client = WeatherClient()
    result = await weather_client.fetch_weather_data()
    for line in result:
        print(line)


if __name__ == "__main__":
    asyncio.run(main())
