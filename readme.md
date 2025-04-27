# Jarvis MKIII

![Python](https://img.shields.io/badge/python-3.9%2B-blue)

A self-hosted voice assistant using OpenAI's Realtime API with a server-to-server approach.

## Overview

Jarvis MKIII implements the [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) for creating a voice assistant that can run on self-hosted hardware like a Raspberry Pi. The system handles wake word detection, audio processing, and tool execution.

## Key Components

- **Server-to-Server Implementation** of OpenAI's Realtime API
- **Tool Registry** that converts LangChain tools to OpenAI function format
- **Wake Word Detection** using Porcupine
- **Event-Driven Architecture** with modular components

## Tool Registry

The system includes a `ToolRegistry` that converts LangChain-style tools to OpenAI's function calling format:

```python
from langchain.tools import tool

@tool
def my_tool(parameter: str) -> str:
    """Tool description for the OpenAI API."""
    return f"Result: {parameter}"
```

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PICO_ACCESS_KEY=your_picovoice_access_key
   ```

## Usage

Run the assistant with:

```
python main.py
```

The system will listen for the wake word and then process voice interactions through the OpenAI Realtime API.
