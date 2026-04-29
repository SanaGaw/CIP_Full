"""Diversity metrics for idea distributions.

Compute the Shannon entropy of a cluster distribution to measure diversity,
using real cluster assignments for accurate diversity scoring.
"""
from __future__ import annotations

from math import log
from typing import Dict, List, Any


def compute_diversity(ideas: List[Dict[str, Any]], clusters: List[Dict[str, Any]] = None) -> float:
    """Compute a diversity score between 0 and 1 for a list of ideas.

    Uses real cluster assignments to compute Shannon entropy.
    A higher score indicates a more even distribution across clusters.

    Args:
        ideas: List of idea dictionaries with cluster assignments.
        clusters: Optional list of cluster information for cluster-based diversity.

    Returns:
        Diversity score between 0 and 1.
    """
    n = len(ideas)
    if n == 0:
        return 0.0

    if clusters:
        # Use real cluster assignments from the cluster parameter
        cluster_counts: Dict[int, int] = {}
        for idea in ideas:
            cluster_id = idea.get("cluster_id")
            if cluster_id is not None:
                cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1

        # Compute probabilities from actual cluster distribution
        if cluster_counts:
            probs = [count / n for count in cluster_counts.values()]
            entropy = -sum(p * log(p, 2) for p in probs if p > 0)
            max_entropy = log(len(cluster_counts), 2) if len(cluster_counts) > 1 else 1.0
            return entropy / max_entropy if max_entropy > 0 else 0.0

    # Fallback to theme-based diversity if cluster assignments not available
    themes: Dict[str, int] = {}
    for idea in ideas:
        theme = idea.get("theme", "general")
        themes[theme] = themes.get(theme, 0) + 1

    if themes:
        probs = [count / n for count in themes.values()]
        entropy = -sum(p * log(p, 2) for p in probs if p > 0)
        max_entropy = log(len(themes), 2) if len(themes) > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    # If no cluster assignments available, assume uniform distribution
    probs = [1 / n] * n
    entropy = -sum(p * log(p, 2) for p in probs)
    max_entropy = log(n, 2)
    return entropy / max_entropy if max_entropy > 0 else 0.0
