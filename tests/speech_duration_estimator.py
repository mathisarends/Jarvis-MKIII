import time
from utils.speech_duration_estimator import SpeechDurationEstimator


def estimate_speech_time(text, wpm=150, language="en"):
    """
    Helper function to estimate speech time for text.

    Args:
        text: Text to estimate
        wpm: Words per minute (default 150)
        language: Language code ('en' or 'de')

    Returns:
        Estimated duration in seconds
    """
    estimator = SpeechDurationEstimator(words_per_minute=wpm, language=language)
    return estimator.estimate_duration(text)


def test_german_speech_duration():
    """
    Test function for the speech duration estimator with various German text samples.
    """
    # Create German test samples with varying complexity
    samples = {
        "kurz": "Hallo!",
        "standard": "Hallo, ich bin ein Sprachassistent. Wie kann ich dir heute helfen?",
        "frage": "Kannst du mir sagen, wie das Wetter morgen wird?",
        "antwort": "Morgen wird es sonnig mit Temperaturen um die 22 Grad.",
        "alltag": "Ich habe heute noch einen Termin beim Arzt und muss danach einkaufen gehen.",
        "pause": "Moment... ich muss kurz nachdenken. Das ist eine gute Frage.",
        "dialog": "User: Wie spät ist es? Assistent: Es ist jetzt 14:30 Uhr.",
        "zahlen": "Meine Telefonnummer ist 0123 456789 und ich wohne in der Bahnhofstraße 42.",
        "interpunktion": "Hallo! Wie geht es dir heute? Mir geht es gut, danke der Nachfrage. Dieser Satz hat: Kommas, Semikolons; und sogar einige Klammern (wie diese hier).",
        "lang": "Heute möchte ich dir etwas über maschinelles Lernen erzählen. Es ist ein Teilbereich der künstlichen Intelligenz, der sich mit Algorithmen beschäftigt, die aus Daten lernen können. Diese Systeme verbessern sich mit der Zeit und können komplexe Aufgaben lösen.",
        "komplex": "Die Implementierung des Voice-Assistenten verwendet WebSocket-Verbindungen für die Echtzeit-Kommunikation. Das System verarbeitet PCM16-Audiodaten mit einer Abtastrate von 16kHz und nutzt verschiedene Callback-Funktionen zur Ereignisbehandlung.",
        "kombiniert": "Hallo! Ich kann dir bei vielen Dingen helfen. Möchtest du das Wetter wissen, einen Timer stellen oder vielleicht Musik hören? Sag einfach Bescheid, was ich für dich tun kann. Ich bin übrigens Version 3.7 deines Assistenten.",
    }

    print("\n--- BEISPIELSÄTZE ---")
    for name, text in samples.items():
        duration = estimate_speech_time(text, language="de")
        word_count = len(text.split())
        chars = len(text)

        print(f"\n{name.upper()}:")
        print(f'Text: "{text}"')
        print(f"Wörter: {word_count}, Zeichen: {chars}")
        print(f"Geschätzte Dauer: {duration:.2f} Sekunden")
        print(
            f"Durchschnitt: {duration/word_count:.2f}s pro Wort, {(duration/chars)*1000:.1f}ms pro Zeichen"
        )

    # Test different speaking rates
    print("\n--- SPRECHGESCHWINDIGKEITEN ---")
    test_text = "Dies ist ein Test für verschiedene Sprechgeschwindigkeiten."

    speeds = {"langsam": 140, "normal": 175, "schnell": 210, "sehr schnell": 250}

    for name, wpm in speeds.items():
        duration = estimate_speech_time(test_text, wpm=wpm, language="de")
        print(f"{name.capitalize()} ({wpm} WPM): {duration:.2f} Sekunden")


if __name__ == "__main__":
    start_time = time.time()
    test_german_speech_duration()
    end_time = time.time()

    print(f"\nTest in {end_time - start_time:.3f} Sekunden abgeschlossen")
