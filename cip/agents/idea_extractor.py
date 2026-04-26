"""Idea extraction and quality scoring.

This module extracts ideas from participant messages, scores their quality,
parses narrative elements and flags cognitive biases. It relies on spaCy for
syntactic analysis when available.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

import numpy as np

try:
    import spacy  # type: ignore
    _nlp_en = spacy.load("en_core_web_sm")  # type: ignore
    _nlp_fr = spacy.load("fr_core_news_sm")  # type: ignore
except Exception:
    _nlp_en = None  # type: ignore
    _nlp_fr = None  # type: ignore

# Quality weighting factors
QUALITY_WEIGHTS = {
    "specificity": 0.25,
    "evidence": 0.25,
    "novelty": 0.20,
    "relevance": 0.20,
    "depth": 0.10,
}

NARRATIVE_PATTERNS = {
    "actors": r"(customer|user|team|manager|client|employee|vendor|hr|finance|engineering|product)",
    "events": r"(happened|occurred|failed|worked|stopped|started|broke|changed|left|joined)",
    "consequences": r"(cost|lost|missed|delayed|prevented|caused|resulted in|burnout|turnover)",
    "stakes": r"(risk|critical|urgent|important|essential|must|cannot afford)",
}

BIAS_SIGNALS = {
    "availability": ["recently", "last week", "just happened"],
    "sunk_cost": ["we already invested", "we've spent", "can't waste"],
    "optimism": ["definitely work", "no way it fails", "easy win"],
    "anchoring": [],
}


def extract_ideas(text: str) -> List[str]:
    """Extract potential idea statements from a message.

    This naive implementation splits the text into sentences and returns them.
    """
    return [sent.strip() for sent in re.split(r"[.?!]\s+", text) if sent.strip()]


def score_quality(idea: str, problem_statement: str = "") -> float:
    """Compute a quality score (0-1) for an idea.

    This placeholder implementation uses simple heuristics based on length and
    presence of numeric tokens. Replace with more sophisticated analysis.
    """
    length_score = min(len(idea) / 100, 1.0)
    specificity = 1.0 if any(char.isdigit() for char in idea) else 0.5
    evidence = 0.5
    novelty = 0.5
    relevance = 0.5
    depth = length_score
    weighted = (
        QUALITY_WEIGHTS["specificity"] * specificity
        + QUALITY_WEIGHTS["evidence"] * evidence
        + QUALITY_WEIGHTS["novelty"] * novelty
        + QUALITY_WEIGHTS["relevance"] * relevance
        + QUALITY_WEIGHTS["depth"] * depth
    )
    return round(weighted, 2)


def parse_narrative_elements(text: str) -> Dict[str, List[str]]:
    """Parse narrative elements from the message using regex patterns."""
    elements: Dict[str, List[str]] = {}
    for key, pattern in NARRATIVE_PATTERNS.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        elements[key] = matches
    return elements


def detect_biases(text: str) -> Dict[str, List[str]]:
    """Detect known cognitive biases in the message."""
    biases: Dict[str, List[str]] = {}
    lowered = text.lower()
    for bias, markers in BIAS_SIGNALS.items():
        found = [m for m in markers if m in lowered]
        if found:
            biases[bias] = found
    return biases