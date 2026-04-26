"""Diversity metrics for idea distributions.

Compute the Shannon entropy of a cluster distribution to measure diversity.
"""
from __future__ import annotations

from math import log
from typing import List


def compute_diversity(ideas: List[str]) -> float:
    """Compute a diversity score between 0 and 1 for a list of ideas.

    A higher score indicates a more even distribution across clusters.
    """
    n = len(ideas)
    if n == 0:
        return 0.0
    # Simple uniform distribution assumption: each idea is its own cluster
    # Real implementation should use cluster assignments.
    probs = [1 / n] * n
    entropy = -sum(p * log(p, 2) for p in probs)
    max_entropy = log(n, 2)
    return entropy / max_entropy if max_entropy > 0 else 0.0