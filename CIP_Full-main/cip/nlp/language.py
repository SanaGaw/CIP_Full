"""Language detection and fluency estimation.

This module implements simple heuristics to detect whether text is English
or French and to estimate the speaker's fluency level.
"""
from __future__ import annotations

from typing import List


def detect_language(text: str) -> str:
    """Detect the language of the given text ('en' or 'fr').

    This heuristic looks for common French words; if found, returns 'fr',
    otherwise defaults to 'en'.
    """
    fr_markers = ["le ", "la ", "les ", "un ", "une ", "et ", "mais ", "ou ", "où ", "que ", "qui "]
    lowered = text.lower()
    for marker in fr_markers:
        if marker in lowered:
            return "fr"
    return "en"


def estimate_fluency(messages: List[str]) -> str:
    """Estimate the speaker's fluency as 'native', 'comfortable', or 'basic'.

    This simplistic implementation uses average sentence length and vocabulary
    diversity as proxies for fluency.
    """
    if not messages:
        return "basic"
    all_text = " ".join(messages)
    words = all_text.split()
    unique_words = set(words)
    avg_length = len(words) / max(1, len(messages))
    vocab_diversity = len(unique_words) / max(1, len(words))
    if avg_length > 12 and vocab_diversity > 0.5:
        return "native"
    elif avg_length > 8 and vocab_diversity > 0.3:
        return "comfortable"
    return "basic"