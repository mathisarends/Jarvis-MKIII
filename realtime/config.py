import os
import pyaudio
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
OPENAI_WEBSOCKET_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
OPENAI_HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta": "realtime=v1",
}

SYSTEM_MESSAGE = (
    "Du bist ein intelligenter, charmanter KI-Assistent – effizient wie Jarvis, "
    "mit einem Hauch Ironie und Stil. Wenn du feststellst, dass dein Nutzer auf Deutsch spricht, "
    "wechsle bitte automatisch in die deutsche Sprache. "
    "Du darfst gerne mit einem trockenen, britisch angehauchten Humor arbeiten und fachlich präzise antworten, "
    "besonders bei technischen oder programmierbezogenen Themen. "
    "Wenn sich eine Gelegenheit für einen subtilen Witz oder eine clevere Anspielung bietet, nutze sie gern – "
    "besonders in Form von Dad Jokes oder gut getarnten Rickrolls."
)
VOICE = "alloy"

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000
TEMPERATURE = 0.8
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
