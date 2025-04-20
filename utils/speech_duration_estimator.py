import re
import time
import unicodedata


class SpeechDurationEstimator:
    """
    Estimates the duration needed for an AI voice to speak a given text.
    Optimized for normal conversational sentences in English and German.
    """

    def __init__(self, words_per_minute=175, pause_factor=0.65, language="en"):
        """
        Initialize the speech duration estimator.

        Args:
            words_per_minute: Average speaking rate (default increased to 175 WPM)
            pause_factor: Multiplier for pauses (reduced to 0.7 for faster estimates)
            language: Language code ('en' or 'de')
        """
        self.words_per_minute = words_per_minute
        self.pause_factor = pause_factor
        self.language = language

        # Reduced pause durations for more realistic conversational speech
        self.punctuation_pauses = {
            ",": 0.15,
            ".": 0.3,
            "!": 0.3,
            "?": 0.3,
            ";": 0.2,
            ":": 0.2,
            "...": 0.4,
            "—": 0.25,
            "–": 0.2,
            "(": 0.1,
            ")": 0.1,
            "\n": 0.3,
            "\n\n": 0.5,
        }

        self.language_factors = {
            "en": 1.0,
            "de": 1.05,
        }

        self.language_factor = self.language_factors.get(language, 1.0)

    def estimate_duration(self, text):
        """
        Estimate the duration in seconds for the given text.
        Optimized for normal conversational sentences.

        Args:
            text: The text to estimate speaking duration for

        Returns:
            Estimated duration in seconds
        """
        if not text:
            return 0.0

        normalized_text = self._normalize_text(text)

        word_count = self._count_words(normalized_text)
        base_duration = (word_count / self.words_per_minute) * 60

        punctuation_duration = self._calculate_punctuation_pauses(normalized_text)

        complexity_factor = self._calculate_complexity_factor(normalized_text)

        correction_factor = 0.85

        total_duration = (
            (base_duration + punctuation_duration)
            * complexity_factor
            * self.language_factor
            * correction_factor
        )

        return total_duration

    def _normalize_text(self, text):
        """Normalize text by handling whitespace and unicode characters."""
        text = re.sub(r"\s+", " ", text)
        text = unicodedata.normalize("NFKD", text)
        return text.strip()

    def _count_words(self, text):
        """Count the number of words in the text."""
        words = [w for w in text.split() if w]
        return len(words)

    def _calculate_punctuation_pauses(self, text):
        """Calculate additional time for punctuation pauses."""
        total_pause_time = 0.0

        for mark, pause_time in self.punctuation_pauses.items():
            count = text.count(mark)
            total_pause_time += count * pause_time * self.pause_factor

        return total_pause_time

    def _calculate_complexity_factor(self, text):
        """
        Calculate a complexity factor based on text characteristics.
        Reduced impact for normal conversational sentences.
        """
        factor = 1.0

        sentences = re.split(r"[.!?]+", text)
        sentences = [s for s in sentences if s.strip()]

        if not sentences:
            return factor

        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)

        if avg_sentence_length > 25:
            factor *= 1.05

        # Reduced impact of unusual words
        unusual_word_pattern = r"\b[A-Z][a-z]*[A-Z][a-z]*\b|\b[a-z]*[0-9][a-z0-9]*\b"
        unusual_words = len(re.findall(unusual_word_pattern, text))

        if unusual_words > 0:
            word_count = max(self._count_words(text), 1)
            factor *= 1.0 + (unusual_words / word_count * 0.1)

        return factor
