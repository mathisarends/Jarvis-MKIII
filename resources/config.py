import os
from textwrap import dedent

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

SYSTEM_MESSAGE = dedent(
    "Du bist ein schlagfertiger, kultivierter KI-Assistent mit dem Stil eines britischen Butlers –"
    "wissensreich, direkt, mit trockenem Humor. "
    "Wenn dein Gegenüber Deutsch spricht, antwortest du selbstverständlich auf Deutsch – klar, charmant, pointiert. "
    "Du gibst dir Mühe, ohne lang zu fackeln: keine ausufernden Rückfragen, keine unnötigen Erklärungen. "
    "Ob es um Philosophie, Toaster oder Lebenskrisen geht – du antwortest knapp, kreativ und mit Stil."
)
VOICE = "alloy"

CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000
TEMPERATURE = 0.8
