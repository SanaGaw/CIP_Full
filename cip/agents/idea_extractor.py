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

def _compute_specificity(text: str) -> float:
    """Compute specificity score (0-1) based on concrete details in text."""
    specificity = 0.0
    if any(c.isdigit() for c in text):
        specificity += 0.4
    if re.search(r"\b(weeks?|months?|years?|days?|hours?|%|€|\$)", text, re.I):
        specificity += 0.3
    if re.search(r"\b[A-Z][a-z]+\b", text):
        specificity += 0.3
    return min(1.0, specificity)


def _compute_evidence(text: str) -> float:
    """Compute evidence score (0-1) based on causal/factual markers."""
    evidence = 0.0
    if re.search(r"\b(because|since|due to|caused by|leads to|results in)\b", text, re.I):
        evidence += 0.5
    if re.search(r"\b(measured|observed|reported|data shows|according to)\b", text, re.I):
        evidence += 0.5
    return min(1.0, evidence)

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


def score_quality(idea: str, problem_statement: str = "", existing_clusters: List[Dict] = None) -> float:
    """Compute a quality score (0-1) for an idea.

    Computes all 5 dimensions: specificity, evidence, novelty, relevance, depth.
    Uses embeddings for novelty (cosine distance to cluster centroids) and relevance
    (similarity to problem statement).
    """
    from ..nlp.embeddings import embed

    # specificity: use helper function
    spec = _compute_specificity(idea)

    # evidence: use helper function
    evidence = _compute_evidence(idea)

    # novelty: cosine distance to nearest cluster centroid
    nov = 0.5
    if existing_clusters:
        try:
            emb = embed(idea)
            sims = []
            for c in existing_clusters:
                if c.get("centroid") is not None:
                    centroid = np.array(c["centroid"])
                    norm_emb = np.linalg.norm(emb)
                    norm_cent = np.linalg.norm(centroid)
                    if norm_emb > 0 and norm_cent > 0:
                        sim = float(np.dot(emb, centroid) / (norm_emb * norm_cent))
                        sims.append(sim)
            if sims:
                nov = 1.0 - max(sims)
        except Exception:
            nov = 0.5

    # relevance: similarity to problem statement
    rel = 0.5
    if problem_statement:
        try:
            e1 = embed(idea)
            e2 = embed(problem_statement)
            norm1 = np.linalg.norm(e1)
            norm2 = np.linalg.norm(e2)
            if norm1 > 0 and norm2 > 0:
                rel = float(np.dot(e1, e2) / (norm1 * norm2))
                rel = max(0.0, min(1.0, rel))
        except Exception:
            rel = 0.5

    # depth: word count + clause count
    words = len(idea.split())
    clauses = len(re.split(r"[,;:]|\b(and|but|because|while|although)\b", idea))
    depth = min(1.0, (words / 30) * 0.6 + (clauses / 4) * 0.4)

    # weighted sum
    score = (
        QUALITY_WEIGHTS["specificity"] * spec
        + QUALITY_WEIGHTS["evidence"] * evidence
        + QUALITY_WEIGHTS["novelty"] * nov
        + QUALITY_WEIGHTS["relevance"] * rel
        + QUALITY_WEIGHTS["depth"] * depth
    )
    return round(score, 3)


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