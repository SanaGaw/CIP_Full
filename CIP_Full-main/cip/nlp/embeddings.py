"""Lightweight embedding utilities.

By default, this avoids downloading sentence-transformer models during a live pilot.
Set ENABLE_EMBEDDINGS=True to enable the heavier model.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None  # type: ignore


@lru_cache()
def _get_model():
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers not installed")
    return SentenceTransformer("all-MiniLM-L6-v2")


def _hash_embedding(text: str, dim: int = 384) -> np.ndarray:
    vec = np.zeros(dim, dtype=float)
    words = [w.lower() for w in text.split() if w.strip()]
    for word in words:
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def embed(text: str) -> np.ndarray:
    if os.getenv("ENABLE_EMBEDDINGS", "False").lower() not in {"1", "true", "yes"}:
        return _hash_embedding(text)
    if SentenceTransformer is None:
        return _hash_embedding(text)
    try:
        model = _get_model()
        vecs = model.encode([text])
        return vecs[0]
    except Exception:
        return _hash_embedding(text)
