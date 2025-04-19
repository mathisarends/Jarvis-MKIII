def convert_langchain_tool_to_openai_function(lc_tool):
    """
    Konvertiert ein LangChain Tool in das OpenAI Funktionsformat
    """
    # Es gibt keine Parameter, da dieses Tool keine Eingaben benötigt
    parameters = {
        "type": "object",
        "properties": {},  # Keine Parameter für dieses einfache Tool
        "required": []
    }
    
    return {
        "type": "function",
        "name": lc_tool.name,
        "description": lc_tool.description,
        "parameters": parameters
    }