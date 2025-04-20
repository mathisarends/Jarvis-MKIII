import json

from tools.tool_registry import ToolRegistry
from tools.weather.weather_tool import get_weather

if __name__ == "__main__":
    registry = ToolRegistry()
    registry.register_tool(get_weather)

    print("\nRegistered Tools:")
    for name in registry.list_tools():
        print(f"- {name}")

    openai_schema = registry.get_openai_schema()

    print("\nOpenAI Schema for all tools:")
    print(json.dumps(openai_schema, indent=2, ensure_ascii=False))
