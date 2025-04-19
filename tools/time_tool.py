import datetime
import json
from langchain.tools import tool

from tools.weather.weather_tool import get_weather

@tool
def get_current_time() -> str:
    """
    Gibt das aktuelle Datum und die aktuelle Uhrzeit in einem menschenlesbaren Format zurück.
    """
    now = datetime.datetime.now()
    return now.strftime("Datum: %Y-%m-%d Uhrzeit: %H:%M:%S")

# TODO: Diese Tool hier funktioniert zwar kann man das aber nicht besser typen?
def convert_langchain_tool_to_openai_function(lc_tool):
    """
    Konvertiert ein LangChain Tool in das OpenAI Funktionsformat
    """
    # Es gibt keine Parameter, da dieses Tool keine Eingaben benötigt
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    return {
        "type": "function",
        "name": lc_tool.name,
        "description": lc_tool.description,
        "parameters": parameters
    }
    
if __name__ == "__main__":
    # Konvertiere das Tool
    openai_function = convert_langchain_tool_to_openai_function(get_weather)
    
    # Zeige das Ergebnis
    print("Konvertiertes Tool als OpenAI-Funktion:")
    print(json.dumps(openai_function, indent=2, ensure_ascii=False))
    
    # Überprüfe Eigenschaften
    print("\nÜberprüfung:")
    print(f"Name: {openai_function['name']}")
    print(f"Beschreibung: {openai_function['description']}")
    print(f"Parametertyp: {openai_function['parameters']['type']}")
    print(f"Hat Properties: {'properties' in openai_function['parameters']}")
    
    # Zeige, wie es in der OpenAI-Tools-Liste aussehen würde
    tools_list = [openai_function]
    print("\nIn der OpenAI-Tools-Liste:")
    print(json.dumps(tools_list, indent=2, ensure_ascii=False))