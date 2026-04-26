"""Clustering utilities for CIP.

This module groups similar ideas into clusters using Agglomerative
Clustering on cosine distances between embeddings. A threshold controls
the distance at which clusters merge.
"""
from __future__ import annotations

from typing import List, Dict

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from .embeddings import embed


def cluster_ideas(ideas: List[Dict], threshold: float = 0.65) -> List[List[int]]:
    """Cluster ideas by semantic similarity.

    Args:
        ideas: A list of idea dicts, each expected to have a 'text' key.
        threshold: Cosine similarity threshold for cluster formation.

    Returns:
        A list of clusters, each containing indices into the input list.
    """
    if not ideas:
        return []
    # Compute embeddings
    vectors = np.stack([embed(idea.get("text", "")) for idea in ideas])
    # Convert similarity threshold to distance threshold
    distance_threshold = 1 - threshold
    clusterer = AgglomerativeClustering(
        affinity="cosine",
        linkage="average",
        distance_threshold=distance_threshold,
        n_clusters=None,
    )
    labels = clusterer.fit_predict(vectors)
    clusters: Dict[int, List[int]] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(idx)
    return list(clusters.values())