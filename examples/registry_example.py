import json
import datetime

from typing import Optional
from tools.tool_registry import ToolRegistry, register_as_tool
from tools.weather.weather_tool import get_weather

if __name__ == "__main__":
    registry = ToolRegistry()
    registry.register_tool(get_weather)

    @register_as_tool()
    def get_current_time() -> str:
        """Returns the current date and time in a human-readable format."""
        now = datetime.datetime.now()
        return now.strftime("Date: %Y-%m-%d Time: %H:%M:%S")

    @register_as_tool()
    def calculate_age(birth_year: int, current_year: Optional[int] = None) -> int:
        """
        Calculates a person's age based on birth year.

        Args:
            birth_year: The person's year of birth
            current_year: Optional; defaults to the current year

        Returns:
            int: The calculated age
        """
        if current_year is None:
            current_year = datetime.datetime.now().year

        return current_year - birth_year

    print("\nRegistered Tools:")
    for name in registry.list_tools():
        print(f"- {name}")

    openai_schema = registry.get_openai_schema()

    print("\nOpenAI Schema for all tools:")
    print(json.dumps(openai_schema, indent=2, ensure_ascii=False))

    weather_schema = registry.get_openai_schema(['get_weather'])
    print("\nOpenAI Schema for weather tool only:")
    print(json.dumps(weather_schema, indent=2, ensure_ascii=False))
