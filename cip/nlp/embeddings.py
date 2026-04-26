"""Embedding utilities for CIP.

This module wraps the sentence-transformers model to compute vector embeddings
for text. To avoid heavy initialisation during import, the model is loaded
lazily on first use.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore


@lru_cache()
def _get_model():
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers not installed")
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed(text: str) -> np.ndarray:
    """Compute an embedding for the given text.

    If the underlying model is not available, returns a zero vector.
    """
    if SentenceTransformer is None:
        return np.zeros(384, dtype=float)
    model = _get_model()
    vecs = model.encode([text])
    return vecs[0]